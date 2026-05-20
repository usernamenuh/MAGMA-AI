"""
Authentication module for the OpenAI-compatible API
"""

from typing import Optional
from fastapi import Header, HTTPException
from config import config
from errors import create_error_response


def verify_token(authorization: Optional[str] = Header(None)) -> str:
    """Verify Bearer token from Authorization header"""
    # Get expected token from configuration
    expected_token = config.api_key
    
    # If no token is configured, allow all requests (for local development)
    if not expected_token:
        return "no-auth-required"
    
    # Check if Authorization header is present
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail=create_error_response("Unauthorized", "invalid_request_error", 
                                        "Missing Authorization header", "authorization_missing")
        )
    
    # Check Bearer token format
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail=create_error_response("Unauthorized", "invalid_request_error",
                                        "Invalid Authorization header format", "authorization_invalid")
        )
    
    # Extract and verify token
    token = authorization.replace("Bearer ", "")
    if token != expected_token:
        raise HTTPException(
            status_code=401,
            detail=create_error_response("Unauthorized", "invalid_request_error",
                                        "Invalid API key", "invalid_api_key")
        )
    
    return token 