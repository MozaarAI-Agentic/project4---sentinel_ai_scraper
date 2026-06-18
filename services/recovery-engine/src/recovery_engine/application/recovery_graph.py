"""Assemblage du graphe LangGraph du Recovery Engine.

Chaque nœud a été testé isolément (Cycles 12-15) comme une fonction pure -
ce module se contente de les câbler ensemble. C'est délibéré : si un bug
apparaît, on sait déjà que la logique de chaque nœud est correcte, donc le
problème ne peut venir que du câblage (routage, noms de nœuds) - un espace
de recherche de bug considérablement réduit.
"""

from functools import partial
from typing import cast

from langgraph.graph import END, StateGraph

from recovery_engine.application.compiled_graph_port import CompiledRecoveryGraph
from recovery_engine.application.nodes.analyze_and_propose import analyze_and_propose
from recovery_engine.application.nodes.capture_screenshot import capture_screenshot
from recovery_engine.application.nodes.decide_next_step import decide_next_step
from recovery_engine.application.nodes.escalate_human import escalate_human
from recovery_engine.application.nodes.handle_no_confident_proposal import (
    handle_no_confident_proposal,
)
from recovery_engine.application.nodes.persist_selector import persist_selector
from recovery_engine.application.nodes.validate_selectors_live import validate_selectors_live
from recovery_engine.application.recovery_state import RecoveryState
from recovery_engine.domain.ports.recovery_engine_port import RecoveryEnginePort
from recovery_engine.domain.ports.worker_service_port import WorkerServicePort


def _route_after_proposal(state: RecoveryState) -> str:
    """Une proposition non confiante ne peut pas être testée en live
    (validate_selectors_live suppose des sélecteurs non-None) - elle est
    traitée comme un rejet immédiat via handle_no_confident_proposal."""
    if state["proposed_selectors"] is None:
        return "handle_no_confident_proposal"
    return "validate_selectors_live"


def build_recovery_graph(
    recovery_engine: RecoveryEnginePort, worker_service: WorkerServicePort
) -> CompiledRecoveryGraph:
    """Construit et compile le graphe. Les dépendances (mock ou réelles)
    sont injectées ici, jamais résolues à l'intérieur des nœuds - cohérent
    avec le Port/Adapter appliqué depuis le Cycle 2."""
    graph = StateGraph(RecoveryState)

    graph.add_node("capture_screenshot", partial(capture_screenshot, worker_service=worker_service))
    graph.add_node(
        "analyze_and_propose", partial(analyze_and_propose, recovery_engine=recovery_engine)
    )
    graph.add_node(
        "validate_selectors_live",
        partial(validate_selectors_live, worker_service=worker_service),
    )
    graph.add_node("handle_no_confident_proposal", handle_no_confident_proposal)
    graph.add_node("persist_selector", partial(persist_selector, worker_service=worker_service))
    graph.add_node("escalate_human", escalate_human)

    graph.set_entry_point("capture_screenshot")
    graph.add_edge("capture_screenshot", "analyze_and_propose")
    graph.add_conditional_edges(
        "analyze_and_propose",
        _route_after_proposal,
        {
            "validate_selectors_live": "validate_selectors_live",
            "handle_no_confident_proposal": "handle_no_confident_proposal",
        },
    )
    graph.add_conditional_edges(
        "validate_selectors_live",
        decide_next_step,
        {
            "persist_selector": "persist_selector",
            "analyze_and_propose": "analyze_and_propose",
            "escalate_human": "escalate_human",
        },
    )
    graph.add_conditional_edges(
        "handle_no_confident_proposal",
        decide_next_step,
        {
            "persist_selector": "persist_selector",
            "analyze_and_propose": "analyze_and_propose",
            "escalate_human": "escalate_human",
        },
    )
    graph.add_edge("persist_selector", END)
    graph.add_edge("escalate_human", END)

    # graph.compile() retourne un CompiledStateGraph dont les surcharges
    # de ainvoke() sont bien plus riches que notre CompiledRecoveryGraph
    # (streaming, checkpointing, versions...). Le comportement réel avec un
    # seul argument positionnel est déjà prouvé par les tests d'intégration
    # du graphe (Cycle 15) - ce cast documente l'écart de typage plutôt que
    # d'élargir notre Protocol à toute la surface de LangGraph pour un
    # bénéfice nul ici.
    return cast(CompiledRecoveryGraph, graph.compile())
