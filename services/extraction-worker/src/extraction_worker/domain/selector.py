"""Entité du domaine représentant un sélecteur CSS/XPath pour un champ donné.

Contrairement à `ExtractionOutcome` (Cycle 1), `Selector` a une identité
conceptuelle (domaine + champ) qui persiste à travers ses versions successives
- c'est une entité, pas un simple value object. Elle reste immuable une fois
créée : une "nouvelle version" est un nouvel objet, jamais une mutation.
"""

from dataclasses import dataclass
from typing import Literal

SelectorSource = Literal["manual", "ai_generated"]


@dataclass(frozen=True)
class Selector:
    domain: str
    field_name: str
    selector_value: str
    source: SelectorSource
    version: int = 1
