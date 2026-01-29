"""
Multi-level cache implementation for BrawlGPT.
Supports L1 (in-memory) and L2 (Redis) caching with automatic fallback.
"""

import asyncio
import hashlib
import json
import logging
import pickle
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, TypeVar, Generic, Callable, Coroutine

from cachetools import TTLCache

from core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


# =============================================================================
# Cache Statistics
# =============================================================================

@dataclass
class CacheStats:
    """Statistics for cache operations."""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0
    l1_hits: int = 0
    l2_hits: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "deletes": self.deletes,
            "errors": self.errors,
            "l1_hits": self.l1_hits,
            "l2_hits": self.l2_hits,
            "hit_rate": f"{self.hit_rate:.1f}%",
        }


# =============================================================================
# Cache Interface
# =============================================================================

class CacheBackend(ABC):
    """Abstract base class for cache backends."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """Clear all values from cache."""
        pass


# =============================================================================
# In-Memory Cache (L1)
# =============================================================================

class InMemoryCache(CacheBackend):
    """
    In-memory cache using cachetools TTLCache.
    Fast but limited to single instance.
    """

    def __init__(self, maxsize: int = 1000, default_ttl: int = 300):
        self._cache = TTLCache(maxsize=maxsize, ttl=default_ttl)
        self._ttls: dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            try:
                return self._cache.get(key)
            except KeyError:
                return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        async with self._lock:
            try:
                # TTLCache doesn't support per-item TTL, but we store anyway
                self._cache[key] = value
                if ttl:
                    self._ttls[key] = ttl
                return True
            except Exception as e:
                logger.error(f"In-memory cache set error: {e}")
                return False

    async def delete(self, key: str) -> bool:
        async with self._lock:
            try:
                if key in self._cache:
                    del self._cache[key]
                if key in self._ttls:
                    del self._ttls[key]
                return True
            except Exception:
                return False

    async def exists(self, key: str) -> bool:
        return key in self._cache

    async def clear(self) -> bool:
        async with self._lock:
            self._cache.clear()
            self._ttls.clear()
            return True

    @property
    def size(self) -> int:
        """Get number of items in cache."""
        return len(self._cache)


# =============================================================================
# Redis Cache (L2)
# =============================================================================

class RedisCache(CacheBackend):
    """
    Redis-based cache for distributed caching.
    Requires aioredis connection.
    """

    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._connected = False

    async def connect(self, url: str) -> bool:
        """Connect to Redis."""
        try:
            import redis.asyncio as aioredis
            self._redis = await aioredis.from_url(
                url,
                encoding="utf-8",
                decode_responses=False,  # We'll handle encoding ourselves
            )
            self._connected = True
            logger.info("Redis cache connected")
            return True
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()
            self._connected = False
            logger.info("Redis cache disconnected")

    @property
    def connected(self) -> bool:
        return self._connected

    async def get(self, key: str) -> Optional[Any]:
        if not self._connected:
            return None

        try:
            data = await self._redis.get(key)
            if data:
                return pickle.loads(data)
            return None
        except Exception as e:
            logger.error(f"Redis get error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        if not self._connected:
            return False

        try:
            data = pickle.dumps(value)
            if ttl:
                await self._redis.setex(key, ttl, data)
            else:
                await self._redis.set(key, data)
            return True
        except Exception as e:
            logger.error(f"Redis set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        if not self._connected:
            return False

        try:
            await self._redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete error for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        if not self._connected:
            return False

        try:
            return await self._redis.exists(key) > 0
        except Exception:
            return False

    async def clear(self) -> bool:
        if not self._connected:
            return False

        try:
            await self._redis.flushdb()
            return True
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            return False

    async def ping(self) -> bool:
        """Check Redis connectivity."""
        if not self._connected:
            return False

        try:
            return await self._redis.ping()
        except Exception:
            return False


# =============================================================================
# Multi-Level Cache Manager
# =============================================================================

class CacheManager:
    """
    Multi-level cache manager with L1 (in-memory) and L2 (Redis).

    Features:
    - Automatic L1 -> L2 fallback
    - Cache-aside pattern
    - Statistics tracking
    - Key prefixing and namespacing
    - Serialization handling

    Usage:
        cache = CacheManager()
        await cache.connect()

        # Simple get/set
        await cache.set("player:ABC123", player_data, ttl=300)
        data = await cache.get("player:ABC123")

        # Cache-aside pattern
        data = await cache.get_or_set(
            "player:ABC123",
            fetcher=lambda: fetch_player("ABC123"),
            ttl=300
        )
    """

    def __init__(
        self,
        prefix: str = "brawlgpt",
        l1_maxsize: int = 1000,
        l1_default_ttl: int = 300,
    ):
        self.prefix = prefix
        self._l1 = InMemoryCache(maxsize=l1_maxsize, default_ttl=l1_default_ttl)
        self._l2: Optional[RedisCache] = None
        self._stats = CacheStats()
        self._enabled = True

    def _make_key(self, key: str) -> str:
        """Generate prefixed cache key."""
        return f"{self.prefix}:{key}"

    async def connect(self) -> bool:
        """Initialize cache connections."""
        if settings().redis_enabled:
            self._l2 = RedisCache()
            connected = await self._l2.connect(settings().redis_url)
            if not connected:
                logger.warning("Redis connection failed, using L1 cache only")
                self._l2 = None
            return connected
        return True

    async def disconnect(self) -> None:
        """Close cache connections."""
        if self._l2:
            await self._l2.disconnect()

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache (L1 first, then L2).

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        if not self._enabled:
            return None

        full_key = self._make_key(key)

        # Try L1 first
        value = await self._l1.get(full_key)
        if value is not None:
            self._stats.hits += 1
            self._stats.l1_hits += 1
            return value

        # Try L2 if available
        if self._l2 and self._l2.connected:
            value = await self._l2.get(full_key)
            if value is not None:
                self._stats.hits += 1
                self._stats.l2_hits += 1
                # Promote to L1
                await self._l1.set(full_key, value)
                return value

        self._stats.misses += 1
        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in cache (both L1 and L2).

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds

        Returns:
            True if set successfully
        """
        if not self._enabled:
            return False

        full_key = self._make_key(key)
        self._stats.sets += 1

        # Set in L1
        await self._l1.set(full_key, value, ttl)

        # Set in L2 if available
        if self._l2 and self._l2.connected:
            await self._l2.set(full_key, value, ttl)

        return True

    async def delete(self, key: str) -> bool:
        """
        Delete value from cache (both L1 and L2).

        Args:
            key: Cache key

        Returns:
            True if deleted
        """
        full_key = self._make_key(key)
        self._stats.deletes += 1

        await self._l1.delete(full_key)

        if self._l2 and self._l2.connected:
            await self._l2.delete(full_key)

        return True

    async def get_or_set(
        self,
        key: str,
        fetcher: Callable[[], Coroutine[Any, Any, T]],
        ttl: Optional[int] = None
    ) -> Optional[T]:
        """
        Get from cache or fetch and cache the result.
        Implements cache-aside pattern.

        Args:
            key: Cache key
            fetcher: Async function to fetch value if not cached
            ttl: Time-to-live in seconds

        Returns:
            Cached or fetched value
        """
        # Try to get from cache
        value = await self.get(key)
        if value is not None:
            return value

        # Fetch the value
        try:
            value = await fetcher()
            if value is not None:
                await self.set(key, value, ttl)
            return value
        except Exception as e:
            logger.error(f"Cache fetcher error for key {key}: {e}")
            self._stats.errors += 1
            raise

    async def clear_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Args:
            pattern: Key pattern (e.g., "player:*")

        Returns:
            Number of keys deleted
        """
        full_pattern = self._make_key(pattern)
        count = 0

        # L2 pattern deletion (if Redis)
        if self._l2 and self._l2.connected:
            try:
                async for key in self._l2._redis.scan_iter(full_pattern):
                    await self._l2.delete(key.decode() if isinstance(key, bytes) else key)
                    count += 1
            except Exception as e:
                logger.error(f"Pattern delete error: {e}")

        return count

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            **self._stats.to_dict(),
            "l1_size": self._l1.size,
            "l2_connected": self._l2.connected if self._l2 else False,
            "enabled": self._enabled,
        }

    def enable(self) -> None:
        """Enable caching."""
        self._enabled = True

    def disable(self) -> None:
        """Disable caching (for testing)."""
        self._enabled = False


# =============================================================================
# Specialized Cache Keys
# =============================================================================

class CacheKeys:
    """Centralized cache key generation."""

    @staticmethod
    def player(tag: str) -> str:
        """Generate player cache key."""
        return f"player:{tag.upper()}"

    @staticmethod
    def battle_log(tag: str) -> str:
        """Generate battle log cache key."""
        return f"battlelog:{tag.upper()}"

    @staticmethod
    def insights(tag: str, player_hash: str) -> str:
        """Generate insights cache key with player state hash."""
        return f"insights:{tag.upper()}:{player_hash}"

    @staticmethod
    def meta_snapshot(trophy_min: int, trophy_max: int) -> str:
        """Generate meta snapshot cache key."""
        return f"meta:{trophy_min}-{trophy_max}"

    @staticmethod
    def global_meta() -> str:
        """Generate global meta cache key."""
        return "meta:global"

    @staticmethod
    def brawler(brawler_id: int) -> str:
        """Generate brawler data cache key."""
        return f"brawler:{brawler_id}"

    @staticmethod
    def events() -> str:
        """Generate events cache key."""
        return "events:rotation"

    @staticmethod
    def counter_picks(brawler_id: int, mode: Optional[str] = None) -> str:
        """Generate counter-picks cache key."""
        if mode:
            return f"counter:{brawler_id}:{mode}"
        return f"counter:{brawler_id}:all"

    @staticmethod
    def synergies(brawler_id: int) -> str:
        """Generate synergies cache key."""
        return f"synergy:{brawler_id}"

    @staticmethod
    def team_composition(mode: str, map_name: Optional[str] = None) -> str:
        """Generate team composition cache key."""
        if map_name:
            # Hash map name for consistent key length
            map_hash = hashlib.md5(map_name.encode()).hexdigest()[:8]
            return f"team:{mode}:{map_hash}"
        return f"team:{mode}:any"


# =============================================================================
# Global Cache Instance
# =============================================================================

# Create global cache manager instance
cache_manager = CacheManager()


async def init_cache() -> None:
    """Initialize global cache manager."""
    await cache_manager.connect()


async def close_cache() -> None:
    """Close global cache manager."""
    await cache_manager.disconnect()
