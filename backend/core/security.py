"""
Security utilities for BrawlGPT.
Handles password hashing and JWT token management.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.exceptions import (
    AuthenticationError,
    InvalidCredentialsError,
    TokenExpiredError,
    InvalidTokenError,
)

logger = logging.getLogger(__name__)

# Configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Password hashing context using Argon2
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__time_cost=2,
    argon2__memory_cost=65536,
    argon2__parallelism=1,
)

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hash.

    Args:
        plain_password: The plain text password
        hashed_password: The hashed password to verify against

    Returns:
        True if password matches, False otherwise
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification failed: {e}")
        return False


def get_password_hash(password: str) -> str:
    """
    Generate a secure hash for a password.

    Args:
        password: The plain text password to hash

    Returns:
        The hashed password
    """
    return pwd_context.hash(password)


def create_access_token(
    data: dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a new JWT access token.

    Args:
        data: Data to encode in the token (typically {"sub": user_email})
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access"
    })

    secret_key = settings().secret_key.get_secret_value()
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    data: dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a new JWT refresh token.

    Args:
        data: Data to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT refresh token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh"
    })

    secret_key = settings().secret_key.get_secret_value()
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT access token.

    Args:
        token: The JWT token to decode

    Returns:
        The decoded token payload

    Raises:
        TokenExpiredError: If the token has expired
        InvalidTokenError: If the token is invalid
    """
    try:
        secret_key = settings().secret_key.get_secret_value()
        payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])

        # Verify token type
        if payload.get("type") != "access":
            raise InvalidTokenError("Invalid token type")

        return payload

    except jwt.ExpiredSignatureError:
        raise TokenExpiredError()
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise InvalidTokenError()


def decode_refresh_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT refresh token.

    Args:
        token: The JWT refresh token to decode

    Returns:
        The decoded token payload

    Raises:
        TokenExpiredError: If the token has expired
        InvalidTokenError: If the token is invalid
    """
    try:
        secret_key = settings().secret_key.get_secret_value()
        payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])

        # Verify token type
        if payload.get("type") != "refresh":
            raise InvalidTokenError("Invalid token type")

        return payload

    except jwt.ExpiredSignatureError:
        raise TokenExpiredError()
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise InvalidTokenError()


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme)
) -> Optional[dict[str, Any]]:
    """
    Get current user from token if provided, otherwise return None.
    Does not raise exception if no token.

    Args:
        token: Optional JWT token

    Returns:
        User payload if authenticated, None otherwise
    """
    if not token:
        return None

    try:
        return decode_access_token(token)
    except (TokenExpiredError, InvalidTokenError):
        return None


async def get_current_user(
    token: str = Depends(oauth2_scheme)
) -> dict[str, Any]:
    """
    Get current user from token. Raises exception if not authenticated.

    Args:
        token: JWT token from request

    Returns:
        User payload

    Raises:
        HTTPException: If authentication fails
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(token)
        email = payload.get("sub")

        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return payload

    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password meets security requirements.

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"

    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"

    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"

    return True, ""
