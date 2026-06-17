"""Double de test pour RecoveryEnginePort, utilisé en développement et en CI
avant l'activation du vrai Claude Computer Use (fin de Phase 8, décision
prise en Phase 1).

Un `random.Random(seed)` **dédié à l'instance** (jamais le module `random`
global) garantit qu'un seed fixe produit toujours la même séquence de
décisions, peu importe combien d'autres tests s'exécutent avant ou en
parallèle - un piège classique du mocking probabiliste que l'utilisation du
module `random` global provoquerait (état partagé entre tests).
"""

import random

from recovery_engine.domain.value_objects import SelectorProposal
from sentinel_shared.observability.metrics import AI_RECOVERY_COST_USD_TOTAL

_PLACEHOLDER_SELECTOR_PREFIX = "css-selector-for"
_SIMULATED_COST_PER_CALL_USD = 0.015  # Approximation d'un appel Claude Computer Use


class MockRecoveryEngine:
    def __init__(self, seed: int | None = None, success_rate: float = 0.7) -> None:
        self._random = random.Random(seed)
        self._success_rate = success_rate

    async def propose_selectors(
        self,
        screenshot_base64: str,
        expected_schema: dict[str, type],
        rejection_history: list[str],
    ) -> SelectorProposal:
        AI_RECOVERY_COST_USD_TOTAL.inc(_SIMULATED_COST_PER_CALL_USD)

        # random.random() retourne une valeur dans [0.0, 1.0) - jamais 1.0.
        # Donc success_rate=0.0 garantit mathématiquement is_confident=False
        # à chaque appel (0.0 < 0.0 est toujours faux), et success_rate=1.0
        # garantit is_confident=True à chaque appel (tout est < 1.0). Ce
        # n'est pas juste statistiquement probable, c'est déterministe aux
        # bornes - voir les tests dédiés à ces deux cas extrêmes.
        is_confident = self._random.random() < self._success_rate

        if not is_confident:
            return SelectorProposal(is_confident=False, selectors={})

        selectors = {
            field_name: f".{_PLACEHOLDER_SELECTOR_PREFIX}-{field_name}"
            for field_name in expected_schema
        }
        return SelectorProposal(is_confident=True, selectors=selectors)
