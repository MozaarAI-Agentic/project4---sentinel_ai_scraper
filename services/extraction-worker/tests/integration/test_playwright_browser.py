"""Test d'intégration de PlaywrightBrowser contre un vrai navigateur Chromium.

Ce test navigue vers une fixture HTML locale (file://) plutôt qu'un site
distant, pour rester rapide et reproductible - cohérent avec la stratégie
de fixtures définie en Phase 1/2 (books.toscrape, quotes.toscrape, et une
fixture "broken-dom" contrôlée).

Ce test est marqué `skip` automatiquement si le binaire Chromium n'est pas
installé (`playwright install chromium`) - c'est le cas dans certains
environnements sandbox restreints en réseau. Il s'exécute normalement en
développement local et doit être exécuté en CI (GitHub Actions installe
Chromium comme étape dédiée, voir Phase 12 - Deployment).
"""

from pathlib import Path

import pytest
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import async_playwright

from extraction_worker.infrastructure.playwright_browser import PlaywrightBrowser

_FIXTURE_PATH = (
    Path(__file__).parents[4] / "fixtures" / "demo-sites" / "static-site" / "book_page.html"
)


async def _chromium_is_installed() -> bool:
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            await browser.close()
        return True
    except PlaywrightError:
        return False


@pytest.fixture
async def skip_if_no_chromium() -> None:
    if not await _chromium_is_installed():
        pytest.skip(
            "Chromium non installé dans cet environnement - exécuter "
            "`playwright install chromium` pour lancer ce test localement ou en CI."
        )


class TestPlaywrightBrowserExtractFields:
    async def test_extracts_fields_from_a_real_local_page(self, skip_if_no_chromium: None) -> None:
        browser = PlaywrightBrowser(headless=True)

        result = await browser.extract_fields(
            url=f"file://{_FIXTURE_PATH}",
            selectors={"title": "h1.title", "price": "span.price"},
        )

        assert result == {"title": "Clean Code", "price": "29.99"}

    async def test_omits_fields_with_a_selector_that_matches_nothing(
        self, skip_if_no_chromium: None
    ) -> None:
        browser = PlaywrightBrowser(headless=True)

        result = await browser.extract_fields(
            url=f"file://{_FIXTURE_PATH}",
            selectors={"title": "h1.title", "author": ".nonexistent-selector"},
        )

        assert result == {"title": "Clean Code"}
        assert "author" not in result
