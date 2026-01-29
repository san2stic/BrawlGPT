"""
Counter-Pick Service

Provides intelligent counter-pick recommendations based on:
- Historical matchup win rates
- Mode-specific performance
- Team composition synergies
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from datetime import datetime
import logging

from db_models import BrawlerMatchup, MapBrawlerPerformance
from brawlstars import BrawlStarsClient


logger = logging.getLogger(__name__)


class CounterPick:
    """Represents a counter-pick recommendation"""
    def __init__(
        self,
        brawler_id: int,
        brawler_name: str,
        win_rate: float,
        sample_size: int,
        mode: Optional[str] = None,
        reasoning: str = ""
    ):
        self.brawler_id = brawler_id
        self.brawler_name = brawler_name
        self.win_rate = win_rate
        self.sample_size = sample_size
        self.mode = mode
        self.reasoning = reasoning
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "brawler_id": self.brawler_id,
            "brawler_name": self.brawler_name,
            "win_rate": round(self.win_rate, 3),
            "sample_size": self.sample_size,
            "mode": self.mode,
            "reasoning": self.reasoning,
            "confidence": self._get_confidence()
        }
    
    def _get_confidence(self) -> str:
        """Calculate confidence level based on sample size"""
        if self.sample_size >= 10000:
            return "high"
        elif self.sample_size >= 1000:
            return "medium"
        else:
            return "low"


class TeamCounterAnalysis:
    """Analysis of counter-picks for an enemy team composition"""
    def __init__(
        self,
        enemy_team: List[str],
        recommended_picks: List[CounterPick],
        synergy_score: float,
        mode: Optional[str] = None
    ):
        self.enemy_team = enemy_team
        self.recommended_picks = recommended_picks
        self.synergy_score = synergy_score
        self.mode = mode
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "enemy_team": self.enemy_team,
            "recommended_picks": [p.to_dict() for p in self.recommended_picks],
            "synergy_score": round(self.synergy_score, 2),
            "mode": self.mode
        }


class CounterPickService:
    """Service for counter-pick recommendations"""
    
    def __init__(self):
        self.brawl_api: Optional[BrawlStarsClient] = None
    
    def set_brawl_api(self, api: BrawlStarsClient):
        """Set the Brawl Stars API client"""
        self.brawl_api = api

    
    async def get_counters(
        self,
        db: AsyncSession,
        brawler_name: str,
        mode: Optional[str] = None,
        top_n: int = 5,
        min_sample_size: int = 100
    ) -> List[CounterPick]:
        """
        Get the best counter-picks for a specific brawler.
        
        Args:
            db: Database session
            brawler_name: Name of the brawler to counter
            mode: Game mode (None for global)
            top_n: Number of counters to return
            min_sample_size: Minimum battles required for inclusion
        
        Returns:
            List of CounterPick objects
        """
        try:
            # Query matchups where brawler_b is the target brawler
            # We want brawlers (A) that have high win rates against target (B)
            query = select(BrawlerMatchup).where(
                and_(
                    BrawlerMatchup.brawler_b_name == brawler_name,
                    BrawlerMatchup.sample_size >= min_sample_size
                )
            )
            
            # Filter by mode if specified
            if mode:
                query = query.where(BrawlerMatchup.mode == mode)
            else:
                query = query.where(BrawlerMatchup.mode.is_(None))
            
            # Order by win rate descending
            query = query.order_by(desc(BrawlerMatchup.win_rate_a_vs_b)).limit(top_n)
            
            result = await db.execute(query)
            matchups = result.scalars().all()
            
            counters = []
            for matchup in matchups:
                reasoning = f"Wins {matchup.win_rate_a_vs_b:.1%} of matchups vs {brawler_name}"
                if mode:
                    reasoning += f" in {mode}"
                
                counters.append(CounterPick(
                    brawler_id=matchup.brawler_a_id,
                    brawler_name=matchup.brawler_a_name,
                    win_rate=matchup.win_rate_a_vs_b,
                    sample_size=matchup.sample_size,
                    mode=mode,
                    reasoning=reasoning
                ))
            
            logger.info(f"Found {len(counters)} counters for {brawler_name}" + (f" in {mode}" if mode else ""))
            return counters
            
        except Exception as e:
            logger.error(f"Error getting counters for {brawler_name}: {e}")
            return []
    
    async def analyze_enemy_team(
        self,
        db: AsyncSession,
        enemy_brawlers: List[str],
        mode: Optional[str] = None,
        top_n: int = 3
    ) -> TeamCounterAnalysis:
        """
        Analyze an enemy team composition and suggest optimal counters.
        
        Args:
            db: Database session
            enemy_brawlers: List of enemy brawler names
            mode: Game mode
            top_n: Number of recommendations per enemy brawler
        
        Returns:
            TeamCounterAnalysis with recommended picks
        """
        try:
            # Get counters for each enemy brawler
            all_counters: Dict[str, List[CounterPick]] = {}
            
            for enemy in enemy_brawlers:
                counters = await self.get_counters(db, enemy, mode, top_n=top_n)
                all_counters[enemy] = counters
            
            # Aggregate and score potential picks
            # A brawler that counters multiple enemies is more valuable
            counter_scores: Dict[str, Dict[str, Any]] = {}
            
            for enemy, counters in all_counters.items():
                for counter in counters:
                    if counter.brawler_name not in counter_scores:
                        counter_scores[counter.brawler_name] = {
                            "brawler_id": counter.brawler_id,
                            "total_win_rate": 0,
                            "enemies_countered": [],
                            "sample_size": 0
                        }
                    
                    counter_scores[counter.brawler_name]["total_win_rate"] += counter.win_rate
                    counter_scores[counter.brawler_name]["enemies_countered"].append(enemy)
                    counter_scores[counter.brawler_name]["sample_size"] += counter.sample_size
            
            # Calculate composite score and create recommendations
            recommendations = []
            for brawler_name, scores in counter_scores.items():
                num_countered = len(scores["enemies_countered"])
                avg_win_rate = scores["total_win_rate"] / len(enemy_brawlers)
                
                # Bonus for countering multiple enemies
                synergy_bonus = num_countered / len(enemy_brawlers)
                composite_score = avg_win_rate + (synergy_bonus * 0.1)
                
                reasoning = f"Counters {num_countered}/{len(enemy_brawlers)} enemies: {', '.join(scores['enemies_countered'])}"
                
                recommendations.append(CounterPick(
                    brawler_id=scores["brawler_id"],
                    brawler_name=brawler_name,
                    win_rate=composite_score,
                    sample_size=scores["sample_size"],
                    mode=mode,
                    reasoning=reasoning
                ))
            
            # Sort by composite score
            recommendations.sort(key=lambda x: x.win_rate, reverse=True)
            recommendations = recommendations[:top_n * 2]  # Return more for team building
            
            # Calculate overall synergy score
            synergy_score = sum(r.win_rate for r in recommendations[:3]) / 3 if recommendations else 0
            
            return TeamCounterAnalysis(
                enemy_team=enemy_brawlers,
                recommended_picks=recommendations,
                synergy_score=synergy_score,
                mode=mode
            )
            
        except Exception as e:
            logger.error(f"Error analyzing enemy team {enemy_brawlers}: {e}")
            return TeamCounterAnalysis(
                enemy_team=enemy_brawlers,
                recommended_picks=[],
                synergy_score=0,
                mode=mode
            )
    
    async def build_matchup_matrix(
        self,
        db: AsyncSession,
        mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build or update the brawler matchup matrix from meta data.
        This would typically be run periodically as a background task.
        
        Args:
            db: Database session
            mode: Game mode to build matrix for
        
        Returns:
            Statistics about the matrix build
        """
        try:
            # This is a placeholder - in production, this would:
            # 1. Fetch battle log data from the API
            # 2. Calculate win rates for each matchup
            # 3. Update the BrawlerMatchup table
            
            logger.info(f"Building matchup matrix for mode: {mode or 'global'}")
            
            # For now, return placeholder stats
            return {
                "mode": mode,
                "matchups_updated": 0,
                "last_updated": datetime.utcnow().isoformat(),
                "status": "placeholder_implementation"
            }
            
        except Exception as e:
            logger.error(f"Error building matchup matrix: {e}")
            return {
                "mode": mode,
                "error": str(e),
                "status": "failed"
            }
