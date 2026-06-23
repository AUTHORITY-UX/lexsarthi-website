# ===================================================================
# 🔱 LEXSARTHI v4.0 - DOCKER CONFIGURATION
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

FROM python:3.10-slim

# Firm Label
LABEL firm="THE ADVOCACY - A LAW FIRM"
LABEL udyam="UDYAM-UP-09-0043193"
LABEL pan="CHFPK3464A"
LABEL owner="UPMANYU KUMAR"
LABEL trident="🔱 PERMANENT ASSET - NEVER REMOVE"

# Install Tesseract for OCR
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-hin \
    libtesseract-dev \
    libleptonica-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:7860/health')" || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]

# ===================================================================
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE
# ===================================================================