# ADR-0014: Migration de la queue de recovery vers Redis Streams

**Statut:** Accepté (remplace la file simple de l'ADR-0004)
**Contexte du projet:** SentinelAI Scraper

## Contexte

L'ADR-0004 avait choisi une liste Redis simple (`LPUSH`/`BRPOP`) pour la
file de recovery, avec une limite documentée dès le départ : `BRPOP`
retire le message de la liste **avant** son traitement. Un crash du
Recovery Engine en cours de traitement perd le job pour toujours - il
reste bloqué au statut `recovery_pending` sans jamais être repris.

## Décision

Migration vers Redis Streams avec un consumer group :
`XADD` (producteur, API Gateway) pousse le job dans le stream. `XREADGROUP`
(consommateur, Recovery Engine) le lit et le place dans une Pending
Entries List (PEL) *avant* de le traiter. `XACK` n'est envoyé qu'**après**
la mise à jour réussie du `Job` en base. `XAUTOCLAIM` permet de réclamer
les messages restés dans la PEL au-delà d'un délai configurable (crash
d'un précédent consommateur).

## Conséquences

### Positives
- Élimine la perte de message documentée dans l'ADR-0004 - prouvé par un
  test d'intégration simulant un crash explicite (`_CrashingGraph`) et
  vérifiant que le message reste dans la PEL, puis qu'un second
  consommateur peut le réclamer et le traiter avec succès
- Redis reste l'unique dépendance (pas de nouveau broker), cohérent avec
  le raisonnement initial de l'ADR-0004
- Ouvre la voie à plusieurs consommateurs du même groupe (scalabilité
  horizontale du Recovery Engine), chaque message n'étant délivré qu'à un
  seul consommateur du groupe à la fois

### Négatives / Dette assumée
- Complexité accrue par rapport à une liste simple (gestion explicite du
  consumer group, de la PEL, de la réclamation)
- `reclaim_stale_messages()` doit être appelé explicitement (par un job
  planifié ou au démarrage du service) - il n'est pas automatique ; un
  message resté en PEL après un crash n'est retraité que si quelque chose
  appelle cette méthode

## Alternatives considérées

| Alternative | Pourquoi rejetée |
|---|---|
| Garder la liste simple, documenter la limite sans la corriger | Acceptable pour un MVP, mais une fois la dette identifiée explicitement (Cycle 8), la corriger était plus cohérent avec la discipline du reste du projet |
| Migrer vers Kafka/RabbitMQ | Toujours la même sur-ingénierie identifiée dans l'ADR-0004 - Redis Streams résout le problème réel (perte de message) sans introduire de nouvelle dépendance |

## Angle recruteur

Démontre la capacité à identifier une limite technique documentée
initialement comme un compromis acceptable, puis à revenir la corriger
avec la bonne primitive (consumer group + PEL) sans sur-ingénierer la
solution vers un broker dédié - et à **prouver** la correction avec un
test qui simule le scénario de défaillance exact que la migration résout,
pas seulement un test du chemin heureux.
