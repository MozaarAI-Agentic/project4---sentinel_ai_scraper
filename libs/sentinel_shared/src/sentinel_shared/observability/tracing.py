"""Configuration OpenTelemetry partagée entre les 3 microservices.

Comme pour metrics.py, chaque processus a son propre TracerProvider - ce
module partage la configuration et les fonctions de propagation, pas une
instance. `inject_trace_context`/`extract_trace_context` sont le mécanisme
central de la propagation à travers la queue Redis Streams (Cycle 17) :
un simple header HTTP ne suffit pas puisqu'il n'y a pas de requête HTTP
entre l'enqueue (API Gateway) et la consommation (Recovery Engine) - le
contexte doit voyager DANS le message lui-même.
"""

from opentelemetry import propagate, trace
from opentelemetry.context import Context
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SpanExporter


def setup_tracing(service_name: str, exporter: SpanExporter | None = None) -> trace.Tracer:
    """Configure le TracerProvider global de ce processus et retourne un
    tracer nommé. `exporter` est injectable pour les tests (ex:
    InMemorySpanExporter) - en production, ConsoleSpanExporter par défaut,
    faute de collecteur Jaeger/Tempo déployé dans ce MVP (voir
    ROADMAP.md pour la migration vers un exporter OTLP réel).
    """
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    provider.add_span_processor(BatchSpanProcessor(exporter or ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)


def inject_trace_context() -> dict[str, str]:
    """Capture le contexte de trace actif dans un dict sérialisable -
    destiné à être inclus comme champ supplémentaire d'un message Redis
    Stream (XADD), pas seulement un header HTTP."""
    carrier: dict[str, str] = {}
    propagate.inject(carrier)
    return carrier


def extract_trace_context(carrier: dict[str, str]) -> Context:
    """Reconstruit un contexte de trace à partir d'un carrier extrait d'un
    message Redis Stream - permet au consommateur de continuer la même
    trace que celle du producteur, plutôt que d'en démarrer une nouvelle
    sans lien avec la requête HTTP d'origine."""
    return propagate.extract(carrier)
