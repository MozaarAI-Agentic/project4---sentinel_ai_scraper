# Recovery Engine
#
# Contrairement aux deux autres services, le CMD ici lance `python -m
# recovery_engine.main`, PAS uvicorn directement - ce service fait tourner
# à la fois un serveur HTTP sidecar (health/metrics) ET la boucle de
# consommation de la queue Redis dans le même processus asyncio (voir
# main.py). Lancer uvicorn seul ferait tourner le sidecar sans jamais
# traiter la queue - un piège facile à ne pas voir si on copie-colle le
# Dockerfile d'un autre service sans réfléchir à sa vraie responsabilité.

FROM python:3.12-slim AS builder

WORKDIR /build

COPY services/recovery-engine/requirements.txt /build/requirements.txt
RUN pip install --no-cache-dir --user -r requirements.txt

COPY libs/sentinel_shared /build/libs/sentinel_shared
RUN pip install --no-cache-dir --user /build/libs/sentinel_shared


FROM python:3.12-slim AS runtime

RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --create-home appuser

WORKDIR /app

COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local
COPY --chown=appuser:appuser services/recovery-engine/src /app/src

ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]

CMD ["python", "-m", "recovery_engine.main"]
