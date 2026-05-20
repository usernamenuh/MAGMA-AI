from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, validator

from core.config import settings
from services import user_service

router = APIRouter()


# ------------------ Models ------------------
class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

    @validator("email")
    def validate_email_domain(cls, value):
        if settings.allowed_domains:
            if not any(value.endswith(domain) for domain in settings.allowed_domains):
                raise HTTPException(status_code=422, detail="Email domain not allowed.")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @validator("email")
    def validate_email_domain(cls, value):
        if settings.allowed_domains:
            if not any(value.endswith(domain) for domain in settings.allowed_domains):
                raise HTTPException(status_code=422, detail="Email domain not allowed.")
        return value


class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    new_password: str



class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ValidateTokenRequest(BaseModel):
    access_token: str



# ------------------ Routes ------------------
@router.post("/register", response_model=dict)
async def register(payload: RegisterRequest):
    """Register a new user."""
    return await user_service.register_user(payload.name, payload.email, payload.password)


@router.post("/login", response_model=dict)
async def login(payload: LoginRequest):
    """Login and receive a JWT token."""
    return await user_service.login_user(payload.email, payload.password)


@router.post("/forgot-password", response_model=dict)
async def forgot_password(payload: ForgotPasswordRequest):
    """Reset a user password (no email send in this simple version)."""
    return await user_service.forgot_password(payload.email, payload.new_password)


@router.post("/refresh-token", response_model=dict)
async def refresh_token(payload: RefreshTokenRequest):
    """
    Validate refresh token and return a new access token.
    """
    return await user_service.refresh_token_service(payload.refresh_token)

@router.post("/validate-token", response_model=dict)
async def validate_token(payload: ValidateTokenRequest):
    """
    Validate access token and return details.
    """
    return await user_service.validate_token(payload.access_token)