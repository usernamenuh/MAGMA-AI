from fastapi import APIRouter, Depends, Header, HTTPException
from services.api_key_service import generate_api_key, revoke_api_key, validate_api_key
from auth import verify_token

router = APIRouter(prefix="/keys")

@router.post("/generate")
async def create_key(_: bool = Depends(verify_token)):
    """Generate a new API key (admin protected)"""
    new_key = generate_api_key()
    return {"api_key": new_key}

@router.post("/revoke/{api_key}")
async def deactivate_key(api_key: str, _: bool = Depends(verify_token)):
    """Revoke an API key"""
    revoke_api_key(api_key)
    return {"status": "revoked", "api_key": api_key}

@router.get("/validate")
async def validate(authorization: str = Header(None)):
    """
    Validate an API key from `Authorization: Bearer <key>`.
    Returns 200 if valid, 401 otherwise.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.split(" ")[1]
    if not validate_api_key(token):
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")

    return {"status": "valid"}