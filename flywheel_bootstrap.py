#!/usr/bin/env python3
"""
Flywheel Bootstrap — processes your existing deliberations table.

Reads all rows from your `deliberations` table, extracts learnings from
each interaction, generates 384-dim embeddings, and seeds them into
moat_learnings + your agent_memories table.

This gives the moat immediate historical context from day one.

Usage:
    python flywheel_bootstrap.py [--limit 1000] [--dry-run]

Requires DATABASE_URL environment variable (or .env file).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import hashlib
import uuid

# Try to load .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


async def bootstrap(limit: int = 1000, dry_run: bool = False) -> dict:
    """Process deliberations and seed the moat with historical data."""
    import asyncpg

    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url or "localhost" in db_url:
        print("❌ DATABASE_URL not set or points to localhost")
        print("   Set it: export DATABASE_URL='postgresql://user:pass@host/db'")
        return {"error": "no_database_url"}

    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    print("🔗 Connecting to Neon...")
    conn = await asyncpg.connect(db_url)

    # Count available deliberations
    total = await conn.fetchval("SELECT COUNT(*) FROM deliberations")
    print(f"📊 Found {total} deliberations in database")
    print(f"   Processing up to {limit} (dry_run={dry_run})")
    print()

    if total == 0:
        print("⚠️  No deliberations found. The flywheel will start fresh from new interactions.")
        await conn.close()
        return {"total": 0, "processed": 0, "message": "no deliberations to process"}

    # Load embedding model
    print("🧠 Loading embedding model (all-MiniLM-L6-v2, 384-dim)...")
    model = None
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        print("   ✅ Model loaded")
    except ImportError:
        print("   ⚠️  sentence-transformers not installed — using hash fallback")
        print("   Install with: pip install sentence-transformers")

    def embed_text(text: str) -> list:
        if model:
            return model.encode(text[:8000]).tolist()
        return _hash_embed(text)

    # Check moat tables exist
    try:
        await conn.fetchval("SELECT 1 FROM moat_learnings LIMIT 1")
        print("✅ moat_learnings table exists")
    except Exception:
        print("❌ moat_learnings table not found — run migration.sql first!")
        await conn.close()
        return {"error": "migration_not_run"}

    # Process deliberations
    rows = await conn.fetch(
        "SELECT id, query, domain, persona, provider, initial_answer, "
        "final_answer, verifier_results, confidence, sources, timestamp "
        "FROM deliberations ORDER BY timestamp DESC LIMIT $1",
        limit,
    )

    stats = {
        "total_deliberations": total,
        "processed": 0,
        "learnings_stored": 0,
        "agent_memories_stored": 0,
        "reasoning_patterns_stored": 0,
        "errors": 0,
        "skipped": 0,
        "start_time": time.time(),
    }

    print(f"\n⚙️  Processing {len(rows)} deliberations...")
    print("-" * 60)

    for i, row in enumerate(rows):
        try:
            query = row.get("query") or ""
            final_answer = row.get("final_answer") or row.get("initial_answer") or ""
            domain = row.get("domain") or "general"
            persona = row.get("persona") or ""
            confidence_str = row.get("confidence") or "medium"
            verifier_results = row.get("verifier_results")

            # Skip empty
            if not query or len(query.strip()) < 10:
                stats["skipped"] += 1
                continue
            if not final_answer or len(final_answer.strip()) < 20:
                stats["skipped"] += 1
                continue

            # Determine outcome from confidence string
            confidence_val = 0.5
            if isinstance(confidence_str, str):
                cl = confidence_str.lower()
                if "high" in cl:
                    confidence_val = 0.85
                    outcome = "success"
                elif "medium" in cl:
                    confidence_val = 0.65
                    outcome = "neutral"
                elif "low" in cl:
                    confidence_val = 0.3
                    outcome = "failure"
                else:
                    outcome = "neutral"
            elif isinstance(confidence_str, (int, float)):
                confidence_val = float(confidence_str)
                outcome = "success" if confidence_val >= 0.7 else "neutral"

            # Build agent_id from domain
            agent_id = f"bootstrap-{domain.lower().replace(' ', '-')}"

            # Generate embedding
            learning_text = (
                f"Query: {query[:500]}\n"
                f"Response: {final_answer[:1000]}\n"
                f"Outcome: {outcome}\n"
                f"Domain: {domain}"
            )
            embedding = embed_text(learning_text)
            vec_str = f"[{','.join(str(v) for v in embedding)}]"

            if dry_run:
                stats["processed"] += 1
                if (i + 1) % 50 == 0:
                    print(f"   [DRY RUN] Processed {i+1}/{len(rows)}...")
                continue

            # 1. Store in moat_learnings
            lid = uuid.uuid4().hex
            try:
                await conn.execute(
                    "INSERT INTO moat_learnings (id, agent_id, interaction_id, context, "
                    "learning, outcome, confidence_delta, shared_to_mesh, embedding, created_at) "
                    "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::vector, NOW())",
                    lid, agent_id, str(row.get("id", "")),
                    query[:2000], learning_text, outcome,
                    0.02 if outcome == "success" else 0.0,
                    outcome == "success", vec_str,
                )
                stats["learnings_stored"] += 1
            except Exception:
                stats["errors"] += 1

            # 2. Store in agent_memories (your existing table)
            try:
                await conn.execute(
                    "INSERT INTO agent_memories (agent_id, query, response, verdict, embedding) "
                    "VALUES ($1, $2, $3, $4, $5::vector)",
                    1,
                    query[:2000], final_answer[:5000],
                    json.dumps({"outcome": outcome, "confidence": confidence_val,
                                "domain": domain, "source": "bootstrap"}),
                    vec_str,
                )
                stats["agent_memories_stored"] += 1
            except Exception:
                pass  # FK constraint may fail — non-fatal

            # 3. Store reasoning pattern if answer has legal structure
            if any(kw in final_answer.lower()
                   for kw in ["issue", "rule", "application", "conclusion",
                              "therefore", "section", "held", "act"]):
                try:
                    rid = uuid.uuid4().hex
                    rh = hashlib.sha256(final_answer[:500].encode()).hexdigest()[:32]
                    await conn.execute(
                        "INSERT INTO moat_reasoning_patterns "
                        "(id, agent_id, issue, rule, application, conclusion, "
                        "jurisdiction, outcome, confidence, reasoning_hash, "
                        "encrypted, embedding, created_at) "
                        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12::vector, NOW())",
                        rid, agent_id, query[:500], "See deliberation record",
                        final_answer[:2000], "See response", "IN", outcome,
                        confidence_val, rh, False, vec_str,
                    )
                    stats["reasoning_patterns_stored"] += 1
                except Exception:
                    pass

            stats["processed"] += 1

            if (i + 1) % 50 == 0:
                elapsed = time.time() - stats["start_time"]
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                eta = (len(rows) - i - 1) / rate if rate > 0 else 0
                print(f"   [{i+1}/{len(rows)}] "
                      f"Learnings: {stats['learnings_stored']} | "
                      f"Memories: {stats['agent_memories_stored']} | "
                      f"Patterns: {stats['reasoning_patterns_stored']} | "
                      f"Rate: {rate:.1f}/s | ETA: {eta:.0f}s")

        except Exception as e:
            stats["errors"] += 1
            if stats["errors"] <= 5:
                print(f"   ⚠️  Error on row {i}: {e}")

    stats["elapsed_seconds"] = round(time.time() - stats["start_time"], 2)
    await conn.close()

    print("\n" + "=" * 60)
    print("📊 FLYWHEEL BOOTSTRAP COMPLETE")
    print("=" * 60)
    print(f"   Total deliberations found:  {stats['total_deliberations']}")
    print(f"   Processed:                  {stats['processed']}")
    print(f"   Skipped (empty/trivial):    {stats['skipped']}")
    print(f"   moat_learnings stored:      {stats['learnings_stored']}")
    print(f"   agent_memories stored:      {stats['agent_memories_stored']}")
    print(f"   reasoning_patterns stored:  {stats['reasoning_patterns_stored']}")
    print(f"   Errors (non-fatal):         {stats['errors']}")
    print(f"   Elapsed:                    {stats['elapsed_seconds']}s")
    print("=" * 60)

    if not dry_run and stats["learnings_stored"] > 0:
        print("\n🧬 The flywheel is now seeded with historical data.")
        print("   Every new /api/chat interaction will compound on this base.")
        print("   Check /api/moat/status to see the growing knowledge base.")
    elif dry_run:
        print("\n🔍 Dry run complete — no data was written.")
        print("   Run without --dry-run to actually seed the database.")

    return stats


def _hash_embed(text: str, dim: int = 384) -> list:
    import numpy as np
    vec = np.zeros(dim, dtype=np.float32)
    for i in range(0, dim, 8):
        h = hashlib.sha256(f"{text}:{i}".encode()).digest()
        for j in range(min(8, dim - i)):
            vec[i + j] = (h[j] / 255.0 - 0.5) * 2
    norm = np.linalg.norm(vec)
    return (vec / norm).tolist() if norm > 0 else vec.tolist()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bootstrap the Moat flywheel from deliberations")
    parser.add_argument("--limit", type=int, default=1000, help="Max deliberations to process")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually write to DB")
    args = parser.parse_args()
    result = asyncio.run(bootstrap(limit=args.limit, dry_run=args.dry_run))
    sys.exit(0 if "error" not in result else 1)
