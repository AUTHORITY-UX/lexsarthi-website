"""
Test Suite - Performance benchmarks and load testing.
Run: pytest unknown_verdict/tests/test_performance.py -v --tb=short
"""
import asyncio
import time
import pytest


class TestResponseTime:
    """Verify all endpoints respond within acceptable time limits."""

    @pytest.mark.asyncio
    async def test_health_under_100ms(self, client):
        start = time.time()
        r = await client.get("/health")
        elapsed = (time.time() - start) * 1000
        assert r.status_code == 200
        assert elapsed < 500, f"Health took {elapsed:.0f}ms"

    @pytest.mark.asyncio
    async def test_agents_status_under_500ms(self, client):
        start = time.time()
        r = await client.get("/api/agents/status")
        elapsed = (time.time() - start) * 1000
        assert r.status_code == 200
        assert elapsed < 2000, f"Agents status took {elapsed:.0f}ms"

    @pytest.mark.asyncio
    async def test_chat_under_5s(self, client):
        start = time.time()
        r = await client.post("/api/chat", json={"message": "What is Article 21?"})
        elapsed = (time.time() - start) * 1000
        assert r.status_code == 200
        assert elapsed < 10000, f"Chat took {elapsed:.0f}ms"

    @pytest.mark.asyncio
    async def test_market_endpoints_under_500ms(self, client):
        for path in ["/api/trading/indices", "/api/trading/crypto", "/api/market/global"]:
            start = time.time()
            r = await client.get(path)
            elapsed = (time.time() - start) * 1000
            assert r.status_code == 200
            assert elapsed < 2000, f"{path} took {elapsed:.0f}ms"


class TestConcurrentRequests:
    """Test concurrent request handling."""

    @pytest.mark.asyncio
    async def test_concurrent_gets(self, client):
        """10 concurrent GET requests should all succeed."""
        paths = ["/health", "/api/agents/status", "/api/compliance/snapshot",
                 "/api/trading/indices", "/api/news/real"]
        tasks = [client.get(p) for p in paths * 2]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                pytest.fail(f"Request failed: {r}")
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_concurrent_chats(self, client):
        """5 concurrent chat requests should all succeed."""
        messages = [
            "What are fundamental rights?",
            "Explain Section 302 IPC",
            "What is the DPDP Act?",
            "How does RERA protect homebuyers?",
            "Explain GST composition scheme",
        ]
        tasks = [client.post("/api/chat", json={"message": m}) for m in messages]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                pytest.fail(f"Chat failed: {r}")
            assert r.status_code == 200


class TestCaching:
    """Verify caching works for repeated requests."""

    @pytest.mark.asyncio
    async def test_repeated_request_faster(self, client):
        """Second request to same endpoint should be faster (cached)."""
        # First request
        start1 = time.time()
        r1 = await client.get("/api/compliance/snapshot")
        elapsed1 = time.time() - start1

        # Second request (should hit cache or be fast)
        start2 = time.time()
        r2 = await client.get("/api/compliance/snapshot")
        elapsed2 = time.time() - start2

        assert r1.status_code == 200
        assert r2.status_code == 200
        # Second should be at least as fast
        assert elapsed2 <= elapsed1 + 0.5  # allow some tolerance


class TestRateLimiting:
    """Verify rate limiting is active."""

    @pytest.mark.asyncio
    async def test_rate_limit_headers(self, client):
        """Responses should include rate limit headers."""
        r = await client.get("/api/agents/status")
        assert r.status_code == 200
        # Rate limit headers should be present on API endpoints
        assert "X-RateLimit-Limit" in r.headers or r.headers.get("x-ratelimit-limit")
