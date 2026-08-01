"""
Auth Routes - Login, Register, Token Refresh, API Key Management.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .auth import (
    auth_service, jwt_handler, get_current_user, require_admin,
    Role, memory_user_store,
)

router = APIRouter()


class LoginRequest(BaseModel):
    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")


class RegisterRequest(BaseModel):
    email: str = Field(..., description="User email")
    password: str = Field(..., min_length=6, description="User password")
    full_name: str = Field("", description="Full name")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh token")


class CreateApiKeyRequest(BaseModel):
    name: str = Field(..., description="Human-readable key name")
    scopes: list = Field(default_factory=lambda: ["chat", "legal", "compliance"])


@router.post("/auth/login", tags=["Auth"])
async def login(request: LoginRequest):
    """Login and receive JWT access + refresh tokens."""
    tokens = await auth_service.login(request.email, request.password)
    return tokens.model_dump()


@router.post("/auth/register", tags=["Auth"])
async def register(request: RegisterRequest):
    """Register a new user account."""
    result = await auth_service.register(request.email, request.password, request.full_name)
    return result


@router.post("/auth/refresh", tags=["Auth"])
async def refresh_token(request: RefreshRequest):
    """Refresh an expired access token using a refresh token."""
    tokens = await auth_service.refresh_token(request.refresh_token)
    return tokens.model_dump()


@router.get("/auth/me", tags=["Auth"])
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user profile."""
    return {
        "user_id": current_user["user_id"],
        "email": current_user["email"],
        "full_name": current_user.get("full_name", ""),
        "role": current_user["role"],
        "is_active": current_user.get("is_active", True),
    }


@router.post("/auth/api-keys", tags=["Auth"])
async def create_api_key(
    request: CreateApiKeyRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create a new API key."""
    result = await auth_service.create_api_key(current_user, request.name, request.scopes)
    return result


@router.get("/auth/api-keys", tags=["Auth"])
async def list_api_keys(current_user: dict = Depends(get_current_user)):
    """List your API keys."""
    keys = await auth_service.list_api_keys(current_user)
    return {"api_keys": keys}


@router.delete("/auth/api-keys/{key_id}", tags=["Auth"])
async def revoke_api_key(
    key_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Revoke an API key."""
    revoked = await auth_service.revoke_api_key(current_user, key_id)
    if not revoked:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"status": "revoked", "key_id": key_id}
