from fastapi import HTTPException, Header
from services.api_key_service import validate_api_key

def verify_token(authorization: str = Header(default=None)):
    """Verify API key from Bearer token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.split(" ")[1]
    if not validate_api_key(token):
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")

    return True
