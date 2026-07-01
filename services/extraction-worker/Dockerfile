# Extraction Worker
#
# Étape unique (pas de multi-stage) : c'est un choix assumé, pas un oubli.
# Playwright installe des dépendances système (libnss3, libatk, etc.) via
# `playwright install --with-deps`, qui ne se copient pas proprement d'une
# étape à l'autre dans un build multi-stage sans un travail méticuleux non
# vérifiable ici (pas de daemon Docker dans cet environnement de build).
# Optimisation multi-stage identifiée en ROADMAP.md, à valider contre un
# vrai daemon Docker avant d'être appliquée.

FROM python:3.12-slim

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# Dépendances d'abord : le cache de layer Docker n'invalide cette étape
# (la plus lente, à cause du téléchargement de Chromium) que si
# requirements.txt change - pas à chaque modification du code source.
COPY services/extraction-worker/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install --with-deps chromium

COPY libs/sentinel_shared /app/libs/sentinel_shared
RUN pip install --no-cache-dir /app/libs/sentinel_shared

COPY services/extraction-worker/src /app/src

RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --create-home appuser \
    && chown -R appuser:appuser /app /ms-playwright

USER appuser

EXPOSE 8000

# Pas de dépendance supplémentaire (httpx) juste pour le healthcheck -
# urllib est dans la stdlib, cohérent avec le choix de ne jamais lister de
# dépendance de production inutilisée par le code applicatif.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/metrics')"]

CMD ["uvicorn", "extraction_worker.interfaces.http.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
