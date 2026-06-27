# ADR-0011: Agent LangGraph unique, multi-nœuds (pas de système multi-agents)

**Statut:** Accepté
**Contexte du projet:** SentinelAI Scraper

## Contexte

Le pipeline de recovery comporte plusieurs étapes séquentielles et
dépendantes (capture d'écran → analyse IA → validation live → décision →
persistance/escalade). LangGraph permet de modéliser ceci soit comme un
seul agent à plusieurs nœuds, soit comme plusieurs agents spécialisés
collaborant.

## Décision

Un seul graphe LangGraph (`StateGraph`) avec des nœuds représentant chaque
étape comme une fonction pure `state -> updates`, orchestré par un routage
conditionnel (`decide_next_step`). Pas de système multi-agents.

## Conséquences

### Positives
- Chaque nœud est testable isolément comme un use case ordinaire, sans jamais instancier de graphe (Cycles 12-15)
- Pas de complexité de coordination inter-agents (délibération, consensus) inutile pour un flux séquentiel
- Le state partagé (`RecoveryState`) rend explicite tout le contexte transporté entre étapes

### Négatives / Dette assumée
- Un bug de câblage entre nœuds n'est détectable qu'à l'exécution du graphe compilé, jamais par les tests de nœuds isolés (découvert concrètement au Cycle 15 avec `handle_no_confident_proposal`)

## Alternatives considérées

| Alternative | Pourquoi rejetée |
|---|---|
| Système multi-agents (agent vision, agent validation, agent décision) | Ajoute de la complexité de coordination sans bénéfice pour un flux strictement séquentiel sans délibération entre étapes |
| State machine maison (sans LangGraph) | Aurait nécessité de réimplémenter la gestion de boucles conditionnelles et de state partagé que LangGraph fournit nativement |

## Angle recruteur

Démontre la capacité à choisir la granularité d'orchestration justifiée
par la nature du problème (séquentiel vs collaboratif) plutôt que d'utiliser
un framework à la mode (multi-agents) sans besoin réel - et à découvrir et
documenter honnêtement un bug de câblage réel plutôt que de prétendre à une
implémentation parfaite du premier coup.
