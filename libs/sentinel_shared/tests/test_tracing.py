"""Tests de sentinel_shared.observability.tracing.

Un exporter en mémoire (InMemorySpanExporter) est injecté pour les tests -
en production, ConsoleSpanExporter est utilisé par défaut faute de
collecteur Jaeger/Tempo déployé dans ce MVP (voir ROADMAP.md).
"""

import opentelemetry.trace as otel_trace
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from sentinel_shared.observability.tracing import (
    extract_trace_context,
    inject_trace_context,
    setup_tracing,
)


class TestSetupTracingCreatesSpans:
    def test_a_created_span_is_captured_by_the_injected_exporter(self) -> None:
        exporter = InMemorySpanExporter()
        tracer = setup_tracing(service_name="test-service", exporter=exporter)

        with tracer.start_as_current_span("test-span"):
            pass
        otel_trace.get_tracer_provider().force_flush()  # type: ignore[union-attr]

        finished_spans = exporter.get_finished_spans()
        assert len(finished_spans) == 1
        assert finished_spans[0].name == "test-span"


class TestTraceContextPropagation:
    def test_extracted_context_preserves_the_original_trace_id(self) -> None:
        """C'est le mécanisme central de la propagation à travers Redis
        Streams (Cycle 17) : un contexte injecté puis extrait doit
        permettre de continuer la MÊME trace, pas d'en démarrer une
        nouvelle."""
        exporter = InMemorySpanExporter()
        tracer = setup_tracing(service_name="test-producer", exporter=exporter)

        with tracer.start_as_current_span("produce") as producer_span:
            original_trace_id = producer_span.get_span_context().trace_id
            carrier = inject_trace_context()

        extracted_context = extract_trace_context(carrier)
        with tracer.start_as_current_span("consume", context=extracted_context) as consumer_span:
            consumer_trace_id = consumer_span.get_span_context().trace_id

        assert consumer_trace_id == original_trace_id
