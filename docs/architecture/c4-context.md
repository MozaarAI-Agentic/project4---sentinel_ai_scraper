# C4 — Diagramme de Contexte

Vue la plus haute : SentinelAI Scraper comme boîte noire, ses utilisateurs
et les systèmes externes avec lesquels il interagit réellement.

```mermaid
C4Context
    title SentinelAI Scraper — Diagramme de Contexte

    Person(client, "Client de l'API", "Système ou développeur déclenchant des jobs de scraping")

    System(sentinel, "SentinelAI Scraper", "Extraction web déterministe avec recovery IA automatique")

    System_Ext(target_sites, "Sites web cibles", "Pages HTML statiques ou dynamiques à scraper")
    System_Ext(claude_api, "Anthropic Claude API", "Analyse visuelle pour la recovery (Computer Use) - activé en fin de développement, mocké pendant le build")
    System_Ext(observability, "Prometheus + Grafana", "Collecte et visualisation des métriques opérationnelles")

    Rel(client, sentinel, "Déclenche un scrape, consulte le statut", "HTTPS/JSON")
    Rel(sentinel, target_sites, "Navigue et extrait les données", "HTTPS (Playwright)")
    Rel(sentinel, claude_api, "Analyse un screenshot en cas d'échec confirmé", "HTTPS (Anthropic SDK)")
    Rel(observability, sentinel, "Scrape /metrics périodiquement", "HTTP")
```

## Ce que ce diagramme révèle

**Claude API n'est PAS au centre du système** — c'est un système externe
optionnel, appelé conditionnellement, exactement comme le sont les sites
cibles. Le mettre visuellement au même niveau que "Sites web cibles"
renforce le message de l'ADR-0001 (Deterministic-First) : l'IA est une
dépendance externe de secours, pas le cœur du produit.

**Un seul point d'entrée pour le client** — même si le système est composé
de 3 microservices en interne, le client de l'API n'en voit qu'un seul
(l'API Gateway). La complexité interne est un détail d'implémentation
invisible depuis ce niveau.
