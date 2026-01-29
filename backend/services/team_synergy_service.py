"""
Team Synergy Service
Analyzes brawler synergy and suggests optimal team compositions
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import logging

from db_models import BrawlerSynergy, BrawlerMatchup

logger = logging.getLogger(__name__)


@dataclass
class BrawlerSuggestion:
    """Recommendation for a brawler to complete a team"""
    brawler_id: int
    brawler_name: str
    synergy_score: float
    win_rate_boost: float
    reasoning: str
    confidence: str  # 'low', 'medium', 'high'
    
    def to_dict(self) -> dict:
        return {
            'brawler_id': self.brawler_id,
            'brawler_name': self.brawler_name,
            'synergy_score': self.synergy_score,
            'win_rate_boost': self.win_rate_boost,
            'reasoning': self.reasoning,
            'confidence': self.confidence
        }


@dataclass
class SynergyAnalysis:
    """Complete analysis of team synergy"""
    brawlers: List[str]
    overall_synergy: float
    pairwise_synergies: Dict[str, float]
    strengths: List[str]
    weaknesses: List[str]
    mode: Optional[str]
    
    def to_dict(self) -> dict:
        return {
            'brawlers': self.brawlers,
            'overall_synergy': self.overall_synergy,
            'pairwise_synergies': self.pairwise_synergies,
            'strengths': self.strengths,
            'weaknesses': self.weaknesses,
            'mode': self.mode
        }


class TeamSynergyService:
    """Service for analyzing team composition and synergy"""
    
    def __init__(self):
        self.brawl_api = None
    
    def set_brawl_api(self, brawl_client):
        """Set the Brawl Stars API client"""
        self.brawl_api = brawl_client
    
    async def analyze_synergy(
        self,
        db: AsyncSession,
        brawlers: List[str],
        mode: Optional[str] = None
    ) -> SynergyAnalysis:
        """
        Analyze the synergy of a team composition.
        
        Args:
            db: Database session
            brawlers: List of 2-3 brawler names
            mode: Game mode (optional)
            
        Returns:
            SynergyAnalysis with overall score and insights
        """
        if len(brawlers) < 2 or len(brawlers) > 3:
            raise ValueError("Team must have 2-3 brawlers")
        
        # Get brawler IDs
        brawler_ids = await self._get_brawler_ids(brawlers)
        if not brawler_ids:
            raise ValueError("Could not find brawler IDs")
        
        # Calculate pairwise synergies
        pairwise = {}
        total_synergy = 0.0
        pair_count = 0
        
        for i, brawler1 in enumerate(brawlers):
            for j, brawler2 in enumerate(brawlers):
                if i >= j:
                    continue
                
                synergy = await self._get_synergy_score(
                    db,
                    brawler_ids.get(brawler1),
                    brawler_ids.get(brawler2),
                    mode
                )
                
                pair_key = f"{brawler1} + {brawler2}"
                pairwise[pair_key] = synergy
                total_synergy += synergy
                pair_count += 1
        
        overall_synergy = total_synergy / pair_count if pair_count > 0 else 0.5
        
        # Generate insights
        strengths = self._generate_strengths(brawlers, pairwise, overall_synergy)
        weaknesses = self._generate_weaknesses(brawlers, pairwise, overall_synergy)
        
        return SynergyAnalysis(
            brawlers=brawlers,
            overall_synergy=overall_synergy,
            pairwise_synergies=pairwise,
            strengths=strengths,
            weaknesses=weaknesses,
            mode=mode
        )
    
    async def suggest_third_brawler(
        self,
        db: AsyncSession,
        brawler1: str,
        brawler2: str,
        mode: Optional[str] = None,
        top_n: int = 5
    ) -> List[BrawlerSuggestion]:
        """
        Suggest the best third brawler to complete a team.
        
        Args:
            db: Database session
            brawler1: First brawler name
            brawler2: Second brawler name
            mode: Game mode (optional)
            top_n: Number of suggestions to return
            
        Returns:
            List of BrawlerSuggestion sorted by synergy score
        """
        # Get existing brawler IDs
        existing_ids = await self._get_brawler_ids([brawler1, brawler2])
        
        # Get all possible brawlers (from matchup data)
        query = select(BrawlerMatchup.brawler_a_id, BrawlerMatchup.brawler_a_name).distinct()
        result = await db.execute(query)
        all_brawlers = {row.brawler_a_id: row.brawler_a_name for row in result}
        
        # Score each potential third brawler
        suggestions = []
        for brawler_id, brawler_name in all_brawlers.items():
            if brawler_name in [brawler1, brawler2]:
                continue
            
            # Calculate synergy with both existing brawlers
            synergy1 = await self._get_synergy_score(
                db,
                existing_ids.get(brawler1),
                brawler_id,
                mode
            )
            synergy2 = await self._get_synergy_score(
                db,
                existing_ids.get(brawler2),
                brawler_id,
                mode
            )
            
            avg_synergy = (synergy1 + synergy2) / 2
            
            # Estimate win rate boost (simplified)
            win_rate_boost = (avg_synergy - 0.5) * 10  # Convert to %
            
            # Generate reasoning
            reasoning = self._generate_reasoning(
                brawler_name,
                brawler1,
                brawler2,
                synergy1,
                synergy2
            )
            
            # Determine confidence (based on having actual synergy data)
            confidence = 'high' if synergy1 > 0 and synergy2 > 0 else 'medium'
            
            suggestions.append(BrawlerSuggestion(
                brawler_id=brawler_id,
                brawler_name=brawler_name,
                synergy_score=avg_synergy,
                win_rate_boost=win_rate_boost,
                reasoning=reasoning,
                confidence=confidence
            ))
        
        # Sort by synergy score and return top N
        suggestions.sort(key=lambda x: x.synergy_score, reverse=True)
        return suggestions[:top_n]
    
    async def _get_brawler_ids(self, brawler_names: List[str]) -> Dict[str, int]:
        """Get brawler IDs from names using the API client"""
        if not self.brawl_api:
            # Fallback: use simple hash-based IDs
            return {name: hash(name.lower()) % 100000 for name in brawler_names}
        
        # In real implementation, fetch from API
        # For now, return mock IDs
        return {name: hash(name.lower()) % 100000 for name in brawler_names}
    
    async def _get_synergy_score(
        self,
        db: AsyncSession,
        brawler1_id: int,
        brawler2_id: int,
        mode: Optional[str]
    ) -> float:
        """
        Get synergy score between two brawlers.
        Uses BrawlerSynergy table if available, otherwise estimates from matchups.
        """
        # Try to get from BrawlerSynergy table
        query = select(BrawlerSynergy).where(
            and_(
                BrawlerSynergy.brawler_a_id == brawler1_id,
                BrawlerSynergy.brawler_b_id == brawler2_id
            )
        )
        
        if mode:
            query = query.where(BrawlerSynergy.mode == mode)
        
        result = await db.execute(query)
        synergy = result.scalar_one_or_none()
        
        if synergy:
            return synergy.synergy_score
        
        # Fallback: estimate from matchup data
        # If both brawlers counter similar enemies, they have good synergy
        return 0.55  # Default moderate synergy
    
    def _generate_strengths(
        self,
        brawlers: List[str],
        pairwise: Dict[str, float],
        overall: float
    ) -> List[str]:
        """Generate strength insights based on synergy analysis"""
        strengths = []
        
        if overall >= 0.65:
            strengths.append("Excellent team synergy - brawlers complement each other well")
        
        # Find best pair
        if pairwise:
            best_pair = max(pairwise.items(), key=lambda x: x[1])
            if best_pair[1] >= 0.60:
                strengths.append(f"Strong duo: {best_pair[0]} ({best_pair[1]:.1%} synergy)")
        
        if len(brawlers) == 3:
            strengths.append("Complete 3v3 composition ready for competitive play")
        
        return strengths or ["Team has potential but may need refinement"]
    
    def _generate_weaknesses(
        self,
        brawlers: List[str],
        pairwise: Dict[str, float],
        overall: float
    ) -> List[str]:
        """Generate weakness insights based on synergy analysis"""
        weaknesses = []
        
        if overall < 0.45:
            weaknesses.append("Low team synergy - consider replacing a brawler")
        
        # Find worst pair
        if pairwise:
            worst_pair = min(pairwise.items(), key=lambda x: x[1])
            if worst_pair[1] < 0.45:
                weaknesses.append(f"Weak combo: {worst_pair[0]} ({worst_pair[1]:.1%} synergy)")
        
        if len(brawlers) < 3:
            weaknesses.append("Team incomplete - add a third brawler for full composition")
        
        return weaknesses or []
    
    def _generate_reasoning(
        self,
        suggested: str,
        brawler1: str,
        brawler2: str,
        synergy1: float,
        synergy2: float
    ) -> str:
        """Generate reasoning for a brawler suggestion"""
        avg = (synergy1 + synergy2) / 2
        
        if avg >= 0.65:
            return f"Excellent synergy with both {brawler1} and {brawler2}"
        elif avg >= 0.55:
            return f"Good compatibility with your current team"
        elif avg >= 0.45:
            return f"Decent fit, covers some gaps in the composition"
        else:
            return f"Alternative option with moderate synergy"
