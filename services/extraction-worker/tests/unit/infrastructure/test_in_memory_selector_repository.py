"""Tests du contrat SelectorRepositoryPort.

Ces tests valident le comportement attendu de N'IMPORTE QUELLE implémentation
du port (in-memory pour les tests, Redis+Postgres en production), sans
dépendre d'une infrastructure réelle. C'est le principe du Port/Adapter :
le contrat est testé une fois, chaque adaptateur doit le respecter.
"""

import pytest

from extraction_worker.domain.selector import Selector
from extraction_worker.infrastructure.in_memory_selector_repository import (
    InMemorySelectorRepository,
)


@pytest.fixture
def repository() -> InMemorySelectorRepository:
    return InMemorySelectorRepository()


class TestGetActiveSelector:
    async def test_returns_none_when_no_selector_registered(
        self, repository: InMemorySelectorRepository
    ) -> None:
        result = await repository.get_active_selector(domain="example.com", field_name="title")

        assert result is None

    async def test_returns_the_registered_active_selector(
        self, repository: InMemorySelectorRepository
    ) -> None:
        selector = Selector(
            domain="example.com",
            field_name="title",
            selector_value="h1.product-title",
            source="manual",
        )
        await repository.save_selector(selector)

        result = await repository.get_active_selector(domain="example.com", field_name="title")

        assert result is not None
        assert result.selector_value == "h1.product-title"

    async def test_selectors_are_isolated_per_domain(
        self, repository: InMemorySelectorRepository
    ) -> None:
        """Un sélecteur enregistré pour un domaine ne doit jamais fuiter vers un autre."""
        await repository.save_selector(
            Selector(domain="site-a.com", field_name="title", selector_value=".a-title", source="manual")
        )

        result = await repository.get_active_selector(domain="site-b.com", field_name="title")

        assert result is None


class TestSaveSelectorReplacesPreviousVersion:
    async def test_saving_a_new_selector_deactivates_the_previous_one(
        self, repository: InMemorySelectorRepository
    ) -> None:
        """Règle métier clé (Phase 5) : un seul sélecteur actif par domaine/champ à la fois."""
        old_selector = Selector(
            domain="example.com", field_name="price", selector_value=".old-price", source="manual"
        )
        await repository.save_selector(old_selector)

        new_selector = Selector(
            domain="example.com",
            field_name="price",
            selector_value=".new-price",
            source="ai_generated",
        )
        await repository.save_selector(new_selector)

        active = await repository.get_active_selector(domain="example.com", field_name="price")
        assert active is not None
        assert active.selector_value == ".new-price"
        assert active.source == "ai_generated"

    async def test_version_increments_with_each_new_selector(
        self, repository: InMemorySelectorRepository
    ) -> None:
        await repository.save_selector(
            Selector(domain="example.com", field_name="price", selector_value=".v1", source="manual")
        )
        await repository.save_selector(
            Selector(domain="example.com", field_name="price", selector_value=".v2", source="ai_generated")
        )

        active = await repository.get_active_selector(domain="example.com", field_name="price")

        assert active is not None
        assert active.version == 2
