import os
from typing import Optional
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.status import HTTP_401_UNAUTHORIZED
import httpx

from services.api_key_service import validate_api_key
from core.config import settings

bearer_scheme = HTTPBearer()


def validate_ms_key(token: str) -> bool:
    ms_key = os.getenv("MS_KEY")
    return ms_key is not None and token == ms_key


async def verify_token_remote(token: str) -> Optional[dict]:
    base_url = settings.AUTH_API_BASE_URL
    if not base_url:
        return None
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{base_url}/auth/me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            if resp.status_code == 200:
                body = resp.json()
                user = body.get("data") or body.get("user") or {}
                return {
                    "id": user.get("id"),
                    "email": user.get("email"),
                    "name": user.get("name"),
                }
        except Exception:
            pass
    return None


async def require_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
):
    if not credentials:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    token = credentials.credentials

    if validate_ms_key(token):
        return {"type": "master_key", "token": token}

    if validate_api_key(token):
        return {"type": "api_key", "token": token}

    payload = await verify_token_remote(token)
    if payload:
        return payload

    raise HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
    )
