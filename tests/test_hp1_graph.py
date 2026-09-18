from uuid import uuid4

import pytest

from app.service.container import build_container


@pytest.fixture
def harness():
    return build_container()


@pytest.mark.asyncio
async def test_hp1_dump_then_probe_then_beginner(harness):
    c = harness
    conv = uuid4()
    user = await c.repository.upsert_user("hv-01")
    await c.repository.insert_conversation(conv, user.id, "t")

    r1 = await c.graph.ainvoke(
        {
            "user_id": "hv-01",
            "session_id": "t",
            "conversation_id": str(conv),
            "client_turn_id": str(uuid4()),
            "turn_id": str(uuid4()),
            "user_message": "RAG là gì?",
            "highlighted_text": "RAG",
            "context_lecture_id": "k4-week3-rag",
            "context_slide_page": 12,
        },
        config={"configurable": {"thread_id": str(conv)}},
    )
    assert r1["response_kind"] == "explanation"
    assert r1.get("explanation_mode") == "technical"

    r2 = await c.graph.ainvoke(
        {
            "user_id": "hv-01",
            "session_id": "t",
            "conversation_id": str(conv),
            "client_turn_id": str(uuid4()),
            "turn_id": str(uuid4()),
            "user_message": "khó hiểu quá",
            "context_lecture_id": "k4-week3-rag",
        },
        config={"configurable": {"thread_id": str(conv)}},
    )
    assert r2["response_kind"] == "probe"
    assert r2.get("probe_choices")

    r3 = await c.graph.ainvoke(
        {
            "user_id": "hv-01",
            "session_id": "t",
            "conversation_id": str(conv),
            "client_turn_id": str(uuid4()),
            "turn_id": str(uuid4()),
            "user_message": "Mình mới học code",
            "context_lecture_id": "k4-week3-rag",
        },
        config={"configurable": {"thread_id": str(conv)}},
    )
    assert r3["response_kind"] == "explanation"
    assert r3["user_level"] == "beginner"
    assert r3["explanation_mode"] == "eli5"
    await c.aclose()
