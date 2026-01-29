"""
Structured Logging Configuration for BrawlGPT.
Provides JSON-formatted logging with rich context for production monitoring.
"""

import logging
import sys
import json
from datetime import datetime
from typing import Any, Optional
from contextvars import ContextVar
import traceback

# Context variables for request tracking
request_id_ctx: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
player_tag_ctx: ContextVar[Optional[str]] = ContextVar('player_tag', default=None)


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    Outputs logs as JSON objects with consistent structure for
    easy parsing by log aggregation tools (ELK, Datadog, etc.).
    """

    LEVEL_MAP = {
        logging.DEBUG: "debug",
        logging.INFO: "info",
        logging.WARNING: "warning",
        logging.ERROR: "error",
        logging.CRITICAL: "critical",
    }

    def __init__(
        self,
        include_timestamp: bool = True,
        include_traceback: bool = True,
        extra_fields: Optional[dict] = None
    ):
        """
        Initialize JSON formatter.

        Args:
            include_timestamp: Include ISO timestamp in output
            include_traceback: Include traceback for exceptions
            extra_fields: Static fields to include in all logs
        """
        super().__init__()
        self.include_timestamp = include_timestamp
        self.include_traceback = include_traceback
        self.extra_fields = extra_fields or {}

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string."""
        log_data = {
            "level": self.LEVEL_MAP.get(record.levelno, "unknown"),
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add timestamp
        if self.include_timestamp:
            log_data["timestamp"] = datetime.utcnow().isoformat() + "Z"

        # Add context variables
        request_id = request_id_ctx.get()
        if request_id:
            log_data["request_id"] = request_id

        player_tag = player_tag_ctx.get()
        if player_tag:
            log_data["player_tag"] = player_tag

        # Add extra fields from record
        if hasattr(record, 'duration_ms'):
            log_data["duration_ms"] = record.duration_ms

        if hasattr(record, 'status_code'):
            log_data["status_code"] = record.status_code

        if hasattr(record, 'method'):
            log_data["method"] = record.method

        if hasattr(record, 'path'):
            log_data["path"] = record.path

        if hasattr(record, 'user_agent'):
            log_data["user_agent"] = record.user_agent

        if hasattr(record, 'client_ip'):
            log_data["client_ip"] = record.client_ip

        # Add any extra attributes passed to the logger
        for key, value in record.__dict__.items():
            if key.startswith('extra_') and not key.startswith('_'):
                clean_key = key[6:]  # Remove 'extra_' prefix
                log_data[clean_key] = value

        # Add static extra fields
        log_data.update(self.extra_fields)

        # Add exception info if present
        if record.exc_info and self.include_traceback:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info) if record.exc_info[0] else None
            }

        return json.dumps(log_data, default=str, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    """
    Human-readable text formatter for development.

    Includes colors when outputting to a TTY.
    """

    COLORS = {
        logging.DEBUG: "\033[36m",     # Cyan
        logging.INFO: "\033[32m",      # Green
        logging.WARNING: "\033[33m",   # Yellow
        logging.ERROR: "\033[31m",     # Red
        logging.CRITICAL: "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def __init__(self, use_colors: bool = True):
        """
        Initialize text formatter.

        Args:
            use_colors: Use ANSI colors in output
        """
        super().__init__()
        self.use_colors = use_colors and sys.stderr.isatty()

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as readable text."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        level = record.levelname.ljust(8)

        if self.use_colors:
            color = self.COLORS.get(record.levelno, "")
            level = f"{color}{level}{self.RESET}"

        # Build message parts
        parts = [
            f"[{timestamp}]",
            level,
            f"{record.name}:{record.funcName}:{record.lineno}",
            "-",
            record.getMessage()
        ]

        # Add context
        request_id = request_id_ctx.get()
        if request_id:
            parts.insert(3, f"[{request_id[:8]}]")

        player_tag = player_tag_ctx.get()
        if player_tag:
            parts.insert(3, f"[{player_tag}]")

        # Add duration if present
        if hasattr(record, 'duration_ms'):
            parts.append(f"({record.duration_ms}ms)")

        message = " ".join(parts)

        # Add exception traceback
        if record.exc_info:
            message += "\n" + "".join(traceback.format_exception(*record.exc_info))

        return message


def setup_logging(
    level: str = "INFO",
    format_type: str = "json",
    extra_fields: Optional[dict] = None
) -> None:
    """
    Configure application logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: "json" for structured or "text" for human-readable
        extra_fields: Static fields to include in all JSON logs
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    root_logger.handlers = []

    # Create handler
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(getattr(logging, level.upper()))

    # Set formatter based on type
    if format_type.lower() == "json":
        formatter = JSONFormatter(extra_fields=extra_fields)
    else:
        formatter = TextFormatter()

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    # Log initial message
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured",
        extra={
            "extra_level": level,
            "extra_format": format_type
        }
    )


class LogContext:
    """
    Context manager for setting request context.

    Usage:
        async with LogContext(request_id="abc123", player_tag="#ABC"):
            logger.info("Processing request")
    """

    def __init__(
        self,
        request_id: Optional[str] = None,
        player_tag: Optional[str] = None
    ):
        self.request_id = request_id
        self.player_tag = player_tag
        self._request_id_token = None
        self._player_tag_token = None

    def __enter__(self):
        if self.request_id:
            self._request_id_token = request_id_ctx.set(self.request_id)
        if self.player_tag:
            self._player_tag_token = player_tag_ctx.set(self.player_tag)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._request_id_token:
            request_id_ctx.reset(self._request_id_token)
        if self._player_tag_token:
            player_tag_ctx.reset(self._player_tag_token)

    async def __aenter__(self):
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return self.__exit__(exc_type, exc_val, exc_tb)


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    **extra
) -> None:
    """
    Log a message with extra context fields.

    Args:
        logger: Logger instance
        level: Log level
        message: Log message
        **extra: Additional fields to include
    """
    # Prefix extra fields for the formatter to pick up
    prefixed_extra = {f"extra_{k}": v for k, v in extra.items()}
    logger.log(level, message, extra=prefixed_extra)


class RequestLogger:
    """
    Logger helper for HTTP requests.

    Automatically logs request start and completion with timing.
    """

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def log_request_start(
        self,
        method: str,
        path: str,
        request_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Log the start of a request."""
        self.logger.info(
            f"Request started: {method} {path}",
            extra={
                "extra_method": method,
                "extra_path": path,
                "extra_client_ip": client_ip,
                "extra_user_agent": user_agent,
                "extra_event": "request_start"
            }
        )

    def log_request_complete(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        request_id: Optional[str] = None
    ):
        """Log the completion of a request."""
        level = logging.INFO if status_code < 400 else logging.WARNING
        if status_code >= 500:
            level = logging.ERROR

        self.logger.log(
            level,
            f"Request completed: {method} {path} -> {status_code} ({duration_ms:.2f}ms)",
            extra={
                "extra_method": method,
                "extra_path": path,
                "extra_status_code": status_code,
                "extra_duration_ms": duration_ms,
                "extra_event": "request_complete"
            }
        )


class MetricsLogger:
    """
    Logger helper for application metrics.

    Logs metrics in a consistent format for monitoring.
    """

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def log_api_call(
        self,
        api_name: str,
        endpoint: str,
        success: bool,
        duration_ms: float,
        error: Optional[str] = None
    ):
        """Log an external API call."""
        level = logging.INFO if success else logging.WARNING
        status = "success" if success else "failed"

        self.logger.log(
            level,
            f"API call {api_name}: {endpoint} {status} ({duration_ms:.2f}ms)",
            extra={
                "extra_api_name": api_name,
                "extra_endpoint": endpoint,
                "extra_success": success,
                "extra_duration_ms": duration_ms,
                "extra_error": error,
                "extra_event": "api_call"
            }
        )

    def log_cache_operation(
        self,
        operation: str,  # get, set, delete
        key: str,
        hit: Optional[bool] = None,
        duration_ms: Optional[float] = None
    ):
        """Log a cache operation."""
        if hit is not None:
            status = "hit" if hit else "miss"
            message = f"Cache {operation} {status}: {key}"
        else:
            message = f"Cache {operation}: {key}"

        self.logger.debug(
            message,
            extra={
                "extra_operation": operation,
                "extra_cache_key": key,
                "extra_cache_hit": hit,
                "extra_duration_ms": duration_ms,
                "extra_event": "cache_operation"
            }
        )

    def log_db_query(
        self,
        operation: str,
        table: str,
        duration_ms: float,
        rows_affected: Optional[int] = None
    ):
        """Log a database query."""
        self.logger.debug(
            f"DB {operation} on {table} ({duration_ms:.2f}ms)",
            extra={
                "extra_operation": operation,
                "extra_table": table,
                "extra_duration_ms": duration_ms,
                "extra_rows_affected": rows_affected,
                "extra_event": "db_query"
            }
        )

    def log_ai_request(
        self,
        model: str,
        tokens_in: int,
        tokens_out: int,
        duration_ms: float,
        success: bool,
        error: Optional[str] = None
    ):
        """Log an AI model request."""
        level = logging.INFO if success else logging.WARNING

        self.logger.log(
            level,
            f"AI request to {model}: {tokens_in}in/{tokens_out}out ({duration_ms:.2f}ms)",
            extra={
                "extra_model": model,
                "extra_tokens_in": tokens_in,
                "extra_tokens_out": tokens_out,
                "extra_duration_ms": duration_ms,
                "extra_success": success,
                "extra_error": error,
                "extra_event": "ai_request"
            }
        )


# Pre-configured loggers
def get_request_logger() -> RequestLogger:
    """Get a request logger instance."""
    return RequestLogger(logging.getLogger("brawlgpt.requests"))


def get_metrics_logger() -> MetricsLogger:
    """Get a metrics logger instance."""
    return MetricsLogger(logging.getLogger("brawlgpt.metrics"))
