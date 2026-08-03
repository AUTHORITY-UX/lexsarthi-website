# ──────────────────────────────────────────────────────────────────────
# Unknown Verdict v41.0 — Hugging Face Spaces Dockerfile
# ──────────────────────────────────────────────────────────────────────
# HF Spaces reads this Dockerfile, builds the image, and runs it.
# The app must listen on port 7860 (HF Spaces requirement).

FROM python:3.12-slim

# Install system dependencies for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY . .

# HF Spaces uses port 7860
ENV PORT=7860
EXPOSE 7860

# Run the app — uvicorn with the app factory
CMD ["python", "-m", "unknown_verdict.app"]
