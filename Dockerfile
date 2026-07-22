FROM python:3.11-slim

WORKDIR /app

# ─── SYSTEM DEPENDENCIES (NO libgl1-mesa-glx) ──────────────────────────
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
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# ─── DIRECTORIES ──────────────────────────────────────────────────────────
RUN mkdir -p static blog legal_docs edge_models deployed_models training_data

# ─── COPY REQUIREMENTS ──────────────────────────────────────────────────
COPY requirements.txt .

# ─── INSTALL PYTHON PACKAGES ────────────────────────────────────────────
RUN pip install --no-cache-dir numpy==1.24.4
RUN pip install --no-cache-dir torch==2.3.0 --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir email-validator==2.1.0

# ─── COPY APPLICATION ──────────────────────────────────────────────────
COPY . .

# ─── ENVIRONMENT ──────────────────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV OMP_NUM_THREADS=1
ENV WORKERS=1

# ─── EXPOSE ──────────────────────────────────────────────────────────────
EXPOSE 7860

# ─── RUN ──────────────────────────────────────────────────────────────────
CMD ["python", "app.py"]