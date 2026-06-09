"""Port du domaine pour la persistance des sélecteurs.

C'est le cœur du pattern Hexagonal Architecture appliqué ici : le domaine et
la couche applicative dépendent de cette abstraction (`Protocol`), jamais
d'une technologie concrète. En production, l'implémentation combine Redis
(cache chaud, lecture rapide) et PostgreSQL (source de vérité, audit) - voir
ADR 0007. Pour les tests, `InMemorySelectorRepository` respecte le même
contrat sans aucune dépendance réseau.

On utilise `typing.Protocol` plutôt qu'une classe abstraite (`ABC`) : le
duck-typing structurel de Protocol évite tout couplage à une hiérarchie de
classes concrète, et s'intègre naturellement avec le typage statique MyPy.
"""

from typing import Protocol

from extraction_worker.domain.selector import Selector


class SelectorRepositoryPort(Protocol):
    async def get_active_selector(self, domain: str, field_name: str) -> Selector | None:
        """Retourne le sélecteur actif pour ce domaine/champ, ou None si aucun n'existe."""
        ...

    async def save_selector(self, selector: Selector) -> None:
        """Enregistre un nouveau sélecteur comme actif, désactivant la version précédente."""
        ...
