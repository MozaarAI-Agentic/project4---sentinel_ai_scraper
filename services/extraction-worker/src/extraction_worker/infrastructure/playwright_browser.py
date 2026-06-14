"""Adaptateur infrastructure : implémentation réelle de BrowserPort via Playwright.

C'est le moteur d'exécution déterministe primaire du système (voir ADR-0001,
architecture deterministic-first) : navigation, résolution de sélecteurs,
extraction de texte - jamais d'IA à cette étape.

Un navigateur Chromium est lancé et fermé à chaque appel plutôt que réutilisé
entre requêtes. C'est un choix simple assumé pour le MVP : la réutilisation
d'un pool de navigateurs (via un `BrowserPoolManager`) est une optimisation
de performance identifiée mais non prématurément implémentée (YAGNI) tant
que la latence réelle n'est pas mesurée en charge.
"""

from playwright.async_api import Page, async_playwright


class PlaywrightBrowser:
    def __init__(self, headless: bool = True, navigation_timeout_ms: int = 15_000) -> None:
        self._headless = headless
        self._navigation_timeout_ms = navigation_timeout_ms

    async def extract_fields(self, url: str, selectors: dict[str, str]) -> dict[str, str]:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=self._headless)
            try:
                page = await browser.new_page()
                await page.goto(
                    url, wait_until="domcontentloaded", timeout=self._navigation_timeout_ms
                )
                return await self._extract_with_selectors(page, selectors)
            finally:
                await browser.close()

    async def capture_screenshot(self, url: str) -> bytes:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=self._headless)
            try:
                page = await browser.new_page()
                await page.goto(
                    url, wait_until="domcontentloaded", timeout=self._navigation_timeout_ms
                )
                return await page.screenshot(type="png")
            finally:
                await browser.close()

    @staticmethod
    async def _extract_with_selectors(page: Page, selectors: dict[str, str]) -> dict[str, str]:
        extracted: dict[str, str] = {}
        for field_name, selector in selectors.items():
            locator = page.locator(selector).first
            if await locator.count() == 0:
                continue  # champ absent -> ExtractionValidator le signalera comme manquant
            text_content = await locator.text_content()
            extracted[field_name] = (text_content or "").strip()
        return extracted
