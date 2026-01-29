"""
Trend Detection Engine for BrawlGPT.
Detects meta trends and shifts by analyzing historical data.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from db_models import (
    BrawlerMeta, MetaSnapshot, BrawlerTrendHistory,
    GlobalTrendInsight
)
from ai_analyst import MetaAnalyst

logger = logging.getLogger(__name__)


class TrendDetectorService:
    """
    Service that detects trends in the meta by comparing
    historical brawler performance data.
    """

    def __init__(
        self,
        ai_analyst: MetaAnalyst,
        interval_hours: int = 6,
        min_confidence: float = 0.7
    ):
        """
        Initialize the trend detector.

        Args:
            ai_analyst: AI analyst for generating insights
            interval_hours: Hours between detection runs
            min_confidence: Minimum confidence score for insights
        """
        self.ai_analyst = ai_analyst
        self.interval_hours = interval_hours
        self.min_confidence = min_confidence
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self, db_session_factory):
        """
        Start the background trend detection service.

        Args:
            db_session_factory: Async session factory for database access
        """
        if self._running:
            logger.warning("Trend detector already running")
            return

        self._running = True
        self._task = asyncio.create_task(
            self._detection_loop(db_session_factory)
        )
        logger.info(f"Trend detector started (interval: {self.interval_hours}h)")

    async def stop(self):
        """Stop the background trend detection service."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Trend detector stopped")

    async def _detection_loop(self, db_session_factory):
        """Main detection loop running in the background."""
        while self._running:
            try:
                logger.info("Starting trend detection cycle")
                async with db_session_factory() as db:
                    await self.detect_trends(db)
                logger.info("Trend detection cycle completed")
            except Exception as e:
                logger.error(f"Error in trend detection cycle: {e}", exc_info=True)

            # Wait for next cycle
            await asyncio.sleep(self.interval_hours * 3600)

    async def detect_trends(self, db: AsyncSession):
        """
        Detect trends by analyzing brawler performance over time.

        Args:
            db: Database session
        """
        try:
            # Update brawler trend history
            await self._update_trend_history(db)
            
            # Detect significant changes
            insights = await self._detect_significant_changes(db)
            
            # Save insights
            for insight in insights:
                db.add(insight)
            
            await db.commit()
            logger.info(f"Detected {len(insights)} trend insights")

        except Exception as e:
            logger.error(f"Failed to detect trends: {e}", exc_info=True)
            await db.rollback()

    async def _update_trend_history(self, db: AsyncSession):
        """
        Update the brawler trend history table with current stats.

        Args:
            db: Database session
        """
        # Get the most recent snapshot from each trophy range
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        stmt = select(MetaSnapshot).where(
            MetaSnapshot.timestamp >= cutoff_time
        ).order_by(MetaSnapshot.timestamp.desc())
        
        result = await db.execute(stmt)
        recent_snapshots = result.scalars().all()

        if not recent_snapshots:
            logger.warning("No recent snapshots for trend history update")
            return

        # Aggregate brawler stats across snapshots
        brawler_stats = defaultdict(lambda: {
            "total_games": 0,
            "total_wins": 0,
            "total_pick_rate": 0,
            "snapshot_count": 0,
            "name": ""
        })

        total_battles = sum(s.sample_size for s in recent_snapshots)

        for snapshot in recent_snapshots:
            # Get brawler metas for this snapshot
            stmt = select(BrawlerMeta).where(BrawlerMeta.snapshot_id == snapshot.id)
            result = await db.execute(stmt)
            brawler_metas = result.scalars().all()

            for bm in brawler_metas:
                stats = brawler_stats[bm.brawler_id]
                stats["name"] = bm.brawler_name
                
                # Estimate games
                estimated_games = int((bm.pick_rate / 100.0) * snapshot.sample_size) if bm.pick_rate else 0
                estimated_wins = int(estimated_games * (bm.win_rate / 100.0)) if bm.win_rate else 0
                
                stats["total_games"] += estimated_games
                stats["total_wins"] += estimated_wins
                stats["total_pick_rate"] += bm.pick_rate or 0
                stats["snapshot_count"] += 1

        # Create trend history entries
        brawler_performances = []
        for brawler_id, stats in brawler_stats.items():
            if stats["total_games"] > 0:
                win_rate = (stats["total_wins"] / stats["total_games"]) * 100
                pick_rate = stats["total_pick_rate"] / stats["snapshot_count"]
                
                brawler_performances.append({
                    "brawler_id": brawler_id,
                    "name": stats["name"],
                    "win_rate": win_rate,
                    "pick_rate": pick_rate,
                    "games": stats["total_games"]
                })

        # Sort by performance score and assign ranks
        brawler_performances.sort(
            key=lambda x: x["win_rate"] * 0.6 + x["pick_rate"] * 0.4,
            reverse=True
        )
        
        brawler_performances_by_popularity = sorted(
            brawler_performances,
            key=lambda x: x["pick_rate"],
            reverse=True
        )

        # Assign ranks and detect trends
        for idx, perf in enumerate(brawler_performances):
            perf["performance_rank"] = idx + 1
        
        for idx, perf in enumerate(brawler_performances_by_popularity):
            if perf["brawler_id"]:
                # Find in performance list
                for p in brawler_performances:
                    if p["brawler_id"] == perf["brawler_id"]:
                        p["popularity_rank"] = idx + 1
                        break

        # Compare with previous history to determine trends
        for perf in brawler_performances:
            # Get previous trend history (48-72 hours ago)
            lookback_start = datetime.utcnow() - timedelta(hours=72)
            lookback_end = datetime.utcnow() - timedelta(hours=48)
            
            stmt = select(BrawlerTrendHistory).where(
                and_(
                    BrawlerTrendHistory.brawler_id == perf["brawler_id"],
                    BrawlerTrendHistory.timestamp >= lookback_start,
                    BrawlerTrendHistory.timestamp <= lookback_end
                )
            ).order_by(BrawlerTrendHistory.timestamp.desc()).limit(1)
            
            result = await db.execute(stmt)
            previous = result.scalar_one_or_none()

            # Determine trend
            trend_direction = "stable"
            trend_strength = 0.0

            if previous:
                pick_rate_change = perf["pick_rate"] - previous.pick_rate
                win_rate_change = perf["win_rate"] - previous.win_rate
                
                # Calculate trend strength (0-1)
                pick_rate_delta = abs(pick_rate_change) / max(previous.pick_rate, 1)
                win_rate_delta = abs(win_rate_change) / max(previous.win_rate, 1)
                trend_strength = min((pick_rate_delta + win_rate_delta) / 2, 1.0)

                # Determine direction
                if pick_rate_change > 2.0 or win_rate_change > 3.0:
                    trend_direction = "rising"
                elif pick_rate_change < -2.0 or win_rate_change < -3.0:
                    trend_direction = "falling"
                else:
                    trend_direction = "stable"

            # Create trend history entry
            trend_entry = BrawlerTrendHistory(
                brawler_id=perf["brawler_id"],
                brawler_name=perf["name"],
                timestamp=datetime.utcnow(),
                pick_rate=round(perf["pick_rate"], 2),
                win_rate=round(perf["win_rate"], 2),
                avg_trophy_change=0.0,  # Could be added later
                trend_direction=trend_direction,
                trend_strength=round(trend_strength, 3),
                popularity_rank=perf.get("popularity_rank", 999),
                performance_rank=perf.get("performance_rank", 999),
                games_analyzed=perf["games"]
            )
            db.add(trend_entry)

        await db.commit()
        logger.info(f"Updated trend history for {len(brawler_performances)} brawlers")

    async def _detect_significant_changes(self, db: AsyncSession) -> List[GlobalTrendInsight]:
        """
        Detect significant meta shifts and create insights.

        Returns:
            List of GlobalTrendInsight objects
        """
        insights = []

        # Get recent trend history (last 24 hours)
        recent_time = datetime.utcnow() - timedelta(hours=24)
        
        stmt = select(BrawlerTrendHistory).where(
            BrawlerTrendHistory.timestamp >= recent_time
        ).order_by(BrawlerTrendHistory.timestamp.desc())
        
        result = await db.execute(stmt)
        recent_trends = result.scalars().all()

        # Group by brawler
        brawler_trends = defaultdict(list)
        for trend in recent_trends:
            brawler_trends[trend.brawler_id].append(trend)

        # Detect rising stars
        for brawler_id, trends in brawler_trends.items():
            if not trends:
                continue
            
            latest = trends[0]
            
            # Check for strong rising trend
            if latest.trend_direction == "rising" and latest.trend_strength > 0.3:
                insight = GlobalTrendInsight(
                    timestamp=datetime.utcnow(),
                    insight_type="brawler_rise",
                    title=f"{latest.brawler_name} en Forte Montée",
                    content=f"**{latest.brawler_name}** connaît une forte progression dans la méta.\n\n"
                            f"- **Win Rate**: {latest.win_rate:.1f}%\n"
                            f"- **Pick Rate**: {latest.pick_rate:.1f}%\n"
                            f"- **Tendance**: {latest.trend_direction} (force: {latest.trend_strength:.1%})\n\n"
                            f"Ce brawler gagne en popularité et en performance. C'est le moment de le maîtriser !",
                    data={
                        "brawler_id": brawler_id,
                        "brawler_name": latest.brawler_name,
                        "win_rate": latest.win_rate,
                        "pick_rate": latest.pick_rate,
                        "trend_strength": latest.trend_strength
                    },
                    confidence_score=min(latest.trend_strength + 0.3, 1.0),
                    impact_level="high" if latest.trend_strength > 0.5 else "medium",
                    expires_at=datetime.utcnow() + timedelta(days=3)
                )
                insights.append(insight)

            # Check for falling trend
            elif latest.trend_direction == "falling" and latest.trend_strength > 0.3:
                insight = GlobalTrendInsight(
                    timestamp=datetime.utcnow(),
                    insight_type="brawler_fall",
                    title=f"{latest.brawler_name} en Déclin",
                    content=f"**{latest.brawler_name}** perd en efficacité dans la méta actuelle.\n\n"
                            f"- **Win Rate**: {latest.win_rate:.1f}%\n"
                            f"- **Pick Rate**: {latest.pick_rate:.1f}%\n"
                            f"- **Tendance**: {latest.trend_direction} (force: {latest.trend_strength:.1%})\n\n"
                            f"Il pourrait être judicieux d'explorer d'autres options.",
                    data={
                        "brawler_id": brawler_id,
                        "brawler_name": latest.brawler_name,
                        "win_rate": latest.win_rate,
                        "pick_rate": latest.pick_rate,
                        "trend_strength": latest.trend_strength
                    },
                    confidence_score=min(latest.trend_strength + 0.2, 1.0),
                    impact_level="medium",
                    expires_at=datetime.utcnow() + timedelta(days=3)
                )
                insights.append(insight)

        # Filter by confidence threshold
        insights = [i for i in insights if i.confidence_score >= self.min_confidence]
        
        return insights

    async def get_trending_brawlers(
        self,
        db: AsyncSession,
        direction: str = "rising",
        min_strength: float = 0.2,
        limit: int = 10
    ) -> List[BrawlerTrendHistory]:
        """
        Get trending brawlers.

        Args:
            db: Database session
            direction: "rising", "falling", or "stable"
            min_strength: Minimum trend strength
            limit: Maximum number of results

        Returns:
            List of BrawlerTrendHistory objects
        """
        # Get recent trends (last 24 hours)
        recent_time = datetime.utcnow() - timedelta(hours=24)
        
        stmt = select(BrawlerTrendHistory).where(
            and_(
                BrawlerTrendHistory.timestamp >= recent_time,
                BrawlerTrendHistory.trend_direction == direction,
                BrawlerTrendHistory.trend_strength >= min_strength
            )
        ).order_by(
            BrawlerTrendHistory.trend_strength.desc()
        ).limit(limit)

        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_recent_insights(
        self,
        db: AsyncSession,
        insight_type: Optional[str] = None,
        days: int = 7,
        limit: int = 20
    ) -> List[GlobalTrendInsight]:
        """
        Get recent trend insights.

        Args:
            db: Database session
            insight_type: Optional filter by type
            days: Number of days to look back
            limit: Maximum number of results

        Returns:
            List of GlobalTrendInsight objects
        """
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        
        conditions = [
            GlobalTrendInsight.timestamp >= cutoff_time,
            GlobalTrendInsight.is_active == True
        ]
        
        if insight_type:
            conditions.append(GlobalTrendInsight.insight_type == insight_type)

        stmt = select(GlobalTrendInsight).where(
            and_(*conditions)
        ).order_by(
            GlobalTrendInsight.timestamp.desc()
        ).limit(limit)

        result = await db.execute(stmt)
        return result.scalars().all()

    async def cleanup_old_insights(self, db: AsyncSession):
        """
        Mark expired insights as inactive.

        Args:
            db: Database session
        """
        try:
            stmt = select(GlobalTrendInsight).where(
                and_(
                    GlobalTrendInsight.expires_at < datetime.utcnow(),
                    GlobalTrendInsight.is_active == True
                )
            )
            result = await db.execute(stmt)
            expired_insights = result.scalars().all()

            for insight in expired_insights:
                insight.is_active = False

            await db.commit()
            logger.info(f"Marked {len(expired_insights)} insights as inactive")

        except Exception as e:
            logger.error(f"Failed to cleanup old insights: {e}")
            await db.rollback()
