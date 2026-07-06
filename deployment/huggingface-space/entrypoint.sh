#!/bin/bash
# Hugging Face Space entrypoint - starts all services as background
# processes in a single container, then launches Gradio in the
# foreground. This is a deliberate simplification of the real
# docker-compose architecture - see ADR-0017.
set -e

SHARED_PYTHONPATH="/app/libs/sentinel_shared/src"
DB_PATH="sqlite+aiosqlite:////data/sentinel.db"
REDIS_URL="redis://localhost:6379/0"

echo "[entrypoint] Starting Redis..."
redis-server --daemonize yes

echo "[entrypoint] Starting Extraction Worker..."
cd /app/services/extraction-worker
DATABASE_URL="$DB_PATH" REDIS_URL="$REDIS_URL" \
  PYTHONPATH="src:$SHARED_PYTHONPATH" \
  uvicorn extraction_worker.interfaces.http.app:create_app --factory --host 0.0.0.0 --port 8001 &

echo "[entrypoint] Waiting for Extraction Worker to be ready..."
for i in $(seq 1 15); do
  curl -sf http://localhost:8001/metrics > /dev/null 2>&1 && break
  sleep 1
done

echo "[entrypoint] Seeding guided demo selector (title known, price unknown)..."
cd /app/deployment/huggingface-space
DATABASE_URL="$DB_PATH" REDIS_URL="$REDIS_URL" \
  PYTHONPATH="/app/services/extraction-worker/src:$SHARED_PYTHONPATH" \
  python seed_demo_data.py

echo "[entrypoint] Starting API Gateway..."
cd /app/services/api-gateway
DATABASE_URL="$DB_PATH" REDIS_URL="$REDIS_URL" \
  EXTRACTION_WORKER_BASE_URL="http://localhost:8001" \
  PYTHONPATH="src:$SHARED_PYTHONPATH" \
  uvicorn api_gateway.interfaces.http.app:create_app --factory --host 0.0.0.0 --port 8000 &

echo "[entrypoint] Starting Recovery Engine consumer (demo engine unless ANTHROPIC_API_KEY is set)..."
cd /app/deployment/huggingface-space
DATABASE_URL="$DB_PATH" REDIS_URL="$REDIS_URL" \
  EXTRACTION_WORKER_BASE_URL="http://localhost:8001" \
  ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}" \
  PYTHONPATH="/app/services/recovery-engine/src:$SHARED_PYTHONPATH:/app/deployment/huggingface-space" \
  python recovery_worker_process.py &

echo "[entrypoint] Waiting for API Gateway to be ready..."
for i in $(seq 1 15); do
  curl -sf http://localhost:8000/metrics > /dev/null 2>&1 && break
  sleep 1
done

echo "[entrypoint] Launching Gradio UI on port 7860..."
cd /app/deployment/huggingface-space
exec python app.py
