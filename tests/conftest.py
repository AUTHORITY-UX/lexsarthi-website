"""
Test Suite - conftest.py with shared fixtures.
"""
import asyncio
import os
import sys
import time
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Ensure the package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from unknown_verdict.app import app
from unknown_verdict.config import settings
from unknown_verdict.auth import jwt_handler, auth_service, memory_user_store, Role


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def client():
    """Async HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="session")
def admin_token():
    """Get an admin JWT token."""
    return jwt_handler.create_access_token(
        "admin-test-id", "admin@unknownverdict.ai", Role.ADMIN.value
    )


@pytest.fixture(scope="session")
def guest_token():
    """Get a guest JWT token."""
    return jwt_handler.create_access_token(
        "guest-test-id", "guest@unknownverdict.ai", Role.GUEST.value
    )


@pytest.fixture(scope="session")
def auth_headers(admin_token):
    """Authorization headers for admin."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="session")
def guest_headers(guest_token):
    """Authorization headers for guest."""
    return {"Authorization": f"Bearer {guest_token}"}


@pytest.fixture(scope="session")
def api_key():
    """Generate a test API key."""
    from unknown_verdict.auth import APIKeyManager
    raw, _ = APIKeyManager.generate_key()
    # Register in the in-memory store
    admin = memory_user_store.get_user("admin@unknownverdict.ai")
    admin.setdefault("api_keys", []).append({
        "key_id": "test-key-001",
        "key_hash": APIKeyManager.hash_key(raw),
        "key_prefix": APIKeyManager.get_prefix(raw),
        "name": "Test Key",
        "scopes": ["chat", "legal", "compliance"],
        "rate_limit": "1000/minute",
        "is_active": True,
        "last_used": None,
        "total_requests": 0,
        "created_at": "2025-01-01T00:00:00Z",
    })
    return raw
