"""Tests du domaine pur pour ExtractionValidator.

Ces tests ne dépendent d'aucune infrastructure (pas de Playwright, pas de DB,
pas de réseau). Ils valident uniquement la règle métier centrale du système :
décider si une extraction doit être considérée réussie ou doit déclencher
une recovery.
"""

from extraction_worker.domain.extraction_validator import ExtractionValidator
from extraction_worker.domain.value_objects import ExtractionOutcome, FailureReason


class TestExtractionValidatorSuccess:
    def test_returns_success_when_all_required_fields_present_and_non_empty(self) -> None:
        validator = ExtractionValidator(required_fields=["title", "price"])

        outcome = validator.validate(extracted_data={"title": "Clean Code", "price": "29.99"})

        assert outcome.is_success is True
        assert outcome.failure_reason is None

    def test_success_allows_extra_unexpected_fields(self) -> None:
        """Des champs additionnels non attendus ne doivent pas faire échouer la validation."""
        validator = ExtractionValidator(required_fields=["title"])

        outcome = validator.validate(
            extracted_data={"title": "Clean Code", "bonus_field": "unexpected"}
        )

        assert outcome.is_success is True


class TestExtractionValidatorFailureMissingField:
    def test_returns_failure_when_a_required_field_is_absent(self) -> None:
        validator = ExtractionValidator(required_fields=["title", "price"])

        outcome = validator.validate(extracted_data={"title": "Clean Code"})

        assert outcome.is_success is False
        assert outcome.failure_reason == FailureReason.MISSING_REQUIRED_FIELD
        assert outcome.missing_fields == ["price"]

    def test_lists_all_missing_fields_when_several_are_absent(self) -> None:
        validator = ExtractionValidator(required_fields=["title", "price", "author"])

        outcome = validator.validate(extracted_data={"title": "Clean Code"})

        assert outcome.missing_fields == ["price", "author"]


class TestExtractionValidatorFailureEmptyField:
    def test_returns_failure_when_a_required_field_is_an_empty_string(self) -> None:
        validator = ExtractionValidator(required_fields=["title", "price"])

        outcome = validator.validate(extracted_data={"title": "Clean Code", "price": ""})

        assert outcome.is_success is False
        assert outcome.failure_reason == FailureReason.EMPTY_REQUIRED_FIELD
        assert outcome.missing_fields == ["price"]

    def test_returns_failure_when_a_required_field_is_whitespace_only(self) -> None:
        """Un champ rempli d'espaces est aussi vide sémantiquement (piège classique du scraping)."""
        validator = ExtractionValidator(required_fields=["title"])

        outcome = validator.validate(extracted_data={"title": "   "})

        assert outcome.is_success is False
        assert outcome.failure_reason == FailureReason.EMPTY_REQUIRED_FIELD


class TestExtractionOutcomeIsImmutable:
    def test_outcome_cannot_be_mutated_after_creation(self) -> None:
        outcome = ExtractionOutcome(is_success=True, failure_reason=None, missing_fields=[])

        with __import__("pytest").raises(Exception):
            outcome.is_success = False  # type: ignore[misc]
