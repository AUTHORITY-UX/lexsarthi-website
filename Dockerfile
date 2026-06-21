# ===================================================================
# LEXSARTHI v4.0 - INDIA'S FIRST AI-NATIVE COMPLETE LEGAL OS
# ===================================================================
# Copyright (c) 2026 THE ADVOCACY A LAW FIRM. All rights reserved.
# Confidential and proprietary. Do not distribute without a license.
# LEXSARTHI IS A PROPERTY OR ASSET OF THE ADVOCACY A LAW FIRM.
# ===================================================================
# "From Contract Review to Supreme Court Judgments"
# "From Law School to Global Legal Practice"
# "One Platform. Every Legal Need. Anywhere in the World."
# ===================================================================
# Powered By THE ADVOCACY A LAW FIRM
# ===================================================================
# ✅ ALL DEPENDENCIES LOADED | WORKING
# ✅ FASTAPI + RAZORPAY + WHOIS + SSL + PDF + ANALYTICS
# ✅ PRODUCTION READY | GLOBAL SCALING
# ===================================================================

FROM python:3.10-slim

WORKDIR /code

# Install system dependencies required for SQLite networking and PDFs
RUN apt-get update && apt-get install -y \
    build-essential \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY . .

# Hugging Face Spaces strictly maps internal routing to port 7860
EXPOSE 7860

# Run uvicorn on host 0.0.0.0 and port 7860
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"]