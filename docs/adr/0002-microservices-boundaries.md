# ADR-0002: Frontières de microservices

**Statut:** Accepté
**Contexte du projet:** SentinelAI Scraper

## Contexte

Le système a trois responsabilités clairement distinctes : orchestrer les
requêtes et décider du chemin sync/async (API Gateway), exécuter le
pipeline déterministe (Extraction Worker), et orchestrer la recovery IA
(Recovery Engine). Il faut décider si ces responsabilités vivent dans un
seul service ou plusieurs.

## Décision

Trois microservices indépendamment déployables : `api-gateway`,
`extraction-worker`, `recovery-engine`. Chacun possède son propre
`Dockerfile`, ses propres dépendances, et communique avec les autres
exclusivement via HTTP interne ou une file Redis — jamais par import direct
de code d'un autre service.

**Règle stricte** : `recovery-engine` ne possède jamais Playwright
lui-même ; toute action navigateur passe par un appel HTTP vers
`extraction-worker` (voir la frontière posée avant le Cycle 13).

## Conséquences

### Positives
- Chaque service peut évoluer, scaler et être redéployé indépendamment
- Le Recovery Engine (dépendance Claude/LangGraph) peut échouer ou redémarrer sans affecter le chemin nominal de scraping
- Frontières explicites forcent une réflexion sur chaque contrat inter-service (voir ADR-0006 pour la tension induite sur la base de données)

### Négatives / Dette assumée
- Complexité opérationnelle accrue (3 processus à orchestrer au lieu d'un)
- Latence réseau ajoutée entre services pour des opérations qui seraient in-process dans un monolithe
- Nécessite une discipline stricte pour ne pas recréer un couplage caché (voir ADR-0005 sur le shared kernel)

## Alternatives considérées

| Alternative | Pourquoi rejetée |
|---|---|
| Monolithe modulaire (1 service, modules séparés) | Plus simple à livrer, mais moins démonstratif de compétences distribuées ; le projet vise explicitement à illustrer une architecture microservices |
| Recovery Engine avec son propre Playwright | Duplique la gestion du cycle de vie navigateur entre deux services, rompant la responsabilité unique posée pour l'Extraction Worker |

## Angle recruteur

Démontre la capacité à tracer des frontières de service justifiées par la
responsabilité métier, pas par convention arbitraire — et à tenir cette
frontière même quand elle impose un détour technique (HTTP au lieu d'un
import direct).
