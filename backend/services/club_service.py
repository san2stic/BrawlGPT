"""
Club Analysis Service
Analyzes club statistics, member performance, and rankings
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import statistics

logger = logging.getLogger(__name__)


@dataclass
class ClubMember:
    """Club member data"""
    tag: str
    name: str
    trophies: int
    role: str  # 'member', 'senior', 'vicePresident', 'president'
    rank: int
    
    def to_dict(self) -> dict:
        return {
            'tag': self.tag,
            'name': self.name,
            'trophies': self.trophies,
            'role': self.role,
            'rank': self.rank
        }


@dataclass
class ClubStats:
    """Overall club statistics"""
    tag: str
    name: str
    description: str
    total_trophies: int
    required_trophies: int
    member_count: int
    average_trophies: float
    median_trophies: float
    top_player: Optional[ClubMember]
    type: str  # 'open', 'inviteOnly', 'closed'
    
    def to_dict(self) -> dict:
        return {
            'tag': self.tag,
            'name': self.name,
            'description': self.description,
            'total_trophies': self.total_trophies,
            'required_trophies': self.required_trophies,
            'member_count': self.member_count,
            'average_trophies': self.average_trophies,
            'median_trophies': self.median_trophies,
            'top_player': self.top_player.to_dict() if self.top_player else None,
            'type': self.type
        }


@dataclass
class MemberComparison:
    """Comparison of a member against club averages"""
    member: ClubMember
    vs_average: float  # percentage difference from average
    vs_median: float
    percentile: float  # where they rank (0-100)
    
    def to_dict(self) -> dict:
        return {
            'member': self.member.to_dict(),
            'vs_average': self.vs_average,
            'vs_median': self.vs_median,
            'percentile': self.percentile
        }


class ClubService:
    """Service for analyzing club data"""
    
    def __init__(self):
        self.brawl_api = None
    
    def set_brawl_api(self, brawl_client):
        """Set the Brawl Stars API client"""
        self.brawl_api = brawl_client
    
    async def get_club_analysis(
        self,
        db: AsyncSession,
        club_tag: str
    ) -> ClubStats:
        """
        Get comprehensive club statistics.
        
        Args:
            db: Database session
            club_tag: Club tag (with or without #)
            
        Returns:
            ClubStats with comprehensive analysis
        """
        # Ensure tag has # prefix
        if not club_tag.startswith('#'):
            club_tag = f'#{club_tag}'
        
        # Fetch club data from Brawl Stars API
        if not self.brawl_api:
            raise ValueError("Brawl API client not initialized")
        
        try:
            club_data = await self.brawl_api.get_club(club_tag)
        except Exception as e:
            logger.error(f"Error fetching club {club_tag}: {e}")
            raise
        
        # Extract member trophies for statistics
        members = club_data.get('members', [])
        member_trophies = [m['trophies'] for m in members]
        
        # Calculate statistics
        total_trophies = sum(member_trophies)
        avg_trophies = statistics.mean(member_trophies) if member_trophies else 0
        median_trophies = statistics.median(member_trophies) if member_trophies else 0
        
        # Find top player
        top_member = None
        if members:
            top_member_data = max(members, key=lambda m: m['trophies'])
            top_member = ClubMember(
                tag=top_member_data['tag'],
                name=top_member_data['name'],
                trophies=top_member_data['trophies'],
                role=top_member_data.get('role', 'member'),
                rank=1
            )
        
        return ClubStats(
            tag=club_data['tag'],
            name=club_data['name'],
            description=club_data.get('description', ''),
            total_trophies=total_trophies,
            required_trophies=club_data.get('requiredTrophies', 0),
            member_count=len(members),
            average_trophies=avg_trophies,
            median_trophies=median_trophies,
            top_player=top_member,
            type=club_data.get('type', 'open')
        )
    
    async def get_member_rankings(
        self,
        db: AsyncSession,
        club_tag: str
    ) -> List[ClubMember]:
        """
        Get ranked list of club members.
        
        Args:
            db: Database session
            club_tag: Club tag
            
        Returns:
            List of ClubMember sorted by trophies
        """
        if not club_tag.startswith('#'):
            club_tag = f'#{club_tag}'
        
        try:
            club_data = await self.brawl_api.get_club(club_tag)
        except Exception as e:
            logger.error(f"Error fetching club members {club_tag}: {e}")
            raise
        
        members = club_data.get('members', [])
        
        # Sort by trophies descending
        members.sort(key=lambda m: m['trophies'], reverse=True)
        
        # Create ClubMember objects with rank
        ranked_members = []
        for idx, member in enumerate(members):
            ranked_members.append(ClubMember(
                tag=member['tag'],
                name=member['name'],
                trophies=member['trophies'],
                role=member.get('role', 'member'),
                rank=idx + 1
            ))
        
        return ranked_members
    
    async def compare_to_club(
        self,
        db: AsyncSession,
        club_tag: str,
        member_tag: str
    ) -> MemberComparison:
        """
        Compare a member against club averages.
        
        Args:
            db: Database session
            club_tag: Club tag
            member_tag: Member player tag
            
        Returns:
            MemberComparison with statistics
        """
        if not club_tag.startswith('#'):
            club_tag = f'#{club_tag}'
        if not member_tag.startswith('#'):
            member_tag = f'#{member_tag}'
        
        # Get club stats and members
        club_stats = await self.get_club_analysis(db, club_tag)
        members = await self.get_member_rankings(db, club_tag)
        
        # Find the specific member
        target_member = None
        for member in members:
            if member.tag == member_tag:
                target_member = member
                break
        
        if not target_member:
            raise ValueError(f"Member {member_tag} not found in club")
        
        # Calculate comparisons
        vs_average = ((target_member.trophies - club_stats.average_trophies) / club_stats.average_trophies) * 100
        vs_median = ((target_member.trophies - club_stats.median_trophies) / club_stats.median_trophies) * 100
        
        # Calculate percentile (higher is better)
        percentile = ((club_stats.member_count - target_member.rank + 1) / club_stats.member_count) * 100
        
        return MemberComparison(
            member=target_member,
            vs_average=vs_average,
            vs_median=vs_median,
            percentile=percentile
        )
