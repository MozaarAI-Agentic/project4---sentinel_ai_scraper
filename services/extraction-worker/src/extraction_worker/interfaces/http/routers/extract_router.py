"""Routeur HTTP pour /internal/extract et /internal/screenshot.

Même discipline que le routeur de l'API Gateway (Cycle 8) : aucune logique
métier ici, seulement la traduction requête/réponse.
"""

import base64

from fastapi import APIRouter, Depends

from extraction_worker.application.use_cases.extract_data_use_case import ExtractDataUseCase
from extraction_worker.domain.ports.browser_port import BrowserPort
from extraction_worker.domain.ports.selector_repository_port import SelectorRepositoryPort
from extraction_worker.domain.selector import Selector, SelectorSource
from extraction_worker.interfaces.http.dependencies import get_browser, get_selector_repository
from extraction_worker.interfaces.http.schemas import (
    ExtractRequestBody,
    ExtractResponseBody,
    SaveSelectorRequestBody,
    ScreenshotRequestBody,
    ScreenshotResponseBody,
)

router = APIRouter(tags=["extraction"])


@router.post("/internal/extract", response_model=ExtractResponseBody)
async def extract(
    body: ExtractRequestBody,
    browser: BrowserPort = Depends(get_browser),
    selector_repository: SelectorRepositoryPort = Depends(get_selector_repository),
) -> ExtractResponseBody:
    use_case = ExtractDataUseCase(browser=browser, selector_repository=selector_repository)

    result = await use_case.execute(
        url=body.url,
        domain=body.domain,
        required_fields=body.required_fields,
        candidate_selectors=body.selectors,
    )

    return ExtractResponseBody.from_attempt_result(result)


@router.post("/internal/screenshot", response_model=ScreenshotResponseBody)
async def screenshot(
    body: ScreenshotRequestBody,
    browser: BrowserPort = Depends(get_browser),
) -> ScreenshotResponseBody:
    raw_png = await browser.capture_screenshot(body.url)
    return ScreenshotResponseBody(screenshot_base64=base64.b64encode(raw_png).decode("ascii"))


@router.post("/internal/selectors", status_code=201)
async def save_selector(
    body: SaveSelectorRequestBody,
    selector_repository: SelectorRepositoryPort = Depends(get_selector_repository),
) -> None:
    source: SelectorSource = "ai_generated" if body.source == "ai_generated" else "manual"
    await selector_repository.save_selector(
        Selector(
            domain=body.domain,
            field_name=body.field_name,
            selector_value=body.selector_value,
            source=source,
        )
    )
