# Copyright (c) 2026 THE ADVOCACY A LAW FIRM. All rights reserved.
# Confidential and proprietary. Do not distribute without a license.
# THE ADVOCACY A LAW FIRM is the sole owner and title holder of this software.

FROM python:3.11-slim

WORKDIR /app

# Remove any old, conflicting 'docx' package before installing dependencies
RUN pip uninstall docx -y || true

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Verify critical packages
RUN python -c "import uvicorn; print('uvicorn version:', uvicorn.__version__)" && \
    python -c "import docx; print('python-docx version:', docx.__version__)" && \
    python -c "import pdfplumber; print('pdfplumber version:', pdfplumber.__version__)"

COPY . .

EXPOSE 7860

CMD ["python", "run.py"]