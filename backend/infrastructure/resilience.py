"""
Resilience patterns for BrawlGPT.
Implements retry logic with exponential backoff and circuit breaker pattern.
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import (
    Any,
    Callable,
    Coroutine,
    Optional,
    Type,
    TypeVar,
    Union,
    Sequence,
)

from core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


# =============================================================================
# Retry Configuration
# =============================================================================

@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = field(default_factory=lambda: settings().retry_max_attempts)
    base_delay: float = field(default_factory=lambda: settings().retry_base_delay)
    max_delay: float = field(default_factory=lambda: settings().retry_max_delay)
    exponential_base: float = field(default_factory=lambda: settings().retry_exponential_base)
    jitter: bool = True
    jitter_factor: float = 0.1  # 10% jitter

    # Exceptions to retry on (default: all exceptions)
    retryable_exceptions: tuple[Type[Exception], ...] = (Exception,)

    # Exceptions to never retry on
    non_retryable_exceptions: tuple[Type[Exception], ...] = ()

    # HTTP status codes to retry on
    retryable_status_codes: tuple[int, ...] = (408, 429, 500, 502, 503, 504)


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """
    Calculate delay before next retry using exponential backoff with jitter.

    Args:
        attempt: Current attempt number (1-indexed)
        config: Retry configuration

    Returns:
        Delay in seconds
    """
    # Exponential backoff: base_delay * (exponential_base ^ (attempt - 1))
    delay = config.base_delay * (config.exponential_base ** (attempt - 1))

    # Cap at max delay
    delay = min(delay, config.max_delay)

    # Add jitter to prevent thundering herd
    if config.jitter:
        jitter_range = delay * config.jitter_factor
        delay = delay + random.uniform(-jitter_range, jitter_range)

    return max(0, delay)


def should_retry(
    exception: Exception,
    config: RetryConfig
) -> bool:
    """
    Determine if an exception should trigger a retry.

    Args:
        exception: The exception that occurred
        config: Retry configuration

    Returns:
        True if should retry, False otherwise
    """
    # Never retry these
    if isinstance(exception, config.non_retryable_exceptions):
        return False

    # Check if exception is retryable
    if isinstance(exception, config.retryable_exceptions):
        return True

    # Check for HTTP response errors with status codes
    if hasattr(exception, "status_code"):
        return exception.status_code in config.retryable_status_codes

    if hasattr(exception, "response") and hasattr(exception.response, "status_code"):
        return exception.response.status_code in config.retryable_status_codes

    return False


# =============================================================================
# Retry Decorator (Async)
# =============================================================================

def retry_with_backoff(
    config: Optional[RetryConfig] = None,
    max_attempts: Optional[int] = None,
    base_delay: Optional[float] = None,
    retryable_exceptions: Optional[tuple[Type[Exception], ...]] = None,
    on_retry: Optional[Callable[[int, Exception, float], None]] = None,
):
    """
    Decorator that retries an async function with exponential backoff.

    Args:
        config: RetryConfig instance (overrides other params if provided)
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay between retries in seconds
        retryable_exceptions: Tuple of exception types to retry on
        on_retry: Optional callback called on each retry with (attempt, exception, delay)

    Example:
        @retry_with_backoff(max_attempts=3)
        async def fetch_data():
            ...

        @retry_with_backoff(config=RetryConfig(max_attempts=5, base_delay=2.0))
        async def slow_operation():
            ...
    """
    def decorator(
        func: Callable[..., Coroutine[Any, Any, T]]
    ) -> Callable[..., Coroutine[Any, Any, T]]:

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            # Build configuration
            retry_config = config or RetryConfig()

            if max_attempts is not None:
                retry_config.max_attempts = max_attempts
            if base_delay is not None:
                retry_config.base_delay = base_delay
            if retryable_exceptions is not None:
                retry_config.retryable_exceptions = retryable_exceptions

            last_exception: Optional[Exception] = None

            for attempt in range(1, retry_config.max_attempts + 1):
                try:
                    return await func(*args, **kwargs)

                except Exception as e:
                    last_exception = e

                    # Check if we should retry
                    if not should_retry(e, retry_config):
                        logger.warning(
                            f"Non-retryable exception in {func.__name__}: {e}"
                        )
                        raise

                    # Check if we have attempts left
                    if attempt >= retry_config.max_attempts:
                        logger.error(
                            f"Max retries ({retry_config.max_attempts}) exceeded for "
                            f"{func.__name__}: {e}"
                        )
                        raise

                    # Calculate delay
                    delay = calculate_delay(attempt, retry_config)

                    logger.warning(
                        f"Retry {attempt}/{retry_config.max_attempts} for "
                        f"{func.__name__} after {delay:.2f}s: {e}"
                    )

                    # Call retry callback if provided
                    if on_retry:
                        on_retry(attempt, e, delay)

                    # Wait before retry
                    await asyncio.sleep(delay)

            # Should never reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper
    return decorator


def retry_with_backoff_sync(
    config: Optional[RetryConfig] = None,
    max_attempts: Optional[int] = None,
    base_delay: Optional[float] = None,
    retryable_exceptions: Optional[tuple[Type[Exception], ...]] = None,
    on_retry: Optional[Callable[[int, Exception, float], None]] = None,
):
    """
    Decorator that retries a sync function with exponential backoff.
    Same as retry_with_backoff but for synchronous functions.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            retry_config = config or RetryConfig()

            if max_attempts is not None:
                retry_config.max_attempts = max_attempts
            if base_delay is not None:
                retry_config.base_delay = base_delay
            if retryable_exceptions is not None:
                retry_config.retryable_exceptions = retryable_exceptions

            last_exception: Optional[Exception] = None

            for attempt in range(1, retry_config.max_attempts + 1):
                try:
                    return func(*args, **kwargs)

                except Exception as e:
                    last_exception = e

                    if not should_retry(e, retry_config):
                        raise

                    if attempt >= retry_config.max_attempts:
                        raise

                    delay = calculate_delay(attempt, retry_config)

                    logger.warning(
                        f"Retry {attempt}/{retry_config.max_attempts} for "
                        f"{func.__name__} after {delay:.2f}s: {e}"
                    )

                    if on_retry:
                        on_retry(attempt, e, delay)

                    time.sleep(delay)

            if last_exception:
                raise last_exception

        return wrapper
    return decorator


# =============================================================================
# Circuit Breaker Pattern
# =============================================================================

class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is open."""

    def __init__(self, message: str = "Circuit breaker is open", reset_time: Optional[datetime] = None):
        self.message = message
        self.reset_time = reset_time
        super().__init__(self.message)


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 2  # Successes needed to close from half-open
    timeout: float = 60.0  # Seconds before trying half-open
    half_open_max_calls: int = 3  # Max calls in half-open state


class CircuitBreaker:
    """
    Circuit breaker implementation for handling failing services.

    Usage:
        breaker = CircuitBreaker(name="brawl_stars_api")

        @breaker
        async def call_api():
            ...

        # Or manually
        if breaker.allow_request():
            try:
                result = await call_api()
                breaker.record_success()
            except Exception as e:
                breaker.record_failure()
                raise
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._half_open_calls = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (rejecting requests)."""
        return self._state == CircuitState.OPEN

    def allow_request(self) -> bool:
        """
        Check if a request should be allowed.

        Returns:
            True if request should proceed, False otherwise
        """
        if self._state == CircuitState.CLOSED:
            return True

        if self._state == CircuitState.OPEN:
            # Check if timeout has passed
            if self._last_failure_time:
                elapsed = (datetime.utcnow() - self._last_failure_time).total_seconds()
                if elapsed >= self.config.timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    logger.info(f"Circuit breaker '{self.name}' entering half-open state")
                    return True
            return False

        if self._state == CircuitState.HALF_OPEN:
            if self._half_open_calls < self.config.half_open_max_calls:
                self._half_open_calls += 1
                return True
            return False

        return False

    def record_success(self) -> None:
        """Record a successful request."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.success_threshold:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0
                logger.info(f"Circuit breaker '{self.name}' closed")

        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success
            self._failure_count = 0

    def record_failure(self) -> None:
        """Record a failed request."""
        self._failure_count += 1
        self._last_failure_time = datetime.utcnow()

        if self._state == CircuitState.HALF_OPEN:
            # Any failure in half-open opens the circuit
            self._state = CircuitState.OPEN
            self._success_count = 0
            logger.warning(f"Circuit breaker '{self.name}' opened (failure in half-open)")

        elif self._state == CircuitState.CLOSED:
            if self._failure_count >= self.config.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(
                    f"Circuit breaker '{self.name}' opened "
                    f"(failures: {self._failure_count})"
                )

    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        self._half_open_calls = 0
        logger.info(f"Circuit breaker '{self.name}' manually reset")

    def __call__(self, func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
        """Use as decorator for async functions."""

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            if not self.allow_request():
                reset_time = None
                if self._last_failure_time:
                    reset_time = self._last_failure_time + timedelta(seconds=self.config.timeout)
                raise CircuitBreakerOpen(
                    f"Circuit breaker '{self.name}' is open",
                    reset_time=reset_time
                )

            try:
                result = await func(*args, **kwargs)
                self.record_success()
                return result
            except Exception as e:
                self.record_failure()
                raise

        return wrapper

    def get_status(self) -> dict[str, Any]:
        """Get current status of the circuit breaker."""
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure": self._last_failure_time.isoformat() if self._last_failure_time else None,
        }


# =============================================================================
# Timeout Wrapper
# =============================================================================

async def with_timeout(
    coro: Coroutine[Any, Any, T],
    timeout: float,
    error_message: str = "Operation timed out"
) -> T:
    """
    Execute a coroutine with a timeout.

    Args:
        coro: Coroutine to execute
        timeout: Timeout in seconds
        error_message: Error message if timeout occurs

    Returns:
        Result of the coroutine

    Raises:
        asyncio.TimeoutError: If operation times out
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        logger.error(f"Timeout after {timeout}s: {error_message}")
        raise asyncio.TimeoutError(error_message)


# =============================================================================
# Bulkhead Pattern (Concurrency Limiter)
# =============================================================================

class Bulkhead:
    """
    Bulkhead pattern to limit concurrent executions.
    Prevents one service from consuming all resources.
    """

    def __init__(self, name: str, max_concurrent: int = 10, max_waiting: int = 50):
        self.name = name
        self.max_concurrent = max_concurrent
        self.max_waiting = max_waiting
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._waiting = 0

    async def execute(self, coro: Coroutine[Any, Any, T]) -> T:
        """
        Execute a coroutine within the bulkhead.

        Args:
            coro: Coroutine to execute

        Returns:
            Result of the coroutine

        Raises:
            RuntimeError: If too many requests are waiting
        """
        if self._waiting >= self.max_waiting:
            raise RuntimeError(
                f"Bulkhead '{self.name}' rejected: too many waiting requests"
            )

        self._waiting += 1
        try:
            async with self._semaphore:
                self._waiting -= 1
                return await coro
        except Exception:
            self._waiting -= 1
            raise

    def __call__(self, func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
        """Use as decorator."""

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await self.execute(func(*args, **kwargs))

        return wrapper
