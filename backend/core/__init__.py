"""
Core module for BrawlGPT.
Contains configuration, security, and exception handling.
"""

from .config import settings, Settings
from .exceptions import (
    BrawlGPTError,
    InvalidTagError,
    PlayerNotFoundError,
    RateLimitError,
    AIGenerationError,
    BrawlStarsAPIError,
    MaintenanceError,
    CacheError,
    DatabaseError,
    AuthenticationError,
    AuthorizationError,
)
from .security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
)

__all__ = [
    # Config
    "settings",
    "Settings",
    # Exceptions
    "BrawlGPTError",
    "InvalidTagError",
    "PlayerNotFoundError",
    "RateLimitError",
    "AIGenerationError",
    "BrawlStarsAPIError",
    "MaintenanceError",
    "CacheError",
    "DatabaseError",
    "AuthenticationError",
    "AuthorizationError",
    # Security
    "verify_password",
    "get_password_hash",
    "create_access_token",
    "decode_access_token",
]
