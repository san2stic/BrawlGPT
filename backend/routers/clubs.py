"""
Club Analysis Router
API endpoints for club statistics and member analysis
"""

from fastapi import APIRouter, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import logging

from database import AsyncSessionLocal
from services.club_service import ClubService

router = APIRouter(prefix="/api/clubs", tags=["clubs"])
logger = logging.getLogger(__name__)

# Initialize service (will be configured with API client in main.py)
club_service = ClubService()


@router.get("/{club_tag}")
async def get_club_stats(club_tag: str):
    """
    Get comprehensive club statistics.
    
    Args:
        club_tag: Club tag (with or without #)
        
    Returns:
        Club statistics including totals, averages, and top player
    """
    try:
        logger.info(f"Fetching club stats for {club_tag}")
        async with AsyncSessionLocal() as db:
            stats = await club_service.get_club_analysis(db, club_tag)
            return stats.to_dict()
    except ValueError as e:
        logger.error(f"Invalid club tag {club_tag}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching club {club_tag}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch club data")


@router.get("/{club_tag}/members")
async def get_club_members(club_tag: str):
    """
    Get ranked list of club members.
    
    Args:
        club_tag: Club tag
        
    Returns:
        List of members sorted by trophies (descending)
    """
    try:
        logger.info(f"Fetching club members for {club_tag}")
        async with AsyncSessionLocal() as db:
            members = await club_service.get_member_rankings(db, club_tag)
            return {
                "members": [m.to_dict() for m in members],
                "total": len(members)
            }
    except ValueError as e:
        logger.error(f"Invalid club tag {club_tag}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching members for {club_tag}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch club members")


@router.get("/{club_tag}/compare/{member_tag}")
async def compare_member(club_tag: str, member_tag: str):
    """
    Compare a member against club averages.
    
    Args:
        club_tag: Club tag
        member_tag: Member player tag
        
    Returns:
        Comparison statistics (vs average, vs median, percentile)
    """
    try:
        logger.info(f"Comparing member {member_tag} in club {club_tag}")
        async with AsyncSessionLocal() as db:
            comparison = await club_service.compare_to_club(db, club_tag, member_tag)
            return comparison.to_dict()
    except ValueError as e:
        logger.error(f"Error comparing member: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error comparing member {member_tag}: {e}")
        raise HTTPException(status_code=500, detail="Failed to compare member")
