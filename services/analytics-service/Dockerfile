FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY services/analytics-service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/shared ./services/shared
COPY services/analytics-service ./services/analytics-service

WORKDIR /app/services/analytics-service

RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8003

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003", "--workers", "1"]