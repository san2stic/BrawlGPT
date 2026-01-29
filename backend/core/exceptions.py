"""
Custom exceptions for BrawlGPT backend.
Provides structured error handling with appropriate HTTP status codes.
"""

from typing import Optional, Any


class BrawlGPTError(Exception):
    """Base exception for all BrawlGPT errors."""
    status_code: int = 500
    message: str = "An internal error occurred"
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None):
        self.message = message or self.__class__.message
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API response."""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details,
        }


# =============================================================================
# Player/Tag Errors
# =============================================================================

class PlayerNotFoundError(BrawlGPTError):
    """Raised when a player tag does not exist."""
    status_code = 404
    message = "Player not found"
    error_code = "PLAYER_NOT_FOUND"


class InvalidTagError(BrawlGPTError):
    """Raised when the player tag format is invalid."""
    status_code = 400
    message = "Invalid player tag format"
    error_code = "INVALID_TAG"


class ClubNotFoundError(BrawlGPTError):
    """Raised when a club tag does not exist."""
    status_code = 404
    message = "Club not found"
    error_code = "CLUB_NOT_FOUND"


# =============================================================================
# API/External Service Errors
# =============================================================================

class RateLimitError(BrawlGPTError):
    """Raised when API rate limit is exceeded."""
    status_code = 429
    message = "Rate limit exceeded. Please try again later"
    error_code = "RATE_LIMIT_EXCEEDED"

    def __init__(self, message: Optional[str] = None, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after
        if retry_after:
            self.details["retry_after"] = retry_after


class BrawlStarsAPIError(BrawlGPTError):
    """Raised when Brawl Stars API returns an error."""
    status_code = 502
    message = "Failed to communicate with Brawl Stars API"
    error_code = "BRAWLSTARS_API_ERROR"


class MaintenanceError(BrawlGPTError):
    """Raised when Brawl Stars API is under maintenance."""
    status_code = 503
    message = "Brawl Stars API is currently under maintenance"
    error_code = "MAINTENANCE"


class AIGenerationError(BrawlGPTError):
    """Raised when AI insight generation fails."""
    status_code = 503
    message = "Failed to generate AI insights"
    error_code = "AI_GENERATION_ERROR"


class AIProviderError(BrawlGPTError):
    """Raised when AI provider (OpenRouter) is unavailable."""
    status_code = 503
    message = "AI service temporarily unavailable"
    error_code = "AI_PROVIDER_ERROR"


# =============================================================================
# Cache Errors
# =============================================================================

class CacheError(BrawlGPTError):
    """Raised when cache operations fail."""
    status_code = 500
    message = "Cache operation failed"
    error_code = "CACHE_ERROR"


class CacheConnectionError(CacheError):
    """Raised when cache connection fails."""
    message = "Failed to connect to cache service"
    error_code = "CACHE_CONNECTION_ERROR"


# =============================================================================
# Database Errors
# =============================================================================

class DatabaseError(BrawlGPTError):
    """Raised when database operations fail."""
    status_code = 500
    message = "Database operation failed"
    error_code = "DATABASE_ERROR"


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails."""
    message = "Failed to connect to database"
    error_code = "DATABASE_CONNECTION_ERROR"


# =============================================================================
# Authentication/Authorization Errors
# =============================================================================

class AuthenticationError(BrawlGPTError):
    """Raised when authentication fails."""
    status_code = 401
    message = "Authentication required"
    error_code = "AUTHENTICATION_REQUIRED"


class InvalidCredentialsError(AuthenticationError):
    """Raised when login credentials are invalid."""
    message = "Invalid email or password"
    error_code = "INVALID_CREDENTIALS"


class TokenExpiredError(AuthenticationError):
    """Raised when JWT token has expired."""
    message = "Token has expired"
    error_code = "TOKEN_EXPIRED"


class InvalidTokenError(AuthenticationError):
    """Raised when JWT token is invalid."""
    message = "Invalid token"
    error_code = "INVALID_TOKEN"


class AuthorizationError(BrawlGPTError):
    """Raised when user lacks permission."""
    status_code = 403
    message = "Access denied"
    error_code = "ACCESS_DENIED"


# =============================================================================
# Validation Errors
# =============================================================================

class ValidationError(BrawlGPTError):
    """Raised when request validation fails."""
    status_code = 400
    message = "Validation error"
    error_code = "VALIDATION_ERROR"

    def __init__(self, message: Optional[str] = None, field_errors: Optional[dict[str, str]] = None):
        super().__init__(message, details={"field_errors": field_errors or {}})


# =============================================================================
# Resource Errors
# =============================================================================

class ResourceNotFoundError(BrawlGPTError):
    """Raised when a requested resource does not exist."""
    status_code = 404
    message = "Resource not found"
    error_code = "RESOURCE_NOT_FOUND"


class ResourceConflictError(BrawlGPTError):
    """Raised when a resource conflict occurs (e.g., duplicate)."""
    status_code = 409
    message = "Resource conflict"
    error_code = "RESOURCE_CONFLICT"


# =============================================================================
# Service Errors
# =============================================================================

class ServiceUnavailableError(BrawlGPTError):
    """Raised when a service is temporarily unavailable."""
    status_code = 503
    message = "Service temporarily unavailable"
    error_code = "SERVICE_UNAVAILABLE"


class TimeoutError(BrawlGPTError):
    """Raised when an operation times out."""
    status_code = 504
    message = "Operation timed out"
    error_code = "TIMEOUT"
