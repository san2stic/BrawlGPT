"""
Intelligent Rate Limiter for Brawl Stars API.
Uses token bucket algorithm with different buckets for different endpoint types.
"""

import asyncio
import time
import logging
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class EndpointType(Enum):
    """Types of endpoints with different rate limits."""
    PLAYER = "player"           # Player data, battle logs
    RANKINGS = "rankings"       # Rankings endpoints
    STATIC = "static"           # Brawlers, events (cacheable)
    CLUB = "club"               # Club data


@dataclass
class BucketConfig:
    """Configuration for a rate limit bucket."""
    rate: float           # Tokens per second
    burst: int            # Maximum burst size
    name: str = ""


@dataclass
class TokenBucket:
    """Token bucket implementation for rate limiting."""
    config: BucketConfig
    tokens: float = field(init=False)
    last_update: float = field(init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    def __post_init__(self):
        self.tokens = float(self.config.burst)
        self.last_update = time.monotonic()

    async def acquire(self, timeout: Optional[float] = None) -> bool:
        """
        Acquire a token from the bucket.

        Args:
            timeout: Maximum time to wait for a token (seconds)

        Returns:
            True if token acquired, False if timeout exceeded
        """
        start_time = time.monotonic()

        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self.last_update
                self.last_update = now

                # Add tokens based on elapsed time
                self.tokens = min(
                    self.config.burst,
                    self.tokens + elapsed * self.config.rate
                )

                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    logger.debug(
                        f"Token acquired from {self.config.name} bucket. "
                        f"Remaining: {self.tokens:.1f}"
                    )
                    return True

                # Calculate wait time for next token
                wait_time = (1.0 - self.tokens) / self.config.rate

                # Check timeout
                if timeout is not None:
                    elapsed_total = now - start_time
                    if elapsed_total + wait_time > timeout:
                        logger.warning(
                            f"Rate limit timeout for {self.config.name} bucket"
                        )
                        return False

                logger.debug(
                    f"Waiting {wait_time:.2f}s for token in {self.config.name} bucket"
                )
                await asyncio.sleep(min(wait_time, 0.1))

    @property
    def available_tokens(self) -> float:
        """Get current available tokens (approximate)."""
        now = time.monotonic()
        elapsed = now - self.last_update
        return min(
            self.config.burst,
            self.tokens + elapsed * self.config.rate
        )


class SmartRateLimiter:
    """
    Intelligent rate limiter with different buckets for different endpoint types.

    Rate limits based on Brawl Stars API guidelines:
    - Player endpoints: Higher rate, frequently accessed
    - Rankings: Lower rate, less frequent access needed
    - Static data: Very low rate, should be heavily cached
    """

    # Bucket configurations
    BUCKET_CONFIGS = {
        EndpointType.PLAYER: BucketConfig(
            rate=10.0,      # 10 requests per second
            burst=20,       # Can burst up to 20
            name="player"
        ),
        EndpointType.RANKINGS: BucketConfig(
            rate=2.0,       # 2 requests per second
            burst=5,        # Can burst up to 5
            name="rankings"
        ),
        EndpointType.STATIC: BucketConfig(
            rate=0.1,       # 1 request per 10 seconds (heavily cached)
            burst=2,        # Can burst up to 2
            name="static"
        ),
        EndpointType.CLUB: BucketConfig(
            rate=5.0,       # 5 requests per second
            burst=10,       # Can burst up to 10
            name="club"
        ),
    }

    # Endpoint to bucket type mapping
    ENDPOINT_MAPPING = {
        "/players/": EndpointType.PLAYER,
        "/clubs/": EndpointType.CLUB,
        "/brawlers": EndpointType.STATIC,
        "/events/": EndpointType.STATIC,
        "/rankings/": EndpointType.RANKINGS,
    }

    def __init__(self):
        """Initialize rate limiter with all buckets."""
        self.buckets: dict[EndpointType, TokenBucket] = {
            endpoint_type: TokenBucket(config)
            for endpoint_type, config in self.BUCKET_CONFIGS.items()
        }
        self._stats = {
            endpoint_type: {"acquired": 0, "rejected": 0}
            for endpoint_type in EndpointType
        }
        logger.info("Smart rate limiter initialized with buckets: %s",
                    list(self.buckets.keys()))

    def _get_endpoint_type(self, endpoint: str) -> EndpointType:
        """
        Determine the endpoint type from the URL path.

        Args:
            endpoint: The API endpoint path

        Returns:
            The endpoint type for rate limiting
        """
        for prefix, endpoint_type in self.ENDPOINT_MAPPING.items():
            if prefix in endpoint:
                return endpoint_type
        # Default to player bucket for unknown endpoints
        return EndpointType.PLAYER

    async def acquire(
        self,
        endpoint: str,
        timeout: Optional[float] = 30.0
    ) -> bool:
        """
        Acquire permission to make a request to the given endpoint.

        Args:
            endpoint: The API endpoint to call
            timeout: Maximum time to wait (seconds)

        Returns:
            True if permission granted, False otherwise
        """
        endpoint_type = self._get_endpoint_type(endpoint)
        bucket = self.buckets[endpoint_type]

        success = await bucket.acquire(timeout)

        if success:
            self._stats[endpoint_type]["acquired"] += 1
        else:
            self._stats[endpoint_type]["rejected"] += 1

        return success

    def get_stats(self) -> dict:
        """Get rate limiting statistics."""
        stats = {}
        for endpoint_type, bucket in self.buckets.items():
            stats[endpoint_type.value] = {
                "available_tokens": round(bucket.available_tokens, 1),
                "config": {
                    "rate": bucket.config.rate,
                    "burst": bucket.config.burst,
                },
                "requests_acquired": self._stats[endpoint_type]["acquired"],
                "requests_rejected": self._stats[endpoint_type]["rejected"],
            }
        return stats

    def reset_stats(self):
        """Reset rate limiting statistics."""
        for endpoint_type in EndpointType:
            self._stats[endpoint_type] = {"acquired": 0, "rejected": 0}


# Singleton instance
rate_limiter = SmartRateLimiter()


# Decorator for rate-limited functions
def rate_limited(endpoint_type: EndpointType = None, timeout: float = 30.0):
    """
    Decorator to apply rate limiting to async functions.

    Args:
        endpoint_type: Override the endpoint type detection
        timeout: Maximum time to wait for rate limit

    Usage:
        @rate_limited(EndpointType.PLAYER)
        async def fetch_player(tag: str):
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Try to detect endpoint from function name or use override
            if endpoint_type:
                bucket = rate_limiter.buckets[endpoint_type]
            else:
                # Default to player bucket
                bucket = rate_limiter.buckets[EndpointType.PLAYER]

            if not await bucket.acquire(timeout):
                raise RateLimitError(
                    f"Rate limit exceeded for {bucket.config.name} bucket"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""
    pass
