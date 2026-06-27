# ADR-0006: Base de données PostgreSQL partagée entre services

**Statut:** Accepté
**Contexte du projet:** SentinelAI Scraper

## Contexte

Le principe "pur" en microservices est *database-per-service*. Or l'entité
`Job` est créée par l'API Gateway, mise à jour par le Recovery Engine, et
consultée par les deux - trois services touchent potentiellement la même
donnée d'état.

## Décision

Une base PostgreSQL unique est partagée. Chaque service définit son propre
mapping SQLAlchemy vers les tables qu'il consulte (pas d'import de modèle
ORM d'un service à l'autre), mais **l'API Gateway reste seul propriétaire
des migrations** de la table `jobs` - le Recovery Engine s'y connecte en
lecture/écriture sans jamais faire évoluer son schéma.

## Conséquences

### Positives
- Évite la complexité d'un pattern Saga/event-sourcing pour maintenir la cohérence entre bases séparées - complexité non justifiée pour ce volume
- Un seul PostgreSQL à opérer, sauvegarder, monitorer en MVP

### Négatives / Dette assumée
- Couplage réel entre services au niveau du schéma physique - un changement de schéma `jobs` par l'API Gateway peut casser silencieusement le Recovery Engine si non coordonné
- Ne respecte pas l'isolation stricte que *database-per-service* offrirait à grande échelle

## Alternatives considérées

| Alternative | Pourquoi rejetée |
|---|---|
| Database-per-service + synchronisation événementielle (Kafka/Debezium) | Architecture correcte à grande échelle, mais complexité disproportionnée pour ce volume de MVP ; documentée comme migration possible, pas ignorée |
| Recovery Engine appelant l'API Gateway via HTTP pour lire/écrire le Job | Alternative valide qui préserverait l'isolation ; écartée pour limiter la latence et la chaîne de dépendances synchrones sur un chemin déjà asynchrone |

## Angle recruteur

Démontre la capacité à assumer un compromis d'architecture documenté
plutôt que de prétendre appliquer un principe "pur" sans en payer le coût
réel - distinction que les entretiens techniques senior testent souvent
directement ("pourquoi pas database-per-service ici ?").
