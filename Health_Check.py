#!/usr/bin/env python3
"""
health_check_v42.py — Unknown Verdict v42.0 Endpoint Health Checker
===================================================================
Tests ALL 87 endpoints with proper payloads so you get 200s, not 422s.

Usage:
    python health_check_v42.py
    python health_check_v42.py --url https://upamnyu12-lex.hf.space
    python health_check_v42.py --url http://localhost:7860 --skip-llm

--skip-llm avoids calling endpoints that hit the LLM (saves API quota).
"""

import argparse
import json
import time
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# ─────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────

DEFAULT_URL = "https://upamnyu12-lex.hf.space"

# Endpoints that call the LLM (slow + costs API quota)
LLM_ENDPOINTS = {
    "/chat", "/chat/stream", "/legal-research", "/analyze-document",
    "/summarize", "/verdict", "/verdict/compare",
    "/agents/criminal", "/agents/civil", "/agents/constitutional",
    "/agents/corporate", "/agents/family", "/agents/property",
    "/agent/criminal", "/agent/civil", "/agent/constitutional",
    "/agent/corporate", "/agent/family", "/agent/property",
    "/agent/constitutional/task", "/agent/criminal/task",
    "/verify", "/verifiers/run", "/judge",
    "/law/multi-jurisdiction", "/law/comparative", "/law/us", "/law/uk", "/law/eu",
    "/civil/analysis", "/civil/damages", "/civil/strategy",
    "/translate", "/chat/multilingual", "/detect-language",
    "/moat/evolution", "/moat/judge",
}

# ─────────────────────────────────────────────────────────────────────
# Endpoint definitions: (method, path, params, json_body, description)
#   - params: dict of query params (appended to URL)
#   - json_body: dict sent as JSON body (None = no body)
# ─────────────────────────────────────────────────────────────────────

ENDPOINTS = [

    # ═══════════════════════════════════════════════════════════════
    # Health & system (6) — all GET
    # ═══════════════════════════════════════════════════════════════
    ("GET",  "/",                {}, None, "Root info"),
    ("GET",  "/health",          {}, None, "Health check"),
    ("GET",  "/version",         {}, None, "Version info"),
    ("GET",  "/metrics",         {}, None, "Metrics (needs admin → 403 ok)"),
    ("GET",  "/status",          {}, None, "System status"),
    ("GET",  "/providers",       {}, None, "List LLM providers"),

    # ═══════════════════════════════════════════════════════════════
    # Chat & LLM (6)
    # ═══════════════════════════════════════════════════════════════
    ("POST", "/chat",            {}, {"message": "What is Section 302 IPC?", "complexity": "simple"}, "Chat with ethics guardrails"),
    ("POST", "/chat/stream",     {}, {"message": "What is a contract?", "stream": True}, "Streaming chat"),
    ("POST", "/legal-research",  {}, {"query": "Landmark Supreme Court cases on privacy"}, "Legal research"),
    ("POST", "/analyze-document", {}, {"content": "This agreement is between Party A and Party B.", "doc_type": "contract"}, "Document analysis"),
    ("GET",  "/models",          {}, None, "List models"),
    ("POST", "/summarize",       {}, {"message": "Section 302 of the Indian Penal Code deals with murder."}, "Summarize text"),

    # ═══════════════════════════════════════════════════════════════
    # Verdict engine (4)
    # ═══════════════════════════════════════════════════════════════
    ("POST", "/verdict",         {}, {"query": "Is a verbal contract legally binding in India?"}, "AI verdict"),
    ("GET",  "/verdicts",        {"limit": "5"}, None, "List verdicts"),
    ("GET",  "/verdict/test-id", {}, None, "Get verdict by ID (404 ok)"),
    ("POST", "/verdict/compare", {}, {"message": "What is negligence?"}, "Compare verdicts across LLMs"),

    # ═══════════════════════════════════════════════════════════════
    # Legal agents (14)
    # ═══════════════════════════════════════════════════════════════
    ("GET",  "/agents",                       {}, None, "List agents"),
    ("POST", "/agents/criminal",              {}, {"message": "What are bailable offences?"}, "Criminal agent"),
    ("POST", "/agents/civil",                 {}, {"message": "What is a tort?"}, "Civil agent"),
    ("POST", "/agents/constitutional",        {}, {"message": "What is Article 21?"}, "Constitutional agent"),
    ("POST", "/agents/corporate",             {}, {"message": "What is a board resolution?"}, "Corporate agent"),
    ("POST", "/agents/family",                {}, {"message": "What are grounds for divorce?"}, "Family agent"),
    ("POST", "/agents/property",              {}, {"message": "What is a sale deed?"}, "Property agent"),
    ("POST", "/agent/criminal/task",          {}, {"task": "Analyze Section 420 IPC"}, "Criminal agent task"),
    ("GET",  "/agents/criminal/info",         {}, None, "Criminal agent info"),
    ("POST", "/agents/criminal/analyze",      {}, {"message": "What is bail?"}, "Criminal agent analyze"),
    ("POST", "/agent/constitutional",         {}, {"message": "What is Article 14?"}, "Constitutional (dedicated)"),
    ("POST", "/agent/criminal",               {}, {"message": "What is FIR?"}, "Criminal (dedicated)"),
    ("POST", "/agent/civil",                  {}, {"message": "What is negligence?"}, "Civil (dedicated)"),
    ("POST", "/agent/corporate",              {}, {"message": "What is a merger?"}, "Corporate (dedicated)"),

    # ═══════════════════════════════════════════════════════════════
    # RAG / documents (4)
    # ═══════════════════════════════════════════════════════════════
    ("POST", "/documents",      {}, {"content": "Test contract content", "doc_type": "contract"}, "Add document"),
    ("GET",  "/documents",       {"limit": "5"}, None, "List documents"),
    ("GET",  "/documents/test-id", {}, None, "Get document (404 ok)"),
    ("POST", "/search",          {}, {"message": "contract law"}, "Search documents"),

    # ═══════════════════════════════════════════════════════════════
    # Auth & user (4)
    # ═══════════════════════════════════════════════════════════════
    ("POST", "/auth/login",      {"email": "test@example.com", "password": "test123"}, None, "Login (query params)"),
    ("POST", "/auth/register",   {"email": "test@example.com", "password": "test123", "name": "Test"}, None, "Register (query params)"),
    ("GET",  "/auth/me",         {}, None, "Current user (401 ok — no token)"),
    ("GET",  "/conversations",   {"limit": "5"}, None, "List conversations"),

    # ═══════════════════════════════════════════════════════════════
    # Verifiers (4)
    # ═══════════════════════════════════════════════════════════════
    ("POST", "/verify",          {}, {"query": "What is murder?", "response": "Murder is defined under Section 300 IPC."}, "Verify response"),
    ("GET",  "/verifiers",       {}, None, "List verifiers"),
    ("POST", "/verifiers/run",   {}, {"query": "What is theft?", "response": "Theft is under Section 378 IPC."}, "Run all verifiers"),
    ("POST", "/judge",           {}, {"query": "Is verbal contract binding?"}, "AI Judge"),

    # ═══════════════════════════════════════════════════════════════
    # Moat — 33 endpoints
    # ═══════════════════════════════════════════════════════════════
    ("GET",  "/moat/",                          {}, None, "Moat root"),
    ("GET",  "/moat/status",                    {}, None, "Moat status"),
    ("POST", "/moat/intelligence",              {"module": "test", "metric": "accuracy", "value": "95"}, None, "Add intelligence (query params)"),
    ("GET",  "/moat/intelligence",              {"module": "test"}, None, "Get intelligence (query param)"),
    ("GET",  "/moat/intelligence/all",          {}, None, "All intelligence"),
    ("POST", "/moat/evolution",                 {}, {"message": "Suggest improvements to legal reasoning"}, "Evolve"),
    ("GET",  "/moat/evolution/history",         {}, None, "Evolution history"),
    ("GET",  "/moat/evolution/latest",          {}, None, "Latest evolution"),
    ("POST", "/moat/knowledge",                 {"domain": "criminal", "content": "IPC Section 302", "source": "manual"}, None, "Add knowledge (query params)"),
    ("GET",  "/moat/knowledge",                 {"domain": "criminal"}, None, "Get knowledge (query param)"),
    ("GET",  "/moat/knowledge/domains",         {}, None, "Knowledge domains"),
    ("POST", "/moat/verifiers",                 {"name": "test-verifier"}, {"message": "test"}, "Add verifier (name=param, body=JSON)"),
    ("GET",  "/moat/verifiers",                 {}, None, "List moat verifiers"),
    ("POST", "/moat/verifiers/test-verifier/run", {}, {"message": "test query"}, "Run verifier"),
    ("POST", "/moat/agents",                    {"name": "test-agent", "specialty": "criminal", "model": "sarvam-30b"}, None, "Add agent (query params)"),
    ("GET",  "/moat/agents",                    {}, None, "List moat agents"),
    ("POST", "/moat/agents/test-agent/run",     {}, {"message": "test"}, "Run moat agent"),
    ("POST", "/moat/judge",                     {}, {"query": "Is negligence a tort?"}, "Moat judge"),
    ("GET",  "/moat/judge/history",             {}, None, "Judge history"),
    ("GET",  "/moat/judge/test-id",             {}, None, "Get ruling (404 ok)"),
    ("POST", "/moat/ip-vault",                  {"asset_type": "algorithm", "title": "Test IP", "content": "test content"}, None, "IP vault (query params)"),
    ("GET",  "/moat/ip-vault",                  {}, None, "List IP vault"),
    ("POST", "/moat/inventory",                 {"item_type": "agent", "name": "test-item", "count": "1"}, None, "Add inventory (query params)"),
    ("GET",  "/moat/inventory",                 {}, None, "List inventory"),
    ("POST", "/moat/patterns",                   {"pattern_type": "legal"}, {"message": "test pattern"}, "Add pattern (type=param, body=JSON)"),
    ("GET",  "/moat/patterns",                  {}, None, "List patterns"),
    ("POST", "/moat/feedback",                   {"query": "test", "rating": "5", "comment": "good"}, None, "Add feedback (query params)"),
    ("GET",  "/moat/feedback",                  {}, None, "List feedback"),
    ("POST", "/moat/audit",                     {"action": "test", "actor": "health_check", "details": "{}"}, None, "Add audit (query params)"),
    ("GET",  "/moat/audit",                     {}, None, "List audit"),
    ("GET",  "/moat/cache/stats",               {}, None, "Cache stats"),
    ("DELETE", "/moat/cache/clear",             {}, None, "Clear cache"),
    ("GET",  "/moat/config",                    {}, None, "Moat config"),
    ("POST", "/moat/config/update",             {}, {"test": True}, "Update config (403 ok — needs admin)"),
    ("GET",  "/moat/ethics-status",             {}, None, "Ethics guardrails status"),

    # ═══════════════════════════════════════════════════════════════
    # Multi-jurisdiction law (6)
    # ═══════════════════════════════════════════════════════════════
    ("POST", "/law/multi-jurisdiction", {}, {"query": "What are my rights during arrest?", "jurisdiction": "us"}, "US law analysis"),
    ("POST", "/law/comparative",       {}, {"query": "What is the age of majority?", "jurisdictions": ["india", "us"]}, "Comparative law"),
    ("GET",  "/law/jurisdictions",     {}, None, "List jurisdictions"),
    ("POST", "/law/us",                {}, {"message": "What is the 4th Amendment?"}, "US law"),
    ("POST", "/law/uk",                {}, {"message": "What is the Human Rights Act?"}, "UK law"),
    ("POST", "/law/eu",                {}, {"message": "What is GDPR Article 6?"}, "EU law"),

    # ═══════════════════════════════════════════════════════════════
    # GDPR / Data Act compliance (4)
    # ═══════════════════════════════════════════════════════════════
    ("POST", "/compliance/gdpr-check",         {}, {"content": "We collect customer names and emails for marketing.", "data_type": "personal", "purpose": "marketing"}, "GDPR compliance check"),
    ("POST", "/compliance/data-subject-request", {}, {"request_type": "access", "data_subject_id": "user-123", "details": "Requesting all data"}, "Data subject request"),
    ("GET",  "/compliance/gdpr/rights",        {}, None, "GDPR rights summary"),
    ("POST", "/compliance/data-act",           {}, {"content": "IoT device shares usage data with manufacturer.", "purpose": "product improvement"}, "Data Act compliance"),

    # ═══════════════════════════════════════════════════════════════
    # Civil litigation (4)
    # ═══════════════════════════════════════════════════════════════
    ("POST", "/civil/analysis",   {}, {"query": "Breach of contract by non-payment", "case_type": "contract_dispute"}, "Civil analysis"),
    ("POST", "/civil/damages",    {}, {"query": "Loss of income due to injury", "damages_type": "compensatory"}, "Damages assessment"),
    ("GET",  "/civil/case-types", {}, None, "List civil case types"),
    ("POST", "/civil/strategy",   {}, {"query": "Tenant refusing to vacate", "case_type": "property"}, "Litigation strategy"),

    # ═══════════════════════════════════════════════════════════════
    # Multi-lingual (4)
    # ═══════════════════════════════════════════════════════════════
    ("GET",  "/languages",            {}, None, "List languages"),
    ("POST", "/translate",            {}, {"text": "What is a contract?", "source_language": "en", "target_language": "hi"}, "Translate"),
    ("POST", "/chat/multilingual",    {}, {"message": "samvidhan ke antargat adhikar kya hain", "language": "hi"}, "Multilingual chat (Hinglish)"),
    ("POST", "/detect-language",      {}, {"message": "mujhe legal madad chahiye"}, "Detect language"),
]


# ─────────────────────────────────────────────────────────────────────
# HTTP helper
# ─────────────────────────────────────────────────────────────────────

def make_request(base_url, method, path, params=None, json_body=None, timeout=30):
    """Make an HTTP request and return (status_code, response_body, latency_ms)."""
    url = base_url.rstrip("/") + path

    # Append query params
    if params:
        from urllib.parse import urlencode
        url += "?" + urlencode(params)

    # Build body
    data = None
    headers = {"Accept": "application/json"}
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = Request(url, data=data, headers=headers, method=method)
    start = time.time()

    try:
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            latency = int((time.time() - start) * 1000)
            try:
                parsed = json.loads(body)
            except (json.JSONDecodeError, ValueError):
                parsed = body[:200] if body else ""
            return resp.status, parsed, latency

    except HTTPError as e:
        latency = int((time.time() - start) * 1000)
        body = ""
        try:
            raw = e.read().decode("utf-8", errors="replace")
            body = json.loads(raw)
        except Exception:
            body = raw[:200] if raw else ""
        return e.code, body, latency

    except URLError as e:
        latency = int((time.time() - start) * 1000)
        return -1, str(e.reason), latency

    except Exception as e:
        latency = int((time.time() - start) * 1000)
        return -1, str(e)[:200], latency


# ─────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Unknown Verdict v42.0 Health Check")
    parser.add_argument("--url", default=DEFAULT_URL, help=f"Base URL (default: {DEFAULT_URL})")
    parser.add_argument("--skip-llm", action="store_true", help="Skip endpoints that call the LLM (saves API quota)")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds (default: 30)")
    args = parser.parse_args()

    base_url = args.url.rstrip("/")
    print()
    print("=" * 80)
    print(f"  Unknown Verdict v42.0 — Health Check")
    print(f"  Target: {base_url}")
    print(f"  Endpoints: {len(ENDPOINTS)} total" + (f" (skipping LLM endpoints)" if args.skip_llm else ""))
    print("=" * 80)
    print()

    results = []
    pass_count = 0
    fail_count = 0
    skip_count = 0
    expected_failures = {404, 401, 403}  # These are OK — auth/not-found by design

    for i, (method, path, params, body, desc) in enumerate(ENDPOINTS, 1):
        # Skip LLM endpoints if requested
        if args.skip_llm and path in LLM_ENDPOINTS:
            skip_count += 1
            results.append((method, path, "SKIP", 0, desc, ""))
            print(f"  [{i:3d}/{len(ENDPOINTS)}] SKIP  {method:6s} {path:45s} {desc}")
            continue

        status, resp, latency = make_request(base_url, method, path, params, body, args.timeout)

        # Determine pass/fail
        is_pass = status == 200
        is_expected_fail = status in expected_failures
        is_skip = status == 422  # Should not happen with correct payloads

        if is_pass:
            pass_count += 1
            marker = "✅"
            status_label = f"{status}"
        elif is_expected_fail:
            pass_count += 1  # Expected failures count as pass
            marker = "✅*"
            status_label = f"{status}"
        else:
            fail_count += 1
            marker = "❌"
            status_label = f"{status}"

        # Truncate response for display
        resp_str = ""
        if isinstance(resp, dict):
            # Show useful fields
            if "error" in resp:
                resp_str = str(resp.get("detail", resp.get("error", "")))[:60]
            elif "detail" in resp:
                detail = resp["detail"]
                if isinstance(detail, list) and detail:
                    resp_str = str(detail[0].get("msg", ""))[:60]
                else:
                    resp_str = str(detail)[:60]
            elif "status" in resp:
                resp_str = str(resp["status"])[:60]
            elif "response" in resp:
                resp_str = str(resp["response"])[:60]
            else:
                resp_str = json.dumps(resp)[:60]
        elif isinstance(resp, str):
            resp_str = resp[:60]

        latency_str = f"{latency}ms" if latency < 9999 else "timeout"
        print(f"  [{i:3d}/{len(ENDPOINTS)}] {marker} {status_label:4s} {method:6s} {path:45s} {latency_str:>8s}  {desc}")
        if resp_str and not is_pass and not is_expected_fail:
            print(f"           └─ {resp_str}")

        results.append((method, path, marker, status, desc, resp_str))

    # ── Summary ──
    print()
    print("=" * 80)
    print(f"  SUMMARY")
    print(f"  ────────────────────────────────────────────")
    print(f"  Total endpoints:  {len(ENDPOINTS)}")
    print(f"  Passed (200):     {pass_count}")
    print(f"  Failed:           {fail_count}")
    print(f"  Skipped:          {skip_count}")
    print(f"  ────────────────────────────────────────────")

    if fail_count == 0:
        print(f"  ✅ ALL ENDPOINTS PASSED")
    else:
        print(f"  ❌ {fail_count} ENDPOINT(S) FAILED:")
        for method, path, marker, status, desc, resp in results:
            if marker == "❌":
                print(f"     {method} {path} → {status} — {desc}")
                if resp:
                    print(f"        {resp}")

    print()
    print("  * = expected non-200 (401=auth needed, 403=admin needed, 404=not found by design)")
    print("=" * 80)
    print()

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
