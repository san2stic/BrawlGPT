"""
Brawler Synergy Analyzer Service for BrawlGPT.
Analyzes team compositions to identify brawler synergies.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple, List, Any
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from db_models import MetaSnapshot, BrawlerSynergy
from crawler import SmartBattleCrawler

logger = logging.getLogger(__name__)


class SynergyAnalyzerService:
    """
    Service that analyzes brawler synergies from battle data.
    Identifies which brawlers work well together based on win rates.
    """

    def __init__(self, interval_hours: int = 2):
        """
        Initialize the synergy analyzer.

        Args:
            interval_hours: Hours between analysis runs
        """
        self.interval_hours = interval_hours
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self, db_session_factory):
        """
        Start the background synergy analysis service.

        Args:
            db_session_factory: Async session factory for database access
        """
        if self._running:
            logger.warning("Synergy analyzer already running")
            return

        self._running = True
        self._task = asyncio.create_task(
            self._analysis_loop(db_session_factory)
        )
        logger.info(f"Synergy analyzer started (interval: {self.interval_hours}h)")

    async def stop(self):
        """Stop the background synergy analysis service."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Synergy analyzer stopped")

    async def _analysis_loop(self, db_session_factory):
        """Main analysis loop running in the background."""
        while self._running:
            try:
                logger.info("Starting synergy analysis cycle")
                async with db_session_factory() as db:
                    await self.analyze_synergies(db)
                logger.info("Synergy analysis cycle completed")
            except Exception as e:
                logger.error(f"Error in synergy analysis cycle: {e}", exc_info=True)

            # Wait for next cycle
            await asyncio.sleep(self.interval_hours * 3600)

    async def analyze_synergies(self, db: AsyncSession):
        """
        Analyze brawler synergies from recent meta snapshots.

        Args:
            db: Database session
        """
        try:
            # Get recent snapshots (last 48 hours for fresher data)
            cutoff_time = datetime.utcnow() - timedelta(hours=48)
            
            stmt = select(MetaSnapshot).where(
                MetaSnapshot.timestamp >= cutoff_time
            )
            result = await db.execute(stmt)
            snapshots = result.scalars().all()

            if not snapshots:
                logger.warning("No recent snapshots found for synergy analysis")
                return

            logger.info(f"Analyzing synergies from {len(snapshots)} snapshots")

            # Extract team composition data from snapshots
            synergy_data = await self._extract_synergy_data(db, snapshots)
            
            # Update or create synergy records
            await self._update_synergy_records(db, synergy_data)

            logger.info(f"Updated {len(synergy_data)} brawler synergy pairs")

        except Exception as e:
            logger.error(f"Failed to analyze synergies: {e}", exc_info=True)
            await db.rollback()

    async def _extract_synergy_data(
        self,
        db: AsyncSession,
        snapshots: List[MetaSnapshot]
    ) -> Dict[Tuple[int, int], Dict[str, Any]]:
        """
        Extract synergy data from meta snapshots.

        Returns:
            Dictionary mapping (brawler_a_id, brawler_b_id) to synergy stats
        """
        synergy_stats = defaultdict(lambda: {
            "games": 0,
            "wins": 0,
            "modes": defaultdict(lambda: {"games": 0, "wins": 0}),
            "trophy_changes": [],
            "brawler_a_name": "",
            "brawler_b_name": ""
        })

        for snapshot in snapshots:
            # Extract team composition data from snapshot if available
            if snapshot.data and "team_compositions" in snapshot.data:
                for comp_data in snapshot.data.get("team_compositions", []):
                    brawlers = comp_data.get("brawlers", [])
                    wins = comp_data.get("wins", 0)
                    games = comp_data.get("games", 1)
                    mode = comp_data.get("mode", "unknown")
                    
                    # Extract all pairs from the composition
                    if len(brawlers) >= 2:
                        for i in range(len(brawlers)):
                            for j in range(i + 1, len(brawlers)):
                                b1 = brawlers[i]
                                b2 = brawlers[j]
                                
                                # Ensure consistent ordering (lower id first)
                                if b1.get("id", 0) > b2.get("id", 0):
                                    b1, b2 = b2, b1
                                
                                key = (b1.get("id"), b2.get("id"))
                                stats = synergy_stats[key]
                                
                                stats["brawler_a_name"] = b1.get("name", "")
                                stats["brawler_b_name"] = b2.get("name", "")
                                stats["games"] += games
                                stats["wins"] += wins
                                stats["modes"][mode]["games"] += games
                                stats["modes"][mode]["wins"] += wins

        return synergy_stats

    async def _update_synergy_records(
        self,
        db: AsyncSession,
        synergy_data: Dict[Tuple[int, int], Dict[str, Any]]
    ):
        """
        Update or create synergy records in the database.

        Args:
            db: Database session
            synergy_data: Extracted synergy statistics
        """
        for (brawler_a_id, brawler_b_id), stats in synergy_data.items():
            if stats["games"] < 5:  # Skip pairs with insufficient data
                continue

            # Check if synergy record exists
            stmt = select(BrawlerSynergy).where(
                and_(
                    BrawlerSynergy.brawler_a_id == brawler_a_id,
                    BrawlerSynergy.brawler_b_id == brawler_b_id
                )
            )
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()

            # Calculate metrics
            win_rate = (stats["wins"] / stats["games"]) * 100 if stats["games"] > 0 else 0
            avg_trophy_change = (
                sum(stats["trophy_changes"]) / len(stats["trophy_changes"])
                if stats["trophy_changes"] else 0
            )

            # Determine data quality
            if stats["games"] >= 50:
                quality = "high"
            elif stats["games"] >= 20:
                quality = "medium"
            else:
                quality = "low"

            # Compile best modes
            best_modes = []
            for mode, mode_stats in stats["modes"].items():
                if mode_stats["games"] > 0:
                    mode_win_rate = (mode_stats["wins"] / mode_stats["games"]) * 100
                    best_modes.append({
                        "mode": mode,
                        "win_rate": round(mode_win_rate, 2),
                        "games": mode_stats["games"]
                    })
            
            best_modes.sort(key=lambda x: x["win_rate"], reverse=True)

            if existing:
                # Update existing record
                existing.games_together = stats["games"]
                existing.wins_together = stats["wins"]
                existing.win_rate = round(win_rate, 2)
                existing.avg_trophy_change = round(avg_trophy_change, 2)
                existing.best_modes = best_modes[:5]  # Keep top 5 modes
                existing.last_updated = datetime.utcnow()
                existing.sample_size_quality = quality
            else:
                # Create new record
                new_synergy = BrawlerSynergy(
                    brawler_a_id=brawler_a_id,
                    brawler_a_name=stats["brawler_a_name"],
                    brawler_b_id=brawler_b_id,
                    brawler_b_name=stats["brawler_b_name"],
                    games_together=stats["games"],
                    wins_together=stats["wins"],
                    win_rate=round(win_rate, 2),
                    avg_trophy_change=round(avg_trophy_change, 2),
                    best_modes=best_modes[:5],
                    sample_size_quality=quality
                )
                db.add(new_synergy)

        await db.commit()

    async def get_brawler_synergies(
        self,
        db: AsyncSession,
        brawler_id: int,
        min_quality: str = "medium",
        limit: int = 10
    ) -> List[BrawlerSynergy]:
        """
        Get the best synergies for a specific brawler.

        Args:
            db: Database session
            brawler_id: ID of the brawler
            min_quality: Minimum data quality ("low", "medium", "high")
            limit: Maximum number of results

        Returns:
            List of BrawlerSynergy objects sorted by win rate
        """
        quality_order = {"low": 1, "medium": 2, "high": 3}
        min_quality_value = quality_order.get(min_quality, 1)

        # Get synergies where this brawler is either A or B
        stmt = select(BrawlerSynergy).where(
            and_(
                (BrawlerSynergy.brawler_a_id == brawler_id) | (BrawlerSynergy.brawler_b_id == brawler_id),
                BrawlerSynergy.sample_size_quality.in_(
                    [k for k, v in quality_order.items() if v >= min_quality_value]
                )
            )
        ).order_by(BrawlerSynergy.win_rate.desc()).limit(limit)

        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_top_synergies(
        self,
        db: AsyncSession,
        min_games: int = 20,
        limit: int = 20
    ) -> List[BrawlerSynergy]:
        """
        Get the top overall synergies across all brawlers.

        Args:
            db: Database session
            min_games: Minimum number of games together
            limit: Maximum number of results

        Returns:
            List of top BrawlerSynergy objects
        """
        stmt = select(BrawlerSynergy).where(
            BrawlerSynergy.games_together >= min_games
        ).order_by(BrawlerSynergy.win_rate.desc()).limit(limit)

        result = await db.execute(stmt)
        return result.scalars().all()

    async def cleanup_old_synergies(self, db: AsyncSession, days_old: int = 7):
        """
        Remove stale synergy records that haven't been updated recently.

        Args:
            db: Database session
            days_old: Number of days before considering a record stale
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            stmt = select(BrawlerSynergy).where(
                BrawlerSynergy.last_updated < cutoff_date
            )
            result = await db.execute(stmt)
            stale_synergies = result.scalars().all()

            for synergy in stale_synergies:
                await db.delete(synergy)

            await db.commit()
            logger.info(f"Cleaned up {len(stale_synergies)} stale synergy records")

        except Exception as e:
            logger.error(f"Failed to cleanup old synergies: {e}")
            await db.rollback()
