"""
Global Meta Aggregator Service for BrawlGPT.
Aggregates meta data across all trophy ranges to provide global insights.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from db_models import (
    MetaSnapshot, BrawlerMeta, GlobalMetaAggregate,
    BrawlerTrendHistory, GlobalTrendInsight
)
from ai_analyst import MetaAnalyst

logger = logging.getLogger(__name__)


class GlobalMetaAggregatorService:
    """
    Service that aggregates meta data from all trophy ranges
    to provide a unified global view of the game meta.
    """

    def __init__(self, ai_analyst: MetaAnalyst, interval_minutes: int = 60):
        """
        Initialize the global meta aggregator.

        Args:
            ai_analyst: AI analyst instance for generating insights
            interval_minutes: Minutes between aggregation runs
        """
        self.ai_analyst = ai_analyst
        self.interval_minutes = interval_minutes
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._db_session_factory = None

    async def start(self, db_session_factory):
        """
        Start the background aggregation service.

        Args:
            db_session_factory: Async session factory for database access
        """
        if self._running:
            logger.warning("Global meta aggregator already running")
            return

        self._db_session_factory = db_session_factory
        self._running = True
        self._task = asyncio.create_task(
            self._aggregation_loop(db_session_factory)
        )
        logger.info(f"Global meta aggregator started (interval: {self.interval_minutes}min)")

    async def stop(self):
        """Stop the background aggregation service."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Global meta aggregator stopped")

    async def _aggregation_loop(self, db_session_factory):
        """Main aggregation loop running in the background."""
        while self._running:
            try:
                logger.info("Starting global meta aggregation cycle")
                async with db_session_factory() as db:
                    await self.aggregate_global_meta(db)
                logger.info("Global meta aggregation cycle completed")
            except Exception as e:
                logger.error(f"Error in global meta aggregation cycle: {e}", exc_info=True)

            # Wait for next cycle
            await asyncio.sleep(self.interval_minutes * 60)

    async def aggregate_global_meta(self, db: AsyncSession) -> Optional[GlobalMetaAggregate]:
        """
        Aggregate meta data from all trophy ranges into a global view.

        Args:
            db: Database session

        Returns:
            Created GlobalMetaAggregate or None if no data available
        """
        try:
            # Get recent snapshots from all trophy ranges (last 24 hours)
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            
            stmt = select(MetaSnapshot).where(
                MetaSnapshot.timestamp >= cutoff_time
            ).order_by(MetaSnapshot.timestamp.desc())
            
            result = await db.execute(stmt)
            snapshots = result.scalars().all()

            if not snapshots:
                logger.warning("No recent meta snapshots found for aggregation")
                return None

            logger.info(f"Aggregating {len(snapshots)} meta snapshots")

            # Aggregate brawler stats across all snapshots
            global_brawler_stats = await self._aggregate_brawler_stats(db, snapshots)
            
            # Calculate global statistics
            total_battles = sum(s.sample_size for s in snapshots)
            unique_players = len(set(
                player_tag 
                for s in snapshots 
                if s.data and 'analyzed_players' in s.data 
                for player_tag in s.data.get('analyzed_players', [])
            ))

            # Compile global data
            global_data = {
                "top_brawlers": global_brawler_stats[:20],  # Top 20
                "total_brawlers_tracked": len(global_brawler_stats),
                "snapshot_count": len(snapshots),
                "trophy_ranges_analyzed": len(set((s.trophy_range_min, s.trophy_range_max) for s in snapshots)),
                "mode_breakdown": await self._aggregate_mode_stats(db, snapshots),
                "timestamp": datetime.utcnow().isoformat()
            }

            # Create global meta aggregate
            aggregate = GlobalMetaAggregate(
                timestamp=datetime.utcnow(),
                total_battles_analyzed=total_battles,
                total_unique_players=unique_players,
                data=global_data
            )
            
            db.add(aggregate)
            await db.commit()
            await db.refresh(aggregate)

            logger.info(f"Created global meta aggregate: {aggregate.id}")

            # Generate AI insights asynchronously
            asyncio.create_task(self._generate_ai_insights(aggregate_id=aggregate.id))

            return aggregate

        except Exception as e:
            logger.error(f"Failed to aggregate global meta: {e}", exc_info=True)
            await db.rollback()
            return None

    async def _aggregate_brawler_stats(
        self,
        db: AsyncSession,
        snapshots: List[MetaSnapshot]
    ) -> List[Dict[str, Any]]:
        """
        Aggregate brawler statistics across multiple snapshots.

        Returns:
            List of brawler stats sorted by performance
        """
        brawler_aggregates = defaultdict(lambda: {
            "total_games": 0,
            "total_wins": 0,
            "appearances": 0,
            "trophy_changes": []
        })

        # Collect all brawler meta entries
        for snapshot in snapshots:
            # Load brawler stats for this snapshot
            stmt = select(BrawlerMeta).where(BrawlerMeta.snapshot_id == snapshot.id)
            result = await db.execute(stmt)
            brawler_metas = result.scalars().all()

            for bm in brawler_metas:
                key = (bm.brawler_id, bm.brawler_name)
                agg = brawler_aggregates[key]
                
                # Estimate games from pick rate (assuming pick rate is percentage)
                estimated_games = int((bm.pick_rate / 100.0) * snapshot.sample_size) if bm.pick_rate else 0
                estimated_wins = int(estimated_games * (bm.win_rate / 100.0)) if bm.win_rate else 0
                
                agg["total_games"] += estimated_games
                agg["total_wins"] += estimated_wins
                agg["appearances"] += 1
                if bm.avg_trophies_change:
                    agg["trophy_changes"].append(bm.avg_trophies_change)

        # Compile results
        results = []
        for (brawler_id, brawler_name), stats in brawler_aggregates.items():
            if stats["total_games"] > 0:
                win_rate = (stats["total_wins"] / stats["total_games"]) * 100
                avg_trophy_change = (
                    sum(stats["trophy_changes"]) / len(stats["trophy_changes"])
                    if stats["trophy_changes"] else 0
                )
                
                results.append({
                    "brawler_id": brawler_id,
                    "brawler_name": brawler_name,
                    "games": stats["total_games"],
                    "wins": stats["total_wins"],
                    "win_rate": round(win_rate, 2),
                    "avg_trophy_change": round(avg_trophy_change, 2),
                    "pick_rate": round((stats["total_games"] / sum(s.sample_size for s in snapshots)) * 100, 2),
                    "data_quality": "high" if stats["appearances"] >= 3 else "medium" if stats["appearances"] >= 2 else "low"
                })

        # Sort by a composite score (win rate + pick rate)
        results.sort(
            key=lambda x: (x["win_rate"] * 0.6 + x["pick_rate"] * 0.4),
            reverse=True
        )

        return results

    async def _aggregate_mode_stats(
        self,
        db: AsyncSession,
        snapshots: List[MetaSnapshot]
    ) -> Dict[str, Any]:
        """
        Aggregate statistics by game mode.

        Returns:
            Dictionary of mode statistics
        """
        mode_stats = defaultdict(lambda: {"brawlers": defaultdict(lambda: {"games": 0, "wins": 0})})

        for snapshot in snapshots:
            stmt = select(BrawlerMeta).where(BrawlerMeta.snapshot_id == snapshot.id)
            result = await db.execute(stmt)
            brawler_metas = result.scalars().all()

            for bm in brawler_metas:
                if bm.best_modes:
                    for mode_data in bm.best_modes:
                        mode_name = mode_data.get("mode", "unknown")
                        mode_win_rate = mode_data.get("win_rate", 0)
                        
                        # Rough estimation of games
                        estimated_games = 10  # Placeholder
                        estimated_wins = int(estimated_games * (mode_win_rate / 100.0))
                        
                        mode_stats[mode_name]["brawlers"][bm.brawler_name]["games"] += estimated_games
                        mode_stats[mode_name]["brawlers"][bm.brawler_name]["wins"] += estimated_wins

        # Compile results
        result = {}
        for mode, data in mode_stats.items():
            best_brawlers = []
            for brawler_name, stats in data["brawlers"].items():
                if stats["games"] > 0:
                    win_rate = (stats["wins"] / stats["games"]) * 100
                    best_brawlers.append({
                        "name": brawler_name,
                        "win_rate": round(win_rate, 2),
                        "games": stats["games"]
                    })
            
            best_brawlers.sort(key=lambda x: x["win_rate"], reverse=True)
            result[mode] = {"best_brawlers": best_brawlers[:5]}

        return result

    async def _generate_ai_insights(self, aggregate_id: int):
        """
        Generate AI insights for a global meta aggregate.
        Runs asynchronously to avoid blocking aggregation.
        """
        try:
            async with self._db_session_factory() as db:
                # Get the aggregate
                stmt = select(GlobalMetaAggregate).where(GlobalMetaAggregate.id == aggregate_id)
                result = await db.execute(stmt)
                aggregate = result.scalar_one_or_none()

                if not aggregate:
                    logger.error(f"Aggregate {aggregate_id} not found for AI insights")
                    return

                # Generate insights
                insights = await self.ai_analyst.analyze_global_meta(aggregate.data)
                
                # Update aggregate with insights
                aggregate.ai_insights = insights
                aggregate.ai_generated_at = datetime.utcnow()
                
                await db.commit()
                logger.info(f"Generated AI insights for aggregate {aggregate_id}")

        except Exception as e:
            logger.error(f"Failed to generate AI insights: {e}", exc_info=True)

    async def get_latest_global_meta(self, db: AsyncSession) -> Optional[GlobalMetaAggregate]:
        """
        Get the most recent global meta aggregate.

        Args:
            db: Database session

        Returns:
            Latest GlobalMetaAggregate or None
        """
        stmt = select(GlobalMetaAggregate).order_by(
            GlobalMetaAggregate.timestamp.desc()
        ).limit(1)
        
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def cleanup_old_aggregates(self, db: AsyncSession, retention_days: int = 30):
        """
        Remove old global meta aggregates to prevent database bloat.

        Args:
            db: Database session
            retention_days: Number of days to retain data
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            
            stmt = select(GlobalMetaAggregate).where(
                GlobalMetaAggregate.timestamp < cutoff_date
            )
            result = await db.execute(stmt)
            old_aggregates = result.scalars().all()

            for aggregate in old_aggregates:
                await db.delete(aggregate)

            await db.commit()
            logger.info(f"Cleaned up {len(old_aggregates)} old global meta aggregates")

        except Exception as e:
            logger.error(f"Failed to cleanup old aggregates: {e}")
            await db.rollback()
