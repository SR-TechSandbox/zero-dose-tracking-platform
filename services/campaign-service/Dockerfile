FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY services/campaign-service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY data/baseline/rounds.json ./data/baseline/rounds.json
COPY services/shared ./services/shared
COPY services/campaign-service ./services/campaign-service

WORKDIR /app/services/campaign-service

RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8001

CMD ["sh", "-c", "alembic upgrade head && python -m app.seed && exec uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 1"]