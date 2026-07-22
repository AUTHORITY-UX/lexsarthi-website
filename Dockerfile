FROM python:3.11-slim

WORKDIR /app

# ─── SYSTEM DEPENDENCIES (FIXED) ──────────────────────────────────────────
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-eng \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# ─── DIRECTORIES ──────────────────────────────────────────────────────────
RUN mkdir -p static blog legal_docs edge_models deployed_models training_data

# ─── COPY AND INSTALL ──────────────────────────────────────────────────────
COPY requirements.txt .

# Install numpy first (pinned to 1.x for compatibility)
RUN pip install --no-cache-dir numpy==1.24.4

# Install CPU-only torch
RUN pip install --no-cache-dir torch==2.3.0 --index-url https://download.pytorch.org/whl/cpu

# Install opencv-python-headless
RUN pip install --no-cache-dir opencv-python-headless==4.8.1.78

# Install remaining packages
RUN pip install --no-cache-dir -r requirements.txt

# Ensure email-validator is installed
RUN pip install --no-cache-dir email-validator==2.1.0

# ─── COPY APPLICATION ──────────────────────────────────────────────────────
COPY . .

# ─── ENVIRONMENT ──────────────────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV OMP_NUM_THREADS=1
ENV WORKERS=1
ENV OPENCV_IO_ENABLE_OPENEXR=1

# ─── EXPOSE ──────────────────────────────────────────────────────────────
EXPOSE 7860

# ─── HEALTH CHECK ──────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:7860/health')" || exit 1

# ─── RUN ──────────────────────────────────────────────────────────────────
CMD ["python", "app.py"]