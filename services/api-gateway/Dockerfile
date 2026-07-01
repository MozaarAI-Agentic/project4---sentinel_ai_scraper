# API Gateway
#
# Multi-stage build : aucune dépendance système lourde (contrairement à
# l'Extraction Worker) - le résultat de `pip install --user` se copie
# proprement d'une étape à l'autre, donc l'optimisation de taille d'image
# est directement applicable ici, sans les mêmes réserves.

FROM python:3.12-slim AS builder

WORKDIR /build

COPY services/api-gateway/requirements.txt /build/requirements.txt
RUN pip install --no-cache-dir --user -r requirements.txt

COPY libs/sentinel_shared /build/libs/sentinel_shared
RUN pip install --no-cache-dir --user /build/libs/sentinel_shared


FROM python:3.12-slim AS runtime

RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --create-home appuser

WORKDIR /app

COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local
COPY --chown=appuser:appuser services/api-gateway/src /app/src

ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/metrics')"]

CMD ["uvicorn", "api_gateway.interfaces.http.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
