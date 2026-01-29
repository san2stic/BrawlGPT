"""
Custom exceptions for BrawlGPT backend.
Provides structured error handling with appropriate HTTP status codes.
"""

from typing import Optional

class BrawlGPTError(Exception):
    """Base exception for all BrawlGPT errors."""
    status_code: int = 500
    message: str = "An internal error occurred"

    def __init__(self, message: Optional[str] = None):
        self.message = message or self.__class__.message
        super().__init__(self.message)


class PlayerNotFoundError(BrawlGPTError):
    """Raised when a player tag does not exist."""
    status_code = 404
    message = "Player not found"


class InvalidTagError(BrawlGPTError):
    """Raised when the player tag format is invalid."""
    status_code = 400
    message = "Invalid player tag format"


class RateLimitError(BrawlGPTError):
    """Raised when API rate limit is exceeded."""
    status_code = 429
    message = "Rate limit exceeded. Please try again later"


class BrawlStarsAPIError(BrawlGPTError):
    """Raised when Brawl Stars API returns an error."""
    status_code = 502
    message = "Failed to communicate with Brawl Stars API"


class AIGenerationError(BrawlGPTError):
    """Raised when AI insight generation fails."""
    status_code = 503
    message = "Failed to generate AI insights"


class MaintenanceError(BrawlGPTError):
    """Raised when Brawl Stars API is under maintenance."""
    status_code = 503
    message = "Brawl Stars API is currently under maintenance"
