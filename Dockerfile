# Copyright (c) 2025 THE ADVOCACY A LAW FIRM. All rights reserved.
# Confidential and proprietary. Do not distribute without a license.
# THE ADVOCACY A LAW FIRM is the sole owner and title holder of this software.

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Verify uvicorn installation
RUN python -c "import uvicorn; print('uvicorn version:', uvicorn.__version__)"

COPY . .

EXPOSE 7860

CMD ["python", "run.py"]