# ADR-0012: Reproductibilité par seed pour MockRecoveryEngine

**Statut:** Accepté
**Contexte du projet:** SentinelAI Scraper

## Contexte

Claude Computer Use n'est activé qu'en toute fin de développement (voir
Phase 1). Pendant le développement et en CI, il faut simuler son
comportement probabiliste (parfois confiant, parfois non) sans dépendre
d'un vrai appel API - tout en gardant les tests reproductibles et non
flaky.

## Décision

`MockRecoveryEngine` accepte un `seed: int | None` et un `success_rate:
float`. Une instance dédiée de `random.Random(seed)` (jamais le module
`random` global) garantit qu'un seed fixe produit toujours la même
séquence de décisions, indépendamment de l'ordre d'exécution des autres
tests.

## Conséquences

### Positives
- Tests CI parfaitement reproductibles (seed fixe)
- Exploration manuelle réaliste possible (sans seed, variance naturelle)
- Aucune pollution d'état entre tests (instance dédiée, pas de `random.seed()` global)
- Les cas limites (`success_rate=0.0` ou `1.0`) sont mathématiquement garantis, pas seulement statistiquement probables

### Négatives / Dette assumée
- Le comportement simulé (sélecteurs placeholder génériques) ne reflète pas la richesse réelle d'une proposition Claude - acceptable pour tester la logique d'orchestration, pas pour évaluer la qualité réelle de proposition

## Alternatives considérées

| Alternative | Pourquoi rejetée |
|---|---|
| Fixtures JSON entièrement déterministes (pas d'aléa) | Moins réaliste pour l'exploration manuelle du comportement du système face à des échecs variés |
| `random.seed()` global | Modifie un état partagé par tout le processus Python - un autre test consommant le générateur global romprait la reproductibilité |

## Angle recruteur

Illustre la maîtrise d'un piège classique du mocking probabiliste (état
partagé du module `random`), et la réconciliation de deux besoins en
apparence contradictoires (reproductibilité stricte et réalisme) par un
seul mécanisme simple.
