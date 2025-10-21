import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from passlib.context import CryptContext
from passlib.hash import bcrypt

# Password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password: Plain text password to hash

    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to verify against

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


# JWT configuration
def get_jwt_secret_key():
    """Get JWT secret key with production validation.

    In production (FLASK_ENV=production), this function validates that:
    - JWT_SECRET_KEY is set and not using weak defaults
    - Secret is at least 32 characters long

    Raises:
        ValueError: If production deployment uses weak or missing JWT secret

    Returns:
        JWT secret key from environment or development default
    """
    secret = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-change-me")
    is_production = os.getenv("FLASK_ENV") == "production"

    if is_production:
        weak_secrets = ["dev-jwt-secret-change-me", "dev-secret-change-me", "secret123"]
        if secret in weak_secrets or len(secret) < 32:
            raise ValueError(
                "Production deployment requires strong JWT_SECRET_KEY (min 32 chars). "
                "Set JWT_SECRET_KEY environment variable."
            )

    return secret


JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token.

    Args:
        data: Payload data to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, get_jwt_secret_key(), algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT access token.

    Args:
        token: JWT token string to decode

    Returns:
        Decoded payload if valid, None if invalid or expired
    """
    try:
        payload = jwt.decode(token, get_jwt_secret_key(), algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None


def create_user_token(user_id: int, email: str) -> str:
    """Create a JWT token for a user.

    Args:
        user_id: User's database ID
        email: User's email address

    Returns:
        JWT token string
    """
    token_data = {"sub": str(user_id), "email": email, "type": "access"}
    return create_access_token(token_data)


def get_user_from_token(token: str) -> Optional[Dict[str, Any]]:
    """Extract user information from a JWT token.

    Args:
        token: JWT token string

    Returns:
        User data dict if valid, None if invalid
    """
    payload = decode_access_token(token)
    if payload is None:
        return None

    user_id = payload.get("sub")
    email = payload.get("email")

    if user_id is None or email is None:
        return None

    return {"user_id": int(user_id), "email": email}


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode a JWT token.

    Args:
        token: JWT token string to verify

    Returns:
        Decoded payload if valid, None if invalid
    """
    return decode_access_token(token)
