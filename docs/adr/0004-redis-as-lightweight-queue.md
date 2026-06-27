# ADR-0004: Redis comme file de tâches légère (pas de broker dédié)

**Statut:** Accepté
**Contexte du projet:** SentinelAI Scraper

## Contexte

Le déclenchement d'une recovery IA (ADR-0003) nécessite un mécanisme de
file de tâches entre l'API Gateway et le Recovery Engine. Redis est déjà
présent dans le stack comme cache de sélecteurs.

## Décision

Une simple liste Redis (`LPUSH`/`BRPOP`) sert de file de tâches pour les
recoveries à traiter. Pas de broker dédié (Kafka, RabbitMQ) pour le MVP.

## Conséquences

### Positives
- Aucune dépendance supplémentaire ; réutilise une brique déjà déployée
- Suffisant pour le volume attendu d'un MVP

### Négatives / Dette assumée
- **Perte de message possible** : `BRPOP` retire le message de la liste avant traitement ; un crash du Recovery Engine pendant le traitement perd le job (reste indéfiniment à `recovery_pending`). Documenté explicitement plutôt que caché.
- Pas de replay d'événements, pas de multi-consommateur avec répartition de charge native

## Alternatives considérées

| Alternative | Pourquoi rejetée |
|---|---|
| Kafka | Sur-ingénierie pour ce volume ; complexité opérationnelle (Zookeeper/KRaft, partitions) non justifiée |
| RabbitMQ | Apporterait un accusé de réception (ack) natif réglant la perte de message, mais ajoute une dépendance non mandatée par le stack pour un besoin qui reste hypothétique à ce stade |
| Redis Streams (consumer groups) | Solution technique correcte au problème de perte de message identifié ; documentée comme migration naturelle (voir amélioration enterprise) plutôt qu'implémentée sans besoin réel mesuré |

## Angle recruteur

Montre la capacité à choisir l'outil proportionné au problème réel plutôt
que le plus sophistiqué disponible, tout en documentant explicitement la
limite connue (perte de message) et le chemin de migration concret.
