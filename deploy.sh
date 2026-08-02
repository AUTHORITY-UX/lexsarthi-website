#!/bin/bash
# ============================================================
# Moat v41.0 — One-shot deployment script
# Run this in your HF Space repo root (where app.py lives)
# ============================================================
set -e

echo "🔱 Moat v41.0 — Starting deployment..."
echo "============================================================"

# --- Step 1: Copy moat/ package into unknown_verdict/ ---
echo ""
echo "📂 STEP 1: Copying moat/ into unknown_verdict/..."
if [ ! -d "unknown_verdict/moat" ]; then
    cp -r moat unknown_verdict/moat
    echo "  ✅ moat/ copied into unknown_verdict/moat/"
else
    echo "  ⚠️  unknown_verdict/moat already exists — updating files..."
    cp -rf moat/* unknown_verdict/moat/ 2>/dev/null || true
    echo "  ✅ moat/ updated"
fi

# --- Step 2: Copy integration.py into the moat package ---
echo ""
echo "🔌 STEP 2: Copying integration.py..."
if [ -f "moat/integration.py" ]; then
    cp -f moat/integration.py unknown_verdict/moat/integration.py
    echo "  ✅ integration.py copied"
elif [ -f "integration.py" ]; then
    cp -f integration.py unknown_verdict/moat/integration.py
    echo "  ✅ integration.py copied"
fi

# --- Step 3: Update requirements.txt ---
echo ""
echo "📦 STEP 3: Updating requirements.txt..."
if [ -f "requirements.txt" ]; then
    if ! grep -q "asyncpg" requirements.txt; then
        echo "asyncpg>=0.29.0" >> requirements.txt
        echo "  ✅ Added asyncpg>=0.29.0"
    else
        echo "  ⚠️  asyncpg already present"
    fi
    if ! grep -q "sentence-transformers" requirements.txt; then
        echo "sentence-transformers>=2.2.0" >> requirements.txt
        echo "  ✅ Added sentence-transformers>=2.2.0"
    else
        echo "  ⚠️  sentence-transformers already present"
    fi
else
    echo "asyncpg>=0.29.0" > requirements.txt
    echo "sentence-transformers>=2.2.0" >> requirements.txt
    echo "fastapi>=0.115.0" >> requirements.txt
    echo "uvicorn[standard]" >> requirements.txt
    echo "loguru" >> requirements.txt
    echo "pydantic-settings" >> requirements.txt
    echo "httpx" >> requirements.txt
    echo "  ✅ Created requirements.txt"
fi

# --- Step 4: Patch app.py ---
echo ""
echo "🔧 STEP 4: Patching app.py..."
python3 - <<'PATCH'
import re

with open("unknown_verdict/app.py", "r") as f:
    content = f.read()

if "install_moat" in content:
    print("  ⚠️  install_moat already present — skipping patch")
else:
    patch = (
        '\n# ===== Moat v41.0 — Self-Evolving Intelligence Layer =====\n'
        'from unknown_verdict.moat import install_moat\n'
        'install_moat(app)\n'
        '\n'
        '# ===== Evolution Loop: capture /api/chat interactions automatically =====\n'
        'from unknown_verdict.moat.integration import EvolutionMiddleware\n'
        'app.add_middleware(EvolutionMiddleware)\n'
    )
    # Insert after the router include line
    pattern = r'(app\.include_router\(router,\s*prefix="/api"\))'
    if re.search(pattern, content):
        content = re.sub(pattern, r'\1' + patch, content, count=1)
        with open("unknown_verdict/app.py", "w") as f:
            f.write(content)
        print("  ✅ Patched app.py: install_moat + EvolutionMiddleware")
    else:
        print("  ❌ Could not find 'app.include_router(router, prefix=\"/api\")'")
        print("     MANUAL PATCH: Add these lines after your router include:")
        print("     from unknown_verdict.moat import install_moat")
        print("     install_moat(app)")
        print("     from unknown_verdict.moat.integration import EvolutionMiddleware")
        print("     app.add_middleware(EvolutionMiddleware)")
PATCH

# --- Step 5: Remind about migration ---
echo ""
echo "📝 STEP 5: Neon Migration"
echo "   If you haven't already, run migration.sql in your Neon SQL Editor:"
echo "   https://console.neon.tech → SQL Editor → paste migration.sql → Run"
echo "   This creates 12 moat_* tables. Your existing tables are untouched."

# --- Step 6: Deploy ---
echo ""
echo "🚀 STEP 6: Deploy to HF Spaces"
echo "   Run these commands:"
echo ""
echo "   git add -A"
echo "   git commit -m 'feat: Moat v41.0 — self-evolving intelligence + evolution loop'"
echo "   git push"
echo ""
echo "   Your space rebuilds automatically."
echo "   Check: https://upamnyu12-lex.hf.space/docs for /api/moat/* endpoints"
echo "   Dashboard: Copy moat_dashboard.html into static/ and visit /static/moat_dashboard.html"
echo ""
echo "============================================================"
echo "🔱 AFTER DEPLOY — Run the flywheel bootstrap:"
echo ""
echo "   cd /path/to/your/repo"
echo "   export DATABASE_URL='your-neon-connection-string'"
echo "   python flywheel_bootstrap.py --dry-run     # test first"
echo "   python flywheel_bootstrap.py               # seed historical data"
echo ""
echo "🔧 FIX LENS ENDPOINT:"
echo "   Replace lens_agents in routes.py with the version from lens_fix.py"
echo "   OR run: python lens_fix.py --fill-embeddings  (if agents have NULL embeddings)"
echo "============================================================"
