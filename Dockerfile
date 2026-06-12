FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose the port Hugging Face expects
EXPOSE 7860

# Run uvicorn using python module
CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"]
