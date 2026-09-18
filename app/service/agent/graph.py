from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.service.agent import nodes as N
from app.service.agent.routing import route_after_intent, route_after_validator
from app.service.agent.state import AgentState, RouteKey


NODE_IMPL = {
    "ingest": N.ingest,
    "load_profile": N.load_profile,
    "regex_prepass": N.regex_prepass,
    "retrieve": N.retrieve,
    "intent_router": N.intent_router,
    "assessor_probe": N.assessor_probe,
    "assessor_score": N.assessor_score,
    "persist_level": N.persist_level,
    "tutor_adaptive": N.tutor_adaptive,
    "tutor_standard": N.tutor_standard,
    "validator": N.validator,
    "persist_turn": N.persist_turn,
    "tutor_redirect": N.tutor_redirect,
    "retrieval_miss": N.retrieval_miss,
}


def _route(state: AgentState) -> RouteKey:
    flags = {
        "DUMP_FIRST": bool(state.get("flags_dump_first")),
        "ADAPTIVE_PROBES": bool(state.get("flags_adaptive_probes", True)),
    }
    return route_after_intent(state, flags)


def build_graph(checkpointer=None):
    g = StateGraph(AgentState)
    for name, fn in NODE_IMPL.items():
        g.add_node(name, fn)
    g.set_entry_point("ingest")
    g.add_edge("ingest", "load_profile")
    g.add_edge("load_profile", "regex_prepass")
    g.add_edge("regex_prepass", "retrieve")
    g.add_edge("retrieve", "intent_router")
    g.add_conditional_edges(
        "intent_router",
        _route,
        {
            "probe": "assessor_probe",
            "score": "assessor_score",
            "persist_then_adapt": "persist_level",
            "adapt": "tutor_adaptive",
            "standard": "tutor_standard",
            "redirect": "tutor_redirect",
            "miss": "retrieval_miss",
        },
    )
    g.add_edge("assessor_probe", "persist_turn")
    g.add_edge("assessor_score", "persist_level")
    g.add_edge("persist_level", "tutor_adaptive")
    g.add_edge("tutor_adaptive", "validator")
    g.add_edge("tutor_standard", "validator")
    g.add_conditional_edges(
        "validator",
        route_after_validator,
        {
            "rewrite_adaptive": "tutor_adaptive",
            "rewrite_standard": "tutor_standard",
            "done": "persist_turn",
        },
    )
    g.add_edge("tutor_redirect", "persist_turn")
    g.add_edge("retrieval_miss", "persist_turn")
    g.add_edge("persist_turn", END)
    return g.compile(checkpointer=checkpointer or MemorySaver())
