"""
Authentication & Authorization Layer
- JWT token generation and validation
- Role-based access control (admin, user, guest)
- API key management
- FastAPI dependencies for protected routes
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger as log
from pydantic import BaseModel

from ..config import settings


# ===== Roles =====

class Role(str, Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


ROLE_HIERARCHY = {
    Role.ADMIN: [Role.ADMIN, Role.USER, Role.GUEST],
    Role.USER: [Role.USER, Role.GUEST],
    Role.GUEST: [Role.GUEST],
}


# ===== Token Models =====

class TokenData(BaseModel):
    user_id: str
    email: str
    role: str
    exp: int
    token_type: str = "access"


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


# ===== JWT Handler =====

class JWTHandler:
    """JWT token generation and validation."""

    def __init__(self) -> None:
        self.secret = settings.JWT_SECRET
        self.algorithm = settings.JWT_ALGORITHM

    def create_access_token(
        self, user_id: str, email: str, role: str, expires_minutes: Optional[int] = None
    ) -> str:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        payload = {
            "user_id": user_id, "email": email, "role": role,
            "exp": int(expire.timestamp()), "token_type": "access",
            "iat": int(datetime.now(timezone.utc).timestamp()),
        }
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def create_refresh_token(self, user_id: str, email: str, role: str) -> str:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        payload = {
            "user_id": user_id, "email": email, "role": role,
            "exp": int(expire.timestamp()), "token_type": "refresh",
            "iat": int(datetime.now(timezone.utc).timestamp()),
        }
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def decode_token(self, token: str) -> Optional[TokenData]:
        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
            return TokenData(
                user_id=payload["user_id"], email=payload["email"],
                role=payload["role"], exp=payload["exp"],
                token_type=payload.get("token_type", "access"),
            )
        except jwt.ExpiredSignatureError:
            log.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            log.warning(f"Invalid JWT token: {e}")
            return None

    def create_token_pair(self, user_id: str, email: str, role: str) -> TokenResponse:
        access = self.create_access_token(user_id, email, role)
        refresh = self.create_refresh_token(user_id, email, role)
        return TokenResponse(
            access_token=access, refresh_token=refresh,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )


jwt_handler = JWTHandler()


# ===== Password Hashing =====

class PasswordManager:
    """Simple password hashing using PBKDF2."""

    @staticmethod
    def hash_password(password: str) -> str:
        salt = secrets.token_hex(16)
        h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
        return f"{salt}${h.hex()}"

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        try:
            salt, stored_hash = hashed.split("$")
            h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
            return h.hex() == stored_hash
        except (ValueError, AttributeError):
            return False


# ===== API Key Manager =====

class APIKeyManager:
    """Generate and validate API keys."""

    @staticmethod
    def generate_key() -> tuple[str, str]:
        """Generate a new API key. Returns (raw_key, key_hash)."""
        raw = f"uv_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw.encode()).hexdigest()
        return raw, key_hash

    @staticmethod
    def hash_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode()).hexdigest()

    @staticmethod
    def get_prefix(raw_key: str) -> str:
        return raw_key[:12] + "..."


api_key_manager = APIKeyManager()


# ===== In-Memory User Store (fallback when DB not available) =====

class InMemoryUserStore:
    """Simple in-memory user store for when database is not configured."""

    def __init__(self) -> None:
        self._users: dict[str, dict] = {}
        self._init_defaults()

    def _init_defaults(self) -> None:
        # Create default admin and guest users
        admin_id = str(uuid.uuid4())
        self._users["admin@unknownverdict.ai"] = {
            "user_id": admin_id, "email": "admin@unknownverdict.ai",
            "password_hash": PasswordManager.hash_password("admin123"),
            "full_name": "System Admin", "role": Role.ADMIN.value,
            "is_active": True, "api_keys": [], "preferences": {},
        }
        guest_id = str(uuid.uuid4())
        self._users["guest@unknownverdict.ai"] = {
            "user_id": guest_id, "email": "guest@unknownverdict.ai",
            "password_hash": PasswordManager.hash_password("guest123"),
            "full_name": "Guest User", "role": Role.GUEST.value,
            "is_active": True, "api_keys": [], "preferences": {},
        }
        log.info(f"✅ In-memory user store initialized with admin and guest users")

    def get_user(self, email: str) -> Optional[dict]:
        return self._users.get(email)

    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        for u in self._users.values():
            if u["user_id"] == user_id:
                return u
        return None

    def create_user(self, email: str, password: str, full_name: str = "", role: str = "user") -> dict:
        if email in self._users:
            raise ValueError("User already exists")
        user = {
            "user_id": str(uuid.uuid4()), "email": email,
            "password_hash": PasswordManager.hash_password(password),
            "full_name": full_name, "role": role,
            "is_active": True, "api_keys": [], "preferences": {},
        }
        self._users[email] = user
        log.info(f"Created user: {email} ({role})")
        return user


memory_user_store = InMemoryUserStore()


# ===== FastAPI Dependencies =====

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
    request: Request = None,
) -> dict:
    """Extract and validate the current user from JWT or API key."""
    # Try API key from header
    api_key = request.headers.get(settings.API_KEY_HEADER) if request else None
    if api_key:
        user = await _authenticate_api_key(api_key)
        if user:
            return user
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Try JWT Bearer token
    if credentials and credentials.credentials:
        token_data = jwt_handler.decode_token(credentials.credentials)
        if token_data and token_data.token_type == "access":
            user = memory_user_store.get_user_by_id(token_data.user_id)
            if user and user["is_active"]:
                return user
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # No auth provided — return guest
    return memory_user_store.get_user("guest@unknownverdict.ai")


async def _authenticate_api_key(raw_key: str) -> Optional[dict]:
    """Authenticate using an API key."""
    key_hash = APIKeyManager.hash_key(raw_key)
    for user in memory_user_store._users.values():
        for stored_key in user.get("api_keys", []):
            if stored_key.get("key_hash") == key_hash and stored_key.get("is_active", True):
                stored_key["last_used"] = datetime.now(timezone.utc).isoformat()
                stored_key["total_requests"] = stored_key.get("total_requests", 0) + 1
                return user
    return None


async def require_role(required_role: Role):
    """Dependency factory: require a minimum role level."""
    async def _check(current_user: dict = Depends(get_current_user)):
        user_role = Role(current_user.get("role", "guest"))
        allowed = ROLE_HIERARCHY.get(user_role, [Role.GUEST])
        if required_role not in allowed:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required: {required_role.value}, "
                       f"Current: {user_role.value}",
            )
        return current_user
    return _check


# Pre-built role dependencies
require_admin = require_role(Role.ADMIN)
require_user = require_role(Role.USER)


# ===== Auth Service =====

class AuthService:
    """Authentication service for login, register, token refresh."""

    async def login(self, email: str, password: str) -> TokenResponse:
        user = memory_user_store.get_user(email)
        if not user or not PasswordManager.verify_password(password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        if not user["is_active"]:
            raise HTTPException(status_code=403, detail="Account deactivated")
        tokens = jwt_handler.create_token_pair(
            user["user_id"], user["email"], user["role"]
        )
        log.info(f"User logged in: {email}")
        return tokens

    async def register(self, email: str, password: str, full_name: str = "") -> dict:
        try:
            user = memory_user_store.create_user(email, password, full_name, Role.USER.value)
            tokens = jwt_handler.create_token_pair(
                user["user_id"], user["email"], user["role"]
            )
            return {"user": {"user_id": user["user_id"], "email": user["email"],
                             "full_name": user["full_name"], "role": user["role"]},
                    "tokens": tokens}
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))

    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        token_data = jwt_handler.decode_token(refresh_token)
        if not token_data or token_data.token_type != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        user = memory_user_store.get_user_by_id(token_data.user_id)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return jwt_handler.create_token_pair(user["user_id"], user["email"], user["role"])

    async def create_api_key(self, user: dict, name: str, scopes: list = None) -> dict:
        raw_key, key_hash = APIKeyManager.generate_key()
        key_record = {
            "key_id": str(uuid.uuid4()),
            "key_hash": key_hash,
            "key_prefix": APIKeyManager.get_prefix(raw_key),
            "name": name,
            "scopes": scopes or ["chat", "legal", "compliance"],
            "rate_limit": "100/minute",
            "is_active": True,
            "last_used": None,
            "total_requests": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        user.setdefault("api_keys", []).append(key_record)
        log.info(f"API key created for {user['email']}: {name}")
        return {"raw_key": raw_key, "key_id": key_record["key_id"],
                "key_prefix": key_record["key_prefix"], "name": name}

    async def list_api_keys(self, user: dict) -> list:
        return [
            {"key_id": k["key_id"], "key_prefix": k["key_prefix"], "name": k["name"],
             "scopes": k.get("scopes", []), "is_active": k["is_active"],
             "total_requests": k.get("total_requests", 0),
             "last_used": k.get("last_used"), "created_at": k.get("created_at")}
            for k in user.get("api_keys", [])
        ]

    async def revoke_api_key(self, user: dict, key_id: str) -> bool:
        for k in user.get("api_keys", []):
            if k["key_id"] == key_id:
                k["is_active"] = False
                log.info(f"API key revoked: {key_id}")
                return True
        return False


auth_service = AuthService()
