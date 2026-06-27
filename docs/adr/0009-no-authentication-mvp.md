# ADR-0009: Absence d'authentification en MVP (avec contrôles compensatoires)

**Statut:** Accepté
**Contexte du projet:** SentinelAI Scraper

## Contexte

Le produit vise un usage portfolio/démonstration, pas une exposition
publique en production. Implémenter un système d'authentification complet
(OAuth2/JWT) ajouterait de la complexité sans démontrer de valeur
d'ingénierie supplémentaire significative pour ce périmètre.

## Décision

Aucune authentification sur l'API en MVP. Compensé par deux garde-fous :
rate limiting par IP sur `POST /jobs`, et binding réseau restreint par
défaut (`127.0.0.1`, pas `0.0.0.0`) dans la configuration Docker Compose
locale.

## Conséquences

### Positives
- Simplicité de démonstration (pas de gestion de clés/tokens pour tester l'API)
- Garde-fous minimaux réels contre l'abus, pas une absence totale de protection

### Négatives / Dette assumée
- Inadapté à toute exposition publique réelle sans ajout d'authentification au préalable
- Documenté explicitement comme limitation connue, jamais dissimulé

## Alternatives considérées

| Alternative | Pourquoi rejetée |
|---|---|
| API Key simple | Solution intermédiaire raisonnable, mais ajoute une gestion de clés pour un gain de sécurité marginal dans ce contexte de démonstration |
| OAuth2/JWT complet | Complexité disproportionnée pour la valeur démontrée dans ce périmètre MVP |

## Angle recruteur

Montre la capacité à documenter une limitation de sécurité assumée avec
des contrôles compensatoires réels, plutôt que de l'ignorer ou de sur-
ingénierer une solution sans bénéfice démontrable pour le contexte.
