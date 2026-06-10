"""Port du domaine pour l'exécution du navigateur.

La couche applicative ne connaît jamais Playwright directement - elle
dépend uniquement de ce contrat. L'adaptateur Playwright réel (couche
infrastructure) sera introduit dans un cycle ultérieur, une fois la
logique d'orchestration validée par des tests rapides et déterministes.
"""

from typing import Protocol


class BrowserPort(Protocol):
    async def extract_fields(self, url: str, selectors: dict[str, str]) -> dict[str, str]:
        """Extrait les champs demandés depuis la page à `url`.

        `selectors` associe un nom de champ à son sélecteur CSS/XPath. Seuls
        les champs pour lesquels un sélecteur est fourni peuvent apparaître
        dans le résultat - un champ absent des `selectors` ne sera jamais
        recherché.
        """
        ...

    async def capture_screenshot(self, url: str) -> bytes:
        """Capture une image PNG de la page à `url`, utilisée par le
        Recovery Engine pour l'analyse visuelle (Claude Computer Use)."""
        ...
