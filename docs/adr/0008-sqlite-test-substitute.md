# ADR-0008: SQLite comme substitut de test pour PostgreSQL

**Statut:** Accepté
**Contexte du projet:** SentinelAI Scraper

## Contexte

Les tests d'intégration touchant la persistance ont besoin d'un vrai moteur
SQL (pas un double en mémoire), mais dépendre d'un PostgreSQL réel démarré
pour chaque exécution de la suite de tests ralentirait le développement
quotidien et ajouterait une dépendance Docker à la boucle de feedback TDD.

## Décision

Les tests d'intégration utilisent SQLite en mémoire
(`sqlite+aiosqlite:///:memory:`) via le même mapping SQLAlchemy que la
production. Un test end-to-end séparé contre un vrai PostgreSQL est prévu
avant chaque release (Phase 12 - Deployment), pas à chaque exécution locale.

## Conséquences

### Positives
- Suite de tests rapide (millisecondes) et sans dépendance Docker pour le développement quotidien
- Le mapping SQLAlchemy testé est strictement identique à celui de production - seul le driver change

### Négatives / Dette assumée
- SQLite ne valide pas les fonctionnalités spécifiques à PostgreSQL (JSONB natif, index partiels `WHERE is_active`) - ces contraintes sont donc réappliquées au niveau applicatif plutôt que garanties par la base en test (voir ADR-0007)
- Un bug spécifique au driver PostgreSQL pourrait échapper à la suite de tests locale

## Alternatives considérées

| Alternative | Pourquoi rejetée |
|---|---|
| PostgreSQL réel pour tous les tests (via testcontainers) | Fidélité totale, mais ralentit sensiblement chaque exécution locale de la suite ; réservé au test end-to-end pré-release |
| Mocker entièrement la couche SQLAlchemy | Perdrait toute valeur de test réel sur les requêtes SQL générées, les jointures, l'ORM lui-même |

## Angle recruteur

Illustre un compromis vitesse-de-développement vs fidélité-de-test assumé
et documenté, avec un filet de sécurité complémentaire (test PostgreSQL réel
pré-release) plutôt qu'un choix aveugle dans un sens ou dans l'autre.
