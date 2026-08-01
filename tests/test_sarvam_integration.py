"""
Test Suite - Sarvam AI integration tests.
"""
import pytest
from unknown_verdict.sarvam.client import sarvam_client, SarvamModel, SarvamMessage
from unknown_verdict.config import settings


class TestSarvamClient:
    """Test Sarvam AI client functionality."""

    @pytest.mark.asyncio
    async def test_health_check(self):
        health = await sarvam_client.health_check()
        assert "status" in health
        assert "configured" in health
        assert "models" in health

    @pytest.mark.asyncio
    async def test_chat_not_configured_fallback(self):
        """When Sarvam is not configured, chat should return error gracefully."""
        if not sarvam_client.is_configured:
            resp = await sarvam_client.chat(
                messages=[SarvamMessage(role="user", content="test")],
                model=SarvamModel.SARVAM_30B,
            )
            assert resp.success is False
            assert resp.error is not None

    @pytest.mark.asyncio
    async def test_reason_not_configured_fallback(self):
        """When Sarvam is not configured, reason should return error gracefully."""
        if not sarvam_client.is_configured:
            resp = await sarvam_client.reason(prompt="test query")
            assert resp.success is False

    @pytest.mark.asyncio
    async def test_fast_response_not_configured_fallback(self):
        if not sarvam_client.is_configured:
            resp = await sarvam_client.fast_response(prompt="test")
            assert resp.success is False


class TestSarvamUsageStats:
    """Test usage statistics tracking."""

    def test_usage_stats_structure(self):
        stats = sarvam_client.usage
        d = stats.to_dict()
        assert "total_requests" in d
        assert "total_105b_requests" in d
        assert "total_30b_requests" in d
        assert "total_tokens" in d
        assert "total_errors" in d
        assert "avg_latency_ms" in d


class TestSarvamModels:
    """Test model enumeration."""

    def test_model_values(self):
        assert SarvamModel.SARVAM_105B.value == "sarvam-105b"
        assert SarvamModel.SARVAM_30B.value == "sarvam-30b"


class TestRAGSystem:
    """Test RAG retrieval system."""

    @pytest.mark.asyncio
    async def test_rag_retrieve(self):
        from unknown_verdict.core import rag_system
        results = rag_system.retrieve("fundamental rights")
        assert isinstance(results, list)
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_rag_context(self):
        from unknown_verdict.core import rag_system
        context = rag_system.get_context("Article 21")
        assert isinstance(context, str)

    @pytest.mark.asyncio
    async def test_rag_ingest(self):
        from unknown_verdict.core import rag_system
        doc = rag_system.ingest_document(
            title="Test Document",
            content="This is a test legal document about contract law.",
            doc_type="test",
        )
        assert doc.doc_id
        assert len(doc.chunks) > 0

    def test_rag_stats(self):
        from unknown_verdict.core import rag_system
        stats = rag_system.stats()
        assert stats["total_documents"] > 0
        assert stats["total_chunks"] > 0


class TestAgentRegistry:
    """Test agent registry."""

    def test_agent_count(self):
        from unknown_verdict.core import agent_registry
        assert len(agent_registry.get_all()) == 250

    def test_agent_specializations(self):
        from unknown_verdict.core import agent_registry
        stats = agent_registry.stats()
        assert stats["total_agents"] == 250
        assert len(stats["by_specialization"]) == 12

    def test_find_best_agent(self):
        from unknown_verdict.core import agent_registry
        agent = agent_registry.find_best_agent("constitutional law fundamental rights")
        assert agent is not None

    def test_elite_agents(self):
        from unknown_verdict.core import agent_registry
        elite = agent_registry.get_elite_agents()
        assert len(elite) > 0


class TestVerifiers:
    """Test the 15 quality verifiers."""

    def test_verifier_count(self):
        from unknown_verdict.core import verifier_registry
        assert len(verifier_registry.get_all()) == 15

    def test_verify_response(self):
        from unknown_verdict.core import verifier_registry
        results = verifier_registry.verify_response(
            "This is a test response about Section 302 IPC. "
            "According to Section 302, murder is punishable by death. "
            "This is not legal advice. Please consult a professional."
        )
        assert len(results) == 15
        assert all(hasattr(r, "passed") for r in results)

    def test_verification_summary(self):
        from unknown_verdict.core import verifier_registry
        results = verifier_registry.verify_response("Test response with Section 302 IPC.")
        summary = verifier_registry.get_verification_summary(results)
        assert "overall_passed" in summary
        assert "overall_score" in summary
        assert "verifiers_passed" in summary
