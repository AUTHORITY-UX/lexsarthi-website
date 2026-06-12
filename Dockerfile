FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Debug: verify uvicorn is installed
RUN python -c "import uvicorn; print('uvicorn version:', uvicorn.__version__)"

COPY . .

EXPOSE 7860

CMD ["python", "run.py"]
