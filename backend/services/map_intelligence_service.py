"""
Map Intelligence Service
Provides map-specific meta recommendations based on performance data
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
import logging

from db_models import MapBrawlerPerformance

logger = logging.getLogger(__name__)


@dataclass
class MapMetaBrawler:
    """Brawler performance on a specific map"""
    brawler_id: int
    brawler_name: str
    win_rate: float
    pick_rate: float
    sample_size: int
    average_trophies: float
    confidence: str  # 'low', 'medium', 'high'
    
    def to_dict(self) -> dict:
        return {
            'brawler_id': self.brawler_id,
            'brawler_name': self.brawler_name,
            'win_rate': self.win_rate,
            'pick_rate': self.pick_rate,
            'sample_size': self.sample_size,
            'average_trophies': self.average_trophies,
            'confidence': self.confidence
        }


@dataclass
class MapMeta:
    """Complete meta analysis for a map"""
    map_name: str
    mode: str
    top_brawlers: List[MapMetaBrawler]
    total_games: int
    last_updated: Optional[str]
    
    def to_dict(self) -> dict:
        return {
            'map_name': self.map_name,
            'mode': self.mode,
            'top_brawlers': [b.to_dict() for b in self.top_brawlers],
            'total_games': self.total_games,
            'last_updated': self.last_updated
        }


class MapIntelligenceService:
    """Service for analyzing map-specific meta and recommendations"""
    
    def __init__(self):
        self.brawl_api = None
        self.min_sample_size = 50  # Minimum games for confidence
    
    def set_brawl_api(self, brawl_client):
        """Set the Brawl Stars API client"""
        self.brawl_api = brawl_client
    
    async def get_map_meta(
        self,
        db: AsyncSession,
        map_name: str,
        mode: str,
        top_n: int = 10,
        min_trophies: int = 0
    ) -> MapMeta:
        """
        Get the meta for a specific map.
        
        Args:
            db: Database session
            map_name: Name of the map
            mode: Game mode
            top_n: Number of top brawlers to return
            min_trophies: Minimum trophy range filter
            
        Returns:
            MapMeta with top brawlers and statistics
        """
        # Query map performance data
        query = select(MapBrawlerPerformance).where(
            and_(
                MapBrawlerPerformance.map_name == map_name,
                MapBrawlerPerformance.mode == mode
            )
        )
        
        if min_trophies > 0:
            query = query.where(MapBrawlerPerformance.average_trophies >= min_trophies)
        
        # Order by win rate descending
        query = query.order_by(desc(MapBrawlerPerformance.win_rate))
        query = query.limit(top_n)
        
        result = await db.execute(query)
        performances = result.scalars().all()
        
        # Convert to MapMetaBrawler objects
        top_brawlers = []
        total_games = 0
        
        for perf in performances:
            confidence = self._calculate_confidence(perf.sample_size)
            
            meta_brawler = MapMetaBrawler(
                brawler_id=perf.brawler_id,
                brawler_name=perf.brawler_name,
                win_rate=perf.win_rate,
                pick_rate=perf.pick_rate,
                sample_size=perf.sample_size,
                average_trophies=perf.average_trophies,
                confidence=confidence
            )
            
            top_brawlers.append(meta_brawler)
            total_games += perf.sample_size
        
        # Get last updated timestamp
        last_updated = None
        if performances:
            last_updated = str(performances[0].updated_at) if hasattr(performances[0], 'updated_at') else None
        
        return MapMeta(
            map_name=map_name,
            mode=mode,
            top_brawlers=top_brawlers,
            total_games=total_games,
            last_updated=last_updated
        )
    
    async def get_current_rotation_meta(
        self,
        db: AsyncSession,
        top_n_per_map: int = 5
    ) -> Dict[str, MapMeta]:
        """
        Get meta for all maps in current rotation.
        
        Args:
            db: Database session
            top_n_per_map: Number of brawlers per map
            
        Returns:
            Dictionary mapping map names to MapMeta objects
        """
        # Get unique map/mode combinations from recent data
        query = select(
            MapBrawlerPerformance.map_name,
            MapBrawlerPerformance.mode
        ).distinct()
        
        result = await db.execute(query)
        map_modes = result.all()
        
        rotation_meta = {}
        
        for map_name, mode in map_modes:
            try:
                meta = await self.get_map_meta(
                    db,
                    map_name,
                    mode,
                    top_n=top_n_per_map
                )
                
                key = f"{map_name}_{mode}"
                rotation_meta[key] = meta
            except Exception as e:
                logger.error(f"Error getting meta for {map_name} ({mode}): {e}")
                continue
        
        return rotation_meta
    
    async def get_brawler_best_maps(
        self,
        db: AsyncSession,
        brawler_name: str,
        top_n: int = 5
    ) -> List[MapMetaBrawler]:
        """
        Find the best maps for a specific brawler.
        
        Args:
            db: Database session
            brawler_name: Name of the brawler
            top_n: Number of maps to return
            
        Returns:
            List of MapMetaBrawler sorted by win rate
        """
        query = select(MapBrawlerPerformance).where(
            MapBrawlerPerformance.brawler_name == brawler_name
        ).order_by(
            desc(MapBrawlerPerformance.win_rate)
        ).limit(top_n)
        
        result = await db.execute(query)
        performances = result.scalars().all()
        
        best_maps = []
        for perf in performances:
            confidence = self._calculate_confidence(perf.sample_size)
            
            best_maps.append(MapMetaBrawler(
                brawler_id=perf.brawler_id,
                brawler_name=perf.brawler_name,
                win_rate=perf.win_rate,
                pick_rate=perf.pick_rate,
                sample_size=perf.sample_size,
                average_trophies=perf.average_trophies,
                confidence=confidence
            ))
        
        return best_maps
    
    def _calculate_confidence(self, sample_size: int) -> str:
        """Calculate confidence level based on sample size"""
        if sample_size >= self.min_sample_size * 10:
            return 'high'
        elif sample_size >= self.min_sample_size:
            return 'medium'
        else:
            return 'low'
