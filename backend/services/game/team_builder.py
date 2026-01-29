"""
Team Builder Service for BrawlGPT.
Builds optimal team compositions based on mode, map, and synergies.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Any
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

logger = logging.getLogger(__name__)


@dataclass
class BrawlerSuggestion:
    """A single brawler suggestion for team composition."""
    brawler_id: int
    brawler_name: str
    role: str  # "carry", "support", "tank", "flex"
    score: float  # Composite score (0-100)
    win_rate: float
    synergy_score: float  # How well it synergizes with existing team
    counter_score: float  # How well it counters current meta
    map_score: float  # Performance on specific map
    reasons: list[str] = field(default_factory=list)


@dataclass
class TeamComposition:
    """A complete team composition recommendation."""
    brawlers: list[BrawlerSuggestion]
    overall_score: float
    synergy_rating: str  # "S", "A", "B", "C"
    playstyle: str  # "aggressive", "defensive", "balanced", "control"
    strengths: list[str]
    weaknesses: list[str]
    tips: list[str]
    mode: str
    map_name: Optional[str] = None


class TeamBuilderService:
    """
    Service for building optimal team compositions.

    Considers:
    - Mode meta
    - Map-specific performance
    - Brawler synergies
    - Team balance (roles)
    - Counter-pick potential

    Usage:
        service = TeamBuilderService()

        # Build optimal team for a mode
        comp = await service.build_optimal_team(db, mode="gemGrab")

        # Get fill suggestions when 2 teammates already picked
        suggestions = await service.suggest_fill(
            db,
            teammates=["Poco", "Rosa"],
            mode="brawlBall"
        )
    """

    # Role definitions for team balance
    ROLES = {
        "tank": {
            "brawlers": ["Bull", "El Primo", "Rosa", "Darryl", "Jacky", "Frank", "Bibi", "Ash"],
            "importance": {"brawlBall": 1.5, "gemGrab": 1.0, "heist": 0.7, "bounty": 0.5}
        },
        "support": {
            "brawlers": ["Poco", "Pam", "Byron", "Ruffs", "Max", "Gene", "Doug", "Gray"],
            "importance": {"gemGrab": 1.5, "brawlBall": 1.2, "hotZone": 1.3, "bounty": 0.8}
        },
        "damage": {
            "brawlers": ["Colt", "Brock", "Piper", "Bea", "Belle", "Mandy", "Rico", "8-Bit"],
            "importance": {"bounty": 1.5, "heist": 1.3, "knockout": 1.4, "brawlBall": 1.0}
        },
        "control": {
            "brawlers": ["Spike", "Crow", "Sandy", "Emz", "Lou", "Gale", "Squeak", "Bo"],
            "importance": {"hotZone": 1.5, "gemGrab": 1.3, "siege": 1.2, "brawlBall": 1.0}
        },
        "assassin": {
            "brawlers": ["Mortis", "Leon", "Edgar", "Buzz", "Fang", "Mico", "Stu"],
            "importance": {"bounty": 0.8, "gemGrab": 1.0, "brawlBall": 1.2, "knockout": 0.9}
        }
    }

    # Synergy pairs (brawlers that work well together)
    SYNERGY_PAIRS = {
        ("Poco", "Rosa"): 1.3,
        ("Poco", "Bull"): 1.25,
        ("Poco", "El Primo"): 1.25,
        ("Poco", "Jacky"): 1.3,
        ("Byron", "Max"): 1.2,
        ("Gene", "Piper"): 1.15,
        ("Gene", "Bea"): 1.15,
        ("Max", "Mortis"): 1.2,
        ("Sandy", "Gene"): 1.15,
        ("Ruffs", "Belle"): 1.2,
        ("Ruffs", "Brock"): 1.15,
        ("Pam", "Colt"): 1.1,
        ("Nita", "Bruce"): 1.0,  # Implied
    }

    # Anti-synergy pairs (brawlers that don't work well together)
    ANTI_SYNERGY_PAIRS = {
        ("Mortis", "Piper"): 0.8,  # Both squishy, need tank
        ("Dynamike", "Tick"): 0.85,  # Double thrower weak to aggro
        ("Edgar", "Mortis"): 0.9,  # Both assassins, no frontline
    }

    def __init__(self):
        pass

    def _get_brawler_role(self, brawler_name: str) -> Optional[str]:
        """Get the primary role of a brawler."""
        for role, data in self.ROLES.items():
            if brawler_name in data["brawlers"]:
                return role
        return "flex"

    def _calculate_synergy(self, team: list[str]) -> float:
        """Calculate synergy score for a team (0-100)."""
        if len(team) < 2:
            return 50.0

        synergy_multiplier = 1.0

        # Check all pairs
        for i, b1 in enumerate(team):
            for b2 in team[i + 1:]:
                pair = tuple(sorted([b1, b2]))
                if pair in self.SYNERGY_PAIRS:
                    synergy_multiplier *= self.SYNERGY_PAIRS[pair]
                elif pair in self.ANTI_SYNERGY_PAIRS:
                    synergy_multiplier *= self.ANTI_SYNERGY_PAIRS[pair]

        # Convert to score (50 = neutral, 100 = excellent)
        return min(100, max(0, 50 * synergy_multiplier))

    def _get_synergy_rating(self, score: float) -> str:
        """Convert synergy score to letter rating."""
        if score >= 80:
            return "S"
        elif score >= 65:
            return "A"
        elif score >= 50:
            return "B"
        return "C"

    def _determine_playstyle(self, team: list[str]) -> str:
        """Determine team playstyle based on composition."""
        roles = [self._get_brawler_role(b) for b in team]
        role_counts = defaultdict(int)
        for role in roles:
            role_counts[role] += 1

        if role_counts["tank"] >= 2 or (role_counts["tank"] >= 1 and role_counts["assassin"] >= 1):
            return "aggressive"
        elif role_counts["control"] >= 2 or role_counts["support"] >= 2:
            return "control"
        elif role_counts["damage"] >= 2:
            return "poke"
        elif role_counts["support"] >= 1 and role_counts["tank"] >= 1:
            return "defensive"
        return "balanced"

    async def build_optimal_team(
        self,
        db: AsyncSession,
        mode: str,
        map_name: Optional[str] = None,
        trophy_range: Optional[tuple[int, int]] = None,
        exclude_brawlers: Optional[list[str]] = None
    ) -> TeamComposition:
        """
        Build an optimal 3-brawler team for a mode/map.

        Args:
            db: Database session
            mode: Game mode
            map_name: Optional specific map
            trophy_range: Optional trophy range filter
            exclude_brawlers: Brawlers to exclude from selection

        Returns:
            Optimal team composition
        """
        try:
            from db_models import BrawlerMeta, MetaSnapshot, MapBrawlerPerformance

            exclude = set(exclude_brawlers or [])

            # Get top brawlers for this mode from meta
            query = select(BrawlerMeta).join(MetaSnapshot).where(
                MetaSnapshot.timestamp >= func.now() - func.cast('7 days', func.interval())
            ).order_by(BrawlerMeta.win_rate.desc()).limit(30)

            result = await db.execute(query)
            meta_brawlers = result.scalars().all()

            # Score each brawler
            brawler_scores: dict[str, dict[str, Any]] = {}

            for bm in meta_brawlers:
                if bm.brawler_name in exclude:
                    continue

                # Base score from win rate
                score = bm.win_rate * 1.5

                # Mode affinity
                role = self._get_brawler_role(bm.brawler_name)
                if role and role in self.ROLES:
                    mode_importance = self.ROLES[role].get("importance", {}).get(mode, 1.0)
                    score *= mode_importance

                # Map performance (if available)
                map_score = 50.0
                if map_name:
                    map_query = select(MapBrawlerPerformance).where(
                        MapBrawlerPerformance.brawler_id == bm.brawler_id,
                        MapBrawlerPerformance.map_name == map_name
                    ).limit(1)
                    map_result = await db.execute(map_query)
                    map_perf = map_result.scalar_one_or_none()
                    if map_perf:
                        map_score = map_perf.win_rate
                        score *= (map_perf.win_rate / 50.0)

                brawler_scores[bm.brawler_name] = {
                    "id": bm.brawler_id,
                    "win_rate": bm.win_rate,
                    "pick_rate": bm.pick_rate,
                    "score": score,
                    "role": role,
                    "map_score": map_score,
                    "best_modes": bm.best_modes or []
                }

            # Build team using greedy selection with role balance
            team = []
            used_roles = set()

            # Priority: 1 damage/control, 1 tank/support, 1 flex
            role_priority = ["damage", "tank", "support", "control", "assassin", "flex"]

            sorted_brawlers = sorted(
                brawler_scores.items(),
                key=lambda x: x[1]["score"],
                reverse=True
            )

            for role in role_priority:
                if len(team) >= 3:
                    break

                for brawler_name, data in sorted_brawlers:
                    if brawler_name in [t.brawler_name for t in team]:
                        continue

                    if data["role"] == role or (role == "flex" and data["role"] not in used_roles):
                        # Check synergy with existing team
                        test_team = [t.brawler_name for t in team] + [brawler_name]
                        synergy = self._calculate_synergy(test_team)

                        if synergy >= 40:  # Minimum synergy threshold
                            suggestion = BrawlerSuggestion(
                                brawler_id=data["id"],
                                brawler_name=brawler_name,
                                role=data["role"],
                                score=data["score"],
                                win_rate=data["win_rate"],
                                synergy_score=synergy,
                                counter_score=50.0,  # Would need counter data
                                map_score=data["map_score"],
                                reasons=[f"Strong in {mode}", f"Role: {data['role']}"]
                            )
                            team.append(suggestion)
                            used_roles.add(data["role"])
                            break

            # Fill remaining slots if needed
            while len(team) < 3:
                for brawler_name, data in sorted_brawlers:
                    if brawler_name not in [t.brawler_name for t in team]:
                        suggestion = BrawlerSuggestion(
                            brawler_id=data["id"],
                            brawler_name=brawler_name,
                            role=data["role"],
                            score=data["score"],
                            win_rate=data["win_rate"],
                            synergy_score=50.0,
                            counter_score=50.0,
                            map_score=data["map_score"],
                            reasons=["Meta pick"]
                        )
                        team.append(suggestion)
                        break

            # Calculate final team metrics
            team_names = [t.brawler_name for t in team]
            overall_synergy = self._calculate_synergy(team_names)
            overall_score = sum(t.score for t in team) / 3
            playstyle = self._determine_playstyle(team_names)

            # Generate tips and analysis
            strengths, weaknesses = self._analyze_team_strengths_weaknesses(team_names, mode)
            tips = self._generate_team_tips(team_names, mode, playstyle)

            return TeamComposition(
                brawlers=team,
                overall_score=round(overall_score, 1),
                synergy_rating=self._get_synergy_rating(overall_synergy),
                playstyle=playstyle,
                strengths=strengths,
                weaknesses=weaknesses,
                tips=tips,
                mode=mode,
                map_name=map_name
            )

        except Exception as e:
            logger.error(f"Error building optimal team: {e}")
            return TeamComposition(
                brawlers=[],
                overall_score=0.0,
                synergy_rating="C",
                playstyle="unknown",
                strengths=[],
                weaknesses=["Unable to generate composition"],
                tips=["Try again or pick based on meta"],
                mode=mode,
                map_name=map_name
            )

    async def suggest_fill(
        self,
        db: AsyncSession,
        teammates: list[str],
        mode: str,
        map_name: Optional[str] = None,
        available_brawlers: Optional[list[str]] = None,
        limit: int = 5
    ) -> list[BrawlerSuggestion]:
        """
        Suggest brawlers to fill remaining team slots.

        Args:
            db: Database session
            teammates: Already selected teammates
            mode: Game mode
            map_name: Optional specific map
            available_brawlers: Player's available brawlers (if None, suggest any)
            limit: Number of suggestions to return

        Returns:
            List of fill suggestions sorted by score
        """
        try:
            from db_models import BrawlerMeta, MetaSnapshot

            # Determine what roles are missing
            existing_roles = [self._get_brawler_role(t) for t in teammates]
            role_counts = defaultdict(int)
            for role in existing_roles:
                role_counts[role] += 1

            # Prioritize missing roles
            needed_roles = []
            if role_counts["tank"] == 0 and mode in ["brawlBall", "gemGrab", "hotZone"]:
                needed_roles.append("tank")
            if role_counts["support"] == 0 and mode in ["gemGrab", "brawlBall"]:
                needed_roles.append("support")
            if role_counts["damage"] == 0 and mode in ["bounty", "heist", "knockout"]:
                needed_roles.append("damage")

            # Get meta brawlers
            query = select(BrawlerMeta).join(MetaSnapshot).order_by(
                BrawlerMeta.win_rate.desc()
            ).limit(50)

            result = await db.execute(query)
            meta_brawlers = result.scalars().all()

            suggestions = []

            for bm in meta_brawlers:
                # Skip already picked brawlers
                if bm.brawler_name in teammates:
                    continue

                # Filter by available brawlers if specified
                if available_brawlers and bm.brawler_name not in available_brawlers:
                    continue

                role = self._get_brawler_role(bm.brawler_name)

                # Calculate synergy with existing team
                test_team = teammates + [bm.brawler_name]
                synergy_score = self._calculate_synergy(test_team)

                # Role bonus
                role_bonus = 1.2 if role in needed_roles else 1.0

                # Calculate final score
                score = bm.win_rate * role_bonus * (synergy_score / 50.0)

                # Generate reasons
                reasons = []
                if role in needed_roles:
                    reasons.append(f"Fills needed {role} role")
                if synergy_score >= 60:
                    reasons.append(f"Good synergy with team ({synergy_score:.0f})")
                if bm.win_rate >= 55:
                    reasons.append(f"Strong meta pick ({bm.win_rate:.1f}% WR)")

                suggestion = BrawlerSuggestion(
                    brawler_id=bm.brawler_id,
                    brawler_name=bm.brawler_name,
                    role=role,
                    score=score,
                    win_rate=bm.win_rate,
                    synergy_score=synergy_score,
                    counter_score=50.0,
                    map_score=50.0,
                    reasons=reasons or ["Meta pick"]
                )
                suggestions.append(suggestion)

            # Sort by score and return top suggestions
            suggestions.sort(key=lambda x: x.score, reverse=True)
            return suggestions[:limit]

        except Exception as e:
            logger.error(f"Error suggesting fill: {e}")
            return []

    def _analyze_team_strengths_weaknesses(
        self,
        team: list[str],
        mode: str
    ) -> tuple[list[str], list[str]]:
        """Analyze team strengths and weaknesses."""
        strengths = []
        weaknesses = []

        roles = [self._get_brawler_role(b) for b in team]
        role_counts = defaultdict(int)
        for role in roles:
            role_counts[role] += 1

        # Strengths
        if role_counts["tank"] >= 1:
            strengths.append("Frontline presence")
        if role_counts["support"] >= 1:
            strengths.append("Team sustain")
        if role_counts["damage"] >= 2:
            strengths.append("High damage output")
        if role_counts["control"] >= 1:
            strengths.append("Area control")

        # Weaknesses
        if role_counts["tank"] == 0 and mode in ["brawlBall", "gemGrab"]:
            weaknesses.append("Vulnerable to aggression")
        if role_counts["support"] == 0:
            weaknesses.append("Limited sustain")
        if role_counts["damage"] == 0:
            weaknesses.append("May lack burst damage")

        return strengths or ["Balanced composition"], weaknesses or ["No major weaknesses"]

    def _generate_team_tips(
        self,
        team: list[str],
        mode: str,
        playstyle: str
    ) -> list[str]:
        """Generate tips for playing this team composition."""
        tips = []

        if playstyle == "aggressive":
            tips.append("Push together and maintain pressure")
            tips.append("Force fights early before opponents can scale")
        elif playstyle == "control":
            tips.append("Control key areas and deny enemy movement")
            tips.append("Be patient and wait for good engagements")
        elif playstyle == "poke":
            tips.append("Keep distance and chip away at enemies")
            tips.append("Don't overcommit to fights")
        elif playstyle == "defensive":
            tips.append("Protect your carry and wait for opportunities")
            tips.append("Counter-engage when enemies overextend")
        else:
            tips.append("Adapt your playstyle to the situation")

        # Mode-specific tips
        if mode == "gemGrab":
            tips.append("Prioritize gem control over kills")
        elif mode == "brawlBall":
            tips.append("Coordinate passes and protect the ball carrier")
        elif mode == "bounty":
            tips.append("Play for trades - don't feed stars")
        elif mode == "heist":
            tips.append("Balance offense and defense based on HP")

        return tips


# Global service instance
team_builder_service = TeamBuilderService()
