"""Définitions de métriques Prometheus partagées entre les microservices.

Chaque processus (Extraction Worker, API Gateway, Recovery Engine) a son
propre registre Prometheus - ces objets ne sont PAS partagés entre
processus. Ce module partage uniquement les définitions (noms, labels,
unités), pour garantir que les trois services parlent le même langage
métrique dans Grafana - sans lui, on risquerait `extraction_duration` ici
et `extract_time_seconds` là, rendant les dashboards inexploitables.

Convention de nommage (norme Prometheus) : <domaine>_<mesure>_<unité>.
"""

from prometheus_client import Counter, Histogram

EXTRACTION_DURATION_SECONDS = Histogram(
    "extraction_duration_seconds",
    "Durée d'une tentative d'extraction déterministe (Extraction Worker)",
    labelnames=["domain", "outcome"],
)

EXTRACTION_RESULT_TOTAL = Counter(
    "extraction_result",
    "Nombre de tentatives d'extraction, par résultat (Extraction Worker)",
    labelnames=["domain", "outcome"],
)

SELECTOR_CACHE_RESULT_TOTAL = Counter(
    "selector_cache_result",
    "Résultat des lectures du cache de sélecteurs, hit ou miss (Extraction Worker)",
    labelnames=["result"],
)

RECOVERY_ATTEMPT_TOTAL = Counter(
    "recovery_attempt",
    "Nombre de tentatives de recovery IA, par résultat (Recovery Engine)",
    labelnames=["outcome"],
)

RECOVERY_DURATION_SECONDS = Histogram(
    "recovery_duration_seconds",
    "Durée totale d'un cycle de recovery, du déclenchement à la résolution "
    "(Recovery Engine)",
)

AI_RECOVERY_COST_USD_TOTAL = Counter(
    "ai_recovery_cost_usd",
    "Coût cumulé estimé des appels de recovery IA, en dollars (Recovery Engine)",
)

JOB_STATUS_TOTAL = Counter(
    "job_status",
    "Nombre de jobs par statut final (API Gateway)",
    labelnames=["status"],
)
