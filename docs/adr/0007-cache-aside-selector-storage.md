# ADR-0007: Stratégie Cache-Aside pour le stockage des sélecteurs

**Statut:** Accepté
**Contexte du projet:** SentinelAI Scraper

## Contexte

Chaque extraction doit résoudre rapidement le sélecteur actif pour un
domaine/champ donné (chemin chaud, exécuté à chaque requête), tout en
conservant un historique auditable des sélecteurs (versions, source
manuelle/IA) pour la traçabilité et le debug.

## Décision

Redis sert de cache de lecture rapide (clé `selector:{domain}:{field}`) ;
PostgreSQL reste la source de vérité avec historique versionné complet.
Toute la logique cache-aside (lecture cache d'abord, fallback PostgreSQL
puis réchauffement du cache, écriture PostgreSQL puis Redis) est
entièrement encapsulée dans un seul adaptateur
(`RedisPostgresSelectorRepository`) - le use case appelant ne sait jamais
laquelle des deux technologies a répondu.

## Conséquences

### Positives
- Latence minimale sur le chemin chaud (lecture Redis)
- Historique complet et audit-ready préservé dans PostgreSQL
- Le use case reste testable sans connaître les détails de cache (Port/Adapter)

### Négatives / Dette assumée
- Fenêtre d'incohérence possible si l'écriture Redis échoue après un succès PostgreSQL (le prochain cache miss se réchauffe correctement, mais transitoirement le cache peut être périmé)
- Contrainte d'unicité "un seul sélecteur actif" appliquée au niveau applicatif, pas par une contrainte SQL native (limite du substitut de test SQLite, voir ADR-0008)

## Alternatives considérées

| Alternative | Pourquoi rejetée |
|---|---|
| Redis uniquement (pas d'historique) | Perd toute traçabilité des versions et de la source (manuel vs IA), cruciale pour le KPI "réparations automatiques" |
| PostgreSQL uniquement (pas de cache) | Latence réseau supplémentaire sur le chemin chaud, exécuté à haute fréquence |

## Angle recruteur

Démontre l'implémentation propre d'un pattern cache-aside connu, avec la
logique de cohérence encapsulée à un seul endroit plutôt que dispersée
dans les use cases appelants.
