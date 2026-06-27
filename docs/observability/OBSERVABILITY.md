# Observability — SentinelAI Scraper

> Toutes les métriques listées ici sont réellement instrumentées dans le
> code (voir `libs/sentinel_shared/observability/metrics.py`), pas des
> objectifs théoriques. Chaque ligne est vérifiable par un test qui
> incrémente la métrique et lit sa valeur.

## 1. Mapping KPI (Phase 2) → Métrique Prometheus

| KPI (Phase 2 - Product Vision) | Métrique Prometheus | Type | Service |
|---|---|---|---|
| Taux de succès d'extraction | `extraction_result{domain,outcome}` | Counter | Extraction Worker |
| Latence d'extraction | `extraction_duration_seconds{domain,outcome}` | Histogram | Extraction Worker |
| Taux de cache hit | `selector_cache_result{result}` | Counter | Extraction Worker |
| Taux de succès de recovery | `recovery_attempt{outcome}` | Counter | Recovery Engine |
| Latence de recovery | `recovery_duration_seconds` | Histogram | Recovery Engine |
| Coût IA | `ai_recovery_cost_usd` | Counter | Recovery Engine |
| Statut des jobs | `job_status{status}` | Counter | API Gateway |

Toutes les métriques suivent la convention Prometheus `<domaine>_<mesure>_<unité>`
et sont exposées via `GET /metrics` sur chaque service.

## 2. Pourquoi ces métriques précisément ?

**`extraction_result{domain, outcome}`** plutôt qu'un compteur global : le
label `domain` permet de répondre à *"quel site cible génère le plus
d'échecs ?"* - une question opérationnelle réelle, pas juste un chiffre
agrégé sans actionnabilité.

**`selector_cache_result{result="hit"|"miss"}`** : un taux de cache hit qui
chute progressivement est un signal d'alerte précoce - ça veut dire que des
sites changent leur structure plus vite que le cache ne se réchauffe,
annonçant une hausse prochaine du coût IA avant même qu'elle ne se
matérialise.

**`ai_recovery_cost_usd`** : c'est LA métrique qui prouve que l'architecture
"deterministic-first" fonctionne. Si ce compteur croît plus vite que
`extraction_result_total`, c'est un signal que le système s'appuie de plus
en plus sur l'IA - contraire à la promesse du produit (Phase 1).

## 3. Structure du dashboard Grafana (à construire en Phase 12)

```
┌─────────────────────────────┬─────────────────────────────┐
│ Taux de succès extraction    │ Taux de succès recovery      │
│ (extraction_result / total)  │ (recovery_attempt / total)   │
├─────────────────────────────┼─────────────────────────────┤
│ Latence p50/p95/p99          │ Latence p50/p95/p99          │
│ (extraction_duration_seconds)│ (recovery_duration_seconds)  │
├─────────────────────────────┼─────────────────────────────┤
│ Cache hit rate (%)           │ Coût IA cumulé ($)           │
│ (selector_cache_result)      │ (ai_recovery_cost_usd)       │
├─────────────────────────────┴─────────────────────────────┤
│ Répartition des statuts de jobs (job_status, par statut)    │
└───────────────────────────────────────────────────────────┘
```

## 4. Ce qui n'est PAS encore instrumenté (limites connues)

- **Traces distribuées (OpenTelemetry)** : le `trace_id` ne traverse pas
  encore API Gateway → Worker → Recovery Engine. C'est une lacune
  identifiée dès la Phase 3 (voir ADR correspondant) - la propagation de
  contexte à travers la queue Redis asynchrone est plus complexe qu'un
  simple header HTTP propagé de service à service, et mérite un cycle dédié.
- **Alerting Prometheus** (règles `alertmanager`) : les seuils d'alerte
  (ex: "coût IA > $50/jour") ne sont pas encore définis - dépend de données
  de production réelles pour calibrer des seuils pertinents plutôt
  qu'arbitraires.
- **Browser failures** (KPI Phase 2) : pas encore de métrique dédiée aux
  échecs Playwright eux-mêmes (timeout, crash navigateur) distincte d'un
  échec de validation métier - actuellement les deux remontent comme
  `extraction_result{outcome="failure"}` sans distinction.

## 5. Endpoints `/metrics` par service

| Service | Endpoint | Contenu |
|---|---|---|
| Extraction Worker | `GET /metrics` | extraction_result, extraction_duration_seconds, selector_cache_result |
| API Gateway | `GET /metrics` | job_status |
| Recovery Engine | `GET /metrics` | recovery_attempt, recovery_duration_seconds, ai_recovery_cost_usd |
