FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV OPENAI_API_BASE=https://api.groq.com/openai/v1
ENV LLM_MODEL_NAME=llama3-70b-8192
ENV EMBED_MODEL_NAME=text-embedding-3-small
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"]
