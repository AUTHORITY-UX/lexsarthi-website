#!/bin/bash
# ===================================================================
# 🔱 LEXSARTHI v4.0 - QUICK SETUP SCRIPT
# ===================================================================
# Copyright (c) 2026 THE ADVOCACY - A LAW FIRM. All rights reserved.
# LEXSARTHI IS A PROPERTY OR ASSET OF THE ADVOCACY - A LAW FIRM.
# ===================================================================
# 🏛️ OWNED BY: THE ADVOCACY - A LAW FIRM
# 📜 UDYAM: UDYAM-UP-09-0043193 | PAN: CHFPK3464A
# 👤 PROPRIETOR: UPMANYU KUMAR | ESTABLISHED: 2026
# ===================================================================
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE
# ===================================================================

echo "🔱 LEXSARTHI v4.0 - QUICK SETUP"
echo "🏛️ THE ADVOCACY - A LAW FIRM"
echo "====================================="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.10+"
    exit 1
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️ .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env with your API keys"
fi

# Create directories
echo "📁 Creating directories..."
mkdir -p uploads
mkdir -p static
mkdir -p logs

# Run tests
echo "🧪 Running tests..."
python test_lexsarthi.py

echo ""
echo "🚀 Setup complete!"
echo ""
echo "Run: python app.py"
echo "Or: uvicorn app:app --host 0.0.0.0 --port 7860 --reload"
echo ""
echo "🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE"

# ===================================================================
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE
# ===================================================================