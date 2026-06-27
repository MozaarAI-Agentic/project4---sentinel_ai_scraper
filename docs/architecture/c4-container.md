# C4 — Diagramme de Conteneurs

Vue détaillée des 3 microservices réellement implémentés, leur base de
données partagée (ADR-0006), et le mécanisme de file Redis (ADR-0004).

```mermaid
C4Container
    title SentinelAI Scraper — Diagramme de Conteneurs

    Person(client, "Client de l'API")

    System_Boundary(sentinel, "SentinelAI Scraper") {
        Container(gateway, "API Gateway", "FastAPI", "Orchestre le chemin sync/async (ADR-0003), expose /api/v1/jobs")
        Container(worker, "Extraction Worker", "FastAPI + Playwright", "Pipeline déterministe ; expose /internal/extract, /internal/screenshot, /internal/selectors")
        Container(recovery, "Recovery Engine", "LangGraph + FastAPI (sidecar)", "Consomme la queue Redis, orchestre la recovery IA (mockée, Claude réel en fin de build)")

        ContainerDb(postgres, "PostgreSQL", "SQLAlchemy async", "Table jobs (ADR-0006, propriété API Gateway) + table selectors (propriété Worker)")
        ContainerDb(redis, "Redis", "redis-py async", "Cache de sélecteurs (ADR-0007) + file de recovery (ADR-0004)")
    }

    System_Ext(target_sites, "Sites web cibles")
    System_Ext(claude_api, "Claude API")
    System_Ext(prometheus, "Prometheus")

    Rel(client, gateway, "POST /api/v1/jobs, GET /api/v1/jobs/{id}", "HTTPS/JSON")
    Rel(gateway, worker, "POST /internal/extract", "HTTP interne, synchrone")
    Rel(gateway, postgres, "Lit/écrit la table jobs", "asyncpg")
    Rel(gateway, redis, "Enfile un recovery si échec réparable", "LPUSH")

    Rel(worker, target_sites, "Navigue et extrait", "Playwright/Chromium")
    Rel(worker, postgres, "Lit/écrit la table selectors", "asyncpg")
    Rel(worker, redis, "Cache-aside sur les sélecteurs actifs", "GET/SET")

    Rel(recovery, redis, "BRPOP le job_id à traiter", "Redis")
    Rel(recovery, postgres, "Lit/met à jour la table jobs (sans en posséder les migrations)", "asyncpg")
    Rel(recovery, worker, "POST /internal/screenshot, /internal/extract (override), /internal/selectors", "HTTP interne")
    Rel(recovery, claude_api, "Analyse visuelle (mockée pendant le build)", "HTTPS")

    Rel(prometheus, gateway, "GET /metrics")
    Rel(prometheus, worker, "GET /metrics")
    Rel(prometheus, recovery, "GET /metrics")
```

## Ce que ce diagramme révèle, en comparaison de l'esquisse théorique de la Phase 3

- **Le Recovery Engine ne touche jamais directement les sites cibles ni PostgreSQL en écriture sur `selectors`** — il passe systématiquement par le Worker, respectant strictement l'ADR-0002.
- **`recovery` a une frontière `FastAPI (sidecar)`** — pas pour du trafic métier, uniquement `/health` et `/metrics` (voir Phase 10), pendant que la vraie logique tourne dans une boucle de consommation en arrière-plan. C'est un détail d'implémentation qui aurait été facile à survoler, mais qui change concrètement comment ce service doit être déployé (Phase 12).
- **Trois flèches distinctes du Recovery Engine vers le Worker** — reflet exact des trois endpoints réellement construits au Cycle 13-15 (`/internal/screenshot`, `/internal/extract` avec override, `/internal/selectors`), pas un unique appel générique imaginé.
