import bcrypt
import jwt
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED

from core.config import settings

# Configuration
SECRET_KEY = settings.JWT_SECRET_KEY
REFRESH_SECRET = settings.JWT_REFRESH_SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # Default 1 day
REFRESH_TOKEN_EXPIRE_DAYS = 30  # Default 30 days


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    if not isinstance(password, str):
        raise ValueError("Password must be a string")

    # Ensure max 72 bytes before encoding (bcrypt limitation)
    # Note: Ideally, hash with SHA256 first to support longer passwords,
    # but this truncation prevents crashes.
    password = password[:72]
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a stored password against one provided by user."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))


def format_validity_duration(interval) -> str:
    """Convert PostgreSQL interval (timedelta or ISO string) to human-readable text."""
    if not interval:
        return "No Limit"

    # Handle timedelta objects
    if isinstance(interval, timedelta):
        days = interval.days
        return f"{days} Day{'s' if days != 1 else ''}"

    # Handle ISO duration strings like "P30D"
    if isinstance(interval, str) and interval.startswith("P"):
        days = interval.replace("P", "").replace("D", "")
        return f"{days} Day{'s' if days != '1' else ''}"

    return str(interval)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a short-lived access token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a long-lived refresh token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, REFRESH_SECRET, algorithm=ALGORITHM)


def verify_token(token: str) -> dict:
    """Decode and verify an Access Token."""
    try:
        # jwt.decode automatically validates the "exp" (expiration) claim
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail="Expired token",
    )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        )


def decode_refresh_token(token: str) -> dict:
    """Decode and verify a Refresh Token."""
    try:
        payload = jwt.decode(token, REFRESH_SECRET, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise Exception("Refresh token expired")
    except jwt.InvalidTokenError:
        raise Exception("Invalid refresh token")