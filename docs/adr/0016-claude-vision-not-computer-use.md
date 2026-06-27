# ADR-0016: Claude en mode vision, pas l'outil "Computer Use"

**Statut:** Accepté
**Contexte du projet:** SentinelAI Scraper

## Contexte

Le projet a été cadré depuis la Phase 1 autour de "Claude Computer Use"
pour la recovery IA. Au moment d'activer Claude réellement (Cycle 17), il
a fallu confronter ce vocabulaire à ce que l'outil Anthropic nommé
"Computer Use" fait réellement : piloter un environnement graphique de
façon interactive (clics, frappe clavier, captures d'écran successives
dans une boucle agentique), destiné à des tâches comme naviguer un site
web pas à pas ou remplir un formulaire.

Ici, le besoin est différent : Playwright a déjà capturé **une image
statique**, et il faut en tirer une **proposition structurée de
sélecteurs CSS** - un problème de vision + sortie structurée, pas de
pilotage d'interface.

## Décision

`ClaudeVisionRecoveryEngine` utilise l'API Messages standard d'Anthropic
avec un bloc image (le screenshot en base64) et un prompt demandant une
réponse JSON stricte - jamais l'outil Computer Use. Le nom de la classe
reflète ce qu'elle fait réellement, plutôt que de perpétuer un vocabulaire
hérité du cadrage initial.

## Conséquences

### Positives
- Un seul appel API par tentative de recovery, pas une boucle agentique multi-tours - plus rapide et nettement moins coûteux
- Sortie strictement validée (JSON parsé, champs filtrés contre le schéma attendu, types vérifiés) avant d'être considérée comme une proposition exploitable, cohérent avec ADR-0001
- `RecoveryEnginePort` (Cycle 11) reste inchangé - le graphe LangGraph ne sait pas si le mock, Claude vision, ou un futur remplaçant répond à l'appel

### Négatives / Dette assumée
- Coût estimé (`_INPUT_COST_PER_MILLION_TOKENS_USD`/`_OUTPUT_COST_PER_MILLION_TOKENS_USD`) codé en dur comme approximation, à maintenir manuellement si la tarification Anthropic évolue - documenté explicitement dans le code, pas une source de vérité facturée
- Aucun appel réel n'a pu être testé dans cet environnement de développement (pas de clé API disponible) - validé uniquement via un double de test structurel imitant l'interface du SDK, jamais contre le vrai service Anthropic

## Alternatives considérées

| Alternative | Pourquoi rejetée |
|---|---|
| Utiliser le véritable outil Computer Use | Conçu pour du pilotage interactif multi-tours d'un environnement graphique - inadapté et plus coûteux pour analyser une image statique une seule fois |
| Function calling / tool use structuré plutôt qu'un JSON en texte libre | Alternative légitime et probablement plus robuste - identifiée comme amélioration possible, non retenue immédiatement pour rester au plus près du contrat `SelectorProposal` déjà existant |

## Angle recruteur

Démontre la capacité à remettre en question un vocabulaire hérité d'un
cadrage initial dès qu'il ne correspond plus à la réalité technique du
besoin - plutôt que de forcer l'usage d'un outil parce qu'il était "prévu
dans le brief", au prix d'une solution plus lente, plus chère et moins
fiable.
