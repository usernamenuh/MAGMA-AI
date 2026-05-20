import inspect
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from services.api_key_service import (
    create_api_key,
    validate_api_key,
    fetch_api_keys_by_user,
    revoke_api_key,
    fetch_all_api_keys,
    remove_api_key,
)
from services.auth_service import require_api_key
from utils.jwt_utils import format_validity_duration


router = APIRouter()


# ------------------ Request Models ------------------
class APIKeyRequest(BaseModel):
    user_id: str
    name: Optional[str] = "Default Key"
    validity_duration_days: Optional[int] = 30


# ------------------ Helper ------------------
async def run_maybe_async(func, *args, **kwargs):
    """
    Execute a callable regardless of whether it is sync or async.
    """
    if inspect.iscoroutinefunction(func):
        return await func(*args, **kwargs)
    return func(*args, **kwargs)

# ------------------ Endpoints ------------------

@router.post("/generate", response_model=dict)
async def generate_api_key(payload: APIKeyRequest, api_key: str = Depends(require_api_key)):
    """
    Generate a new API key for a given user.
    """
    api_key_entry = await run_maybe_async(
        create_api_key,
        user_id=payload.user_id,
        validity_duration_days=payload.validity_duration_days,
        name=payload.name,
    )
    return {
        "status": "success",
        "api_key": api_key_entry["api_key"],
        "name": api_key_entry["name"],
        "validity_duration_days": payload.validity_duration_days,
        "created_at": api_key_entry["created_at"],
    }


@router.get("/validate/{key}", response_model=dict)
async def validate_key(key: str, api_key: str = Depends(require_api_key)):
    """
    Validate if an API key is active and not expired.
    """
    is_valid = await run_maybe_async(validate_api_key, key)
    return {"status": "valid" if is_valid else "invalid"}


@router.get("/user/{user_id}", response_model=List[dict])
async def get_api_keys_by_user(user_id: str, api_key: str = Depends(require_api_key)):
    """
    Fetch all API keys associated with a specific user.
    """
    keys = await run_maybe_async(fetch_api_keys_by_user, user_id)
    return [
        {
            "user_id": k.user_id,
            "api_key": k.api_key,
            "name": k.name,
            "valid": k.valid,
            "validity_duration_days": k.validity_duration_days,
            "created_at": k.created_at,
            "updated_at": k.updated_at,
        }
        for k in keys
    ]


@router.post("/revoke/{key}", response_model=dict)
async def revoke_key(key: str, api_key: str = Depends(require_api_key)):
    """
    Invalidate an API key without deleting it.
    """
    success = await run_maybe_async(revoke_api_key, key)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"status": "success", "message": f"API key {key} revoked"}


@router.get("/all", response_model=List[dict])
async def get_all_api_keys(api_key: str = Depends(require_api_key)):
    """
    Return all API keys stored in the system.
    """
    keys = await run_maybe_async(fetch_all_api_keys)
    return [
        {
            "user_id": k.user_id,
            "api_key": k.api_key,
            "name": k.name,
            "valid": k.valid,
            "validity_duration_days": k.validity_duration_days,
            "created_at": k.created_at,
            "updated_at": k.updated_at,
        }
        for k in keys
    ]


@router.delete("/remove/{key}", response_model=dict)
async def remove_api_key_route(key: str, api_key: str = Depends(require_api_key)):
    """
    Permanently delete an API key by its value.
    """
    success = await run_maybe_async(remove_api_key, key)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"status": "success", "message": f"API key {key} deleted successfully"}
