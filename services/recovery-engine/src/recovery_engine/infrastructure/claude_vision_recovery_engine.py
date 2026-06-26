"""Implémentation de production de RecoveryEnginePort, utilisant Claude en
mode vision (pas l'outil "Computer Use" - voir la clarification technique
qui a précédé ce fichier : on analyse une image statique déjà capturée par
Playwright pour en extraire des sélecteurs structurés, pas piloter un
environnement graphique interactif).

Toute sortie de Claude est traitée avec méfiance : un JSON malformé, un
objet qui n'est pas un dict, des valeurs du mauvais type, ou des champs
non demandés produisent tous une non-confiance plutôt qu'une exception -
cohérent avec le contrat de RecoveryEnginePort (Cycle 11) et avec le
principe deterministic-first (ADR-0001) : même la sortie de l'IA passe par
une validation stricte avant d'être considérée exploitable.
"""

import json
from typing import Any

from anthropic import AsyncAnthropic

from recovery_engine.domain.value_objects import SelectorProposal
from sentinel_shared.observability.metrics import AI_RECOVERY_COST_USD_TOTAL

# Tarifs approximatifs par million de tokens (modèle de classe Sonnet) -
# à maintenir à jour manuellement si la tarification Anthropic évolue ;
# documenté comme approximation, pas une source de vérité facturée.
_INPUT_COST_PER_MILLION_TOKENS_USD = 3.0
_OUTPUT_COST_PER_MILLION_TOKENS_USD = 15.0

_SYSTEM_PROMPT = (
    "You are analyzing a screenshot of a web page where a data extraction "
    "selector has stopped working. Propose CSS selectors for the requested "
    "fields based on what you see in the image. Respond with ONLY a JSON "
    "object mapping each requested field name to a CSS selector string, "
    "nothing else - no markdown fences, no explanation. If you cannot "
    "confidently identify a selector for a field, omit it from the object."
)


class ClaudeVisionRecoveryEngine:
    """Type directement sur AsyncAnthropic (le vrai client du SDK) plutôt
    que sur un Protocol maison : cette classe est déjà la frontière
    d'abstraction (RecoveryEnginePort, Cycle 11) - ajouter un second niveau
    d'abstraction juste pour le client HTTP brut du SDK n'apporterait
    aucun bénéfice réel, seulement de la complexité de typage (les
    surcharges internes du SDK ne correspondent pas proprement à un
    Protocol simplifié - même limite que CompiledRecoveryGraph face à
    LangGraph)."""

    def __init__(self, client: AsyncAnthropic, model: str = "claude-sonnet-4-6") -> None:
        self._client = client
        self._model = model

    async def propose_selectors(
        self,
        screenshot_base64: str,
        expected_schema: dict[str, type],
        rejection_history: list[str],
    ) -> SelectorProposal:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": screenshot_base64,
                            },
                        },
                        {"type": "text", "text": self._build_user_prompt(expected_schema, rejection_history)},
                    ],
                }
            ],
        )

        self._record_cost(response)
        return self._parse_response(response, expected_schema)

    @staticmethod
    def _build_user_prompt(expected_schema: dict[str, type], rejection_history: list[str]) -> str:
        fields = ", ".join(expected_schema.keys())
        prompt = f"Requested fields: {fields}."
        if rejection_history:
            prompt += " Previous rejected attempts (avoid repeating these):\n" + "\n".join(
                rejection_history
            )
        return prompt

    @staticmethod
    def _record_cost(response: Any) -> None:
        usage = getattr(response, "usage", None)
        if usage is None:
            return
        cost = (
            usage.input_tokens / 1_000_000 * _INPUT_COST_PER_MILLION_TOKENS_USD
            + usage.output_tokens / 1_000_000 * _OUTPUT_COST_PER_MILLION_TOKENS_USD
        )
        AI_RECOVERY_COST_USD_TOTAL.inc(cost)

    @staticmethod
    def _parse_response(response: Any, expected_schema: dict[str, type]) -> SelectorProposal:
        text_content = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )

        try:
            parsed = json.loads(text_content)
        except (json.JSONDecodeError, TypeError):
            return SelectorProposal(is_confident=False, selectors={})

        if not isinstance(parsed, dict):
            return SelectorProposal(is_confident=False, selectors={})

        valid_selectors = {
            field_name: value
            for field_name, value in parsed.items()
            if field_name in expected_schema and isinstance(value, str)
        }

        if not valid_selectors:
            return SelectorProposal(is_confident=False, selectors={})

        return SelectorProposal(is_confident=True, selectors=valid_selectors)
