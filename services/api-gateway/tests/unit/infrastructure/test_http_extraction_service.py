"""Tests de HttpExtractionService.

Utilise httpx.MockTransport pour intercepter les requêtes au niveau
transport - aucun socket réseau réel n'est ouvert. C'est un test de contrat :
il vérifie que l'adaptateur sérialise correctement la requête et interprète
correctement la réponse (ou son absence), sans dépendre d'un vrai Extraction
Worker démarré.
"""

import json

import httpx

from api_gateway.infrastructure.http_extraction_service import HttpExtractionService
from sentinel_shared.enums import FailureReason


class TestHttpExtractionServiceSuccess:
    async def test_returns_success_result_from_worker_response(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json={"success": True, "data": {"title": "Clean Code"}, "failure_reason": None}
            )

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        service = HttpExtractionService(client=client, base_url="http://extraction-worker")

        result = await service.extract(
            url="https://books.example/1", domain="books.example", required_fields=["title"]
        )

        assert result.success is True
        assert result.data == {"title": "Clean Code"}
        assert result.failure_reason is None

    async def test_sends_the_correct_request_payload_to_the_worker(self) -> None:
        captured_requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured_requests.append(request)
            return httpx.Response(200, json={"success": True, "data": {}, "failure_reason": None})

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        service = HttpExtractionService(client=client, base_url="http://extraction-worker")

        await service.extract(
            url="https://books.example/1", domain="books.example", required_fields=["title", "price"]
        )

        assert len(captured_requests) == 1
        payload = json.loads(captured_requests[0].content)
        assert payload == {
            "url": "https://books.example/1",
            "domain": "books.example",
            "required_fields": ["title", "price"],
        }
        assert str(captured_requests[0].url) == "http://extraction-worker/internal/extract"


class TestHttpExtractionServiceFailureReason:
    async def test_returns_failure_result_with_reason_from_worker_response(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={"success": False, "data": {}, "failure_reason": "missing_required_field"},
            )

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        service = HttpExtractionService(client=client, base_url="http://extraction-worker")

        result = await service.extract(
            url="https://books.example/1", domain="books.example", required_fields=["price"]
        )

        assert result.success is False
        assert result.failure_reason == FailureReason.MISSING_REQUIRED_FIELD


class TestHttpExtractionServiceContractViolation:
    async def test_returns_http_error_when_worker_sends_an_unknown_failure_reason(self) -> None:
        """Un contrat rompu entre services (le Worker envoie une valeur que
        l'API Gateway ne reconnaît pas - ex: déploiement désynchronisé) doit
        être traité comme un échec d'infrastructure, jamais comme une
        exception non gérée qui ferait planter la requête."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={"success": False, "data": {}, "failure_reason": "some_future_reason_unknown_here"},
            )

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        service = HttpExtractionService(client=client, base_url="http://extraction-worker")

        result = await service.extract(
            url="https://books.example/1", domain="books.example", required_fields=["price"]
        )

        assert result.success is False
        assert result.failure_reason == FailureReason.HTTP_ERROR


class TestHttpExtractionServiceUnreachableWorker:
    async def test_returns_http_error_failure_when_worker_is_unreachable(self) -> None:
        """Le Worker injoignable est un échec d'infrastructure, jamais une
        exception qui remonte brute - et jamais un déclencheur de recovery IA
        (RecoveryDecisionPolicy rejette HTTP_ERROR, voir Cycle 4)."""

        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection refused", request=request)

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        service = HttpExtractionService(client=client, base_url="http://extraction-worker")

        result = await service.extract(
            url="https://books.example/1", domain="books.example", required_fields=["title"]
        )

        assert result.success is False
        assert result.failure_reason == FailureReason.HTTP_ERROR
