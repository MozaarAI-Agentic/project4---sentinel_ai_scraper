# Diagrammes de Séquence

Les deux flux d'exécution réellement implémentés (ADR-0003), avec les noms
d'endpoints et de composants exacts du code — pas une simplification.

## 1. Chemin nominal (synchrone) — extraction réussie du premier coup

```mermaid
sequenceDiagram
    participant C as Client
    participant GW as API Gateway
    participant W as Extraction Worker
    participant PG as PostgreSQL

    C->>GW: POST /api/v1/jobs {url, domain, required_fields}
    GW->>GW: Job.create() → status=PENDING
    GW->>PG: save(job)
    GW->>W: POST /internal/extract {url, domain, required_fields}
    W->>W: ExtractDataUseCase.execute()
    Note over W: Résout les sélecteurs connus (cache-aside, ADR-0007)<br/>Playwright extrait, ExtractionValidator valide
    W-->>GW: 200 {success: true, data, failure_reason: null}
    GW->>GW: job.mark_succeeded(result=data)
    GW->>PG: save(job) → status=SUCCESS
    GW-->>C: 200 {job_id, status: "success", result, recovery_used: false}
```

## 2. Chemin de recovery (asynchrone) — échec réparable par IA

```mermaid
sequenceDiagram
    participant C as Client
    participant GW as API Gateway
    participant W as Extraction Worker
    participant Q as Redis (queue)
    participant R as Recovery Engine
    participant AI as Claude API (mocké)
    participant PG as PostgreSQL

    C->>GW: POST /api/v1/jobs {url, domain, required_fields}
    GW->>W: POST /internal/extract
    W-->>GW: 200 {success: false, failure_reason: "missing_required_field"}
    GW->>GW: RecoveryDecisionPolicy.should_trigger_recovery() → true
    GW->>GW: job.mark_recovery_pending()
    GW->>PG: save(job) → status=RECOVERY_PENDING
    GW->>Q: LPUSH recovery_queue job_id
    GW-->>C: 202 {job_id, status: "recovery_pending", poll_url}

    Note over R: Traitement asynchrone, indépendant de la requête HTTP
    R->>Q: BRPOP recovery_queue
    R->>PG: get(job_id) → url, domain, required_fields
    R->>W: POST /internal/screenshot {url}
    W-->>R: 200 {screenshot_base64}

    loop Jusqu'à max_attempts ou succès (LangGraph, ADR-0011)
        R->>AI: propose_selectors(screenshot, schema, rejection_history)
        AI-->>R: SelectorProposal(is_confident, selectors)
        R->>W: POST /internal/extract {selectors: candidats}
        W-->>R: {success, data, failure_reason}
    end

    alt Validation réussie
        R->>W: POST /internal/selectors {domain, field_name, selector_value, source: "ai_generated"}
        W->>PG: save_selector() → nouvelle version active
        R->>PG: update(job) → status=SUCCESS, result=recovered_data
    else Tentatives épuisées
        R->>PG: update(job) → status=NEEDS_HUMAN_REVIEW
    end

    Note over C: Le client poll GET /api/v1/jobs/{job_id}
    C->>GW: GET /api/v1/jobs/{job_id}
    GW->>PG: get(job_id)
    GW-->>C: 200 {status: "success"|"needs_human_review", result}
```

## Différences avec l'esquisse théorique de la Phase 3

- **Le screenshot transite en base64 dans le JSON** (ADR-0010), pas comme un chemin de fichier — détail qui n'existait pas dans la première esquisse et qui a émergé en construisant réellement le Cycle 13.
- **`/internal/extract` sert deux rôles** : résolution normale des sélecteurs connus (chemin nominal) ET validation de sélecteurs candidats via le paramètre optionnel `selectors` (chemin de recovery) — réutilisation délibérée d'un seul endpoint plutôt que duplication.
- **Le Recovery Engine met à jour `PostgreSQL` directement**, pas via un rappel HTTP vers l'API Gateway — reflet de l'ADR-0006 (base partagée) et du `SqlJobRepository` propre au Recovery Engine.
