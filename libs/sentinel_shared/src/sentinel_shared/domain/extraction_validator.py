"""Règle métier partagée : décide si une extraction doit être considérée
réussie ou doit déclencher/poursuivre une recovery.

Migré depuis extraction-worker (Cycle 1) vers le shared kernel : le
Recovery Engine applique cette même règle après chaque tentative de
réparation (nœud `validate_data_schema`, Cycle 13) - c'est un contrat de
domaine partagé entre bounded contexts, pas une coïncidence de nommage.
"""

from sentinel_shared.domain.value_objects import ExtractionOutcome, FailureReason


class ExtractionValidator:
    def __init__(self, required_fields: list[str]) -> None:
        self._required_fields = required_fields

    def validate(self, extracted_data: dict[str, str]) -> ExtractionOutcome:
        missing_fields = [
            field_name
            for field_name in self._required_fields
            if self._is_missing_or_empty(extracted_data, field_name)
        ]

        if not missing_fields:
            return ExtractionOutcome(is_success=True, failure_reason=None, missing_fields=[])

        failure_reason = self._determine_failure_reason(extracted_data, missing_fields)
        return ExtractionOutcome(
            is_success=False,
            failure_reason=failure_reason,
            missing_fields=missing_fields,
        )

    @staticmethod
    def _is_missing_or_empty(extracted_data: dict[str, str], field_name: str) -> bool:
        if field_name not in extracted_data:
            return True
        value = extracted_data[field_name]
        return not value.strip()

    @staticmethod
    def _determine_failure_reason(
        extracted_data: dict[str, str], missing_fields: list[str]
    ) -> FailureReason:
        first_missing = missing_fields[0]
        if first_missing not in extracted_data:
            return FailureReason.MISSING_REQUIRED_FIELD
        return FailureReason.EMPTY_REQUIRED_FIELD
