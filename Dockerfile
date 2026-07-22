# ===================================================================
# 🔱 LEXSARTHI v4.0 / UNKNOWN VERDICT v12.1
# ===================================================================
# Copyright (c) 2026 THE ADVOCACY - A LAW FIRM. All rights reserved.
# LEXSARTHI IS A PROPERTY OR ASSET OF THE ADVOCACY - A LAW FIRM.
# ===================================================================
# 🏛️ OWNED BY: THE ADVOCACY - A LAW FIRM
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE
# ===================================================================

FROM python:3.11-slim

# ─── METADATA ──────────────────────────────────────────────────────────
LABEL maintainer="THE ADVOCACY - A LAW FIRM"
LABEL version="12.1"
LABEL description="Unknown Verdict / Lexsarthi - Enterprise AI Governance & Legal Intelligence"
LABEL asset="TRIDENT-PERMANENT"
LABEL owner="THE ADVOCACY"

# ─── ENVIRONMENT ──────────────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=7860

# ─── WORK DIRECTORY ──────────────────────────────────────────────────
WORKDIR /app

# ─── SYSTEM DEPENDENCIES ─────────────────────────────────────────────
# FIXED: libgl1-mesa-glx → libgl1 (Debian Trixie compatibility)
# Added all required libraries for PDF, OCR, and image processing
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# ─── COPY REQUIREMENTS FIRST (for caching) ──────────────────────────
COPY requirements.txt .

# ─── INSTALL PYTHON DEPENDENCIES ────────────────────────────────────
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ─── COPY APPLICATION CODE ──────────────────────────────────────────
COPY . .

# ─── CREATE NECESSARY DIRECTORIES ──────────────────────────────────
RUN mkdir -p static uploads temp blog data logs training_data && \
    chmod -R 755 static uploads temp blog data logs training_data

# ─── EXPOSE PORT ────────────────────────────────────────────────────
EXPOSE 7860

# ─── HEALTH CHECK ──────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

# ─── START APPLICATION ──────────────────────────────────────────────
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]

# ===================================================================
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE
# ===================================================================