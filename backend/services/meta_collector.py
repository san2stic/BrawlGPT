"""
Meta Collector Service for BrawlGPT.
Periodically collects meta statistics for different trophy ranges.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from db_models import MetaSnapshot, CachedBrawlerData, CachedEventRotation
from brawlstars import BrawlStarsClient
from crawler import SmartBattleCrawler

logger = logging.getLogger(__name__)


class MetaCollectorService:
    """
    Service that periodically collects meta statistics.
    Runs in the background to keep meta data fresh.
    """

    # Trophy ranges for meta collection
    TROPHY_RANGES = [
        (0, 5000),       # Beginners
        (5000, 10000),   # Intermediate
        (10000, 20000),  # Advanced
        (20000, 30000),  # Expert
        (30000, 50000),  # Master
        (50000, 100000), # Legendary
    ]

    # Default interval between collections (6 hours)
    DEFAULT_INTERVAL_HOURS = 6

    # Maximum snapshots to keep per trophy range
    MAX_SNAPSHOTS_PER_RANGE = 10

    def __init__(
        self,
        brawl_client: BrawlStarsClient,
        interval_hours: int = DEFAULT_INTERVAL_HOURS,
        max_players_per_range: int = 100
    ):
        """
        Initialize the meta collector service.

        Args:
            brawl_client: Brawl Stars API client
            interval_hours: Hours between collection runs
            max_players_per_range: Maximum players to analyze per trophy range
        """
        self.client = brawl_client
        self.crawler = SmartBattleCrawler(brawl_client)
        self.interval_hours = interval_hours
        self.max_players_per_range = max_players_per_range
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self, db_session_factory):
        """
        Start the background collection service.

        Args:
            db_session_factory: Async session factory for database access
        """
        if self._running:
            logger.warning("Meta collector service already running")
            return

        self._running = True
        self._task = asyncio.create_task(
            self._collection_loop(db_session_factory)
        )
        logger.info(f"Meta collector service started (interval: {self.interval_hours}h)")

    async def stop(self):
        """Stop the background collection service."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Meta collector service stopped")

    async def _collection_loop(self, db_session_factory):
        """Main collection loop running in the background."""
        while self._running:
            try:
                logger.info("Starting meta collection cycle")
                async with db_session_factory() as db:
                    await self.collect_all_ranges(db)
                    await self.update_static_data(db)
                    await self.cleanup_old_snapshots(db)
                logger.info("Meta collection cycle completed")
            except Exception as e:
                logger.error(f"Error in meta collection cycle: {e}")

            # Wait for next cycle
            await asyncio.sleep(self.interval_hours * 3600)

    async def collect_all_ranges(self, db: AsyncSession):
        """
        Collect meta data for all trophy ranges.

        Args:
            db: Database session
        """
        for trophy_range in self.TROPHY_RANGES:
            try:
                logger.info(f"Collecting meta for range {trophy_range[0]}-{trophy_range[1]}")
                await self.collect_meta_snapshot(db, trophy_range)
                # Pause between ranges to avoid rate limiting
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Failed to collect meta for range {trophy_range}: {e}")

    async def collect_meta_snapshot(
        self,
        db: AsyncSession,
        trophy_range: tuple[int, int]
    ):
        """
        Collect a meta snapshot for a specific trophy range.

        Args:
            db: Database session
            trophy_range: (min, max) trophy range
        """
        # Get seed players from rankings
        seed_players = await self._get_seed_players(trophy_range)

        if not seed_players:
            logger.warning(f"No seed players found for range {trophy_range}")
            return

        # Run the crawler
        await self.crawler.crawl_meta(
            seed_players=seed_players,
            trophy_range=trophy_range,
            depth=2,
            max_players=self.max_players_per_range,
            db=db
        )

    async def _get_seed_players(
        self,
        trophy_range: tuple[int, int]
    ) -> list[str]:
        """
        Get seed player tags for starting the crawl.

        For higher trophy ranges, uses ranking data.
        For lower ranges, uses a random sample approach.
        """
        seed_players = []

        try:
            # For high trophy ranges, use global rankings
            if trophy_range[0] >= 30000:
                rankings = self.client.get_player_rankings("global", limit=50)
                for player in rankings.get("items", [])[:20]:
                    seed_players.append(player.get("tag", ""))

            # For mid ranges, try to use brawler rankings
            elif trophy_range[0] >= 10000:
                # Get top players for a popular brawler
                try:
                    brawlers = self.client.get_all_brawlers()
                    if brawlers.get("items"):
                        brawler_id = brawlers["items"][0].get("id", 16000000)
                        rankings = self.client.get_brawler_rankings(brawler_id, "global", limit=50)
                        for player in rankings.get("items", [])[:20]:
                            seed_players.append(player.get("tag", ""))
                except Exception:
                    pass

            # If we don't have enough seeds, use club rankings
            if len(seed_players) < 10:
                try:
                    club_rankings = self.client.get_club_rankings("global", limit=10)
                    for club in club_rankings.get("items", [])[:5]:
                        club_tag = club.get("tag", "")
                        if club_tag:
                            members = self.client.get_club_members(club_tag)
                            for member in members.get("items", [])[:10]:
                                seed_players.append(member.get("tag", ""))
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Failed to get seed players: {e}")

        # Remove duplicates and empty tags
        seed_players = list(set(tag for tag in seed_players if tag))
        logger.info(f"Found {len(seed_players)} seed players for range {trophy_range}")

        return seed_players[:30]  # Limit to 30 seeds

    async def update_static_data(self, db: AsyncSession):
        """
        Update cached static data (brawlers, events).

        Args:
            db: Database session
        """
        try:
            # Update brawlers data
            brawlers = self.client.get_all_brawlers()
            for brawler in brawlers.get("items", []):
                brawler_id = brawler.get("id")
                if not brawler_id:
                    continue

                # Check if exists
                stmt = select(CachedBrawlerData).where(
                    CachedBrawlerData.brawler_id == brawler_id
                )
                result = await db.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    existing.name = brawler.get("name", "Unknown")
                    existing.data = brawler
                    existing.last_updated = datetime.utcnow()
                else:
                    new_brawler = CachedBrawlerData(
                        brawler_id=brawler_id,
                        name=brawler.get("name", "Unknown"),
                        data=brawler
                    )
                    db.add(new_brawler)

            # Update events data
            events = self.client.get_event_rotation()

            # Clear old events
            await db.execute(delete(CachedEventRotation))

            # Add new events
            new_events = CachedEventRotation(
                last_updated=datetime.utcnow(),
                active_events=events,
                upcoming_events=[]
            )
            db.add(new_events)

            await db.commit()
            logger.info("Updated cached static data")

        except Exception as e:
            logger.error(f"Failed to update static data: {e}")
            await db.rollback()

    async def cleanup_old_snapshots(self, db: AsyncSession):
        """
        Remove old meta snapshots to prevent database bloat.

        Keeps only the most recent snapshots per trophy range.
        """
        try:
            for trophy_range in self.TROPHY_RANGES:
                # Get all snapshots for this range, ordered by timestamp desc
                stmt = select(MetaSnapshot).where(
                    MetaSnapshot.trophy_range_min == trophy_range[0],
                    MetaSnapshot.trophy_range_max == trophy_range[1]
                ).order_by(MetaSnapshot.timestamp.desc())

                result = await db.execute(stmt)
                snapshots = result.scalars().all()

                # Delete old snapshots beyond the limit
                if len(snapshots) > self.MAX_SNAPSHOTS_PER_RANGE:
                    for old_snapshot in snapshots[self.MAX_SNAPSHOTS_PER_RANGE:]:
                        await db.delete(old_snapshot)

            await db.commit()
            logger.info("Cleaned up old meta snapshots")

        except Exception as e:
            logger.error(f"Failed to cleanup old snapshots: {e}")
            await db.rollback()

    async def get_latest_meta(
        self,
        db: AsyncSession,
        trophy_range: tuple[int, int]
    ) -> Optional[MetaSnapshot]:
        """
        Get the latest meta snapshot for a trophy range.

        Args:
            db: Database session
            trophy_range: (min, max) trophy range

        Returns:
            Latest MetaSnapshot or None
        """
        stmt = select(MetaSnapshot).where(
            MetaSnapshot.trophy_range_min == trophy_range[0],
            MetaSnapshot.trophy_range_max == trophy_range[1]
        ).order_by(MetaSnapshot.timestamp.desc()).limit(1)

        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_meta_for_trophies(
        self,
        db: AsyncSession,
        trophies: int
    ) -> Optional[MetaSnapshot]:
        """
        Get the latest meta snapshot for a player's trophy count.

        Args:
            db: Database session
            trophies: Player's trophy count

        Returns:
            Latest MetaSnapshot for the appropriate range
        """
        # Find the appropriate range
        for low, high in self.TROPHY_RANGES:
            if low <= trophies < high:
                return await self.get_latest_meta(db, (low, high))

        # Default to highest range
        return await self.get_latest_meta(db, (50000, 100000))

    async def trigger_manual_collection(
        self,
        db: AsyncSession,
        trophy_range: Optional[tuple[int, int]] = None
    ):
        """
        Trigger a manual collection outside the normal schedule.

        Args:
            db: Database session
            trophy_range: Optional specific range to collect (all if None)
        """
        if trophy_range:
            await self.collect_meta_snapshot(db, trophy_range)
        else:
            await self.collect_all_ranges(db)
