# ADR-0010: Transfert des captures d'écran en base64 (pas de filesystem partagé)

**Statut:** Accepté
**Contexte du projet:** SentinelAI Scraper

## Contexte

Le Recovery Engine a besoin d'une capture d'écran produite par
l'Extraction Worker (qui seul possède Playwright, ADR-0002). Les deux
services sont des conteneurs distincts, sans système de fichiers partagé.

## Décision

L'endpoint `POST /internal/screenshot` du Worker retourne l'image PNG
encodée en base64 dans le corps JSON de la réponse, plutôt qu'un chemin de
fichier ou un identifiant vers un stockage partagé.

## Conséquences

### Positives
- Aucune dépendance à un volume Docker partagé ou un stockage objet externe pour le MVP
- Simple à débugger (payload lisible dans les logs de requête)

### Négatives / Dette assumée
- Overhead de ~33% de taille par rapport aux bytes bruts (caractéristique du base64)
- Non adapté à un volume élevé de captures ou des images de grande taille

## Alternatives considérées

| Alternative | Pourquoi rejetée |
|---|---|
| Chemin de fichier sur un volume partagé | Suppose un système de fichiers partagé entre conteneurs, fragile et contraire à l'indépendance de déploiement des microservices |
| Upload multipart | Complexité additionnelle non justifiée par le volume (une capture par tentative de recovery, pas un flux vidéo) |
| Stockage objet (S3) + URL signée | Solution correcte à grande échelle, sur-ingénierie pour le volume actuel du MVP |

## Angle recruteur

Prouve la compréhension qu'un système distribué ne peut pas supposer un
filesystem partagé, et la capacité à choisir une solution simple
proportionnée au volume réel plutôt que la plus scalable en théorie.
