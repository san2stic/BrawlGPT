"""
Resilience patterns for BrawlGPT.
Provides circuit breaker, retry with exponential backoff, and timeout handling.
"""

import asyncio
import functools
import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, TypeVar, ParamSpec

logger = logging.getLogger(__name__)

P = ParamSpec('P')
T = TypeVar('T')


class CircuitState(Enum):
    """States of the circuit breaker."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5        # Failures before opening
    success_threshold: int = 2        # Successes to close from half-open
    timeout: float = 30.0             # Seconds before trying half-open
    excluded_exceptions: tuple = ()    # Exceptions that don't count as failures


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker."""
    state: CircuitState = CircuitState.CLOSED
    failures: int = 0
    successes: int = 0
    last_failure_time: Optional[float] = None
    total_calls: int = 0
    total_failures: int = 0
    total_successes: int = 0


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    Prevents cascading failures by stopping calls to a failing service.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Service is failing, requests are rejected immediately
    - HALF_OPEN: Testing if service recovered, limited requests allowed

    Usage:
        circuit = CircuitBreaker("brawl_api")

        @circuit
        async def call_api():
            ...
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Identifier for this circuit breaker
            config: Circuit breaker configuration
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._stats = CircuitBreakerStats()
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._stats.state

    @property
    def stats(self) -> dict:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self._stats.state.value,
            "failures": self._stats.failures,
            "successes": self._stats.successes,
            "total_calls": self._stats.total_calls,
            "total_failures": self._stats.total_failures,
            "total_successes": self._stats.total_successes,
            "last_failure": self._stats.last_failure_time,
        }

    async def _check_state(self) -> bool:
        """
        Check and potentially transition circuit state.

        Returns:
            True if call should proceed, False if rejected
        """
        async with self._lock:
            if self._stats.state == CircuitState.CLOSED:
                return True

            if self._stats.state == CircuitState.OPEN:
                # Check if timeout has passed
                if self._stats.last_failure_time:
                    elapsed = time.monotonic() - self._stats.last_failure_time
                    if elapsed >= self.config.timeout:
                        logger.info(
                            f"Circuit {self.name}: transitioning from OPEN to HALF_OPEN"
                        )
                        self._stats.state = CircuitState.HALF_OPEN
                        self._stats.successes = 0
                        return True
                return False

            # HALF_OPEN: allow limited requests
            return True

    async def _record_success(self):
        """Record a successful call."""
        async with self._lock:
            self._stats.total_successes += 1
            self._stats.total_calls += 1

            if self._stats.state == CircuitState.HALF_OPEN:
                self._stats.successes += 1
                if self._stats.successes >= self.config.success_threshold:
                    logger.info(
                        f"Circuit {self.name}: transitioning from HALF_OPEN to CLOSED"
                    )
                    self._stats.state = CircuitState.CLOSED
                    self._stats.failures = 0
                    self._stats.successes = 0

            elif self._stats.state == CircuitState.CLOSED:
                # Reset failure count on success
                self._stats.failures = 0

    async def _record_failure(self, error: Exception):
        """Record a failed call."""
        async with self._lock:
            self._stats.total_failures += 1
            self._stats.total_calls += 1
            self._stats.last_failure_time = time.monotonic()

            if self._stats.state == CircuitState.HALF_OPEN:
                logger.warning(
                    f"Circuit {self.name}: transitioning from HALF_OPEN to OPEN "
                    f"after failure: {error}"
                )
                self._stats.state = CircuitState.OPEN
                self._stats.failures = self.config.failure_threshold

            elif self._stats.state == CircuitState.CLOSED:
                self._stats.failures += 1
                if self._stats.failures >= self.config.failure_threshold:
                    logger.warning(
                        f"Circuit {self.name}: transitioning from CLOSED to OPEN "
                        f"after {self._stats.failures} failures"
                    )
                    self._stats.state = CircuitState.OPEN

    def __call__(self, func: Callable[P, T]) -> Callable[P, T]:
        """Decorator to wrap async function with circuit breaker."""
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            if not await self._check_state():
                raise CircuitOpenError(
                    f"Circuit {self.name} is OPEN, call rejected"
                )

            try:
                result = await func(*args, **kwargs)
                await self._record_success()
                return result
            except self.config.excluded_exceptions:
                # Don't count excluded exceptions as failures
                raise
            except Exception as e:
                await self._record_failure(e)
                raise

        return wrapper

    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute a function through the circuit breaker.

        Args:
            func: Async function to call
            *args, **kwargs: Arguments to pass to function

        Returns:
            Function result

        Raises:
            CircuitOpenError: If circuit is open
        """
        if not await self._check_state():
            raise CircuitOpenError(f"Circuit {self.name} is OPEN, call rejected")

        try:
            result = await func(*args, **kwargs)
            await self._record_success()
            return result
        except self.config.excluded_exceptions:
            raise
        except Exception as e:
            await self._record_failure(e)
            raise

    async def reset(self):
        """Manually reset the circuit breaker to closed state."""
        async with self._lock:
            self._stats.state = CircuitState.CLOSED
            self._stats.failures = 0
            self._stats.successes = 0
            logger.info(f"Circuit {self.name}: manually reset to CLOSED")


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


@dataclass
class RetryConfig:
    """Configuration for retry decorator."""
    max_attempts: int = 3             # Maximum retry attempts
    base_delay: float = 1.0           # Base delay in seconds
    max_delay: float = 30.0           # Maximum delay in seconds
    exponential_base: float = 2.0     # Exponential backoff base
    jitter: bool = True               # Add random jitter
    retryable_exceptions: tuple = (Exception,)  # Exceptions to retry


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple = (Exception,),
    on_retry: Optional[Callable[[int, Exception], None]] = None
):
    """
    Decorator for retry with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts (including initial)
        base_delay: Initial delay between retries
        max_delay: Maximum delay cap
        exponential_base: Base for exponential calculation
        jitter: Add random jitter to prevent thundering herd
        retryable_exceptions: Tuple of exceptions to retry on
        on_retry: Optional callback called on each retry (attempt, exception)

    Usage:
        @retry_with_backoff(max_attempts=3, base_delay=1.0)
        async def fetch_data():
            ...
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt >= max_attempts:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {e}"
                        )
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(
                        base_delay * (exponential_base ** (attempt - 1)),
                        max_delay
                    )

                    # Add jitter (±25%)
                    if jitter:
                        delay = delay * (0.75 + random.random() * 0.5)

                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f}s"
                    )

                    if on_retry:
                        on_retry(attempt, e)

                    await asyncio.sleep(delay)

            # Should never reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper
    return decorator


def with_timeout(
    timeout: float,
    timeout_message: Optional[str] = None
):
    """
    Decorator to add timeout to async function.

    Args:
        timeout: Timeout in seconds
        timeout_message: Custom timeout error message

    Usage:
        @with_timeout(30.0)
        async def slow_operation():
            ...
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                msg = timeout_message or f"{func.__name__} timed out after {timeout}s"
                logger.error(msg)
                raise TimeoutError(msg)
        return wrapper
    return decorator


class ResilientClient:
    """
    Wrapper providing resilience patterns for any async client.

    Combines circuit breaker, retry, and timeout.

    Usage:
        client = ResilientClient(
            name="brawl_api",
            circuit_config=CircuitBreakerConfig(failure_threshold=5),
            retry_config=RetryConfig(max_attempts=3)
        )

        result = await client.execute(
            api_call,
            arg1, arg2,
            timeout=30.0
        )
    """

    def __init__(
        self,
        name: str,
        circuit_config: Optional[CircuitBreakerConfig] = None,
        retry_config: Optional[RetryConfig] = None,
        default_timeout: float = 30.0
    ):
        """
        Initialize resilient client.

        Args:
            name: Client identifier
            circuit_config: Circuit breaker configuration
            retry_config: Retry configuration
            default_timeout: Default timeout for operations
        """
        self.name = name
        self.circuit = CircuitBreaker(name, circuit_config)
        self.retry_config = retry_config or RetryConfig()
        self.default_timeout = default_timeout

    async def execute(
        self,
        func: Callable[..., T],
        *args,
        timeout: Optional[float] = None,
        **kwargs
    ) -> T:
        """
        Execute function with all resilience patterns applied.

        Args:
            func: Async function to execute
            *args, **kwargs: Arguments for function
            timeout: Operation timeout (uses default if None)

        Returns:
            Function result
        """
        timeout = timeout or self.default_timeout

        async def _execute_with_retry():
            last_exception = None

            for attempt in range(1, self.retry_config.max_attempts + 1):
                try:
                    # Apply timeout
                    return await asyncio.wait_for(
                        self.circuit.call(func, *args, **kwargs),
                        timeout=timeout
                    )
                except CircuitOpenError:
                    # Don't retry if circuit is open
                    raise
                except asyncio.TimeoutError as e:
                    last_exception = e
                    if attempt >= self.retry_config.max_attempts:
                        raise TimeoutError(
                            f"{self.name}: operation timed out after {timeout}s"
                        )
                except self.retry_config.retryable_exceptions as e:
                    last_exception = e
                    if attempt >= self.retry_config.max_attempts:
                        raise

                    # Calculate backoff delay
                    delay = min(
                        self.retry_config.base_delay * (
                            self.retry_config.exponential_base ** (attempt - 1)
                        ),
                        self.retry_config.max_delay
                    )

                    if self.retry_config.jitter:
                        delay = delay * (0.75 + random.random() * 0.5)

                    logger.warning(
                        f"{self.name}: attempt {attempt}/{self.retry_config.max_attempts} "
                        f"failed: {e}. Retrying in {delay:.2f}s"
                    )

                    await asyncio.sleep(delay)

            if last_exception:
                raise last_exception

        return await _execute_with_retry()

    @property
    def stats(self) -> dict:
        """Get resilient client statistics."""
        return {
            "name": self.name,
            "circuit": self.circuit.stats,
            "retry_config": {
                "max_attempts": self.retry_config.max_attempts,
                "base_delay": self.retry_config.base_delay,
                "max_delay": self.retry_config.max_delay,
            },
            "default_timeout": self.default_timeout,
        }

    async def reset(self):
        """Reset the circuit breaker."""
        await self.circuit.reset()


# Pre-configured clients for common use cases
brawl_api_circuit = CircuitBreaker(
    "brawl_api",
    CircuitBreakerConfig(
        failure_threshold=5,
        success_threshold=2,
        timeout=60.0
    )
)

openrouter_circuit = CircuitBreaker(
    "openrouter",
    CircuitBreakerConfig(
        failure_threshold=3,
        success_threshold=1,
        timeout=30.0
    )
)


# Resilient clients for external services
brawl_api_client = ResilientClient(
    name="brawl_api",
    circuit_config=CircuitBreakerConfig(
        failure_threshold=5,
        success_threshold=2,
        timeout=60.0
    ),
    retry_config=RetryConfig(
        max_attempts=3,
        base_delay=1.0,
        max_delay=30.0,
        jitter=True
    ),
    default_timeout=30.0
)

openrouter_client = ResilientClient(
    name="openrouter",
    circuit_config=CircuitBreakerConfig(
        failure_threshold=3,
        success_threshold=1,
        timeout=30.0
    ),
    retry_config=RetryConfig(
        max_attempts=2,
        base_delay=2.0,
        max_delay=10.0,
        jitter=True
    ),
    default_timeout=60.0
)
