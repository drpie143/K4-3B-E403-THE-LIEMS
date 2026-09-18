from app.service.agent.routing import regex_prepass, select_retrieval_query


def test_abandon_does_not_reuse_rag_query():
    state = {
        "awaiting_probe_answer": True,
        "last_kind": "probe",
        "pending_original_query": "RAG là gì?",
        "last_retrieval_query": "RAG là gì?",
        "user_message": "Docker volume là gì?",
        "highlighted_text": "Docker volume",
    }
    out = regex_prepass(state)
    state = {**state, **out}
    q = select_retrieval_query(state)
    assert state["regex_intent"] == "ask_concept"
    assert q is not None and "docker" in q.lower()
    assert "rag" not in q.lower()


def test_probe_answer_reuses_pending():
    state = {
        "awaiting_probe_answer": True,
        "last_kind": "probe",
        "pending_original_query": "RAG là gì?",
        "user_message": "Mình mới học code",
    }
    out = regex_prepass(state)
    state = {**state, **out}
    assert state["regex_intent"] == "answer_probe"
    q = select_retrieval_query(state)
    assert q == "RAG là gì?"
