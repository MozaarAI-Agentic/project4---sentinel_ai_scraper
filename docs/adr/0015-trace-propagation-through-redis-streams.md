# ADR-0015: Propagation du contexte de trace à travers Redis Streams

**Statut:** Accepté
**Contexte du projet:** SentinelAI Scraper

## Contexte

Les métriques Prometheus (Phase 10) mesurent des agrégats (latence
moyenne, taux de succès), mais ne permettent pas de suivre **une requête
précise** à travers les trois microservices - en particulier à travers le
saut asynchrone de la queue Redis, où il n'y a pas de requête HTTP dans
laquelle propager un header `traceparent` classique.

## Décision

Le contexte OpenTelemetry actif au moment de l'`enqueue` (API Gateway) est
injecté directement dans les champs du message Redis Stream
(`inject_trace_context()`). Le Recovery Engine l'extrait à la lecture
(`extract_trace_context()`) et démarre son span de traitement avec ce
contexte comme parent - garantissant que le span du Recovery Engine
apparaît comme un **enfant** du span de la requête HTTP d'origine, malgré
l'absence de lien HTTP direct entre les deux.

## Conséquences

### Positives
- Une trace complète API Gateway → Redis → Recovery Engine est possible,
  prouvée par un test d'intégration vérifiant l'égalité des `trace_id`
  entre le span producteur et le span consommateur
- Le mécanisme de propagation (`inject`/`extract`) est le standard W3C
  Trace Context, pas une solution maison

### Négatives / Dette assumée
- `ConsoleSpanExporter` est utilisé par défaut, faute de collecteur
  Jaeger/Tempo déployé dans ce MVP - les traces s'affichent dans les logs,
  pas dans une UI dédiée (voir ROADMAP.md pour la migration vers un
  exporter OTLP réel)
- Un `Exception while exporting Span` cosmétique apparaît parfois en fin
  de suite de tests (fermeture de flux stdout par pytest avant le flush
  final du `BatchSpanProcessor`) - sans effet sur le résultat des tests,
  documenté plutôt que masqué

## Alternatives considérées

| Alternative | Pourquoi rejetée |
|---|---|
| Ne pas propager de trace à travers la queue, démarrer une trace neuve côté Recovery Engine | Aurait rendu impossible de relier une recovery à sa requête HTTP d'origine - perd l'essentiel de la valeur du tracing distribué sur le chemin le plus intéressant du système |
| Stocker le trace_id dans PostgreSQL (colonne sur `Job`) plutôt que dans le message Redis | Couplerait le tracing à un aller-retour base de données ; le message est déjà le vecteur naturel de propagation entre producteur et consommateur |

## Angle recruteur

Démontre la compréhension qu'un header HTTP ne suffit pas à propager une
trace dans un système avec un saut asynchrone par message queue - et la
capacité à implémenter le standard W3C Trace Context manuellement dans ce
contexte, plutôt que de se limiter à l'auto-instrumentation HTTP qui
s'arrête à la frontière de la queue.
