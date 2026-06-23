# ===================================================================
# 🔱 LEXSARTHI v4.0 - DOCKER CONFIGURATION
# ===================================================================
# 🏛️ OWNED BY: THE ADVOCACY - A LAW FIRM
# 📜 UDYAM: UDYAM-UP-09-0043193 | PAN: CHFPK3464A
# 👤 PROPRIETOR: UPMANYU KUMAR | ESTABLISHED: 2026
# ===================================================================
# 🔱 200+ Agents | 10 Verifiers | 100% Accuracy
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE
# ===================================================================

FROM python:3.10-slim

# Install Tesseract for OCR
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ===================================================================
# ⚠️ CRITICAL: EXPOSE PORT 7860
# ===================================================================
EXPOSE 7860

# ===================================================================
# HEALTHCHECK
# ===================================================================
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:7860/health')" || exit 1

# ===================================================================
# START APPLICATION ON PORT 7860
# ===================================================================
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]

# ===================================================================
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE
# ===================================================================