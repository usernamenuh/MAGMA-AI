import asyncio
from fastapi import HTTPException, status
from db.session import SessionLocal
from repositories import user_repository as repo
from utils.jwt_utils import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    verify_token,
)

# ---------------- UTIL -----------------

async def run_db(fn, *args):
    """Run synchronous DB work in thread executor (non-blocking)."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: fn(*args))


# ---------------- REGISTER -----------------

async def register_user(name: str, email: str, password: str):
    """Register new user (non-blocking)."""
    def task():
        with SessionLocal() as db:
            existing = repo.get_user_by_email(db, email)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )

            hashed_pw = hash_password(password)
            user = repo.create_user(db, name, email, hashed_pw)
            return {"message": "User registered successfully", "user_id": user.user_id}

    return await run_db(task)


# ---------------- LOGIN -----------------

async def login_user(email: str, password: str):
    """Authenticate and return tokens (non-blocking)."""
    def task():
        with SessionLocal() as db:
            user = repo.get_user_by_email(db, email)
            if not user or not verify_password(password, user.password_hash):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password",
                )

            access_token = create_access_token({"id": user.user_id, "email": user.email})
            refresh_token = create_refresh_token({"id": user.user_id, "email": user.email})

            repo.update_refresh_token(db, user.user_id, refresh_token)

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "user": {
                    "id": user.user_id,
                    "email": user.email,
                    "name": user.name,
                },
            }

    return await run_db(task)


# ---------------- REFRESH TOKEN -----------------

async def refresh_token_service(refresh_token: str):
    """Validate and issue new access token."""
    def task():
        with SessionLocal() as db:
            try:
                payload = decode_refresh_token(refresh_token)
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token",
                )

            user = repo.get_user_by_id(db, payload.get("id"))

            if not user or user.refresh_token != refresh_token:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Refresh token expired or invalid",
                )

            new_access = create_access_token({"id": user.user_id, "email": user.email})
            return {"access_token": new_access, "token_type": "bearer"}

    return await run_db(task)


# ---------------- VALIDATE ACCESS TOKEN -----------------

async def validate_token(token: str):
    """Validate access token (still synchronous but cheap)."""
    # cheap operation; no DB
    try:
        payload = verify_token(token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    return {
        "valid": True,
        "user_id": payload.get("id"),
        "email": payload.get("email"),
        "expires_at": payload.get("exp"),
    }


# ---------------- FORGOT PASSWORD -----------------

async def forgot_password(email: str, new_password: str):
    """Reset password (non-blocking)."""
    def task():
        with SessionLocal() as db:
            user = repo.get_user_by_email(db, email)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            hashed_pw = hash_password(new_password)
            repo.update_user_password(db, email, hashed_pw)
            return {"message": "Password updated successfully"}

    return await run_db(task)
