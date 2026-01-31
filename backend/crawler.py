"""
Smart Battle Crawler for BrawlGPT.
Analyzes battle logs to extract meta statistics with real win rates.
"""

import logging
import asyncio
from typing import Any, Optional
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from brawlstars import BrawlStarsClient
from cache import cache
from db_models import MetaSnapshot, BrawlerMeta, PlayerHistory

logger = logging.getLogger(__name__)


@dataclass
class BrawlerPerformance:
    """Performance statistics for a single brawler."""
    brawler_id: int
    brawler_name: str
    total_games: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0
    trophy_changes: list[int] = field(default_factory=list)
    modes: dict[str, dict] = field(default_factory=lambda: defaultdict(lambda: {"wins": 0, "games": 0}))
    maps: dict[str, dict] = field(default_factory=lambda: defaultdict(lambda: {"wins": 0, "games": 0}))

    @property
    def win_rate(self) -> float:
        """Calculate win rate percentage."""
        if self.total_games == 0:
            return 0.0
        return (self.wins / self.total_games) * 100

    @property
    def avg_trophy_change(self) -> float:
        """Calculate average trophy change per game."""
        if not self.trophy_changes:
            return 0.0
        return sum(self.trophy_changes) / len(self.trophy_changes)

    def get_best_modes(self, min_games: int = 3) -> list[dict]:
        """Get best performing modes with minimum game threshold."""
        mode_stats = []
        for mode, stats in self.modes.items():
            if stats["games"] >= min_games:
                win_rate = (stats["wins"] / stats["games"]) * 100
                mode_stats.append({
                    "mode": mode,
                    "win_rate": round(win_rate, 1),
                    "games": stats["games"]
                })
        return sorted(mode_stats, key=lambda x: x["win_rate"], reverse=True)[:5]

    def get_best_maps(self, min_games: int = 2) -> list[dict]:
        """Get best performing maps with minimum game threshold."""
        map_stats = []
        for map_name, stats in self.maps.items():
            if stats["games"] >= min_games:
                win_rate = (stats["wins"] / stats["games"]) * 100
                map_stats.append({
                    "map": map_name,
                    "win_rate": round(win_rate, 1),
                    "games": stats["games"]
                })
        return sorted(map_stats, key=lambda x: x["win_rate"], reverse=True)[:5]


@dataclass
class TeamComposition:
    """Statistics for a team composition."""
    brawlers: tuple[str, str, str]
    wins: int = 0
    games: int = 0
    modes: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    @property
    def win_rate(self) -> float:
        if self.games == 0:
            return 0.0
        return (self.wins / self.games) * 100


class SmartBattleCrawler:
    """
    Smart crawler that analyzes battle logs to extract real win rates
    and meta statistics with support for deep crawling.
    """

    # Trophy ranges for meta analysis
    TROPHY_RANGES = [
        (0, 5000),
        (5000, 10000),
        (10000, 20000),
        (20000, 30000),
        (30000, 50000),
        (50000, 100000),
    ]
    
    # Mapping for internal/beta brawler names to display names or cleanup
    BRAWLER_NAME_MAPPING = {
        "Trunk": "Unknown (Beta)",
        "Pierce": "Unknown (Beta)",
        "Alli": "Unknown (Beta)",
        "Gigi": "Unknown (Beta)",
        "Hook": "Gene",  # Example of known internal names
        "Sniper": "Bea",
    }

    def __init__(self, client: BrawlStarsClient):
        self.client = client
        self.visited_players: set[str] = set()

    def _get_trophy_range(self, trophies: int) -> tuple[int, int]:
        """Determine which trophy range a player belongs to."""
        for low, high in self.TROPHY_RANGES:
            if low <= trophies < high:
                return (low, high)
        return (50000, 100000)  # Default to highest range

    async def crawl_battle_log(
        self,
        player_tag: str,
        depth: int = 2
    ) -> dict[str, Any]:
        """
        Analyze a single player's battle log (Legacy/Simple mode).
        
        Args:
            player_tag: The player to analyze
            depth: How deep to crawl networks (default 2)
            
        Returns:
            Dictionary with simple analysis results
        """
        logger.info(f"Crawling battle log for {player_tag} with depth {depth}")
        
        # Get battle log
        clean_tag = BrawlStarsClient.validate_tag(player_tag)
        battle_log = cache.get_battle_log(clean_tag)
        if not battle_log:
            battle_log = self.client.get_battle_log(clean_tag)
            cache.set_battle_log(clean_tag, battle_log)
            
        if not battle_log or "items" not in battle_log:
            return {"error": "No battles found"}

        # Basic analysis using existing methods
        brawler_stats = {}
        # Simple analysis of the player's own battles
        self._analyze_battles(
            clean_tag, 
            battle_log["items"], 
            brawler_stats, 
            {}
        )
        
        # Format for response
        total_games = sum(s.total_games for s in brawler_stats.values())
        most_popular = []
        
        for name, stats in brawler_stats.items():
            freq = (stats.total_games / total_games * 100) if total_games > 0 else 0
            most_popular.append({
                "name": name,
                "count": stats.total_games,
                "frequency": f"{freq:.1f}%",
                "win_rate": stats.win_rate
            })
            
        # Sort by count descending
        most_popular.sort(key=lambda x: x["count"], reverse=True)

        return {
            "player_tag": player_tag,
            "analyzed_matches": len(battle_log["items"]),
            "most_popular_brawlers": most_popular,
            "win_rate": sum(s.wins for s in brawler_stats.values()) / sum(s.total_games for s in brawler_stats.values()) * 100 if brawler_stats else 0
        }

    async def crawl_meta(
        self,
        seed_players: list[str],
        trophy_range: tuple[int, int],
        depth: int = 2,
        max_players: int = 100,
        db: Optional[AsyncSession] = None
    ) -> dict[str, Any]:
        """
        Crawl battle logs starting from seed players to build meta statistics.

        Args:
            seed_players: Initial player tags to start crawling from
            trophy_range: (min, max) trophy range to focus on
            depth: How deep to crawl (1 = only seeds, 2 = + their teammates)
            max_players: Maximum number of unique players to analyze
            db: Optional database session to save results

        Returns:
            Dictionary containing aggregated meta statistics
        """
        logger.info(f"Starting meta crawl for trophy range {trophy_range} with {len(seed_players)} seeds")

        self.visited_players.clear()
        brawler_stats: dict[str, BrawlerPerformance] = {}
        team_comps: dict[tuple, TeamComposition] = {}
        total_battles = 0

        # Queue of players to process: (tag, current_depth)
        player_queue = [(tag, 1) for tag in seed_players]

        while player_queue and len(self.visited_players) < max_players:
            player_tag, current_depth = player_queue.pop(0)

            # Skip if already visited
            try:
                clean_tag = BrawlStarsClient.validate_tag(player_tag)
            except Exception:
                continue

            if clean_tag in self.visited_players:
                continue

            self.visited_players.add(clean_tag)

            try:
                # Get player data to check trophy range
                player_data = cache.get_player(clean_tag)
                if not player_data:
                    player_data = self.client.get_player(clean_tag)
                    cache.set_player(clean_tag, player_data)

                player_trophies = player_data.get("trophies", 0)

                # Skip if not in target trophy range
                if not (trophy_range[0] <= player_trophies < trophy_range[1]):
                    logger.debug(f"Skipping {clean_tag}: {player_trophies} trophies not in range")
                    continue

                # Get battle log
                battle_log = cache.get_battle_log(clean_tag)
                if not battle_log:
                    battle_log = self.client.get_battle_log(clean_tag)
                    cache.set_battle_log(clean_tag, battle_log)

                if not battle_log or "items" not in battle_log:
                    continue

                # Analyze battles
                new_players = self._analyze_battles(
                    clean_tag,
                    battle_log["items"],
                    brawler_stats,
                    team_comps
                )
                total_battles += len(battle_log["items"])

                # Add new players to queue if we haven't reached max depth
                if current_depth < depth:
                    for new_tag in new_players:
                        if new_tag not in self.visited_players:
                            player_queue.append((new_tag, current_depth + 1))

                # Small delay to respect rate limits
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.warning(f"Error processing player {player_tag}: {e}")
                continue

        # Compile results
        meta_report = self._compile_meta_report(brawler_stats, team_comps, total_battles)

        # Save to database if session provided
        if db:
            await self._save_meta_snapshot(db, trophy_range, meta_report, brawler_stats)

        logger.info(f"Meta crawl complete. Analyzed {len(self.visited_players)} players, {total_battles} battles")

        return meta_report

    def _analyze_battles(
        self,
        player_tag: str,
        battles: list[dict],
        brawler_stats: dict[str, BrawlerPerformance],
        team_comps: dict[tuple, TeamComposition]
    ) -> set[str]:
        """
        Analyze a player's battles and update statistics.

        Returns set of teammate tags discovered.
        """
        discovered_players: set[str] = set()

        for battle_item in battles:
            battle = battle_item.get("battle", {})
            event = battle_item.get("event", {})

            mode = event.get("mode", "unknown")
            map_name = event.get("map", "unknown")
            result = battle.get("result")
            trophy_change = battle.get("trophyChange")

            # Find the player's team and determine if they won
            my_team = []
            opponent_team = []
            is_victory = result == "victory"
            is_defeat = result == "defeat"

            if "teams" in battle:
                # 3v3 modes
                for team in battle["teams"]:
                    player_in_team = any(
                        p.get("tag", "").upper().replace("#", "") == player_tag
                        for p in team
                    )
                    if player_in_team:
                        my_team = team
                    else:
                        opponent_team = team

            elif "players" in battle:
                # Solo/Duo Showdown - different logic
                # For Showdown, we can only analyze the player's own brawler
                for p in battle["players"]:
                    if p.get("tag", "").upper().replace("#", "") == player_tag:
                        brawler = p.get("brawler", {})
                        brawler_name = brawler.get("name", "Unknown")
                        brawler_id = brawler.get("id", 0)


                        # Normalize name
                        if brawler_name in self.BRAWLER_NAME_MAPPING:
                            brawler_name = self.BRAWLER_NAME_MAPPING[brawler_name]

                        if brawler_name not in brawler_stats:
                            brawler_stats[brawler_name] = BrawlerPerformance(
                                brawler_id=brawler_id,
                                brawler_name=brawler_name
                            )

                        stats = brawler_stats[brawler_name]
                        stats.total_games += 1

                        rank = battle.get("rank", 10)
                        if rank <= 4:  # Top 4 in Showdown = win
                            stats.wins += 1
                            stats.modes[mode]["wins"] += 1
                            stats.maps[map_name]["wins"] += 1
                        else:
                            stats.losses += 1

                        stats.modes[mode]["games"] += 1
                        stats.maps[map_name]["games"] += 1

                        if trophy_change is not None:
                            stats.trophy_changes.append(trophy_change)
                continue

            # Process 3v3 team battles
            if my_team:
                # Update brawler stats for all players in my team
                for p in my_team:
                    brawler = p.get("brawler", {})
                    brawler_name = brawler.get("name", "Unknown")
                    brawler_id = brawler.get("id", 0)
                    p_tag = p.get("tag", "").upper().replace("#", "")

                    # Discover teammates
                    if p_tag and p_tag != player_tag:
                        discovered_players.add(p_tag)
                    
                    # Normalize name
                    if brawler_name in self.BRAWLER_NAME_MAPPING:
                        brawler_name = self.BRAWLER_NAME_MAPPING[brawler_name]

                    if brawler_name not in brawler_stats:
                        brawler_stats[brawler_name] = BrawlerPerformance(
                            brawler_id=brawler_id,
                            brawler_name=brawler_name
                        )

                    stats = brawler_stats[brawler_name]
                    stats.total_games += 1

                    if is_victory:
                        stats.wins += 1
                        stats.modes[mode]["wins"] += 1
                        stats.maps[map_name]["wins"] += 1
                    elif is_defeat:
                        stats.losses += 1
                    else:
                        stats.draws += 1

                    stats.modes[mode]["games"] += 1
                    stats.maps[map_name]["games"] += 1

                    # Only add trophy change for the main player
                    if p_tag == player_tag and trophy_change is not None:
                        stats.trophy_changes.append(trophy_change)

                # Track team composition (3v3 only)
                if len(my_team) == 3:
                    comp = tuple(sorted([
                        p.get("brawler", {}).get("name", "Unknown")
                        for p in my_team
                    ]))

                    if comp not in team_comps:
                        team_comps[comp] = TeamComposition(brawlers=comp)

                    team_comps[comp].games += 1
                    team_comps[comp].modes[mode] += 1
                    if is_victory:
                        team_comps[comp].wins += 1

        return discovered_players

    def _compile_meta_report(
        self,
        brawler_stats: dict[str, BrawlerPerformance],
        team_comps: dict[tuple, TeamComposition],
        total_battles: int
    ) -> dict[str, Any]:
        """Compile statistics into a meta report."""

        # Calculate total games across all brawlers
        total_brawler_appearances = sum(s.total_games for s in brawler_stats.values())

        # Brawler rankings
        brawler_rankings = []
        for name, stats in brawler_stats.items():
            if stats.total_games >= 5:  # Minimum games threshold
                pick_rate = (stats.total_games / total_brawler_appearances * 100) if total_brawler_appearances > 0 else 0
                brawler_rankings.append({
                    "brawler_id": stats.brawler_id,
                    "name": name,
                    "games": stats.total_games,
                    "pick_rate": round(pick_rate, 2),
                    "win_rate": round(stats.win_rate, 2),
                    "avg_trophy_change": round(stats.avg_trophy_change, 1),
                    "best_modes": stats.get_best_modes(),
                    "best_maps": stats.get_best_maps(),
                })

        # Sort by win rate (with pick rate as tiebreaker)
        brawler_rankings.sort(key=lambda x: (x["win_rate"], x["pick_rate"]), reverse=True)

        # Top team compositions
        top_comps = []
        for comp, stats in team_comps.items():
            if stats.games >= 3:  # Minimum games threshold
                top_comps.append({
                    "brawlers": list(comp),
                    "games": stats.games,
                    "win_rate": round(stats.win_rate, 2),
                    "modes": dict(stats.modes),
                })

        top_comps.sort(key=lambda x: (x["win_rate"], x["games"]), reverse=True)

        # Identify tier list
        tier_s = [b for b in brawler_rankings if b["win_rate"] >= 55 and b["pick_rate"] >= 3][:5]
        tier_a = [b for b in brawler_rankings if 50 <= b["win_rate"] < 55 and b["pick_rate"] >= 2][:8]
        tier_b = [b for b in brawler_rankings if 45 <= b["win_rate"] < 50][:10]

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "sample_size": {
                "players": len(self.visited_players),
                "battles": total_battles,
                "brawler_appearances": total_brawler_appearances,
            },
            "tier_list": {
                "S": [b["name"] for b in tier_s],
                "A": [b["name"] for b in tier_a],
                "B": [b["name"] for b in tier_b],
            },
            "brawler_rankings": brawler_rankings[:20],  # Top 20
            "top_compositions": top_comps[:10],  # Top 10
            "mode_meta": self._compile_mode_meta(brawler_stats),
        }

    def _compile_mode_meta(self, brawler_stats: dict[str, BrawlerPerformance]) -> dict[str, list]:
        """Compile best brawlers per game mode."""
        mode_stats: dict[str, list] = defaultdict(list)

        for name, stats in brawler_stats.items():
            for mode, mode_data in stats.modes.items():
                if mode_data["games"] >= 3:
                    win_rate = (mode_data["wins"] / mode_data["games"]) * 100
                    mode_stats[mode].append({
                        "name": name,
                        "win_rate": round(win_rate, 2),
                        "games": mode_data["games"],
                    })

        # Sort each mode by win rate and keep top 5
        for mode in mode_stats:
            mode_stats[mode].sort(key=lambda x: x["win_rate"], reverse=True)
            mode_stats[mode] = mode_stats[mode][:5]

        return dict(mode_stats)

    async def _save_meta_snapshot(
        self,
        db: AsyncSession,
        trophy_range: tuple[int, int],
        meta_report: dict[str, Any],
        brawler_stats: dict[str, BrawlerPerformance]
    ):
        """Save meta snapshot to database."""
        try:
            # Create snapshot
            snapshot = MetaSnapshot(
                timestamp=datetime.utcnow(),
                trophy_range_min=trophy_range[0],
                trophy_range_max=trophy_range[1],
                sample_size=meta_report["sample_size"]["battles"],
                data={
                    "tier_list": meta_report["tier_list"],
                    "top_compositions": meta_report["top_compositions"],
                    "mode_meta": meta_report["mode_meta"],
                }
            )
            db.add(snapshot)
            await db.flush()  # Get the snapshot ID

            # Add brawler stats
            for name, stats in brawler_stats.items():
                if stats.total_games >= 5:
                    total_appearances = sum(s.total_games for s in brawler_stats.values())
                    pick_rate = (stats.total_games / total_appearances * 100) if total_appearances > 0 else 0

                    brawler_meta = BrawlerMeta(
                        snapshot_id=snapshot.id,
                        brawler_id=stats.brawler_id,
                        brawler_name=name,
                        pick_rate=round(pick_rate, 2),
                        win_rate=round(stats.win_rate, 2),
                        avg_trophies_change=round(stats.avg_trophy_change, 1),
                        best_modes=stats.get_best_modes(),
                        best_maps=stats.get_best_maps(),
                    )
                    db.add(brawler_meta)

            await db.commit()
            logger.info(f"Saved meta snapshot ID {snapshot.id} to database")

        except Exception as e:
            logger.error(f"Failed to save meta snapshot: {e}")
            await db.rollback()

    async def analyze_brawler_performance(
        self,
        battles: list[dict],
        brawler_name: str,
        player_tag: str
    ) -> Optional[BrawlerPerformance]:
        """
        Analyze performance of a specific brawler for a player.

        Args:
            battles: List of battle items
            brawler_name: Name of the brawler to analyze
            player_tag: Player's tag

        Returns:
            BrawlerPerformance object or None if not found
        """
        stats = BrawlerPerformance(brawler_id=0, brawler_name=brawler_name)
        clean_tag = player_tag.upper().replace("#", "")

        for battle_item in battles:
            battle = battle_item.get("battle", {})
            event = battle_item.get("event", {})
            mode = event.get("mode", "unknown")
            map_name = event.get("map", "unknown")
            result = battle.get("result")
            trophy_change = battle.get("trophyChange")

            # Find player's brawler in this battle
            player_brawler = None

            if "teams" in battle:
                for team in battle["teams"]:
                    for p in team:
                        if p.get("tag", "").upper().replace("#", "") == clean_tag:
                            player_brawler = p.get("brawler", {})
                            break
                    if player_brawler:
                        break
            elif "players" in battle:
                for p in battle["players"]:
                    if p.get("tag", "").upper().replace("#", "") == clean_tag:
                        player_brawler = p.get("brawler", {})
                        break

            if not player_brawler or player_brawler.get("name") != brawler_name:
                continue

            stats.brawler_id = player_brawler.get("id", 0)
            stats.total_games += 1

            if result == "victory" or (battle.get("rank", 10) <= 4):
                stats.wins += 1
                stats.modes[mode]["wins"] += 1
                stats.maps[map_name]["wins"] += 1
            elif result == "defeat":
                stats.losses += 1
            else:
                stats.draws += 1

            stats.modes[mode]["games"] += 1
            stats.maps[map_name]["games"] += 1

            if trophy_change is not None:
                stats.trophy_changes.append(trophy_change)

        return stats if stats.total_games > 0 else None

    async def get_trending_compositions(
        self,
        battles: list[dict],
        player_tag: str,
        min_games: int = 2
    ) -> list[dict]:
        """
        Identify trending team compositions from battles.

        Returns list of compositions with win rates.
        """
        comps: dict[tuple, TeamComposition] = {}
        clean_tag = player_tag.upper().replace("#", "")

        for battle_item in battles:
            battle = battle_item.get("battle", {})
            event = battle_item.get("event", {})
            mode = event.get("mode", "unknown")
            result = battle.get("result")

            if "teams" not in battle:
                continue

            for team in battle["teams"]:
                player_in_team = any(
                    p.get("tag", "").upper().replace("#", "") == clean_tag
                    for p in team
                )

                if player_in_team and len(team) == 3:
                    comp = tuple(sorted([
                        p.get("brawler", {}).get("name", "Unknown")
                        for p in team
                    ]))

                    if comp not in comps:
                        comps[comp] = TeamComposition(brawlers=comp)

                    comps[comp].games += 1
                    comps[comp].modes[mode] += 1
                    if result == "victory":
                        comps[comp].wins += 1

        # Format and filter results
        results = []
        for comp, stats in comps.items():
            if stats.games >= min_games:
                results.append({
                    "brawlers": list(comp),
                    "games": stats.games,
                    "win_rate": round(stats.win_rate, 2),
                    "best_mode": max(stats.modes.items(), key=lambda x: x[1])[0] if stats.modes else None,
                })

        results.sort(key=lambda x: (x["win_rate"], x["games"]), reverse=True)
        return results[:10]


# Legacy compatibility - keep BattleCrawler as alias
BattleCrawler = SmartBattleCrawler
