"""
Test Suite - All 36 endpoints.
Run: pytest unknown_verdict/tests/test_endpoints.py -v
"""
import pytest
import time


class TestSystemEndpoints:
    """System and health endpoints."""

    @pytest.mark.asyncio
    async def test_root(self, client):
        r = await client.get("/")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_health(self, client):
        r = await client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "healthy"
        assert "components" in data

    @pytest.mark.asyncio
    async def test_metrics(self, client):
        r = await client.get("/metrics")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_api_info(self, client):
        r = await client.get("/api/info")
        assert r.status_code == 200
        assert r.json()["version"] == "40.0"


class TestCoreLegal:
    """Group 1: Core Legal endpoints (1-8)."""

    @pytest.mark.asyncio
    async def test_chat(self, client):
        r = await client.post("/api/chat", json={"message": "What are my fundamental rights?"})
        assert r.status_code == 200
        data = r.json()
        assert "response" in data
        assert "agent_name" in data
        assert "verdict" in data

    @pytest.mark.asyncio
    async def test_chat_missing_message(self, client):
        r = await client.post("/api/chat", json={})
        assert r.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_legal_research(self, client):
        r = await client.post("/api/legal/research", json={"query": "Article 21 right to privacy"})
        assert r.status_code == 200
        assert "analysis" in r.json()

    @pytest.mark.asyncio
    async def test_legal_draft(self, client):
        r = await client.post("/api/legal/draft", json={
            "document_type": "contract", "title": "NDA",
            "parties": ["Party A", "Party B"], "terms": ["Confidentiality", "Term: 2 years"]
        })
        assert r.status_code == 200
        assert "draft" in r.json()

    @pytest.mark.asyncio
    async def test_legal_cases(self, client):
        r = await client.get("/api/legal/cases")
        assert r.status_code == 200
        assert "cases" in r.json()

    @pytest.mark.asyncio
    async def test_legal_cases_search(self, client):
        r = await client.get("/api/legal/cases", params={"query": "privacy"})
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_legal_manage(self, client):
        r = await client.get("/api/legal/manage")
        assert r.status_code == 200
        assert "cases" in r.json()

    @pytest.mark.asyncio
    async def test_compliance_snapshot(self, client):
        r = await client.get("/api/compliance/snapshot")
        assert r.status_code == 200
        assert "GDPR" in r.json()["frameworks"]

    @pytest.mark.asyncio
    async def test_compliance_scan(self, client):
        r = await client.post("/api/compliance/scan", json={"url": "https://example.com"})
        assert r.status_code == 200
        assert "compliance_scores" in r.json()

    @pytest.mark.asyncio
    async def test_compliance_monitor(self, client):
        r = await client.get("/api/compliance/monitor")
        assert r.status_code == 200
        assert r.json()["monitoring_status"] == "active"


class TestMarketsTrading:
    """Group 2: Markets & Trading (9-12)."""

    @pytest.mark.asyncio
    async def test_trading_indices(self, client):
        r = await client.get("/api/trading/indices")
        assert r.status_code == 200
        assert "NIFTY_50" in r.json()["indices"]

    @pytest.mark.asyncio
    async def test_trading_crypto(self, client):
        r = await client.get("/api/trading/crypto")
        assert r.status_code == 200
        assert "BTC" in r.json()["cryptocurrencies"]

    @pytest.mark.asyncio
    async def test_trading_market_symbol(self, client):
        r = await client.get("/api/trading/market/RELIANCE")
        assert r.status_code == 200
        assert r.json()["symbol"] == "RELIANCE"

    @pytest.mark.asyncio
    async def test_market_global(self, client):
        r = await client.get("/api/market/global")
        assert r.status_code == 200
        assert "indices" in r.json()
        assert "commodities" in r.json()


class TestReportsNews:
    """Group 3: Reports & News (13-16)."""

    @pytest.mark.asyncio
    async def test_reports_generate(self, client):
        r = await client.post("/api/reports/generate", json={
            "report_type": "market_analysis", "title": "Q3 Report"
        })
        assert r.status_code == 200
        assert "content" in r.json()

    @pytest.mark.asyncio
    async def test_reports_pdf(self, client):
        r = await client.post("/api/reports/pdf", json={
            "content": "Test report", "title": "Test"
        })
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_news_real(self, client):
        r = await client.get("/api/news/real")
        assert r.status_code == 200
        assert "articles" in r.json()

    @pytest.mark.asyncio
    async def test_news_personalized(self, client):
        r = await client.post("/api/news/personalized", json={
            "interests": ["Corporate", "Tax", "Data Protection"]
        })
        assert r.status_code == 200
        assert "curated_articles" in r.json()


class TestSportsGovernance:
    """Group 4: Sports & Governance (17-20)."""

    @pytest.mark.asyncio
    async def test_sports_cricket(self, client):
        r = await client.get("/api/sports/cricket")
        assert r.status_code == 200
        assert "matches" in r.json()

    @pytest.mark.asyncio
    async def test_sports_player(self, client):
        r = await client.get("/api/sports/player/P001")
        assert r.status_code == 200
        assert "contract_type" in r.json()

    @pytest.mark.asyncio
    async def test_governance_framework(self, client):
        r = await client.get("/api/governance/framework")
        assert r.status_code == 200
        assert "principles" in r.json()

    @pytest.mark.asyncio
    async def test_governance_policy(self, client):
        r = await client.post("/api/governance/policy", json={
            "organization": "TestCorp", "policy_type": "AI Usage Policy"
        })
        assert r.status_code == 200
        assert "sections" in r.json()


class TestPredictiveAI:
    """Group 5: Predictive AI (21-24)."""

    @pytest.mark.asyncio
    async def test_predict_case(self, client):
        r = await client.post("/api/predict/case", json={
            "case_type": "civil", "facts": "Breach of contract"
        })
        assert r.status_code == 200
        assert "predicted_outcome" in r.json()

    @pytest.mark.asyncio
    async def test_predict_market(self, client):
        r = await client.post("/api/predict/market", json={"symbol": "NIFTY_50"})
        assert r.status_code == 200
        assert "predicted_trend" in r.json()

    @pytest.mark.asyncio
    async def test_predict_risk(self, client):
        r = await client.post("/api/predict/risk", json={"industry": "Technology"})
        assert r.status_code == 200
        assert "risk_level" in r.json()

    @pytest.mark.asyncio
    async def test_train_web(self, client):
        r = await client.post("/api/train/web", json={
            "url": "https://indiacode.nic.in", "max_pages": 10
        })
        assert r.status_code == 200
        assert r.json()["training_status"] == "completed"


class TestPrivacySecurity:
    """Group 6: Privacy & Security (25-28)."""

    @pytest.mark.asyncio
    async def test_privacy_dsar(self, client):
        r = await client.post("/api/privacy/dsar", json={
            "request_type": "access",
            "data_subject_name": "John Doe",
            "data_subject_email": "john@test.com",
            "identification_verified": True,
        })
        assert r.status_code == 200
        assert "request_id" in r.json()

    @pytest.mark.asyncio
    async def test_privacy_dsar_invalid_type(self, client):
        r = await client.post("/api/privacy/dsar", json={
            "request_type": "invalid",
            "data_subject_name": "John",
            "data_subject_email": "j@test.com",
        })
        assert r.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_privacy_drop_check(self, client):
        r = await client.get("/api/privacy/drop/check", params={"entity_name": "TestCorp"})
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_security_alerts(self, client):
        r = await client.get("/api/security/alerts")
        assert r.status_code == 200
        assert "alerts" in r.json()

    @pytest.mark.asyncio
    async def test_security_scan(self, client):
        r = await client.post("/api/security/scan", json={"target": "system"})
        assert r.status_code == 200
        assert "scan_completed" in r.json()


class TestFinanceHrReIntl:
    """Group 7: Finance/HR/RE/Intl (29-32)."""

    @pytest.mark.asyncio
    async def test_finance_stocks(self, client):
        r = await client.get("/api/finance/stocks")
        assert r.status_code == 200
        assert "stocks" in r.json()

    @pytest.mark.asyncio
    async def test_hr_tasks(self, client):
        r = await client.get("/api/hr/tasks")
        assert r.status_code == 200
        assert "payroll" in r.json()

    @pytest.mark.asyncio
    async def test_realestate_properties(self, client):
        r = await client.get("/api/realestate/properties")
        assert r.status_code == 200
        assert "properties" in r.json()

    @pytest.mark.asyncio
    async def test_international_treaties(self, client):
        r = await client.get("/api/international/treaties")
        assert r.status_code == 200
        assert "treaties" in r.json()


class TestAdditionalCore:
    """Group 8: Additional Core (33-36)."""

    @pytest.mark.asyncio
    async def test_health_compliance(self, client):
        r = await client.get("/api/health/compliance")
        assert r.status_code == 200
        assert "compliance_scores" in r.json()

    @pytest.mark.asyncio
    async def test_doc_intelligence(self, client):
        r = await client.post(
            "/api/doc/intelligence",
            files={"file": ("test.txt", b"Test legal document about Section 302 IPC.", "text/plain")},
            data={"extract_text": "true"},
        )
        assert r.status_code == 200
        assert "entities_extracted" in r.json()

    @pytest.mark.asyncio
    async def test_lens_agents(self, client):
        r = await client.post("/api/lens/agents", json={"url": "https://example.com"})
        assert r.status_code == 200
        assert "compliance_scores" in r.json()

    @pytest.mark.asyncio
    async def test_infinity_status(self, client):
        r = await client.get("/api/infinity/status")
        assert r.status_code == 200
        assert r.json()["infinity_mode"] == "ENABLED"
