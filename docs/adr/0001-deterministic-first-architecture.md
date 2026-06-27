# ADR-0001: Architecture Deterministic-First

**Statut:** Accepté
**Contexte du projet:** SentinelAI Scraper

## Contexte

Le web scraping traditionnel casse dès qu'un site modifie son DOM, forçant
une maintenance manuelle constante. Les LLMs modernes (Claude Computer Use)
permettent une extraction par raisonnement visuel, mais sont non
déterministes, lents relativement à un parsing DOM, et coûteux à l'échelle.
Il faut décider quelle place donner à l'IA dans le pipeline d'extraction.

## Décision

Playwright + BeautifulSoup + Pydantic gèrent 100% du chemin nominal.
Claude Computer Use n'est invoqué qu'en dernier recours, après une
**validation de défaillance confirmée** (sélecteur introuvable, champ
requis manquant, échec Pydantic) — jamais de façon préventive ou
systématique. Toute proposition de Claude est revalidée par Playwright et
Pydantic avant d'être acceptée ; l'IA ne modifie jamais directement la
donnée persistée.

## Conséquences

### Positives
- Coût IA proportionnel au taux réel de rupture des sites, pas au volume total de trafic
- Latence du chemin nominal indépendante de la disponibilité/latence d'un LLM
- Comportement du chemin nominal entièrement déterministe et testable sans réseau

### Négatives / Dette assumée
- Complexité accrue : deux chemins d'exécution distincts à maintenir et tester
- Le système reste vulnérable si Playwright ne peut techniquement pas confirmer un échec (ex: timeout ambigu) — nécessite une classification fine des raisons d'échec (voir `FailureReason`)

## Alternatives considérées

| Alternative | Pourquoi rejetée |
|---|---|
| Extraction 100% par Claude Computer Use | Coût et latence disqualifiants à l'échelle ; non-déterminisme inacceptable pour un pipeline de données structurées |
| IA en pré-validation systématique de chaque extraction | Double le coût sans bénéfice sur le chemin qui, par définition, fonctionne déjà |

## Angle recruteur

Prouve la capacité à borner l'usage de l'IA à sa valeur ajoutée réelle
plutôt que de l'appliquer par réflexe — compétence rare et recherchée à
mesure que les coûts d'inférence deviennent un sujet de P&L en entreprise.
