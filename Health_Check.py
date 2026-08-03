#!/usr/bin/env python3
"""
Unknown Verdict v41.0 — Health Check Script
=============================================
Tests all 68 endpoints against a running instance.

Usage:
  python health_check.py                    # tests https://upamnyu12-lex.hf.space
  python health_check.py http://localhost:7860
  python health_check.py https://upamnyu12-lex.hf.space --admin-key YOUR_KEY
"""

import sys
import time
import json
import argparse
import httpx

BASE = "https://upamnyu12-lex.hf.space"

# All 68 endpoints
GET_ENDPOINTS = [
    "/", "/health", "/version", "/metrics", "/status", "/providers",
    "/models", "/agents",
    "/verdicts",
    "/documents",
    "/conversations",
    "/moat/", "/moat/status", "/moat/config",
    "/moat/intelligence/all", "/moat/evolution/history", "/moat/evolution/latest",
    "/moat/knowledge/domains", "/moat/verifiers", "/moat/agents",
    "/moat/judge/history", "/moat/ip-vault", "/moat/inventory",
    "/moat/patterns", "/moat/feedback", "/moat/audit", "/moat/cache/stats",
]

POST_ENDPOINTS = [
    ("/chat", {"message": "What is Section 420 IPC?"}),
    ("/legal-research", {"query": "Right to privacy under Indian Constitution", "jurisdiction": "india"}),
    ("/analyze-document", {"content": "This agreement is made between Party A and Party B.", "doc_type": "contract"}),
    ("/summarize", {"message": "Article 21 of the Constitution of India guarantees protection of life and personal liberty."}),
    ("/verdict", {"query": "A tenant refuses to vacate after lease expiry. What is the legal remedy?"}),
    ("/search", {"message": "property dispute"}),
    ("/agents/criminal", {"task": "Explain bail provisions under CrPC", "agent_type": "criminal"}),
    ("/moat/evolution", {"message": "Analyze and suggest improvements to legal response quality"}),
    ("/moat/verifiers", {"message": "Create verifier"}),
    ("/moat/verifiers/citation/run", {"message": "Section 420 IPC deals with cheating. AIR 1980 SC 1576."}),
    ("/moat/judge", {"query": "Whether a WhatsApp message constitutes a legally binding contract?"}),
    ("/moat/feedback", {"query": "test", "rating": 5}),
]


def color(code, text):
    return f"\033[{code}m{text}\033[0m"


def test_get(client, path, admin_key=None):
    headers = {}
    if admin_key:
        headers["X-Admin-Key"] = admin_key
    t0 = time.monotonic()
    try:
        resp = client.get(path, headers=headers, timeout=30)
        latency = (time.monotonic() - t0) * 1000
        return {
            "method": "GET", "path": path,
            "status": resp.status_code,
            "latency_ms": round(latency),
            "ok": 200 <= resp.status_code < 300,
        }
    except Exception as e:
        return {"method": "GET", "path": path, "status": 0, "error": str(e)[:100], "ok": False}


def test_post(client, path, body, admin_key=None):
    headers = {"Content-Type": "application/json"}
    if admin_key:
        headers["X-Admin-Key"] = admin_key
    t0 = time.monotonic()
    try:
        resp = client.post(path, json=body, headers=headers, timeout=60)
        latency = (time.monotonic() - t0) * 1000
        return {
            "method": "POST", "path": path,
            "status": resp.status_code,
            "latency_ms": round(latency),
            "ok": 200 <= resp.status_code < 300,
        }
    except Exception as e:
        return {"method": "POST", "path": path, "status": 0, "error": str(e)[:100], "ok": False}


def main():
    parser = argparse.ArgumentParser(description="Unknown Verdict health check")
    parser.add_argument("base_url", nargs="?", default=BASE, help="Base URL")
    parser.add_argument("--admin-key", default="", help="Admin key for protected endpoints")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  Unknown Verdict v41.0 — Health Check")
    print(f"  Target: {args.base_url}")
    print(f"{'='*60}\n")

    passed = 0
    failed = 0
    total_latency = 0

    with httpx.Client(timeout=60) as client:
        # GET endpoints
        print(f"--- GET Endpoints ({len(GET_ENDPOINTS)}) ---")
        for path in GET_ENDPOINTS:
            result = test_get(client, f"{args.base_url}{path}", args.admin_key)
            status_icon = color("32", "✅") if result["ok"] else color("31", "❌")
            latency_str = f"{result.get('latency_ms', '?')}ms"
            print(f"  {status_icon} GET  {path:40s} {result.get('status','?'):>4}  {latency_str:>8}")
            if result["ok"]:
                passed += 1
                total_latency += result.get("latency_ms", 0)
            else:
                failed += 1

        # POST endpoints
        print(f"\n--- POST Endpoints ({len(POST_ENDPOINTS)}) ---")
        for path, body in POST_ENDPOINTS:
            result = test_post(client, f"{args.base_url}{path}", body, args.admin_key)
            status_icon = color("32", "✅") if result["ok"] else color("31", "❌")
            latency_str = f"{result.get('latency_ms', '?')}ms"
            print(f"  {status_icon} POST {path:40s} {result.get('status','?'):>4}  {latency_str:>8}")
            if result["ok"]:
                passed += 1
                total_latency += result.get("latency_ms", 0)
            else:
                failed += 1

    # Summary
    total = passed + failed
    avg_latency = total_latency / passed if passed else 0
    print(f"\n{'='*60}")
    print(f"  Results: {color('32', str(passed))} passed, {color('31', str(failed))} failed, {total} total")
    print(f"  Avg latency (passed): {avg_latency:.0f}ms")
    print(f"  Pass rate: {passed/total*100:.1f}%")
    print(f"{'='*60}\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
