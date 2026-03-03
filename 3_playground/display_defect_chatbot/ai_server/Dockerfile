FROM python:3.11-slim

WORKDIR /app

COPY ai_server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ai_server/ ./ai_server/

WORKDIR /app/ai_server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
