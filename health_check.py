#!/usr/bin/env python3
"""
Health Check Script — Unknown Verdict v41.0
=============================================
Tests ALL endpoints discovered from the live OpenAPI spec.
Auto-generates appropriate payloads for POST endpoints based on schema.

USAGE:
    # Test against the live HF Space
    python health_check.py

    # Test against localhost (during dev)
    python health_check.py --base http://localhost:7860

    # Output JSON report
    python health_check.py --json

    # Only show failures
    python health_check.py --failures-only

REQUIREMENTS:
    pip install httpx

DEPLOY: Run from any machine with network access to the Space.
"""

import argparse
import json
import sys
import time
import random
import string
from datetime import datetime
from typing import Any, Optional

try:
    import httpx
except ImportError:
    print("ERROR: pip install httpx")
    sys.exit(1)

# ──────────────────────────────────────────────────────────────────────────
# Smart payload generator — builds appropriate bodies from Pydantic schema
# ──────────────────────────────────────────────────────────────────────────
SAMPLE_LEGAL_QUERIES = [
    "What are the grounds for divorce under Hindu Marriage Act, 1955?",
    "Explain Section 302 of the Indian Penal Code.",
    "What is the process for filing an RTI application?",
    "What are my rights if arrested by police in India?",
    "Explain the concept of anticipatory bail under CrPC Section 438.",
]

SAMPLE_CASE_SUMMARIES = [
    "A tenant has not paid rent for 6 months. Landlord wants to evict.",
    "An employee was terminated without notice. Seeks reinstatement.",
    "A consumer received a defective product. Seller refuses refund.",
]


def _sample_value(prop_name: str, prop_schema: dict) -> Any:
    """Generate a sample value for a property based on its name and type."""
    name_lower = prop_name.lower()

    # Type-based defaults
    if prop_schema.get("type") == "boolean":
        return True
    if prop_schema.get("type") == "integer":
        return 1
    if prop_schema.get("type") == "number":
        return 1.0
    if prop_schema.get("type") == "array":
        items = prop_schema.get("items", {})
        return [_sample_value(prop_name, items)] if items else []
    if prop_schema.get("type") == "object":
        return {}

    # String — smart defaults based on name
    if prop_schema.get("type") == "string" or "string" in str(prop_schema.get("anyOf", [])):
        if "query" in name_lower or "question" in name_lower or "prompt" in name_lower:
            return random.choice(SAMPLE_LEGAL_QUERIES)
        if "message" in name_lower or "content" in name_lower or "text" in name_lower:
            return random.choice(SAMPLE_LEGAL_QUERIES)
        if "case" in name_lower or "summary" in name_lower:
            return random.choice(SAMPLE_CASE_SUMMARIES)
        if "email" in name_lower:
            return "test@example.com"
        if "id" in name_lower or "uuid" in name_lower:
            return "00000000-0000-0000-0000-000000000000"
        if "jurisdiction" in name_lower:
            return "india"
        if "language" in name_lower or "lang" in name_lower:
            return "en"
        if "model" in name_lower:
            return "sarvam"
        if "url" in name_lower:
            return "https://example.com"
        if "agent" in name_lower:
            return "legal_researcher"
        if "module" in name_lower:
            return "intelligence"
        if "name" in name_lower:
            return "test_item"
        if "title" in name_lower:
            return "Test Case"
        return "test_value"

    return "test_value"


def build_payload(schema: dict, openapi: dict) -> dict:
    """Build a request body from the OpenAPI request body schema."""
    if not schema:
        return {}

    # Resolve $ref
    if "$ref" in schema:
        ref_path = schema["$ref"].replace("#/", "").split("/")
        ref_schema = openapi
        for part in ref_path:
            ref_schema = ref_schema.get(part, {})
        schema = ref_schema

    # Handle requestBody → content → application/json → schema
    if "content" in schema:
        content = schema["content"]
        json_spec = content.get("application/json", content.get("*/*", {}))
        schema = json_spec.get("schema", {})

    # Resolve schema ref again
    if "$ref" in schema:
        ref_path = schema["$ref"].replace("#/", "").split("/")
        ref_schema = openapi
        for part in ref_path:
            ref_schema = ref_schema.get(part, {})
        schema = ref_schema

    properties = schema.get("properties", {})
    required = schema.get("required", [])

    payload = {}
    for prop_name in required:
        payload[prop_name] = _sample_value(prop_name, properties.get(prop_name, {}))

    # Also fill optional props with sample values for better coverage
    for prop_name, prop_schema in properties.items():
        if prop_name not in payload:
            payload[prop_name] = _sample_value(prop_name, prop_schema)

    return payload


# ──────────────────────────────────────────────────────────────────────────
# Main health checker
# ──────────────────────────────────────────────────────────────────────────
class HealthChecker:
    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout, connect=10.0),
            follow_redirects=True,
        )
        self.results: list[dict] = []
        self.openapi: dict = {}

    async def fetch_openapi(self) -> bool:
        """Fetch the OpenAPI spec to discover all endpoints."""
        try:
            resp = await self.client.get("/openapi.json")
            if resp.status_code == 200:
                self.openapi = resp.json()
                return True
            print(f"  ⚠️  /openapi.json returned {resp.status_code}")
            return False
        except Exception as e:
            print(f"  ❌ Cannot fetch /openapi.json: {e}")
            return False

    def extract_endpoints(self) -> list[dict]:
        """Extract all endpoints from the OpenAPI spec."""
        endpoints = []
        paths = self.openapi.get("paths", {})

        for path, methods in paths.items():
            for method, spec in methods.items():
                if method.upper() not in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                    continue
                # Skip HEAD/OPTIONS
                if method.upper() in ("HEAD", "OPTIONS"):
                    continue

                # Build query params for GET
                query_params = {}
                path_params = {}
                for param in spec.get("parameters", []):
                    if param.get("in") == "query":
                        query_params[param["name"]] = _sample_value(
                            param["name"], param.get("schema", {})
                        )
                    elif param.get("in") == "path":
                        path_params[param["name"]] = "test"

                # Build request body for POST/PUT/PATCH
                request_body = {}
                if "requestBody" in spec:
                    request_body = build_payload(spec["requestBody"], self.openapi)

                # Replace path params in URL
                test_path = path
                for pname, pval in path_params.items():
                    test_path = test_path.replace(f"{{{pname}}}", str(pval))

                endpoints.append({
                    "method": method.upper(),
                    "path": path,
                    "test_path": test_path,
                    "query_params": query_params,
                    "request_body": request_body,
                    "operation_id": spec.get("operationId", ""),
                    "summary": spec.get("summary", ""),
                    "tag": (spec.get("tags", ["untagged"]) or ["untagged"])[0],
                })

        return endpoints

    async def test_endpoint(self, ep: dict) -> dict:
        """Test a single endpoint and record the result."""
        start = time.time()
        result = {
            "method": ep["method"],
            "path": ep["path"],
            "tag": ep["tag"],
            "summary": ep["summary"],
            "status_code": None,
            "latency_ms": None,
            "success": False,
            "error": None,
            "response_preview": None,
        }

        try:
            if ep["method"] == "GET":
                resp = await self.client.get(
                    ep["test_path"],
                    params=ep["query_params"] or None,
                )
            elif ep["method"] == "POST":
                resp = await self.client.post(
                    ep["test_path"],
                    json=ep["request_body"] if ep["request_body"] else {},
                )
            elif ep["method"] == "PUT":
                resp = await self.client.put(
                    ep["test_path"],
                    json=ep["request_body"] if ep["request_body"] else {},
                )
            elif ep["method"] == "PATCH":
                resp = await self.client.patch(
                    ep["test_path"],
                    json=ep["request_body"] if ep["request_body"] else {},
                )
            elif ep["method"] == "DELETE":
                resp = await self.client.delete(ep["test_path"])
            else:
                result["error"] = f"Unsupported method: {ep['method']}"
                return result

            elapsed = (time.time() - start) * 1000
            result["status_code"] = resp.status_code
            result["latency_ms"] = round(elapsed, 1)

            # Success: 2xx
            if 200 <= resp.status_code < 300:
                result["success"] = True
                # Try to parse JSON for preview
                try:
                    body = resp.json()
                    preview = json.dumps(body)[:200]
                    result["response_preview"] = preview
                except Exception:
                    result["response_preview"] = resp.text[:200]
            elif resp.status_code == 422:
                result["error"] = "Validation error (422) — payload mismatch"
                result["response_preview"] = resp.text[:200]
            elif resp.status_code == 404:
                result["error"] = "Not found (404)"
            elif resp.status_code == 405:
                result["error"] = "Method not allowed (405)"
            elif resp.status_code >= 500:
                result["error"] = f"Server error ({resp.status_code})"
                result["response_preview"] = resp.text[:200]
            else:
                result["error"] = f"HTTP {resp.status_code}"

        except httpx.TimeoutException:
            elapsed = (time.time() - start) * 1000
            result["latency_ms"] = round(elapsed, 1)
            result["error"] = "Timeout"
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            result["latency_ms"] = round(elapsed, 1)
            result["error"] = str(e)[:200]

        return result

    async def run_all(self) -> dict:
        """Run health checks on all endpoints."""
        print(f"\n{'='*70}")
        print(f"  Unknown Verdict v41.0 — Health Check")
        print(f"  Target: {self.base_url}")
        print(f"  Time:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}\n")

        # 1. Fetch OpenAPI spec
        print("📡 Fetching OpenAPI spec...")
        if not await self.fetch_openapi():
            print("❌ Cannot reach the server. Is the HF Space awake?")
            print("   Tip: Visit https://upamnyu12-lex.hf.space in your browser to wake it.")
            await self.client.aclose()
            return {}

        # 2. Extract endpoints
        endpoints = self.extract_endpoints()
        print(f"✅ Discovered {len(endpoints)} endpoints\n")

        if not endpoints:
            print("⚠️  No endpoints found in OpenAPI spec.")
            await self.client.aclose()
            return {}

        # 3. Test each endpoint
        print(f"{'METHOD':<7} {'PATH':<45} {'STATUS':<8} {'LATENCY':<10} {'RESULT'}")
        print("-" * 90)

        for ep in endpoints:
            result = await self.test_endpoint(ep)
            self.results.append(result)

            status = str(result["status_code"] or "---")
            latency = f"{result['latency_ms']}ms" if result["latency_ms"] else "---"

            if result["success"]:
                status_str = f"✅ {status}"
            elif result["error"] and "Timeout" in str(result["error"]):
                status_str = f"⏰ {status}"
            elif result["status_code"] == 422:
                status_str = f"⚠️  {status}"
            elif result["status_code"] and result["status_code"] >= 500:
                status_str = f"❌ {status}"
            else:
                status_str = f"⚠️  {status}"

            print(f"{ep['method']:<7} {ep['path']:<45} {status_str:<17} {latency:<10}")

            # If there's an error, show it indented
            if result["error"] and not result["success"]:
                print(f"{'':>7} └─ {result['error']}")

        # 4. Summary
        total = len(self.results)
        passed = sum(1 for r in self.results if r["success"])
        failed_5xx = sum(1 for r in self.results if r["status_code"] and r["status_code"] >= 500)
        validation = sum(1 for r in self.results if r["status_code"] == 422)
        timeouts = sum(1 for r in self.results if r["error"] == "Timeout")
        other = total - passed - failed_5xx - validation - timeouts

        print(f"\n{'='*70}")
        print(f"  SUMMARY")
        print(f"{'='*70}")
        print(f"  Total endpoints:   {total}")
        print(f"  ✅ Passed (2xx):    {passed}")
        print(f"  ❌ Server errors:   {failed_5xx}")
        print(f"  ⚠️  Validation (422): {validation}")
        print(f"  ⏰ Timeouts:        {timeouts}")
        print(f"  ❓ Other:           {other}")
        print(f"  Pass rate:         {(passed/total*100):.1f}%")

        # Latency stats
        latencies = [r["latency_ms"] for r in self.results if r["latency_ms"] and r["success"]]
        if latencies:
            print(f"\n  Latency (successful endpoints):")
            print(f"    Min:    {min(latencies):.0f}ms")
            print(f"    Avg:    {sum(latencies)/len(latencies):.0f}ms")
            print(f"    Max:    {max(latencies):.0f}ms")
            print(f"    P95:    {sorted(latencies)[int(len(latencies)*0.95)]:.0f}ms")

        # Group by tag
        print(f"\n  By module:")
        tags = {}
        for r in self.results:
            tag = r["tag"]
            if tag not in tags:
                tags[tag] = {"total": 0, "passed": 0}
            tags[tag]["total"] += 1
            if r["success"]:
                tags[tag]["passed"] += 1
        for tag, counts in sorted(tags.items()):
            print(f"    {tag:<25} {counts['passed']}/{counts['total']} passed")

        print(f"\n{'='*70}\n")

        await self.client.aclose()
        return self.get_report()

    def get_report(self) -> dict:
        """Return full report as dict."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r["success"])
        return {
            "timestamp": datetime.now().isoformat(),
            "base_url": self.base_url,
            "total_endpoints": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": f"{(passed/total*100):.1f}%" if total else "0%",
            "endpoints": self.results,
        }


# ──────────────────────────────────────────────────────────────────────────
# CLI entry point
# ──────────────────────────────────────────────────────────────────────────
async def main():
    parser = argparse.ArgumentParser(description="Unknown Verdict v41.0 Health Check")
    parser.add_argument(
        "--base",
        default="https://upamnyu12-lex.hf.space",
        help="Base URL (default: https://upamnyu12-lex.hf.space)",
    )
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    parser.add_argument("--timeout", type=float, default=30.0, help="Per-request timeout (seconds)")
    parser.add_argument("--failures-only", action="store_true", help="Only show failed endpoints")
    parser.add_argument("--output", "-o", help="Save report to file")
    args = parser.parse_args()

    checker = HealthChecker(base_url=args.base, timeout=args.timeout)
    report = await checker.run_all()

    if not report:
        sys.exit(1)

    if args.json:
        if args.failures_only:
            report["endpoints"] = [e for e in report["endpoints"] if not e["success"]]
        print(json.dumps(report, indent=2, default=str))
    elif args.failures_only:
        print("\nFAILED ENDPOINTS:")
        for r in report["endpoints"]:
            if not r["success"]:
                print(f"  {r['method']:<6} {r['path']:<45} → {r['status_code']} ({r['error']})")

    if args.output:
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\n📄 Report saved to {args.output}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
