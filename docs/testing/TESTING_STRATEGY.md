# Stratégie de Test — SentinelAI Scraper

> Ce document formalise une discipline déjà appliquée strictement pendant le
> développement incrémental (TDD Red → Green → Refactor, voir `docs/adr/`).
> Les chiffres ci-dessous sont mesurés sur le code réel du monorepo, pas des
> objectifs théoriques.

## 1. Philosophie

Le domaine et la couche applicative ne dépendent **jamais** d'infrastructure
réelle (Playwright, Redis, PostgreSQL, HTTP). C'est ce qui permet une
pyramide de tests où l'essentiel de la couverture s'exécute en millisecondes,
sans conteneur Docker démarré.

Un test qui a besoin d'un vrai service (Redis, une base SQL, un navigateur)
est un test d'**intégration**, jamais un test unitaire — peu importe sa
rapidité d'exécution. La distinction porte sur la nature de la dépendance,
pas sur la durée.

## 2. Pyramide de tests actuelle (mesurée)

| Service | Tests unitaires | Tests d'intégration | Total | Couverture globale |
|---|---|---|---|---|
| Extraction Worker | 19 | 6 | 25 | 94% |
| API Gateway | 19 | 6 | 25 | 92% |
| **Total monorepo** | **38 (76%)** | **12 (24%)** | **50** | **93%** |

Ratio ~3:1 unitaire/intégration — cohérent avec une architecture hexagonale
où le domaine (testé unitairement) représente la majorité du code métier,
et où chaque adaptateur infrastructure n'a besoin que d'une poignée de tests
de contrat pour être couvert.

## 3. Conventions de répertoire

```
tests/
├── unit/           # Doubles de test uniquement (Fake*, InMemory*), 0 I/O réseau
│   ├── domain/
│   ├── application/
│   └── interfaces/  # Routeurs testés via ASGITransport + dependency_overrides
└── integration/    # Contre de vrais backends (Redis, SQL, Chromium)
```

Un `tests/e2e/` est prévu (non créé à ce stade) pour des scénarios complets
via `docker compose up`, une fois le Recovery Engine implémenté — voir
section 6.

## 4. Cibles de couverture par couche

| Couche | Cible | Justification |
|---|---|---|
| `domain/` | 100% | Logique métier pure, sans excuse pour un chemin non testé |
| `application/` (use cases) | 100% | Orchestration testée exhaustivement via doubles |
| `infrastructure/` (adaptateurs) | ≥ 90% | Chaque branche de contrat (succès, échec, erreur réseau) testée ; le code de câblage pur (ex: construction d'un client) n'ajoute pas de valeur à tester unitairement |
| `interfaces/http/app.py` (lifespan) | Non couvert par pytest, validé manuellement | Voir section 5 |

**Mesure actuelle : 100% sur `domain/` et `application/` dans les deux services** — vérifié, pas supposé.

## 5. Le trou de couverture assumé : le `lifespan` FastAPI

`app.py::_lifespan` (création du moteur SQLAlchemy, du client Redis, du
client HTTP) n'est **volontairement** pas exercé par la suite pytest : les
tests utilisent `httpx.ASGITransport`, qui n'invoque jamais les événements
de cycle de vie de l'application (voir Cycle 8).

Plutôt que d'ajouter un test artificiel qui instancierait un vrai serveur
uniquement pour couvrir ces lignes, ce code a été validé par une **démo
end-to-end réelle** (`curl` contre un vrai serveur, vrai Redis, vraie base
SQL — voir Cycle 8/9 du journal de développement) : preuve empirique que le
câblage fonctionne, sans gonfler artificiellement un pourcentage de
couverture avec un test qui ne testerait rien de plus qu'un mock de test.

**Action de suivi** : un test `tests/e2e/test_startup.py` utilisant
`asgi-lifespan` (bibliothèque dédiée) sera ajouté en Phase 12 (Deployment)
pour automatiser cette vérification en CI plutôt que de dépendre d'une
démo manuelle.

## 6. Stratégie de test du Recovery Engine (à venir)

Décidée en Phase 7, appliquée dès l'implémentation :

- **Mock à seed configurable** : `MockRecoveryEngine(seed=42, success_rate=0.7)` —
  déterministe en CI, réaliste en exploration manuelle (voir Phase 7 pour le
  raisonnement complet sur la réconciliation reproductibilité/réalisme).
- **Fixture `broken-dom-site`** (v1/v2) : permet de déclencher la recovery à
  la demande, sans dépendre d'un vrai site tiers qui changerait son DOM au
  hasard pendant l'exécution des tests.
- **Tests de graphe LangGraph** : chaque nœud testé isolément (comme un use
  case classique), puis le graphe complet testé avec le mock seedé pour
  valider les transitions (succès direct, retry après rejet, escalade
  humaine après `max_attempts`).

## 7. Lacune de test de contrat identifiée (dette assumée)

Le contrat JSON entre l'API Gateway (`HttpExtractionService`, Cycle 6) et
l'Extraction Worker (`ExtractResponseBody`, Cycle 9) est **documenté comme
identique des deux côtés**, mais jamais vérifié automatiquement l'un contre
l'autre — chaque service est testé avec ses propres doubles.

**Risque concret** : si l'un des deux schémas dérive silencieusement (ex:
renommage d'un champ), aucun test actuel ne le détecterait avant un vrai
déploiement.

**Mitigation prévue** : un test de contrat partagé (`tests/contract/`,
nouveau répertoire à la racine du monorepo) qui importe les deux schémas
Pydantic et vérifie leur compatibilité structurelle - à construire avant la
Phase 12 (Deployment).

## 8. Convention de nommage des doubles de test

| Préfixe | Signification | Exemple |
|---|---|---|
| `Fake*` | Retourne un résultat pré-configuré, sans logique | `FakeBrowser`, `FakeExtractionService` |
| `InMemory*` | Réimplémente la logique métier du port en mémoire (versionnement, isolation par clé) | `InMemorySelectorRepository`, `InMemoryJobRepository` |

Cette distinction n'est pas cosmétique : un `InMemory*` a sa propre logique
qui peut elle-même contenir des bugs (voir les tests dédiés à
`InMemorySelectorRepository` au Cycle 2) — ce n'est pas qu'un simple stub.

## 9. Exécution en CI (GitHub Actions, Phase 12)

```yaml
# Aperçu de la stratégie, détaillée en Phase 12
- Tests unitaires : exécutés à chaque push, aucune dépendance externe
- Tests d'intégration : exécutés à chaque push, avec Redis + Postgres
  éphémères via services GitHub Actions (pas de mock, vrais conteneurs)
- Seuil de couverture : échec du build si < 90% sur domain/ + application/
  combinés (pas de seuil global unique, pour éviter qu'une infrastructure
  correctement testée à 100% ne masque une régression sur le domaine)
```
