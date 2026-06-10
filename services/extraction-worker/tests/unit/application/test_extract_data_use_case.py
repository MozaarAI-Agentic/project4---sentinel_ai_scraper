"""Tests du use case ExtractDataUseCase.

Ce use case orchestre trois collaborateurs, tous accédés via leurs ports
abstraits : le navigateur (BrowserPort), le repository de sélecteurs
(SelectorRepositoryPort) et la règle de validation (ExtractionValidator).
Aucune dépendance réelle à Playwright ou Redis - on utilise les doubles de
test des cycles précédents.
"""

import pytest

from extraction_worker.application.use_cases.extract_data_use_case import ExtractDataUseCase
from extraction_worker.domain.selector import Selector
from extraction_worker.infrastructure.fake_browser import FakeBrowser
from extraction_worker.infrastructure.in_memory_selector_repository import (
    InMemorySelectorRepository,
)


@pytest.fixture
def selector_repository() -> InMemorySelectorRepository:
    return InMemorySelectorRepository()


class TestExtractDataUseCaseSuccess:
    async def test_returns_success_outcome_when_all_selectors_resolve_valid_data(
        self, selector_repository: InMemorySelectorRepository
    ) -> None:
        await selector_repository.save_selector(
            Selector(domain="books.example", field_name="title", selector_value="h1.title", source="manual")
        )
        await selector_repository.save_selector(
            Selector(domain="books.example", field_name="price", selector_value=".price", source="manual")
        )
        browser = FakeBrowser(canned_response={"title": "Clean Code", "price": "29.99"})
        use_case = ExtractDataUseCase(browser=browser, selector_repository=selector_repository)

        result = await use_case.execute(
            url="https://books.example/1", domain="books.example", required_fields=["title", "price"]
        )

        assert result.outcome.is_success is True
        assert result.extracted_data == {"title": "Clean Code", "price": "29.99"}


class TestExtractDataUseCaseMissingSelector:
    async def test_field_without_a_registered_selector_is_reported_as_missing(
        self, selector_repository: InMemorySelectorRepository
    ) -> None:
        """Aucun sélecteur enregistré pour 'price' -> le use case ne doit même pas
        essayer de le demander au navigateur, et la validation doit le signaler
        comme un champ manquant, exactement comme un sélecteur cassé le ferait.
        """
        await selector_repository.save_selector(
            Selector(domain="books.example", field_name="title", selector_value="h1.title", source="manual")
        )
        browser = FakeBrowser(canned_response={"title": "Clean Code", "price": "29.99"})
        use_case = ExtractDataUseCase(browser=browser, selector_repository=selector_repository)

        result = await use_case.execute(
            url="https://books.example/1", domain="books.example", required_fields=["title", "price"]
        )

        assert result.outcome.is_success is False
        assert result.outcome.missing_fields == ["price"]
        assert "price" not in result.extracted_data

    async def test_use_case_only_sends_resolved_selectors_to_the_browser(
        self, selector_repository: InMemorySelectorRepository
    ) -> None:
        await selector_repository.save_selector(
            Selector(domain="books.example", field_name="title", selector_value="h1.title", source="manual")
        )
        browser = FakeBrowser(canned_response={"title": "Clean Code", "price": "29.99"})
        use_case = ExtractDataUseCase(browser=browser, selector_repository=selector_repository)

        await use_case.execute(
            url="https://books.example/1", domain="books.example", required_fields=["title", "price"]
        )

        assert browser.last_call_selectors == {"title": "h1.title"}
        assert browser.last_call_url == "https://books.example/1"


class TestExtractDataUseCaseEmptyField:
    async def test_selector_resolves_but_browser_returns_empty_value(
        self, selector_repository: InMemorySelectorRepository
    ) -> None:
        await selector_repository.save_selector(
            Selector(domain="books.example", field_name="price", selector_value=".price", source="manual")
        )
        browser = FakeBrowser(canned_response={"price": ""})
        use_case = ExtractDataUseCase(browser=browser, selector_repository=selector_repository)

        result = await use_case.execute(
            url="https://books.example/1", domain="books.example", required_fields=["price"]
        )

        assert result.outcome.is_success is False
        assert result.outcome.missing_fields == ["price"]


class TestExtractDataUseCaseWithCandidateSelectorsOverride:
    """Utilisé par le Recovery Engine (Cycle 13) pour tester des sélecteurs
    candidats sans les enregistrer au préalable dans le repository - ils ne
    sont approuvés qu'après validation réussie."""

    async def test_override_selectors_bypass_the_repository_entirely(
        self, selector_repository: InMemorySelectorRepository
    ) -> None:
        # Un sélecteur DIFFÉRENT est enregistré, mais l'override doit prévaloir
        await selector_repository.save_selector(
            Selector(domain="books.example", field_name="title", selector_value=".old-title", source="manual")
        )
        browser = FakeBrowser(canned_response={"title": "Clean Code"})
        use_case = ExtractDataUseCase(browser=browser, selector_repository=selector_repository)

        result = await use_case.execute(
            url="https://books.example/1",
            domain="books.example",
            required_fields=["title"],
            candidate_selectors={"title": "h1.title"},
        )

        assert browser.last_call_selectors == {"title": "h1.title"}
        assert result.outcome.is_success is True

    async def test_field_without_a_candidate_selector_is_still_reported_missing(
        self, selector_repository: InMemorySelectorRepository
    ) -> None:
        browser = FakeBrowser(canned_response={"title": "Clean Code", "price": "29.99"})
        use_case = ExtractDataUseCase(browser=browser, selector_repository=selector_repository)

        result = await use_case.execute(
            url="https://books.example/1",
            domain="books.example",
            required_fields=["title", "price"],
            candidate_selectors={"title": "h1.title"},  # pas de candidat pour "price"
        )

        assert result.outcome.is_success is False
        assert result.outcome.missing_fields == ["price"]


class TestExtractDataUseCaseMetrics:
    """Vérifie que chaque exécution incrémente les métriques Prometheus
    partagées (Phase 10 - Observability), via un delta plutôt qu'une valeur
    absolue - le registre Prometheus est global au process et accumule les
    valeurs entre tests."""

    async def test_records_a_successful_extraction(
        self, selector_repository: InMemorySelectorRepository
    ) -> None:
        from sentinel_shared.observability.metrics import EXTRACTION_RESULT_TOTAL

        await selector_repository.save_selector(
            Selector(domain="metrics.example", field_name="title", selector_value="h1", source="manual")
        )
        browser = FakeBrowser(canned_response={"title": "Clean Code"})
        use_case = ExtractDataUseCase(browser=browser, selector_repository=selector_repository)

        before = EXTRACTION_RESULT_TOTAL.labels(domain="metrics.example", outcome="success")._value.get()
        await use_case.execute(url="https://metrics.example/1", domain="metrics.example", required_fields=["title"])
        after = EXTRACTION_RESULT_TOTAL.labels(domain="metrics.example", outcome="success")._value.get()

        assert after == before + 1

    async def test_records_a_failed_extraction(
        self, selector_repository: InMemorySelectorRepository
    ) -> None:
        from sentinel_shared.observability.metrics import EXTRACTION_RESULT_TOTAL

        browser = FakeBrowser(canned_response={})
        use_case = ExtractDataUseCase(browser=browser, selector_repository=selector_repository)

        before = EXTRACTION_RESULT_TOTAL.labels(domain="metrics-fail.example", outcome="failure")._value.get()
        await use_case.execute(
            url="https://metrics-fail.example/1", domain="metrics-fail.example", required_fields=["title"]
        )
        after = EXTRACTION_RESULT_TOTAL.labels(domain="metrics-fail.example", outcome="failure")._value.get()

        assert after == before + 1
