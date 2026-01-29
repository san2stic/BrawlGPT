"""
AI Agent Tools for BrawlGPT.
Dynamic tools (function calling) that the AI can invoke to get real-time data.
"""

import logging
from typing import Any, Optional
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from db_models import (
    MetaSnapshot, BrawlerMeta, PlayerHistory,
    CachedBrawlerData, CachedEventRotation,
    ConversationMemory, ProgressionGoal
)
from brawlstars import BrawlStarsClient
from crawler import SmartBattleCrawler
from cache import cache

logger = logging.getLogger(__name__)


# =============================================================================
# TOOL DEFINITIONS (OpenAI Function Calling Format)
# =============================================================================

AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_brawler_stats",
            "description": "Obtenir les statistiques complètes d'un brawler: HP, damage, super, gadgets, star powers, et ses meilleurs modes de jeu",
            "parameters": {
                "type": "object",
                "properties": {
                    "brawler_name": {
                        "type": "string",
                        "description": "Nom du brawler (ex: Shelly, Colt, Spike)"
                    }
                },
                "required": ["brawler_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_meta",
            "description": "Obtenir la meta actuelle: tier list, pick rates, win rates des brawlers dominants pour une tranche de trophées",
            "parameters": {
                "type": "object",
                "properties": {
                    "trophy_range": {
                        "type": "string",
                        "description": "Tranche de trophées (ex: '20000-30000', 'auto' pour détecter automatiquement)"
                    }
                },
                "required": ["trophy_range"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_best_brawlers_for_mode",
            "description": "Obtenir les meilleurs brawlers pour un mode de jeu spécifique basé sur les win rates réels",
            "parameters": {
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "description": "Mode de jeu (ex: gemGrab, brawlBall, heist, bounty, siege, hotZone, knockout, duels, soloShowdown, duoShowdown)"
                    },
                    "trophy_range": {
                        "type": "string",
                        "description": "Tranche de trophées optionnelle (ex: '20000-30000')"
                    }
                },
                "required": ["mode"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_matchup",
            "description": "Analyser un matchup entre deux brawlers: avantages, inconvénients, conseils tactiques",
            "parameters": {
                "type": "object",
                "properties": {
                    "brawler1": {
                        "type": "string",
                        "description": "Premier brawler"
                    },
                    "brawler2": {
                        "type": "string",
                        "description": "Deuxième brawler (adversaire)"
                    }
                },
                "required": ["brawler1", "brawler2"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_events",
            "description": "Obtenir les events actuellement en rotation avec les modes et maps actifs",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_player_progression",
            "description": "Obtenir l'historique de progression du joueur sur une période donnée",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Nombre de jours d'historique (défaut: 7)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compare_with_similar_players",
            "description": "Comparer le joueur avec d'autres joueurs de niveau similaire pour identifier les points forts et faibles",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_trending_compositions",
            "description": "Obtenir les compositions d'équipe gagnantes actuellement populaires",
            "parameters": {
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "description": "Mode de jeu optionnel pour filtrer"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_player_brawler",
            "description": "Analyser les performances d'un brawler spécifique pour le joueur actuel",
            "parameters": {
                "type": "object",
                "properties": {
                    "brawler_name": {
                        "type": "string",
                        "description": "Nom du brawler à analyser"
                    }
                },
                "required": ["brawler_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_player_goal",
            "description": "Définir un objectif de progression pour le joueur",
            "parameters": {
                "type": "object",
                "properties": {
                    "goal_type": {
                        "type": "string",
                        "description": "Type d'objectif (total_trophies, brawler_rank, victories)"
                    },
                    "target_value": {
                        "type": "integer",
                        "description": "Valeur cible à atteindre"
                    },
                    "description": {
                        "type": "string",
                        "description": "Description de l'objectif"
                    },
                    "brawler_name": {
                        "type": "string",
                        "description": "Nom du brawler (pour objectifs spécifiques à un brawler)"
                    }
                },
                "required": ["goal_type", "target_value"]
            }
        }
    }
]


# =============================================================================
# TOOL EXECUTOR CLASS
# =============================================================================

class AgentToolExecutor:
    """
    Executes AI agent tools and returns results.
    """

    # Trophy range mapping
    TROPHY_RANGES = {
        "0-5000": (0, 5000),
        "5000-10000": (5000, 10000),
        "10000-20000": (10000, 20000),
        "20000-30000": (20000, 30000),
        "30000-50000": (30000, 50000),
        "50000-100000": (50000, 100000),
    }

    def __init__(
        self,
        brawl_client: BrawlStarsClient,
        db: AsyncSession,
        player_context: Optional[dict] = None
    ):
        """
        Initialize the tool executor.

        Args:
            brawl_client: Brawl Stars API client
            db: Database session
            player_context: Optional player data for context
        """
        self.client = brawl_client
        self.db = db
        self.player_context = player_context
        self.crawler = SmartBattleCrawler(brawl_client)

    def _get_player_trophy_range(self) -> tuple[int, int]:
        """Get the trophy range for the current player context."""
        if not self.player_context:
            return (20000, 30000)  # Default

        trophies = self.player_context.get("trophies", 0)
        for range_str, range_tuple in self.TROPHY_RANGES.items():
            if range_tuple[0] <= trophies < range_tuple[1]:
                return range_tuple
        return (50000, 100000)

    async def execute_tool(self, tool_name: str, arguments: dict) -> dict:
        """
        Execute a tool and return the result.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments

        Returns:
            Tool execution result as a dictionary
        """
        logger.info(f"Executing tool: {tool_name} with args: {arguments}")

        try:
            if tool_name == "get_brawler_stats":
                return await self._get_brawler_stats(arguments.get("brawler_name"))

            elif tool_name == "get_current_meta":
                return await self._get_current_meta(arguments.get("trophy_range", "auto"))

            elif tool_name == "get_best_brawlers_for_mode":
                return await self._get_best_brawlers_for_mode(
                    arguments.get("mode"),
                    arguments.get("trophy_range")
                )

            elif tool_name == "analyze_matchup":
                return await self._analyze_matchup(
                    arguments.get("brawler1"),
                    arguments.get("brawler2")
                )

            elif tool_name == "get_current_events":
                return await self._get_current_events()

            elif tool_name == "get_player_progression":
                return await self._get_player_progression(
                    arguments.get("days", 7)
                )

            elif tool_name == "compare_with_similar_players":
                return await self._compare_with_similar_players()

            elif tool_name == "get_trending_compositions":
                return await self._get_trending_compositions(
                    arguments.get("mode")
                )

            elif tool_name == "analyze_player_brawler":
                return await self._analyze_player_brawler(
                    arguments.get("brawler_name")
                )

            elif tool_name == "set_player_goal":
                return await self._set_player_goal(
                    arguments.get("goal_type"),
                    arguments.get("target_value"),
                    arguments.get("description", ""),
                    arguments.get("brawler_name")
                )

            else:
                return {"error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return {"error": str(e)}

    # =========================================================================
    # TOOL IMPLEMENTATIONS
    # =========================================================================

    async def _get_brawler_stats(self, brawler_name: str) -> dict:
        """Get detailed stats for a brawler."""
        if not brawler_name:
            return {"error": "Brawler name required"}

        # Try to get from cache/DB first
        stmt = select(CachedBrawlerData).where(
            func.lower(CachedBrawlerData.name) == brawler_name.lower()
        )
        result = await self.db.execute(stmt)
        cached = result.scalar_one_or_none()

        if cached and cached.data:
            brawler_data = cached.data
        else:
            # Fetch from API
            try:
                all_brawlers = self.client.get_all_brawlers()
                brawler_data = None
                for b in all_brawlers.get("items", []):
                    if b.get("name", "").lower() == brawler_name.lower():
                        brawler_data = b
                        break

                if not brawler_data:
                    return {"error": f"Brawler '{brawler_name}' not found"}
            except Exception as e:
                return {"error": f"Failed to fetch brawler data: {e}"}

        # Get meta stats for this brawler
        trophy_range = self._get_player_trophy_range()
        stmt = select(BrawlerMeta).join(MetaSnapshot).where(
            func.lower(BrawlerMeta.brawler_name) == brawler_name.lower(),
            MetaSnapshot.trophy_range_min == trophy_range[0],
            MetaSnapshot.trophy_range_max == trophy_range[1]
        ).order_by(MetaSnapshot.timestamp.desc()).limit(1)

        result = await self.db.execute(stmt)
        meta_stats = result.scalar_one_or_none()

        return {
            "brawler": {
                "id": brawler_data.get("id"),
                "name": brawler_data.get("name"),
                "starPowers": brawler_data.get("starPowers", []),
                "gadgets": brawler_data.get("gadgets", []),
            },
            "meta_stats": {
                "pick_rate": meta_stats.pick_rate if meta_stats else None,
                "win_rate": meta_stats.win_rate if meta_stats else None,
                "avg_trophy_change": meta_stats.avg_trophies_change if meta_stats else None,
                "best_modes": meta_stats.best_modes if meta_stats else [],
                "best_maps": meta_stats.best_maps if meta_stats else [],
            } if meta_stats else None,
            "trophy_range": f"{trophy_range[0]}-{trophy_range[1]}"
        }

    async def _get_current_meta(self, trophy_range_str: str) -> dict:
        """Get current meta for a trophy range."""
        if trophy_range_str == "auto":
            trophy_range = self._get_player_trophy_range()
        else:
            trophy_range = self.TROPHY_RANGES.get(trophy_range_str, (20000, 30000))

        # Get latest snapshot
        stmt = select(MetaSnapshot).where(
            MetaSnapshot.trophy_range_min == trophy_range[0],
            MetaSnapshot.trophy_range_max == trophy_range[1]
        ).order_by(MetaSnapshot.timestamp.desc()).limit(1)

        result = await self.db.execute(stmt)
        snapshot = result.scalar_one_or_none()

        if not snapshot:
            return {
                "error": "No meta data available for this trophy range",
                "trophy_range": f"{trophy_range[0]}-{trophy_range[1]}"
            }

        # Get brawler rankings
        stmt = select(BrawlerMeta).where(
            BrawlerMeta.snapshot_id == snapshot.id
        ).order_by(BrawlerMeta.win_rate.desc()).limit(15)

        result = await self.db.execute(stmt)
        brawlers = result.scalars().all()

        return {
            "trophy_range": f"{trophy_range[0]}-{trophy_range[1]}",
            "timestamp": snapshot.timestamp.isoformat(),
            "sample_size": snapshot.sample_size,
            "tier_list": snapshot.data.get("tier_list", {}),
            "top_brawlers": [
                {
                    "name": b.brawler_name,
                    "win_rate": b.win_rate,
                    "pick_rate": b.pick_rate,
                    "best_modes": b.best_modes[:3] if b.best_modes else []
                }
                for b in brawlers
            ],
            "mode_meta": snapshot.data.get("mode_meta", {})
        }

    async def _get_best_brawlers_for_mode(
        self,
        mode: str,
        trophy_range_str: Optional[str] = None
    ) -> dict:
        """Get best brawlers for a specific game mode."""
        if not mode:
            return {"error": "Mode required"}

        if trophy_range_str:
            trophy_range = self.TROPHY_RANGES.get(trophy_range_str, (20000, 30000))
        else:
            trophy_range = self._get_player_trophy_range()

        # Get latest snapshot
        stmt = select(MetaSnapshot).where(
            MetaSnapshot.trophy_range_min == trophy_range[0],
            MetaSnapshot.trophy_range_max == trophy_range[1]
        ).order_by(MetaSnapshot.timestamp.desc()).limit(1)

        result = await self.db.execute(stmt)
        snapshot = result.scalar_one_or_none()

        if not snapshot:
            return {"error": "No meta data available"}

        mode_meta = snapshot.data.get("mode_meta", {})
        mode_brawlers = mode_meta.get(mode, [])

        return {
            "mode": mode,
            "trophy_range": f"{trophy_range[0]}-{trophy_range[1]}",
            "best_brawlers": mode_brawlers[:10]
        }

    async def _analyze_matchup(self, brawler1: str, brawler2: str) -> dict:
        """Analyze matchup between two brawlers."""
        if not brawler1 or not brawler2:
            return {"error": "Both brawlers required"}

        # Get stats for both brawlers
        b1_stats = await self._get_brawler_stats(brawler1)
        b2_stats = await self._get_brawler_stats(brawler2)

        if "error" in b1_stats or "error" in b2_stats:
            return {"error": "Failed to get brawler stats"}

        # Basic matchup analysis based on meta stats
        b1_wr = b1_stats.get("meta_stats", {}).get("win_rate", 50) or 50
        b2_wr = b2_stats.get("meta_stats", {}).get("win_rate", 50) or 50

        advantage = "neutral"
        if b1_wr - b2_wr > 5:
            advantage = brawler1
        elif b2_wr - b1_wr > 5:
            advantage = brawler2

        return {
            "brawler1": {
                "name": brawler1,
                "win_rate": b1_wr,
                "best_modes": b1_stats.get("meta_stats", {}).get("best_modes", [])
            },
            "brawler2": {
                "name": brawler2,
                "win_rate": b2_wr,
                "best_modes": b2_stats.get("meta_stats", {}).get("best_modes", [])
            },
            "advantage": advantage,
            "analysis": f"Based on current meta win rates, {advantage} has a slight advantage." if advantage != "neutral" else "This is an even matchup in the current meta."
        }

    async def _get_current_events(self) -> dict:
        """Get current event rotation."""
        # Try DB cache first
        stmt = select(CachedEventRotation).order_by(
            CachedEventRotation.last_updated.desc()
        ).limit(1)

        result = await self.db.execute(stmt)
        cached = result.scalar_one_or_none()

        if cached and cached.active_events:
            return {
                "last_updated": cached.last_updated.isoformat(),
                "events": cached.active_events
            }

        # Fetch from API
        try:
            events = self.client.get_event_rotation()
            return {
                "last_updated": datetime.utcnow().isoformat(),
                "events": events
            }
        except Exception as e:
            return {"error": f"Failed to fetch events: {e}"}

    async def _get_player_progression(self, days: int = 7) -> dict:
        """Get player progression history."""
        if not self.player_context:
            return {"error": "No player context available"}

        player_tag = self.player_context.get("tag", "").upper().replace("#", "")
        if not player_tag:
            return {"error": "Player tag not found"}

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        stmt = select(PlayerHistory).where(
            PlayerHistory.player_tag == player_tag,
            PlayerHistory.timestamp >= cutoff_date
        ).order_by(PlayerHistory.timestamp.asc())

        result = await self.db.execute(stmt)
        history = result.scalars().all()

        if not history:
            return {
                "player_tag": player_tag,
                "days": days,
                "message": "No historical data available. Progress tracking starts from first analysis.",
                "current": {
                    "trophies": self.player_context.get("trophies", 0),
                    "highest_trophies": self.player_context.get("highestTrophies", 0),
                }
            }

        first = history[0]
        last = history[-1]

        return {
            "player_tag": player_tag,
            "days": days,
            "progression": {
                "trophy_change": last.trophies - first.trophies,
                "victories_3v3_change": last.victories_3v3 - first.victories_3v3,
                "solo_victories_change": last.solo_victories - first.solo_victories,
            },
            "history": [
                {
                    "date": h.timestamp.isoformat(),
                    "trophies": h.trophies,
                    "victories_3v3": h.victories_3v3,
                }
                for h in history
            ]
        }

    async def _compare_with_similar_players(self) -> dict:
        """Compare player with others in similar trophy range."""
        if not self.player_context:
            return {"error": "No player context available"}

        trophy_range = self._get_player_trophy_range()
        player_trophies = self.player_context.get("trophies", 0)
        player_brawlers = len(self.player_context.get("brawlers", []))

        # This would require more data - for now return basic comparison
        return {
            "player_stats": {
                "trophies": player_trophies,
                "brawler_count": player_brawlers,
                "avg_trophies_per_brawler": player_trophies // max(player_brawlers, 1)
            },
            "trophy_range": f"{trophy_range[0]}-{trophy_range[1]}",
            "comparison": {
                "message": f"You are in the {trophy_range[0]//1000}k-{trophy_range[1]//1000}k trophy range.",
                "tip": "Focus on pushing your highest potential brawlers to maximize trophy gains."
            }
        }

    async def _get_trending_compositions(self, mode: Optional[str] = None) -> dict:
        """Get trending team compositions."""
        trophy_range = self._get_player_trophy_range()

        stmt = select(MetaSnapshot).where(
            MetaSnapshot.trophy_range_min == trophy_range[0],
            MetaSnapshot.trophy_range_max == trophy_range[1]
        ).order_by(MetaSnapshot.timestamp.desc()).limit(1)

        result = await self.db.execute(stmt)
        snapshot = result.scalar_one_or_none()

        if not snapshot:
            return {"error": "No meta data available"}

        compositions = snapshot.data.get("top_compositions", [])

        if mode:
            compositions = [
                c for c in compositions
                if mode in c.get("modes", {})
            ]

        return {
            "trophy_range": f"{trophy_range[0]}-{trophy_range[1]}",
            "mode_filter": mode,
            "compositions": compositions[:10]
        }

    async def _analyze_player_brawler(self, brawler_name: str) -> dict:
        """Analyze a specific brawler's performance for the current player."""
        if not self.player_context:
            return {"error": "No player context available"}

        if not brawler_name:
            return {"error": "Brawler name required"}

        # Find the brawler in player's roster
        player_brawler = None
        for b in self.player_context.get("brawlers", []):
            if b.get("name", "").lower() == brawler_name.lower():
                player_brawler = b
                break

        if not player_brawler:
            return {"error": f"Player doesn't have {brawler_name}"}

        # Get battle log for detailed analysis
        player_tag = self.player_context.get("tag", "")
        battle_log = cache.get_battle_log(player_tag.replace("#", ""))

        performance = None
        if battle_log and "items" in battle_log:
            performance = await self.crawler.analyze_brawler_performance(
                battle_log["items"],
                brawler_name,
                player_tag
            )

        return {
            "brawler": {
                "name": player_brawler.get("name"),
                "trophies": player_brawler.get("trophies"),
                "highest_trophies": player_brawler.get("highestTrophies"),
                "rank": player_brawler.get("rank"),
                "power": player_brawler.get("power"),
            },
            "recent_performance": {
                "games": performance.total_games if performance else 0,
                "win_rate": round(performance.win_rate, 1) if performance else None,
                "avg_trophy_change": round(performance.avg_trophy_change, 1) if performance else None,
                "best_modes": performance.get_best_modes() if performance else [],
            } if performance else None
        }

    async def _set_player_goal(
        self,
        goal_type: str,
        target_value: int,
        description: str = "",
        brawler_name: Optional[str] = None
    ) -> dict:
        """Set a progression goal for the player."""
        if not self.player_context:
            return {"error": "No player context available"}

        player_tag = self.player_context.get("tag", "").upper().replace("#", "")
        if not player_tag:
            return {"error": "Player tag not found"}

        # Determine current value based on goal type
        current_value = 0
        if goal_type == "total_trophies":
            current_value = self.player_context.get("trophies", 0)
        elif goal_type == "brawler_rank" and brawler_name:
            for b in self.player_context.get("brawlers", []):
                if b.get("name", "").lower() == brawler_name.lower():
                    current_value = b.get("rank", 0)
                    break
        elif goal_type == "victories":
            current_value = (
                self.player_context.get("3vs3Victories", 0) +
                self.player_context.get("soloVictories", 0) +
                self.player_context.get("duoVictories", 0)
            )

        # Create the goal
        goal = ProgressionGoal(
            player_tag=player_tag,
            goal_type=goal_type,
            description=description or f"Reach {target_value} {goal_type}",
            target_value=target_value,
            current_value=current_value,
            initial_value=current_value,
            status="active",
            brawler_name=brawler_name
        )

        self.db.add(goal)
        await self.db.commit()

        return {
            "success": True,
            "goal": {
                "type": goal_type,
                "description": goal.description,
                "current": current_value,
                "target": target_value,
                "progress": f"{(current_value / target_value * 100):.1f}%" if target_value > 0 else "0%"
            }
        }
