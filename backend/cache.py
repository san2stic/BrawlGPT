"""
Caching layer for BrawlGPT API.
Provides in-memory caching for player data and AI insights.
"""

import logging
from typing import Any, TypeVar, Callable, Optional
from functools import wraps
from cachetools import TTLCache
import hashlib

logger = logging.getLogger(__name__)

# Type variable for generic cache functions
T = TypeVar("T")

# Cache configurations
PLAYER_CACHE_TTL = 300  # 5 minutes for player data
INSIGHTS_CACHE_TTL = 900  # 15 minutes for AI insights
MAX_CACHE_SIZE = 1000  # Maximum number of cached items

# Initialize caches
player_cache: TTLCache[str, dict[str, Any]] = TTLCache(
    maxsize=MAX_CACHE_SIZE, ttl=PLAYER_CACHE_TTL
)
insights_cache: TTLCache[str, str] = TTLCache(
    maxsize=MAX_CACHE_SIZE, ttl=INSIGHTS_CACHE_TTL
)


def get_cache_key(tag: str, prefix: str = "") -> str:
    """
    Generate a cache key for a player tag.

    Args:
        tag: Player tag
        prefix: Optional prefix for different cache types

    Returns:
        Cache key string
    """
    clean_tag = tag.upper().replace("#", "").strip()
    return f"{prefix}:{clean_tag}" if prefix else clean_tag


def get_insights_cache_key(tag: str, player_hash: str) -> str:
    """
    Generate a cache key for AI insights.
    Includes a hash of player data to invalidate when data changes.

    Args:
        tag: Player tag
        player_hash: Hash of player data

    Returns:
        Cache key string
    """
    clean_tag = tag.upper().replace("#", "").strip()
    return f"insights:{clean_tag}:{player_hash}"


def hash_player_data(player_data: dict[str, Any]) -> str:
    """
    Create a hash of relevant player data for cache invalidation.

    Args:
        player_data: Player data dictionary

    Returns:
        Short hash string
    """
    # Use key stats that change frequently
    key_fields = (
        player_data.get("trophies", 0),
        player_data.get("3vs3Victories", 0),
        player_data.get("soloVictories", 0),
        player_data.get("duoVictories", 0),
    )
    hash_input = str(key_fields).encode()
    return hashlib.md5(hash_input).hexdigest()[:8]


class CacheManager:
    """Manager for cache operations."""

    @staticmethod
    def get_player(tag: str) -> Optional[dict[str, Any]]:
        """
        Get cached player data.

        Args:
            tag: Player tag

        Returns:
            Cached player data or None if not found
        """
        key = get_cache_key(tag, "player")
        result = player_cache.get(key)
        if result:
            logger.debug(f"Cache hit for player: {tag}")
        return result

    @staticmethod
    def set_player(tag: str, data: dict[str, Any]) -> None:
        """
        Cache player data.

        Args:
            tag: Player tag
            data: Player data to cache
        """
        key = get_cache_key(tag, "player")
        player_cache[key] = data
        logger.debug(f"Cached player data for: {tag}")

    @staticmethod
    def get_battle_log(tag: str) -> Optional[dict[str, Any]]:
        """
        Get cached battle log.

        Args:
            tag: Player tag

        Returns:
            Cached battle log or None if not found
        """
        key = get_cache_key(tag, "battles")
        result = player_cache.get(key)
        if result:
            logger.debug(f"Cache hit for battle log: {tag}")
        return result

    @staticmethod
    def set_battle_log(tag: str, data: dict[str, Any]) -> None:
        """
        Cache battle log.

        Args:
            tag: Player tag
            data: Battle log to cache
        """
        key = get_cache_key(tag, "battles")
        player_cache[key] = data
        logger.debug(f"Cached battle log for: {tag}")

    @staticmethod
    def get_insights(tag: str, player_data: dict[str, Any]) -> Optional[str]:
        """
        Get cached AI insights.

        Args:
            tag: Player tag
            player_data: Current player data (for hash validation)

        Returns:
            Cached insights or None if not found/stale
        """
        player_hash = hash_player_data(player_data)
        key = get_insights_cache_key(tag, player_hash)
        result = insights_cache.get(key)
        if result:
            logger.debug(f"Cache hit for insights: {tag}")
        return result

    @staticmethod
    def set_insights(tag: str, player_data: dict[str, Any], insights: str) -> None:
        """
        Cache AI insights.

        Args:
            tag: Player tag
            player_data: Current player data (for hash generation)
            insights: AI insights to cache
        """
        player_hash = hash_player_data(player_data)
        key = get_insights_cache_key(tag, player_hash)
        insights_cache[key] = insights
        logger.debug(f"Cached insights for: {tag}")

    @staticmethod
    def clear_player(tag: str) -> None:
        """
        Clear all cached data for a player.

        Args:
            tag: Player tag
        """
        player_key = get_cache_key(tag, "player")
        battles_key = get_cache_key(tag, "battles")

        player_cache.pop(player_key, None)
        player_cache.pop(battles_key, None)

        # Note: insights cache entries will expire naturally
        # since they're keyed by player data hash

        logger.debug(f"Cleared cache for: {tag}")

    @staticmethod
    def get_stats() -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        return {
            "player_cache": {
                "size": len(player_cache),
                "maxsize": player_cache.maxsize,
                "ttl": PLAYER_CACHE_TTL,
            },
            "insights_cache": {
                "size": len(insights_cache),
                "maxsize": insights_cache.maxsize,
                "ttl": INSIGHTS_CACHE_TTL,
            },
        }

    @staticmethod
    def clear_all() -> None:
        """Clear all caches."""
        player_cache.clear()
        insights_cache.clear()
        logger.info("All caches cleared")


# Singleton instance
cache = CacheManager()
