"""
Error handling for OpenAI-compatible API
"""

from typing import Optional, Dict
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException


def create_error_response(message: str, error_type: str = "invalid_request_error", 
                         param: Optional[str] = None, code: Optional[str] = None) -> Dict:
    """Create OpenAI-compatible error response"""
    error = {
        "message": message,
        "type": error_type,
    }
    if param:
        error["param"] = param
    if code:
        error["code"] = code
    
    return {"error": error}


async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with OpenAI-compatible error format"""
    # If detail is already in OpenAI format, use it
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail
        )
    
    # Convert to OpenAI format
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(str(exc.detail))
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with OpenAI-compatible error format"""
    errors = exc.errors()
    if errors:
        first_error = errors[0]
        param = ".".join(str(loc) for loc in first_error["loc"])
        message = f"{first_error['msg']} at {param}"
    else:
        message = "Invalid request"
        param = None
    
    return JSONResponse(
        status_code=422,
        content=create_error_response(message, "invalid_request_error", param)
    ) 