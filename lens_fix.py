"""
Lens Endpoint Fix - fixes the /api/lens/agents 400 Bad Request.

ROOT CAUSE (found in your routes.py at line 1123):

    @router.post("/lens/agents", tags=["8-Additional Core"])
    async def lens_agents(request: dict):
        url = request.get("url", "")
        if not url:
            raise HTTPException(status_code=400, detail="url is required")

The endpoint is named "lens/agents" but it's actually a website compliance
scanner (same as /api/compliance/scan). Callers POSTing to it expect
agent-matching (the name says "agents"), but the handler requires a "url"
field. When callers POST {} or {"query": "..."} without a url, they get 400.

This file provides TWO things:
1. A drop-in replacement for the lens_agents route that handles BOTH
   use cases: agent search (when query provided) and compliance scan
   (when url provided).
2. A diagnostic script to verify the fix.

HOW TO APPLY:
Option A - Replace the route in routes.py:
  Find the lens_agents function (line ~1123) and replace it with the
  version below.

Option B - Mount as a moat override (no routes.py edit needed):
  The moat router doesn't override /api/lens/agents (it's under /api/moat).
  So you need to either edit routes.py OR add a new route in app.py.
"""

# ============================================================
# REPLACEMENT ROUTE - paste this into routes.py replacing the
# existing lens_agents function (line ~1123-1150)
# ============================================================

LENS_AGENTS_REPLACEMENT = '''
@router.post("/lens/agents", tags=["8-Additional Core"])
async def lens_agents(request: dict):
    """Lens scanning agents - agent matching OR website compliance scan.

    If 'query' is provided: finds agents matching the query (vector search).
    If 'url' is provided: runs website compliance scan (original behavior).
    If neither: returns all available agents.
    """
    query = request.get("query", "")
    url = request.get("url", "")
    top_k = request.get("top_k", request.get("limit", 5))

    # --- Mode 1: Agent search (query provided) ---
    if query and not url:
        try:
            import asyncpg
            import os
            db_url = os.environ.get("DATABASE_URL", "")
            if db_url.startswith("postgresql+asyncpg://"):
                db_url = db_url.replace("postgresql+asyncpg://", "postgresql://", 1)

            if db_url and "localhost" not in db_url:
                conn = await asyncpg.connect(db_url)

                # Try vector search if embeddings exist
                try:
                    from sentence_transformers import SentenceTransformer
                    model = SentenceTransformer("all-MiniLM-L6-v2")
                    query_vec = model.encode(query[:8000]).tolist()
                    vec_str = "[" + ",".join(str(v) for v in query_vec) + "]"

                    rows = await conn.fetch(
                        "SELECT id, name, domain, category, jurisdiction, "
                        "experience_level, persona_prompt, "
                        "1 - (embedding <=> $1::vector) AS similarity "
                        "FROM agents WHERE embedding IS NOT NULL "
                        "ORDER BY embedding <=> $1::vector LIMIT $2",
                        vec_str, top_k
                    )
                    await conn.close()
                    return {
                        "agents": [{
                            "id": r["id"], "name": r["name"],
                            "domain": r["domain"], "category": r["category"],
                            "jurisdiction": r["jurisdiction"],
                            "experience_level": r["experience_level"],
                            "similarity": round(float(r["similarity"]), 4),
                        } for r in rows],
                        "count": len(rows),
                        "search_type": "vector",
                        "query": query,
                    }
                except ImportError:
                    # Fallback: text search
                    rows = await conn.fetch(
                        "SELECT id, name, domain, category, jurisdiction, "
                        "experience_level, persona_prompt "
                        "FROM agents WHERE domain ILIKE $1 OR name ILIKE $1 "
                        "OR persona_prompt ILIKE $1 LIMIT $2",
                        "%" + query + "%", top_k
                    )
                    await conn.close()
                    return {
                        "agents": [dict(r) for r in rows],
                        "count": len(rows),
                        "search_type": "text_fallback",
                        "query": query,
                    }
        except Exception as e:
            log.warning(f"lens_agents search error: {e}")

        # Final fallback: return all agents from registry
        all_agents = agent_registry.get_all()
        return {
            "agents": [{
                "agent_id": a.agent_id, "name": a.name,
                "specialization": a.specialization,
                "sub_specialty": a.sub_specialty,
                "tier": a.tier.value,
                "status": a.status.value if hasattr(a.status, 'value') else str(a.status),
            } for a in all_agents[:top_k]],
            "count": min(len(all_agents), top_k),
            "search_type": "registry_fallback",
            "query": query,
        }

    # --- Mode 2: Website compliance scan (url provided) ---
    if not url:
        # Neither query nor url - return help message instead of 400
        return {
            "error": "Provide 'query' for agent search or 'url' for compliance scan",
            "usage": {
                "agent_search": {"query": "property dispute", "top_k": 5},
                "compliance_scan": {"url": "https://example.com"},
            },
            "available_agents": len(agent_registry.get_all()),
        }

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    page_content = ""
    fetch_status = "not_fetched"
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                page_content = resp.text.lower()
                fetch_status = "fetched"
            else:
                fetch_status = f"http_{resp.status_code}"
    except Exception:
        fetch_status = "fetch_failed"

    checks = {
        "GDPR": _check_fw(page_content, ["privacy", "consent", "gdpr", "data subject"], fetch_status),
        "DPDPA": _check_fw(page_content, ["consent", "data principal", "dpdp", "privacy"], fetch_status),
        "CCPA": _check_fw(page_content, ["do not sell", "opt-out", "ccpa", "california"], fetch_status),
        "HIPAA": _check_fw(page_content, ["hipaa", "phi", "health information", "breach"], fetch_status),
    }
    issues = []
    if "privacy" not in page_content:
        issues.append({"severity": "high", "framework": "All", "issue": "No privacy policy detected"})
    if "cookie" not in page_content:
        issues.append({"severity": "medium", "framework": "GDPR", "issue": "No cookie consent mechanism"})
    if "consent" not in page_content:
        issues.append({"severity": "high", "framework": "DPDPA", "issue": "No consent mechanism"})

    overall = round(sum(checks.values()) / len(checks), 2)
    return {
        "url": url, "fetch_status": fetch_status,
        "compliance_scores": checks, "overall_score": overall,
        "issues_found": issues,
        "recommendations": [
            "Implement comprehensive privacy policy",
            "Add cookie consent banner",
            "Include data subject rights information",
            "Ensure HTTPS encryption",
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
'''


# ============================================================
# DIAGNOSTIC SCRIPT
# ============================================================

async def diagnose():
    """Diagnose the lens endpoint issue."""
    import os

    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url or "localhost" in db_url:
        print("DIAGNOSIS (without DB connection):")
        print("=" * 60)
        print()
        print("ROOT CAUSE:")
        print("  The /api/lens/agents endpoint in routes.py (line ~1123)")
        print("  requires a 'url' field in the POST body:")
        print()
        print("    async def lens_agents(request: dict):")
        print("        url = request.get('url', '')")
        print("        if not url:")
        print("            raise HTTPException(status_code=400, detail='url is required')")
        print()
        print("  Callers posting {} or {'query': '...'} get 400 because")
        print("  there's no 'url' field. The endpoint name 'lens/agents'")
        print("  implies agent search, but the handler does compliance scanning.")
        print()
        print("FIX:")
        print("  Replace the lens_agents function in routes.py with the")
        print("  version in LENS_AGENTS_REPLACEMENT (above).")
        print("  The new version:")
        print("    - If 'query' provided: does agent vector search")
        print("    - If 'url' provided: does compliance scan (original)")
        print("    - If neither: returns help + agent count (not 400)")
        print()
        print("QUICK PATCH (add to app.py after install_moat):")
        print("  This doesn't fix the route, but adds a working agent search:")
        print("  POST /api/moat/evolution/recall with {'query': '...', 'top_k': 5}")
        return

    import asyncpg
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    print("Connecting to Neon to check agents table...")
    conn = await asyncpg.connect(db_url)

    # Check agents table
    cols = await conn.fetch(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_name = 'agents' ORDER BY ordinal_position"
    )
    print(f"\nAgents table has {len(cols)} columns:")
    for c in cols:
        print(f"  - {c['column_name']}: {c['data_type']}")

    # Check embeddings
    total_agents = await conn.fetchval("SELECT COUNT(*) FROM agents")
    agents_with_emb = await conn.fetchval("SELECT COUNT(*) FROM agents WHERE embedding IS NOT NULL")
    null_emb = total_agents - agents_with_emb
    print(f"\nAgents: {total_agents} total, {agents_with_emb} with embeddings, {null_emb} NULL")

    if null_emb > 0:
        print(f"\nWARNING: {null_emb} agents have NULL embeddings!")
        print("  Vector search will skip these. Run lens_fix.py --fill-embeddings to fix.")

    await conn.close()

    print("\n" + "=" * 60)
    print("FIX: Replace lens_agents in routes.py with LENS_AGENTS_REPLACEMENT")
    print("=" * 60)


async def fill_embeddings():
    """Generate embeddings for agents with NULL values."""
    import os
    import asyncpg

    db_url = os.environ.get("DATABASE_URL", "")
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    print("Loading embedding model...")
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        print("  Model loaded")
    except ImportError:
        print("  sentence-transformers not installed. Run: pip install sentence-transformers")
        return

    conn = await asyncpg.connect(db_url)
    agents = await conn.fetch(
        "SELECT id, name, domain, category, persona_prompt FROM agents WHERE embedding IS NULL"
    )
    print(f"Found {len(agents)} agents with NULL embeddings")

    updated = 0
    for agent in agents:
        text = " ".join(filter(None, [
            agent["name"], agent.get("domain", ""),
            agent.get("category", ""), agent.get("persona_prompt", "")
        ]))
        vec = model.encode(text[:8000]).tolist()
        vec_str = "[" + ",".join(str(v) for v in vec) + "]"
        await conn.execute(
            "UPDATE agents SET embedding = $1::vector WHERE id = $2",
            vec_str, agent["id"]
        )
        updated += 1
        if updated % 25 == 0:
            print(f"  Updated {updated}/{len(agents)}...")

    await conn.close()
    print(f"\nGenerated embeddings for {updated} agents")


if __name__ == "__main__":
    import argparse
    import asyncio
    import sys

    parser = argparse.ArgumentParser(description="Fix /api/lens/agents 400 error")
    parser.add_argument("--fill-embeddings", action="store_true",
                        help="Generate embeddings for agents with NULL values")
    args = parser.parse_args()

    if args.fill_embeddings:
        asyncio.run(fill_embeddings())
    else:
        asyncio.run(diagnose())
