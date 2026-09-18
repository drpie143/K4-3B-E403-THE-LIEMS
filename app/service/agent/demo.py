"""CLI happy-path dump-first: python -m app.service.agent.demo"""

from __future__ import annotations

import asyncio
from uuid import uuid4

from app.service.container import build_container


async def _turn(container, user, session, conv, message, highlight=None):
    client = uuid4()
    turn = uuid4()
    if await container.repository.get_conversation(conv) is None:
        user_row = await container.repository.upsert_user(user)
        await container.repository.insert_conversation(conv, user_row.id, session)
    return await container.graph.ainvoke(
        {
            "user_id": user,
            "session_id": session,
            "conversation_id": str(conv),
            "client_turn_id": str(client),
            "turn_id": str(turn),
            "user_message": message,
            "highlighted_text": highlight,
            "context_lecture_id": "k4-week3-rag",
            "context_slide_page": 12,
        },
        config={"configurable": {"thread_id": str(conv)}},
    )


async def main() -> None:
    container = build_container()
    conv = uuid4()
    user, session = "hv-01", "demo"

    print("=== 1. RAG là gì? → trả lời học thuật ===")
    r1 = await _turn(container, user, session, conv, "RAG là gì?", "RAG")
    print("kind:", r1.get("response_kind"), "| level:", r1.get("user_level"), "| mode:", r1.get("explanation_mode"))
    print(r1.get("final_answer"))

    print("\n=== 2. khó hiểu quá → probe ===")
    r2 = await _turn(container, user, session, conv, "khó hiểu quá")
    print("kind:", r2.get("response_kind"), "| level:", r2.get("user_level"))
    print(r2.get("final_answer"))
    if r2.get("probe_choices"):
        for c in r2["probe_choices"]:
            print(f"  [{c['id']}] {c['text']}")

    print("\n=== 3. Mình mới học code → beginner ELI5 ===")
    r3 = await _turn(container, user, session, conv, "Mình mới học code")
    print("kind:", r3.get("response_kind"), "| level:", r3.get("user_level"), "| mode:", r3.get("explanation_mode"))
    print(r3.get("final_answer"))
    await container.aclose()


if __name__ == "__main__":
    asyncio.run(main())
