# Hugging Face Space - simplified single-container demo (see ADR-0017).
# This is NOT the production architecture - see /Dockerfile and
# infra/docker-compose.yml at the repo root for the real one.

FROM python:3.12-slim

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    redis-server curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY libs/sentinel_shared /app/libs/sentinel_shared
COPY services/extraction-worker /app/services/extraction-worker
COPY services/api-gateway /app/services/api-gateway
COPY services/recovery-engine /app/services/recovery-engine
COPY fixtures /app/fixtures
COPY deployment/huggingface-space /app/deployment/huggingface-space

RUN pip install --no-cache-dir -e /app/libs/sentinel_shared \
    && pip install --no-cache-dir -r /app/services/extraction-worker/requirements.txt \
    && pip install --no-cache-dir -r /app/services/api-gateway/requirements.txt \
    && pip install --no-cache-dir -r /app/services/recovery-engine/requirements.txt \
    && pip install --no-cache-dir -r /app/deployment/huggingface-space/requirements.txt \
    && playwright install --with-deps chromium

# Hugging Face Spaces run containers as a non-root user by convention.
# /data (SQLite) and /ms-playwright (Chromium, already installed above
# to this fixed, world-known path) need to be writable by that user -
# same reasoning as services/extraction-worker/Dockerfile.
RUN useradd -m -u 1000 spaceuser \
    && mkdir -p /data \
    && chown -R spaceuser:spaceuser /app /data /ms-playwright \
    && chmod +x /app/deployment/huggingface-space/entrypoint.sh

USER spaceuser

EXPOSE 7860

CMD ["/app/deployment/huggingface-space/entrypoint.sh"]
