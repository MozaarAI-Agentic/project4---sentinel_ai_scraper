"""Value objects du domaine Recovery Engine.

`SelectorProposal` représente le résultat d'une tentative de recovery, que
la source soit MockRecoveryEngine ou (plus tard) le vrai Claude Computer
Use. `is_confident=False` signifie explicitement "aucune proposition
exploitable" - pas une proposition vide qu'il faudrait quand même essayer
de valider.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SelectorProposal:
    is_confident: bool
    selectors: dict[str, str] = field(default_factory=dict)
