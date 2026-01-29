"""
Counter-Pick Service for BrawlGPT.
Analyzes matchup data to provide counter-pick recommendations.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Any
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

logger = logging.getLogger(__name__)


@dataclass
class CounterPick:
    """Represents a counter-pick recommendation."""
    brawler_id: int
    brawler_name: str
    win_rate_against: float  # Win rate when picking this brawler against the target
    pick_rate: float
    sample_size: int
    confidence: str  # "low", "medium", "high"
    best_modes: list[str] = field(default_factory=list)
    reasoning: Optional[str] = None

    @property
    def is_reliable(self) -> bool:
        """Check if this counter-pick has enough data to be reliable."""
        return self.sample_size >= 50 and self.confidence != "low"


@dataclass
class TeamCounterAnalysis:
    """Analysis of counters for an entire enemy team."""
    enemy_team: list[str]
    recommended_counters: list[CounterPick]
    team_synergy_counters: list[dict[str, Any]]  # Brawlers that counter multiple enemies
    weaknesses: list[str]  # What the enemy team is weak against
    strengths: list[str]  # What the enemy team is strong against
    overall_strategy: str
    confidence_score: float


class CounterPickService:
    """
    Service for generating counter-pick recommendations.

    Uses battle log data to build a matchup matrix and provide
    data-driven counter-pick suggestions.

    Usage:
        service = CounterPickService()

        # Get counters for a single brawler
        counters = await service.get_counters(db, brawler_id=123, mode="gemGrab")

        # Analyze enemy team
        analysis = await service.analyze_enemy_team(
            db,
            enemy_brawlers=["Shelly", "Colt", "Brock"]
        )
    """

    # Brawler archetypes for strategic analysis
    ARCHETYPES = {
        "tank": ["Bull", "El Primo", "Rosa", "Darryl", "Jacky", "Frank", "Bibi", "Ash"],
        "assassin": ["Mortis", "Leon", "Crow", "Edgar", "Buzz", "Fang", "Mico"],
        "sharpshooter": ["Colt", "Brock", "Piper", "Bea", "Belle", "Mandy", "Angelo"],
        "thrower": ["Dynamike", "Barley", "Tick", "Sprout", "Grom", "Larry & Lawrie"],
        "support": ["Poco", "Pam", "Byron", "Ruffs", "Max", "Gene", "Doug"],
        "controller": ["Spike", "Crow", "Sandy", "Emz", "Lou", "Gale", "Squeak"],
        "damage_dealer": ["Shelly", "Nita", "Jessie", "Penny", "8-Bit", "Rico", "Carl"],
    }

    # Mode-specific counter weights
    MODE_WEIGHTS = {
        "gemGrab": {"support": 1.3, "controller": 1.2, "assassin": 0.9},
        "brawlBall": {"tank": 1.3, "assassin": 1.2, "sharpshooter": 0.8},
        "heist": {"sharpshooter": 1.3, "thrower": 1.2, "tank": 1.0},
        "bounty": {"sharpshooter": 1.4, "assassin": 0.7, "tank": 0.6},
        "hotZone": {"controller": 1.3, "tank": 1.2, "thrower": 1.1},
        "knockout": {"sharpshooter": 1.2, "support": 1.1, "tank": 0.9},
    }

    def __init__(self):
        self._matchup_cache: dict[tuple[int, int], dict] = {}

    def _get_brawler_archetype(self, brawler_name: str) -> Optional[str]:
        """Get the archetype of a brawler."""
        for archetype, brawlers in self.ARCHETYPES.items():
            if brawler_name in brawlers:
                return archetype
        return None

    def _calculate_confidence(self, sample_size: int) -> str:
        """Calculate confidence level based on sample size."""
        if sample_size >= 200:
            return "high"
        elif sample_size >= 50:
            return "medium"
        return "low"

    async def get_counters(
        self,
        db: AsyncSession,
        brawler_id: int,
        mode: Optional[str] = None,
        limit: int = 10,
        min_sample_size: int = 20
    ) -> list[CounterPick]:
        """
        Get counter-picks for a specific brawler.

        Args:
            db: Database session
            brawler_id: ID of the brawler to counter
            mode: Optional game mode filter
            limit: Maximum number of counters to return
            min_sample_size: Minimum sample size for reliable data

        Returns:
            List of counter-pick recommendations sorted by effectiveness
        """
        try:
            # Import here to avoid circular imports
            from db_models import BrawlerMatchup, BrawlerMeta

            # Build query for matchup data
            query = select(BrawlerMatchup).where(
                BrawlerMatchup.brawler_b_id == brawler_id,
                BrawlerMatchup.sample_size >= min_sample_size
            )

            if mode:
                query = query.where(BrawlerMatchup.mode == mode)

            query = query.order_by(BrawlerMatchup.win_rate_a_vs_b.desc()).limit(limit * 2)

            result = await db.execute(query)
            matchups = result.scalars().all()

            counters = []
            for matchup in matchups:
                # Get additional brawler meta info
                meta_query = select(BrawlerMeta).where(
                    BrawlerMeta.brawler_id == matchup.brawler_a_id
                ).order_by(BrawlerMeta.snapshot_id.desc()).limit(1)

                meta_result = await db.execute(meta_query)
                meta = meta_result.scalar_one_or_none()

                counter = CounterPick(
                    brawler_id=matchup.brawler_a_id,
                    brawler_name=matchup.brawler_a_name,
                    win_rate_against=matchup.win_rate_a_vs_b,
                    pick_rate=meta.pick_rate if meta else 0.0,
                    sample_size=matchup.sample_size,
                    confidence=self._calculate_confidence(matchup.sample_size),
                    best_modes=meta.best_modes[:3] if meta and meta.best_modes else [],
                )
                counters.append(counter)

            # Sort by win rate and filter
            counters.sort(key=lambda x: x.win_rate_against, reverse=True)
            return counters[:limit]

        except Exception as e:
            logger.error(f"Error getting counters for brawler {brawler_id}: {e}")
            return []

    async def analyze_enemy_team(
        self,
        db: AsyncSession,
        enemy_brawlers: list[str],
        mode: Optional[str] = None,
        available_brawlers: Optional[list[str]] = None
    ) -> TeamCounterAnalysis:
        """
        Analyze an enemy team and suggest counter strategies.

        Args:
            db: Database session
            enemy_brawlers: List of enemy brawler names
            mode: Game mode
            available_brawlers: Optional list of brawlers the player has

        Returns:
            Complete team counter analysis
        """
        try:
            # Import here to avoid circular imports
            from db_models import BrawlerMatchup

            # Analyze each enemy brawler
            enemy_archetypes = []
            all_counters: dict[str, list[float]] = defaultdict(list)

            for enemy_name in enemy_brawlers:
                archetype = self._get_brawler_archetype(enemy_name)
                if archetype:
                    enemy_archetypes.append(archetype)

                # Get counters for this enemy
                # First, find the brawler ID
                query = select(BrawlerMatchup.brawler_b_id).where(
                    func.lower(BrawlerMatchup.brawler_b_name) == enemy_name.lower()
                ).limit(1)
                result = await db.execute(query)
                brawler_id_row = result.first()

                if brawler_id_row:
                    counters = await self.get_counters(
                        db, brawler_id_row[0], mode=mode, limit=15
                    )
                    for counter in counters:
                        all_counters[counter.brawler_name].append(counter.win_rate_against)

            # Find brawlers that counter multiple enemies (synergy counters)
            synergy_counters = []
            for brawler_name, win_rates in all_counters.items():
                if len(win_rates) >= 2:  # Counters at least 2 enemies
                    avg_win_rate = sum(win_rates) / len(win_rates)
                    synergy_counters.append({
                        "brawler": brawler_name,
                        "counters_count": len(win_rates),
                        "avg_win_rate": round(avg_win_rate, 1),
                        "effectiveness": "high" if avg_win_rate > 55 and len(win_rates) >= 2 else "medium"
                    })

            synergy_counters.sort(key=lambda x: (x["counters_count"], x["avg_win_rate"]), reverse=True)

            # Determine team weaknesses and strengths
            weaknesses = self._analyze_team_weaknesses(enemy_archetypes)
            strengths = self._analyze_team_strengths(enemy_archetypes)

            # Generate overall strategy
            strategy = self._generate_team_strategy(enemy_archetypes, mode)

            # Get top recommended counters
            recommended = []
            for synergy in synergy_counters[:5]:
                # Get full counter info
                query = select(BrawlerMatchup).where(
                    func.lower(BrawlerMatchup.brawler_a_name) == synergy["brawler"].lower()
                ).limit(1)
                result = await db.execute(query)
                matchup = result.scalar_one_or_none()

                if matchup:
                    recommended.append(CounterPick(
                        brawler_id=matchup.brawler_a_id,
                        brawler_name=synergy["brawler"],
                        win_rate_against=synergy["avg_win_rate"],
                        pick_rate=0.0,  # Would need to fetch
                        sample_size=100,  # Estimate
                        confidence="medium",
                        reasoning=f"Counters {synergy['counters_count']} enemy brawlers"
                    ))

            # Calculate confidence score
            confidence = len(synergy_counters) / 10.0  # Normalize
            confidence = min(1.0, max(0.3, confidence))

            return TeamCounterAnalysis(
                enemy_team=enemy_brawlers,
                recommended_counters=recommended,
                team_synergy_counters=synergy_counters[:10],
                weaknesses=weaknesses,
                strengths=strengths,
                overall_strategy=strategy,
                confidence_score=round(confidence, 2)
            )

        except Exception as e:
            logger.error(f"Error analyzing enemy team: {e}")
            return TeamCounterAnalysis(
                enemy_team=enemy_brawlers,
                recommended_counters=[],
                team_synergy_counters=[],
                weaknesses=[],
                strengths=[],
                overall_strategy="Insufficient data for analysis",
                confidence_score=0.0
            )

    def _analyze_team_weaknesses(self, archetypes: list[str]) -> list[str]:
        """Determine what a team composition is weak against."""
        weaknesses = []

        archetype_counts = defaultdict(int)
        for arch in archetypes:
            archetype_counts[arch] += 1

        # Heavy tank team = weak to sharpshooters
        if archetype_counts["tank"] >= 2:
            weaknesses.append("Long-range sharpshooters")
            weaknesses.append("Throwers with area denial")

        # No tanks = weak to assassins
        if archetype_counts["tank"] == 0:
            weaknesses.append("Aggressive assassins")
            weaknesses.append("Close-range pressure")

        # Heavy sharpshooter = weak to assassins
        if archetype_counts["sharpshooter"] >= 2:
            weaknesses.append("Flanking assassins")
            weaknesses.append("Walls and cover usage")

        # No support = weak to sustain damage
        if archetype_counts["support"] == 0:
            weaknesses.append("Chip damage and poke")
            weaknesses.append("Extended fights")

        return weaknesses if weaknesses else ["Balanced composition - no major weaknesses"]

    def _analyze_team_strengths(self, archetypes: list[str]) -> list[str]:
        """Determine what a team composition is strong at."""
        strengths = []

        archetype_counts = defaultdict(int)
        for arch in archetypes:
            archetype_counts[arch] += 1

        if archetype_counts["tank"] >= 2:
            strengths.append("Strong frontline pressure")
            strengths.append("Zone control")

        if archetype_counts["sharpshooter"] >= 2:
            strengths.append("Long-range control")
            strengths.append("Picking off targets")

        if archetype_counts["support"] >= 1:
            strengths.append("Team sustain")
            strengths.append("Extended engagements")

        if archetype_counts["assassin"] >= 1:
            strengths.append("Burst damage")
            strengths.append("Target elimination")

        if archetype_counts["thrower"] >= 1:
            strengths.append("Area denial")
            strengths.append("Siege potential")

        return strengths if strengths else ["Versatile composition"]

    def _generate_team_strategy(self, archetypes: list[str], mode: Optional[str]) -> str:
        """Generate strategic advice against the enemy team."""
        archetype_counts = defaultdict(int)
        for arch in archetypes:
            archetype_counts[arch] += 1

        strategies = []

        # Mode-specific strategies
        if mode == "gemGrab":
            if archetype_counts["assassin"] >= 1:
                strategies.append("Protect your gem carrier from assassin flanks")
            if archetype_counts["thrower"] >= 1:
                strategies.append("Don't group up - spread to avoid thrower value")

        elif mode == "brawlBall":
            if archetype_counts["tank"] >= 2:
                strategies.append("Keep distance and poke - don't engage directly")
            if archetype_counts["assassin"] >= 1:
                strategies.append("Support your ball carrier against assassin threats")

        elif mode == "bounty":
            if archetype_counts["sharpshooter"] >= 2:
                strategies.append("Use cover aggressively - don't peek long sightlines")

        # General strategies
        if archetype_counts["tank"] >= 2:
            strategies.append("Pick brawlers with knockback or slow to kite tanks")
        elif archetype_counts["tank"] == 0:
            strategies.append("Play aggressively - they lack frontline protection")

        if archetype_counts["support"] >= 1:
            strategies.append("Focus the support first to reduce their sustain")

        if not strategies:
            strategies.append("Play to your brawlers' strengths and control the map")

        return " | ".join(strategies)

    async def build_matchup_matrix(
        self,
        db: AsyncSession,
        battle_logs: list[dict[str, Any]]
    ) -> int:
        """
        Build/update the matchup matrix from battle log data.

        Args:
            db: Database session
            battle_logs: List of battle log entries

        Returns:
            Number of matchups updated
        """
        # This would analyze battle logs and update BrawlerMatchup table
        # Implementation depends on battle log structure
        logger.info("Building matchup matrix from battle logs")

        matchup_data: dict[tuple[int, int, str], dict] = defaultdict(
            lambda: {"wins_a": 0, "total": 0}
        )

        for battle in battle_logs:
            # Extract brawler matchup data from battle
            # This is a simplified version - real implementation would be more complex
            pass

        # Update database with aggregated matchup data
        updates = 0
        # ... database update logic ...

        logger.info(f"Updated {updates} matchups in matrix")
        return updates


# Global service instance
counter_pick_service = CounterPickService()
