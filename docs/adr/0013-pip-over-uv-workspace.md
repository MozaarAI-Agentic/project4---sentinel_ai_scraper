# ADR-0013: pip + requirements.txt plutôt que uv workspace

**Statut:** Accepté (remplace la décision initiale de la Phase 4)
**Contexte du projet:** SentinelAI Scraper

## Contexte

En Phase 4 (Repository Structure), `uv` avait été choisi comme gestionnaire
de dépendances pour le monorepo, pour sa gestion native des workspaces
multi-packages et sa rapidité. En pratique, tout le développement (Cycles
1 à 16) s'est fait avec des `pip install` directs dans l'environnement de
travail, jamais avec `uv`. Arrivé en Phase 12 (Deployment), il fallait
créer les manifestes de dépendances - le moment de vérité entre le plan et
la pratique réelle.

## Décision

Utiliser `pip` + un `requirements.txt` par service (+ un
`requirements-dev.txt` partagé), et un `pyproject.toml` minimal pour
`sentinel_shared` (setuptools, pas uv) le rendant installable via
`pip install`.

## Conséquences

### Positives
- Cohérence totale entre l'outil réellement utilisé et testé pendant tout le développement et celui documenté/utilisé dans les Dockerfiles - aucune surprise de compatibilité de dernière minute
- `pip` reste l'outil le plus universellement compris, sans courbe d'apprentissage pour un contributeur externe

### Négatives / Dette assumée
- Perd les bénéfices de vitesse et de gestion de workspace natif de `uv`
- Pas de fichier de verrouillage (`lock file`) générant des installations bit-à-bit reproductibles - les bornes de version (`>=X,<Y`) dans les `requirements.txt` limitent le risque sans l'éliminer complètement

## Alternatives considérées

| Alternative | Pourquoi rejetée |
|---|---|
| Migrer vers `uv` maintenant, en Phase 12 | Introduirait un outil jamais testé pendant les 16 cycles de développement précédents, au moment even où la reproductibilité du build devient critique - le pire moment pour introduire une inconnue |
| `pip-tools` (`pip-compile`) pour un vrai lock file | Amélioration légitime, mais un ajout distinct de la décision d'outillage elle-même - documenté comme piste dans ROADMAP.md plutôt que mélangé à cette décision |

## Angle recruteur

Illustre une qualité rare : la capacité à **reconnaître et corriger un
écart entre un plan initial et la pratique réelle**, plutôt que de forcer
rétroactivement le code à se conformer à une décision prise avant d'avoir
la moindre expérience concrète du projet. Beaucoup de plans d'architecture
ne survivent pas au premier contact avec l'implémentation - ce qui compte,
c'est de le documenter honnêtement, pas de prétendre que le plan initial a
été suivi à la lettre.
