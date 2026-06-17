"""Tests de HttpWorkerService.

Même approche qu'au Cycle 6 (HttpExtractionService côté API Gateway) :
httpx.MockTransport intercepte au niveau transport, aucune dépendance
réseau réelle.
"""

import json

import httpx

from recovery_engine.infrastructure.http_worker_service import HttpWorkerService
from sentinel_shared.enums import FailureReason


class TestCaptureScreenshot:
    async def test_returns_the_base64_screenshot_from_the_worker_response(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert str(request.url) == "http://extraction-worker/internal/screenshot"
            return httpx.Response(200, json={"screenshot_base64": "aGVsbG8="})

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        service = HttpWorkerService(client=client, base_url="http://extraction-worker")

        result = await service.capture_screenshot(url="https://books.example/1")

        assert result == "aGVsbG8="

    async def test_sends_the_url_in_the_request_body(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"screenshot_base64": "x"})

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        service = HttpWorkerService(client=client, base_url="http://extraction-worker")

        await service.capture_screenshot(url="https://books.example/1")

        assert json.loads(captured[0].content) == {"url": "https://books.example/1"}


class TestValidateSelectors:
    async def test_returns_success_result_when_worker_confirms_extraction(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert str(request.url) == "http://extraction-worker/internal/extract"
            return httpx.Response(
                200, json={"success": True, "data": {"title": "Clean Code"}, "failure_reason": None}
            )

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        service = HttpWorkerService(client=client, base_url="http://extraction-worker")

        result = await service.validate_selectors(
            url="https://books.example/1",
            domain="books.example",
            required_fields=["title"],
            selectors={"title": "h1.title"},
        )

        assert result.success is True
        assert result.data == {"title": "Clean Code"}

    async def test_sends_the_candidate_selectors_as_override(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"success": True, "data": {}, "failure_reason": None})

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        service = HttpWorkerService(client=client, base_url="http://extraction-worker")

        await service.validate_selectors(
            url="https://books.example/1",
            domain="books.example",
            required_fields=["title"],
            selectors={"title": "h1.title"},
        )

        payload = json.loads(captured[0].content)
        assert payload["selectors"] == {"title": "h1.title"}

    async def test_returns_failure_result_with_reason_when_worker_rejects(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json={"success": False, "data": {}, "failure_reason": "empty_required_field"}
            )

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        service = HttpWorkerService(client=client, base_url="http://extraction-worker")

        result = await service.validate_selectors(
            url="https://books.example/1",
            domain="books.example",
            required_fields=["title"],
            selectors={"title": ".wrong-selector"},
        )

        assert result.success is False
        assert result.failure_reason == FailureReason.EMPTY_REQUIRED_FIELD

    async def test_returns_http_error_when_worker_sends_an_unknown_failure_reason(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json={"success": False, "data": {}, "failure_reason": "some_future_reason"}
            )

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        service = HttpWorkerService(client=client, base_url="http://extraction-worker")

        result = await service.validate_selectors(
            url="https://books.example/1",
            domain="books.example",
            required_fields=["title"],
            selectors={"title": ".wrong-selector"},
        )

        assert result.success is False
        assert result.failure_reason == FailureReason.HTTP_ERROR


class TestSaveApprovedSelector:
    async def test_sends_the_selector_with_ai_generated_source(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            assert str(request.url) == "http://extraction-worker/internal/selectors"
            return httpx.Response(201)

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        service = HttpWorkerService(client=client, base_url="http://extraction-worker")

        await service.save_approved_selector(
            domain="books.example", field_name="title", selector_value="h1.title"
        )

        payload = json.loads(captured[0].content)
        assert payload == {
            "domain": "books.example",
            "field_name": "title",
            "selector_value": "h1.title",
            "source": "ai_generated",
        }
