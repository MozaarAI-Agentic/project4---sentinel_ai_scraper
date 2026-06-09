"""Adaptateur en mémoire de SelectorRepositoryPort.

Utilisé exclusivement pour les tests unitaires et l'application layer,
afin de valider toute la logique métier sans dépendre d'un vrai Redis.
L'implémentation de production (Redis + PostgreSQL) suit exactement le
même contrat et sera introduite plus tard sans modifier un seul test qui
dépend uniquement du port.
"""

from extraction_worker.domain.selector import Selector


class InMemorySelectorRepository:
    """Implémentation de test du port SelectorRepositoryPort.

    Le typage structurel de `Protocol` signifie qu'aucun héritage explicite
    n'est nécessaire ici : cette classe satisfait le contrat simplement en
    implémentant les mêmes méthodes avec les mêmes signatures.
    """

    def __init__(self) -> None:
        self._selectors: dict[tuple[str, str], Selector] = {}

    async def get_active_selector(self, domain: str, field_name: str) -> Selector | None:
        return self._selectors.get((domain, field_name))

    async def save_selector(self, selector: Selector) -> None:
        # Le versionnement est une responsabilité du repository, pas de l'appelant :
        # celui qui propose un nouveau sélecteur (use case applicatif, ou le Recovery
        # Engine) ne devrait jamais avoir à connaître la version courante pour agir.
        # Le champ `version` reçu en paramètre est donc ignoré ici par conception.
        key = (selector.domain, selector.field_name)
        previous = self._selectors.get(key)
        next_version = previous.version + 1 if previous else selector.version

        self._selectors[key] = Selector(
            domain=selector.domain,
            field_name=selector.field_name,
            selector_value=selector.selector_value,
            source=selector.source,
            version=next_version,
        )
