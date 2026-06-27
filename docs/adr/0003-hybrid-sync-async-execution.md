# ADR-0003: Modèle d'exécution hybride synchrone/asynchrone

**Statut:** Accepté
**Contexte du projet:** SentinelAI Scraper

## Contexte

Une extraction réussie (chemin nominal) prend quelques centaines de
millisecondes. Une recovery IA peut prendre de plusieurs secondes à
plusieurs dizaines de secondes (analyse visuelle, plusieurs tentatives).
Traiter les deux cas de la même façon (tout synchrone, ou tout
asynchrone) est sous-optimal dans les deux cas.

## Décision

`POST /api/v1/jobs` répond de façon **synchrone** (`200` + données) si
l'extraction déterministe réussit immédiatement. Si une recovery est
nécessaire, l'API répond immédiatement avec `202 Accepted` + `job_id` +
`poll_url`, et le traitement se poursuit de façon asynchrone via une file
Redis consommée par le Recovery Engine.

## Conséquences

### Positives
- Le client obtient une réponse rapide dans le cas majoritaire (chemin nominal)
- Aucun risque de timeout HTTP sur un chemin dont la durée est par nature incertaine
- Le statut `recovery_pending` explicite dans la réponse évite toute ambiguïté entre "lent" et "en cours de réparation"

### Négatives / Dette assumée
- Deux modes de communication à documenter et tester pour les clients de l'API
- Le client doit implémenter un polling (ou webhook, non fait dans le MVP) pour connaître le résultat final

## Alternatives considérées

| Alternative | Pourquoi rejetée |
|---|---|
| Tout synchrone | Risque de timeout HTTP sur le chemin de recovery ; expose le client à des architectures internes non pertinentes pour lui |
| Tout asynchrone (même le chemin nominal) | Ajoute une latence perçue et une complexité de polling inutiles pour l'écrasante majorité des requêtes qui réussissent du premier coup |

## Angle recruteur

Illustre la capacité à adapter le protocole de communication à la nature
réelle du travail plutôt que d'appliquer une règle uniforme par simplicité
- distinction qu'un architecte confirmé sait faire et justifier.
