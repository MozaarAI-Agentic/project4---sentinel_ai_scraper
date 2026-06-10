"""Double de test pour BrowserPort.

Simule un navigateur de façon réaliste : il ne retourne un champ que si un
sélecteur a été fourni pour celui-ci ET que ce champ existe dans les données
"canned" (représentant la page réelle). Ça permet de tester les cas de
sélecteur manquant sans navigateur réel. L'adaptateur Playwright de
production suit le même contrat (BrowserPort) et arrive dans un cycle
ultérieur.
"""


class FakeBrowser:
    def __init__(self, canned_response: dict[str, str], canned_screenshot: bytes = b"fake-png-bytes") -> None:
        self._canned_response = canned_response
        self._canned_screenshot = canned_screenshot
        self.last_call_url: str | None = None
        self.last_call_selectors: dict[str, str] | None = None

    async def extract_fields(self, url: str, selectors: dict[str, str]) -> dict[str, str]:
        self.last_call_url = url
        self.last_call_selectors = selectors

        return {
            field_name: self._canned_response[field_name]
            for field_name in selectors
            if field_name in self._canned_response
        }

    async def capture_screenshot(self, url: str) -> bytes:
        self.last_call_url = url
        return self._canned_screenshot
