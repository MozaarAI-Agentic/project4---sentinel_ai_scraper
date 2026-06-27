# ADR-0005: Monorepo avec Shared Kernel

**Statut:** Accepté
**Contexte du projet:** SentinelAI Scraper

## Contexte

Trois microservices indépendants (ADR-0002) doivent partager certains
contrats (statuts de job, raisons d'échec, règle de validation
d'extraction, entité Job) sans dupliquer cette logique trois fois - une
duplication de règle métier étant la pire forme de duplication (une
correction future risquant de n'être appliquée que d'un côté).

## Décision

Un seul repository Git héberge les trois services **et** un package
partagé `libs/sentinel_shared`, qui contient exclusivement des contrats
(enums `FailureReason`/`JobStatus`, l'entité `Job`, `ExtractionValidator`)
- jamais de logique spécifique à un seul service. Chaque service reste
indépendamment buildable et déployable (son propre `Dockerfile`).

Ce shared kernel n'a pas été créé d'un coup : il a grossi organiquement,
migration après migration, chaque fois qu'une duplication réelle entre
deux services était identifiée (Cycles 4, 13, 16).

## Conséquences

### Positives
- Un seul repository facilite la revue de code cross-service et la découverte pour un lecteur externe (portfolio)
- Élimine la duplication de règles métier réellement partagées
- Chaque migration vers le shared kernel a été sécurisée par la suite de tests existante avant/après (aucune régression sur 3 migrations)

### Négatives / Dette assumée
- Risque de "shared kernel qui grossit mal" si des éléments non réellement partagés y sont ajoutés par facilité - discipline requise pour n'y placer que des contrats, jamais de logique d'un seul service
- Un changement dans le shared kernel nécessite de revalider tous les services qui en dépendent

## Alternatives considérées

| Alternative | Pourquoi rejetée |
|---|---|
| Polyrepo (3 repositories séparés) | Fragmente la visibilité portfolio ; complique la distribution du code partagé (nécessiterait un package PyPI privé, sur-ingénierie pour ce contexte) |
| Duplication du code partagé dans chaque service | Risque réel de dérive silencieuse entre copies, déjà expérimenté avant chaque migration (ex: `FailureReason` dupliqué avant Cycle 4) |

## Angle recruteur

Prouve la compréhension que monorepo et microservices ne sont pas
contradictoires (Google, Meta opèrent ainsi à l'échelle), et la discipline
de ne migrer vers un shared kernel que sur une duplication réelle
constatée, jamais par anticipation spéculative.
