from __future__ import annotations

import json
from typing import Any

from app.config import Settings
from app.service.ai.prompts import MODE_HINT, SYSTEM_CORE


def fake_explain(mode: str, topic: str, query: str, excerpts: list[dict]) -> dict:
    if not excerpts:
        return {
            "markdown": "Slide không đề cập nội dung này trong kho bài giảng hiện tại.",
            "citations": [],
        }
    top = excerpts[0]
    page = top.get("slide_page") or "?"
    lec = top.get("lecture_id") or "lecture"
    body = (top.get("text") or "").strip()
    cite = {"chunk_id": top.get("chunk_id"), "slide_page": page, "lecture_id": lec}
    tag = f"[slide:{page}|{lec}]"
    if mode == "eli5":
        md = (
            f"Hãy tưởng tượng thư viện quá lớn để nhớ hết sách — RAG là cách AI "
            f"**đi tìm đúng trang** rồi mới trả lời, thay vì đoán từ trí nhớ.\n\n"
            f"Trên slide {page}: {body[:180]}\n\n{tag}"
        )
        if topic in ("self_attention", "attention"):
            md = (
                f"Hãy tưởng tượng tìm sách trong thư viện: nhãn trên gáy là **Key**, "
                f"cuốn đang tìm là **Query**, nội dung trong sách là **Value**. "
                f"Self-attention là cách mỗi từ nhìn các từ khác cùng lúc để biết lấy thông tin từ đâu.\n\n"
                f"Trên slide {page}: {body[:180]}\n\n{tag}"
            )
        elif topic == "docker":
            md = (
                f"Hãy tưởng tượng hộp cơm (container) bị vứt mỗi khi hết buổi — "
                f"**volume** là ngăn tủ bên ngoài để thức ăn không mất.\n\n"
                f"Trên slide {page}: {body[:180]}\n\n{tag}"
            )
    elif mode == "slide_short":
        md = (
            f"Trên slide {page}, {topic.upper()} nghĩa là: {body[:220]}\n\n"
            f"Ví dụ lấy từ slide: hệ thống retrieve top-k đoạn rồi nhồi vào prompt.\n\n{tag}"
        )
    else:
        md = (
            f"{body}\n\n"
            f"Cơ chế: embed câu hỏi → retrieve → generate. Trade-off: thêm độ trễ retrieve "
            f"để giảm hallucination so với LLM thuần.\n\n{tag}"
        )
    return {"markdown": md, "citations": [cite]}


class TutorEngine:
    """Gọi LLM (SpaceXAI / OpenAI-compatible) hoặc fallback template."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._openai = None
        key = settings.resolved_llm_key
        if key:
            from openai import AsyncOpenAI

            self._openai = AsyncOpenAI(
                api_key=key,
                base_url=settings.llm_base_url,
                timeout=settings.llm_timeout_seconds,
            )

    @property
    def live(self) -> bool:
        return self._openai is not None

    async def explain(
        self,
        *,
        mode: str,
        topic: str,
        query: str,
        excerpts: list[dict],
    ) -> dict[str, Any]:
        if not self.live:
            return fake_explain(mode, topic, query, excerpts)
        chunks_xml = "\n".join(
            f'<chunk id="{c.get("chunk_id")}" slide="{c.get("slide_page")}" '
            f'lecture="{c.get("lecture_id")}">{c.get("text")}</chunk>'
            for c in excerpts
        )
        user = (
            f"Topic: {topic}\nQuery: {query}\nMode: {mode}\n{MODE_HINT.get(mode, '')}\n"
            f"<lecture_excerpts>\n{chunks_xml}\n</lecture_excerpts>"
        )
        try:
            resp = await self._openai.chat.completions.create(
                model=self.settings.llm_model,
                messages=[
                    {"role": "system", "content": SYSTEM_CORE},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_object"},
            )
            data = json.loads(resp.choices[0].message.content or "{}")
            return {
                "markdown": data.get("markdown") or "",
                "citations": data.get("citations") or [],
            }
        except Exception:
            return fake_explain(mode, topic, query, excerpts)

    async def generate_probe(
        self,
        *,
        topic: str,
        query: str,
        history: str,
        excerpts: list[dict],
    ) -> dict | None:
        if not self.live:
            return None
        excerpt = (excerpts[0].get("text") if excerpts else "") or ""
        user = (
            f"Topic: {topic}\nOriginal question: {query}\nRecent chat:\n{history[:1200]}\n"
            f"Excerpt: {excerpt[:400]}\n"
            "Hãy đặt ĐÚNG 1 câu hỏi thăm dò trình độ (tiếng Việt) với 3 lựa chọn a/b/c "
            "maps_to_level beginner|intermediate|advanced. JSON: "
            '{"question":"...","choices":[{"id":"a","text":"...","maps_to_level":"beginner"},'
            '{"id":"b","text":"...","maps_to_level":"intermediate"},'
            '{"id":"c","text":"...","maps_to_level":"advanced"}]}'
        )
        try:
            resp = await self._openai.chat.completions.create(
                model=self.settings.llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": "Bạn là Assessor. Chỉ JSON, không markdown. Không giải thích khái niệm.",
                    },
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_object"},
            )
            data = json.loads(resp.choices[0].message.content or "{}")
            choices = data.get("choices") or []
            if not data.get("question") or len(choices) < 3:
                return None
            return {"question": data["question"], "choices": choices[:3]}
        except Exception:
            return None

    async def aclose(self) -> None:
        if self._openai is not None:
            await self._openai.close()
            self._openai = None
