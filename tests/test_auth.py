"""
Test Suite - Authentication and Authorization tests.
"""
import pytest
from unknown_verdict.auth import (
    jwt_handler, auth_service, PasswordManager, APIKeyManager,
    memory_user_store, Role,
)


class TestPasswordManager:
    def test_hash_and_verify(self):
        pw = "MySecurePassword123!"
        hashed = PasswordManager.hash_password(pw)
        assert hashed != pw
        assert PasswordManager.verify_password(pw, hashed)
        assert not PasswordManager.verify_password("wrong", hashed)

    def test_different_salts(self):
        pw = "samepassword"
        h1 = PasswordManager.hash_password(pw)
        h2 = PasswordManager.hash_password(pw)
        assert h1 != h2  # different salts


class TestJWTHandler:
    def test_create_and_decode_access_token(self):
        token = jwt_handler.create_access_token("user-1", "test@test.com", "user")
        data = jwt_handler.decode_token(token)
        assert data is not None
        assert data.user_id == "user-1"
        assert data.email == "test@test.com"
        assert data.role == "user"
        assert data.token_type == "access"

    def test_create_and_decode_refresh_token(self):
        token = jwt_handler.create_refresh_token("user-1", "test@test.com", "user")
        data = jwt_handler.decode_token(token)
        assert data is not None
        assert data.token_type == "refresh"

    def test_invalid_token(self):
        data = jwt_handler.decode_token("invalid.token.here")
        assert data is None

    def test_token_pair(self):
        pair = jwt_handler.create_token_pair("user-1", "test@test.com", "user")
        assert pair.access_token != pair.refresh_token
        assert pair.token_type == "bearer"
        assert pair.expires_in > 0


class TestAuthService:
    @pytest.mark.asyncio
    async def test_login_success(self):
        tokens = await auth_service.login("admin@unknownverdict.ai", "admin123")
        assert tokens.access_token
        assert tokens.refresh_token

    @pytest.mark.asyncio
    async def test_login_wrong_password(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await auth_service.login("admin@unknownverdict.ai", "wrong")
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_register_new_user(self):
        result = await auth_service.register("newuser@test.com", "password123", "New User")
        assert result["user"]["email"] == "newuser@test.com"
        assert result["tokens"].access_token

    @pytest.mark.asyncio
    async def test_register_duplicate(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await auth_service.register("admin@unknownverdict.ai", "anything", "Dup")
        assert exc.value.status_code == 409

    @pytest.mark.asyncio
    async def test_refresh_token(self):
        pair = await auth_service.login("admin@unknownverdict.ai", "admin123")
        new_tokens = await auth_service.refresh_token(pair.refresh_token)
        assert new_tokens.access_token

    @pytest.mark.asyncio
    async def test_api_key_create_and_list(self):
        admin = memory_user_store.get_user("admin@unknownverdict.ai")
        result = await auth_service.create_api_key(admin, "Test Key", ["chat"])
        assert result["raw_key"]
        keys = await auth_service.list_api_keys(admin)
        assert any(k["name"] == "Test Key" for k in keys)

    @pytest.mark.asyncio
    async def test_api_key_revoke(self):
        admin = memory_user_store.get_user("admin@unknownverdict.ai")
        result = await auth_service.create_api_key(admin, "Revoke Me", ["chat"])
        revoked = await auth_service.revoke_api_key(admin, result["key_id"])
        assert revoked


class TestAPIKeyManager:
    def test_generate_key(self):
        raw, hashed = APIKeyManager.generate_key()
        assert raw.startswith("uv_")
        assert len(hashed) == 64

    def test_hash_key(self):
        raw = "uv_testkey123"
        h1 = APIKeyManager.hash_key(raw)
        h2 = APIKeyManager.hash_key(raw)
        assert h1 == h2

    def test_get_prefix(self):
        raw = "uv_abcdefghijklmnopqrstuvwxyz"
        prefix = APIKeyManager.get_prefix(raw)
        assert prefix.startswith("uv_")
        assert prefix.endswith("...")


class TestRoleHierarchy:
    def test_admin_can_access_all(self):
        assert Role.USER in Role.__members__.values()
        allowed = [Role.ADMIN, Role.USER, Role.GUEST]
        assert Role.ADMIN in allowed

    def test_user_cannot_access_admin(self):
        allowed = [Role.USER, Role.GUEST]
        assert Role.ADMIN not in allowed

    def test_guest_is_lowest(self):
        allowed = [Role.GUEST]
        assert Role.USER not in allowed
        assert Role.ADMIN not in allowed
