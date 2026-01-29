"""
Redis Cache Manager for BrawlGPT.
Provides distributed caching with configurable TTLs.
Falls back to in-memory cache if Redis is unavailable.
"""

import logging
import json
import hashlib
from typing import Any, Optional
from datetime import datetime

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    aioredis = None

from config import get_settings

logger = logging.getLogger(__name__)


class RedisCacheManager:
    """
    Redis-based cache manager with automatic fallback to in-memory cache.
    """

    # Cache key prefixes
    PREFIX_PLAYER = "player"
    PREFIX_BATTLELOG = "battles"
    PREFIX_INSIGHTS = "insights"
    PREFIX_META = "meta"
    PREFIX_BRAWLERS = "brawlers"
    PREFIX_EVENTS = "events"

    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize the Redis cache manager.

        Args:
            redis_url: Redis connection URL (defaults to config)
        """
        settings = get_settings()
        self.redis_url = redis_url or settings.redis_url
        self.redis_enabled = settings.redis_enabled and REDIS_AVAILABLE

        # TTL configurations from settings
        self.ttl_player = settings.cache_ttl_player
        self.ttl_battlelog = settings.cache_ttl_battlelog
        self.ttl_insights = settings.cache_ttl_insights
        self.ttl_meta = settings.cache_ttl_meta
        self.ttl_brawlers = settings.cache_ttl_brawlers
        self.ttl_events = settings.cache_ttl_events

        self._redis: Optional[aioredis.Redis] = None
        self._fallback_cache: dict[str, tuple[Any, float]] = {}
        self._connected = False

    async def connect(self):
        """Establish connection to Redis."""
        if not self.redis_enabled:
            logger.info("Redis disabled, using in-memory fallback cache")
            return

        try:
            self._redis = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self._redis.ping()
            self._connected = True
            logger.info(f"Connected to Redis at {self.redis_url}")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Using fallback cache.")
            self._connected = False
            self._redis = None

    async def disconnect(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._connected = False
            logger.info("Disconnected from Redis")

    def _make_key(self, prefix: str, *parts: str) -> str:
        """Create a cache key from prefix and parts."""
        clean_parts = [str(p).upper().replace("#", "").strip() for p in parts]
        return f"brawlgpt:{prefix}:{':'.join(clean_parts)}"

    def _hash_data(self, data: dict) -> str:
        """Create a hash of data for cache invalidation."""
        key_fields = (
            data.get("trophies", 0),
            data.get("3vs3Victories", 0),
            data.get("soloVictories", 0),
            data.get("duoVictories", 0),
        )
        hash_input = str(key_fields).encode()
        return hashlib.md5(hash_input).hexdigest()[:8]

    async def _get(self, key: str) -> Optional[str]:
        """Get value from cache (Redis or fallback)."""
        if self._connected and self._redis:
            try:
                return await self._redis.get(key)
            except Exception as e:
                logger.error(f"Redis GET error: {e}")

        # Fallback to in-memory
        if key in self._fallback_cache:
            value, expiry = self._fallback_cache[key]
            if datetime.now().timestamp() < expiry:
                return value
            else:
                del self._fallback_cache[key]
        return None

    async def _set(self, key: str, value: str, ttl: int):
        """Set value in cache (Redis or fallback)."""
        if self._connected and self._redis:
            try:
                await self._redis.setex(key, ttl, value)
                return
            except Exception as e:
                logger.error(f"Redis SET error: {e}")

        # Fallback to in-memory
        expiry = datetime.now().timestamp() + ttl
        self._fallback_cache[key] = (value, expiry)

    async def _delete(self, key: str):
        """Delete value from cache."""
        if self._connected and self._redis:
            try:
                await self._redis.delete(key)
            except Exception as e:
                logger.error(f"Redis DELETE error: {e}")

        if key in self._fallback_cache:
            del self._fallback_cache[key]

    # =========================================================================
    # PLAYER DATA CACHE
    # =========================================================================

    async def get_player(self, tag: str) -> Optional[dict]:
        """Get cached player data."""
        key = self._make_key(self.PREFIX_PLAYER, tag)
        data = await self._get(key)
        if data:
            logger.debug(f"Cache hit for player: {tag}")
            return json.loads(data)
        return None

    async def set_player(self, tag: str, data: dict):
        """Cache player data."""
        key = self._make_key(self.PREFIX_PLAYER, tag)
        await self._set(key, json.dumps(data), self.ttl_player)
        logger.debug(f"Cached player data for: {tag}")

    # =========================================================================
    # BATTLE LOG CACHE
    # =========================================================================

    async def get_battle_log(self, tag: str) -> Optional[dict]:
        """Get cached battle log."""
        key = self._make_key(self.PREFIX_BATTLELOG, tag)
        data = await self._get(key)
        if data:
            logger.debug(f"Cache hit for battle log: {tag}")
            return json.loads(data)
        return None

    async def set_battle_log(self, tag: str, data: dict):
        """Cache battle log."""
        key = self._make_key(self.PREFIX_BATTLELOG, tag)
        await self._set(key, json.dumps(data), self.ttl_battlelog)
        logger.debug(f"Cached battle log for: {tag}")

    # =========================================================================
    # AI INSIGHTS CACHE
    # =========================================================================

    async def get_insights(self, tag: str, player_data: dict) -> Optional[str]:
        """Get cached AI insights (validated by player data hash)."""
        player_hash = self._hash_data(player_data)
        key = self._make_key(self.PREFIX_INSIGHTS, tag, player_hash)
        data = await self._get(key)
        if data:
            logger.debug(f"Cache hit for insights: {tag}")
            return data
        return None

    async def set_insights(self, tag: str, player_data: dict, insights: str):
        """Cache AI insights."""
        player_hash = self._hash_data(player_data)
        key = self._make_key(self.PREFIX_INSIGHTS, tag, player_hash)
        await self._set(key, insights, self.ttl_insights)
        logger.debug(f"Cached insights for: {tag}")

    # =========================================================================
    # META SNAPSHOT CACHE
    # =========================================================================

    async def get_meta(self, trophy_range: tuple[int, int]) -> Optional[dict]:
        """Get cached meta snapshot for trophy range."""
        key = self._make_key(self.PREFIX_META, str(trophy_range[0]), str(trophy_range[1]))
        data = await self._get(key)
        if data:
            logger.debug(f"Cache hit for meta: {trophy_range}")
            return json.loads(data)
        return None

    async def set_meta(self, trophy_range: tuple[int, int], data: dict):
        """Cache meta snapshot."""
        key = self._make_key(self.PREFIX_META, str(trophy_range[0]), str(trophy_range[1]))
        await self._set(key, json.dumps(data), self.ttl_meta)
        logger.debug(f"Cached meta for: {trophy_range}")

    # =========================================================================
    # BRAWLERS CACHE (STATIC DATA)
    # =========================================================================

    async def get_all_brawlers(self) -> Optional[dict]:
        """Get cached brawlers list."""
        key = self._make_key(self.PREFIX_BRAWLERS, "all")
        data = await self._get(key)
        if data:
            logger.debug("Cache hit for all brawlers")
            return json.loads(data)
        return None

    async def set_all_brawlers(self, data: dict):
        """Cache brawlers list."""
        key = self._make_key(self.PREFIX_BRAWLERS, "all")
        await self._set(key, json.dumps(data), self.ttl_brawlers)
        logger.debug("Cached all brawlers")

    async def get_brawler(self, brawler_id: int) -> Optional[dict]:
        """Get cached brawler details."""
        key = self._make_key(self.PREFIX_BRAWLERS, str(brawler_id))
        data = await self._get(key)
        if data:
            logger.debug(f"Cache hit for brawler: {brawler_id}")
            return json.loads(data)
        return None

    async def set_brawler(self, brawler_id: int, data: dict):
        """Cache brawler details."""
        key = self._make_key(self.PREFIX_BRAWLERS, str(brawler_id))
        await self._set(key, json.dumps(data), self.ttl_brawlers)
        logger.debug(f"Cached brawler: {brawler_id}")

    # =========================================================================
    # EVENTS CACHE
    # =========================================================================

    async def get_events(self) -> Optional[dict]:
        """Get cached event rotation."""
        key = self._make_key(self.PREFIX_EVENTS, "rotation")
        data = await self._get(key)
        if data:
            logger.debug("Cache hit for events")
            return json.loads(data)
        return None

    async def set_events(self, data: dict):
        """Cache event rotation."""
        key = self._make_key(self.PREFIX_EVENTS, "rotation")
        await self._set(key, json.dumps(data), self.ttl_events)
        logger.debug("Cached events")

    # =========================================================================
    # CACHE MANAGEMENT
    # =========================================================================

    async def clear_player(self, tag: str):
        """Clear all cached data for a player."""
        await self._delete(self._make_key(self.PREFIX_PLAYER, tag))
        await self._delete(self._make_key(self.PREFIX_BATTLELOG, tag))
        # Note: insights will expire naturally due to hash-based keys
        logger.debug(f"Cleared cache for player: {tag}")

    async def clear_all(self):
        """Clear all cached data."""
        if self._connected and self._redis:
            try:
                keys = await self._redis.keys("brawlgpt:*")
                if keys:
                    await self._redis.delete(*keys)
            except Exception as e:
                logger.error(f"Redis CLEAR error: {e}")

        self._fallback_cache.clear()
        logger.info("All caches cleared")

    async def get_stats(self) -> dict:
        """Get cache statistics."""
        stats = {
            "backend": "redis" if self._connected else "in-memory",
            "connected": self._connected,
            "ttls": {
                "player": self.ttl_player,
                "battlelog": self.ttl_battlelog,
                "insights": self.ttl_insights,
                "meta": self.ttl_meta,
                "brawlers": self.ttl_brawlers,
                "events": self.ttl_events,
            }
        }

        if self._connected and self._redis:
            try:
                info = await self._redis.info("memory")
                stats["redis"] = {
                    "used_memory": info.get("used_memory_human"),
                    "keys": await self._redis.dbsize(),
                }
            except Exception:
                pass
        else:
            stats["fallback"] = {
                "entries": len(self._fallback_cache)
            }

        return stats


# Singleton instance
redis_cache = RedisCacheManager()
