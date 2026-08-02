!/usr/bin/env python3
"""
Flywheel Bootstrap — processes your existing deliberations table.

Reads all rows from your `deliberations` table, extracts learnings from
each interaction, generates 384-dim embeddings, and seeds them into
moat_learnings + your agent_memories table.

This gives the moat immediate historical context from day one.

Usage:
    python flywheel_bootstrap.py [--limit 1000] [--dry-run] [--check]

Requires DATABASE_URL environment variable (or .env file).
