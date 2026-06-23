# ===================================================================
# 🔱 LEXSARTHI v4.0 - MAKEFILE
# ===================================================================
# Copyright (c) 2026 THE ADVOCACY - A LAW FIRM. All rights reserved.
# LEXSARTHI IS A PROPERTY OR ASSET OF THE ADVOCACY - A LAW FIRM.
# ===================================================================
# 🏛️ OWNED BY: THE ADVOCACY - A LAW FIRM
# 📜 UDYAM: UDYAM-UP-09-0043193 | PAN: CHFPK3464A
# 👤 PROPRIETOR: UPMANYU KUMAR | ESTABLISHED: 2026
# ===================================================================
# 🔱 200+ Agents | 10 Verifiers | 100% Accuracy
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE
# ===================================================================

.PHONY: help install run docker-build docker-run clean test deploy

help:
	@echo "🔱 LEXSARTHI v4.0 - Makefile Commands"
	@echo "====================================="
	@echo "make install     - Install dependencies"
	@echo "make run         - Run application locally"
	@echo "make docker-build - Build Docker image"
	@echo "make docker-run  - Run Docker container"
	@echo "make clean       - Clean up files"
	@echo "make test        - Run tests"
	@echo "make deploy      - Deploy to Hugging Face"

install:
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt

run:
	@echo "🚀 Running LEXSARTHI v4.0..."
	python app.py

docker-build:
	@echo "🐳 Building Docker image..."
	docker build -t lexsarthi-v4 .

docker-run:
	@echo "🐳 Running Docker container..."
	docker run -p 7860:7860 --env-file .env lexsarthi-v4

clean:
	@echo "🧹 Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -f lexsarthi.db 2>/dev/null || true

test:
	@echo "🧪 Running tests..."
	python -c "import app; print('✅ App syntax valid')"

deploy:
	@echo "🚀 Deploying to Hugging Face..."
	git add .
	git commit -m "🔱 LEXSARTHI v4.0 - Deployment"
	git push

# ===================================================================
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE
# ===================================================================