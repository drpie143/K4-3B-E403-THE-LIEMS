from __future__ import annotations

from uuid import UUID, uuid4

from langchain_core.messages import AIMessage, HumanMessage

from app.service.agent.assessor import get_probe_template, score_probe_answer
from app.service.agent.intent import (
    is_ambiguous_detail,
    is_length_only,
    resolve_ambiguous_detail,
)
from app.service.agent.routing import (
    apply_abandon_if_needed,
    apply_delta,
    assign_explain_persona,
    next_cooldown,
    regex_prepass as regex_prepass_fn,
    select_retrieval_query,
)
from app.service.agent.runtime import get_runtime
from app.service.agent.state import TURN_RESET_DEFAULTS, AgentState, UserLevel
from app.service.agent.topics import resolve_topic_key
from app.config import get_settings
from app.model.entities import MessageRow


async def ingest(state: AgentState) -> dict:
    settings = get_settings()
    idx = int(state.get("turn_index") or 0) + 1
    msg = (state.get("user_message") or "").strip()
    hi = (state.get("highlighted_text") or "").strip()
    if not msg and hi:
        msg = hi
    out = dict(TURN_RESET_DEFAULTS)
    out.update(
        {
            "turn_index": idx,
            "user_message": msg,
            "flags_dump_first": settings.dump_first,
            "flags_adaptive_probes": settings.adaptive_probes,
            "messages": [HumanMessage(content=msg)],
            "validator_ok": True,
            "rewrite_count": 0,
            "llm_hops": 0,
            "proposed_level_delta": 0,
        }
    )
    return out


async def load_profile(state: AgentState) -> dict:
    rt = get_runtime()
    user = await rt.repository.upsert_user(state["user_id"])
    conv_id = UUID(state["conversation_id"])
    conv = await rt.repository.get_conversation(conv_id)
    skills = await rt.repository.skill_map(user.id)
    overlay: dict = {
        "user_pk": str(user.id),
        "default_level": user.default_level,
        "skill_map": skills,
    }
    if conv:
        last_topic = conv.pending_topic
        for m in reversed(await rt.repository.list_messages(conv.id)):
            if m.topic_key:
                last_topic = m.topic_key
                break
        overlay.update(
            {
                "awaiting_probe_answer": conv.awaiting_probe,
                "pending_original_query": conv.pending_original_query,
                "pending_topic": conv.pending_topic or last_topic,
                "current_topic": last_topic,
                "probe_asked_this_episode": conv.probe_asked_this_episode,
                "episode_id": str(conv.episode_id) if conv.episode_id else state.get("episode_id"),
                "last_kind": conv.last_kind,
                "last_assistant_mode": conv.last_explanation_mode,
                "last_assistant_sentence_count": conv.last_assistant_sentence_count,
                "last_retrieval_query": conv.last_retrieval_query,
                "last_retrieved_chunk_ids": [str(x) for x in conv.last_retrieved_chunk_ids],
                "turn_index": max(int(state.get("turn_index") or 0), conv.turn_index),
            }
        )
    return overlay


async def regex_prepass(state: AgentState) -> dict:
    return regex_prepass_fn(state)


async def retrieve(state: AgentState) -> dict:
    rt = get_runtime()
    q = select_retrieval_query(state)
    if q is None:
        return {
            "retrieval_skipped": True,
            "retrieved_docs": [],
            "retrieval_query": None,
        }
    last_q = state.get("last_retrieval_query")
    last_ids = state.get("last_retrieved_chunk_ids") or []
    if q == last_q and last_ids:
        docs = await rt.retriever.get_by_ids(last_ids)
        return {
            "retrieval_skipped": False,
            "retrieval_query": q,
            "retrieved_docs": docs,
        }
    docs = await rt.retriever.retrieve(
        q, k=6, lecture_id=state.get("context_lecture_id")
    )
    return {
        "retrieval_skipped": False,
        "retrieval_query": q,
        "retrieved_docs": docs,
    }


async def intent_router(state: AgentState) -> dict:
    apply_abandon_if_needed(state)
    ri = state.get("regex_intent")
    text = state.get("user_message") or ""
    intent = ri
    source = "regex"
    length_only = is_length_only(text)

    if is_ambiguous_detail(text) and ri in (None, "ask_concept"):
        intent = resolve_ambiguous_detail(
            state.get("last_kind"),
            state.get("last_assistant_mode"),
            int(state.get("last_assistant_sentence_count") or 0),
        )
        source = "forced"

    feedback = intent in ("answer_probe", "refuse_probe", "clarify_harder", "ask_deeper")
    if state.get("route_reason") == "abandon_probe_new_question":
        topic = resolve_topic_key(text, state.get("highlighted_text"))
    elif feedback:
        topic = (
            state.get("pending_topic")
            or state.get("current_topic")
            or resolve_topic_key(state.get("pending_original_query") or text, state.get("highlighted_text"))
        )
        if topic == "misc" and state.get("current_topic"):
            topic = state["current_topic"]
    else:
        topic = resolve_topic_key(text, state.get("highlighted_text"))

    skills = state.get("skill_map") or {}
    entry = skills.get(topic)
    user_level: UserLevel = entry["level"] if entry else "unknown"  # type: ignore[assignment]
    asked = bool(state.get("probe_asked_this_episode"))
    turn_index = int(state.get("turn_index") or 0)
    in_cd = bool(entry and turn_index < int(entry.get("cooldown_until_turn") or 0))

    if intent == "clarify_harder" and in_cd:
        asked = True

    delta = 0
    proposed: UserLevel | None = None
    mode = None
    P = bool(state.get("awaiting_probe_answer"))

    if intent == "refuse_probe" and P:
        proposed = "beginner"
    elif intent == "clarify_harder" and P:
        proposed = "beginner"
    elif intent == "clarify_harder" and asked and not length_only:
        delta = -1
        proposed = apply_delta(user_level, -1)
    elif intent == "clarify_harder" and length_only:
        proposed = None
        delta = 0
    elif intent == "ask_deeper":
        delta = 1
        proposed = apply_delta(user_level, 1)
    elif intent == "ask_concept" and not state.get("flags_adaptive_probes") and user_level == "unknown":
        proposed = "beginner"
        mode = "eli5"

    if proposed and proposed != "unknown":
        _, mode = assign_explain_persona(proposed)
    elif user_level != "unknown":
        _, mode = assign_explain_persona(user_level)

    return {
        "intent": intent,
        "intent_source": source,
        "intent_confidence": 0.9 if source == "regex" else 0.7,
        "length_only": length_only,
        "current_topic": topic,
        "user_level": user_level,
        "probe_consumed_for_topic": bool(entry and entry.get("probe_consumed")),
        "proposed_level_delta": delta,
        "proposed_level": proposed,
        "explanation_mode": mode,
        "probe_asked_this_episode": asked,
        "learning_bottleneck": intent == "clarify_harder" and not length_only,
        "pending_topic": topic if state.get("awaiting_probe_answer") or intent == "ask_concept" else state.get("pending_topic"),
    }


async def assessor_probe(state: AgentState) -> dict:
    rt = get_runtime()
    topic = state.get("current_topic") or "misc"
    tmpl = get_probe_template(topic)
    pending = (
        state.get("last_retrieval_query")
        or state.get("pending_original_query")
        or state.get("user_message")
    )
    if rt.settings.llm_probe and rt.ai.live:
        hist = []
        for m in state.get("messages") or []:
            content = getattr(m, "content", None) or (m.get("content") if isinstance(m, dict) else "")
            if content:
                hist.append(str(content)[:240])
        gen = await rt.ai.generate_probe(
            topic=topic,
            query=pending or "",
            history="\n".join(hist[-8:]),
            excerpts=state.get("retrieved_docs") or [],
        )
        if gen and gen.get("question") and gen.get("choices"):
            tmpl = gen
    return {
        "probe_question": tmpl["question"],
        "probe_choices": tmpl["choices"],
        "awaiting_probe_answer": True,
        "probe_asked_this_episode": True,
        "pending_original_query": pending,
        "pending_topic": topic,
        "episode_id": state.get("episode_id") or str(uuid4()),
        "response_kind": "probe",
        "final_answer": tmpl["question"],
        "route_reason": state.get("route_reason") or "diagnostic_probe",
        "messages": [AIMessage(content=tmpl["question"])],
        "llm_hops": int(state.get("llm_hops") or 0) + (1 if rt.ai.live and rt.settings.llm_probe else 0),
    }


async def assessor_score(state: AgentState) -> dict:
    rt = get_runtime()
    choices = state.get("probe_choices")
    if not choices:
        conv = await rt.repository.get_conversation(UUID(state["conversation_id"]))
        if conv:
            for m in reversed(await rt.repository.list_messages(conv.id)):
                if m.response_kind == "probe" and m.payload:
                    choices = m.payload.get("choices")
                    break
    result = score_probe_answer(state.get("user_message") or "", choices)
    level = result["level"]
    conf = float(result["confidence"])
    source = result["source"]
    if conf < 0.6:
        level = "beginner"
        source = "fallback_low_conf"
    mode = assign_explain_persona(level)[1]
    return {
        "proposed_level": level,
        "proposed_level_delta": 0,
        "user_level": level,
        "explanation_mode": mode,
        "probe_answer": state.get("user_message"),
        "route_reason": "score_probe",
        "intent_confidence": conf,
        "_score_source": source,
    }


async def persist_level(state: AgentState) -> dict:
    rt = get_runtime()
    topic = state.get("current_topic") or state.get("pending_topic") or "misc"
    user = await rt.repository.get_user(state["user_id"])
    assert user
    skills = dict(state.get("skill_map") or {})
    entry = skills.get(topic)
    turn_index = int(state.get("turn_index") or 0)
    intent = state.get("intent")
    explicit = intent in ("clarify_harder", "ask_deeper") and not state.get("length_only")
    in_cd = bool(entry and turn_index < int(entry.get("cooldown_until_turn") or 0))

    if (not explicit) and in_cd and entry:
        level = entry["level"]
        source = entry.get("source") or "assessor"
        cooldown = entry.get("cooldown_until_turn") or 0
        last_change = entry.get("last_level_change_turn") or 0
    else:
        level = state.get("proposed_level")
        if not level:
            level = apply_delta(state.get("user_level") or "unknown", int(state.get("proposed_level_delta") or 0))
        if level == "unknown":
            level = "beginner"
        source = "explicit_signal" if explicit else (state.get("intent") and "assessor") or "assessor"
        if state.get("intent") == "refuse_probe":
            source = "fallback_refuse"
            level = "beginner"
        if state.get("intent") == "answer_probe" and float(state.get("intent_confidence") or 1) < 0.6:
            source = "fallback_low_conf"
            level = "beginner"
        cooldown = next_cooldown(turn_index)
        last_change = turn_index

    from_level = entry["level"] if entry else "unknown"
    await rt.repository.upsert_skill(
        user.id,
        topic,
        level=level,
        confidence=float(state.get("intent_confidence") or 0.9),
        source=source,
        probe_consumed=True,
        last_level_change_turn=last_change,
        cooldown_until_turn=cooldown,
    )
    await rt.repository.add_level_event(
        {
            "id": str(uuid4()),
            "user_id": str(user.id),
            "conversation_id": state.get("conversation_id"),
            "topic_key": topic,
            "from_level": from_level,
            "to_level": level,
            "reason": source,
            "probe_question": state.get("probe_question"),
            "probe_answer": state.get("probe_answer") or state.get("user_message"),
            "confidence": float(state.get("intent_confidence") or 0),
        }
    )
    skills[topic] = {
        "level": level,
        "confidence": float(state.get("intent_confidence") or 0.9),
        "source": source,
        "probe_consumed": True,
        "cooldown_until_turn": cooldown,
        "last_level_change_turn": last_change,
    }
    _, mode = assign_explain_persona(level)  # type: ignore[arg-type]
    if state.get("length_only"):
        mode = state.get("explanation_mode") or mode
    return {
        "skill_map": skills,
        "user_level": level,
        "explanation_mode": mode,
        "probe_consumed_for_topic": True,
    }


async def generate_explanation(state: AgentState) -> dict:
    rt = get_runtime()
    updates: dict = {}
    if state.get("validator_ok") is False:
        updates["rewrite_count"] = int(state.get("rewrite_count") or 0) + 1
    level = state.get("user_level") or "unknown"
    mode = state.get("explanation_mode")
    if not mode:
        level, mode = assign_explain_persona(level)  # type: ignore[assignment]
        updates["user_level"] = level
        updates["explanation_mode"] = mode
    query = (
        state.get("pending_original_query")
        or state.get("retrieval_query")
        or state.get("user_message")
        or ""
    )
    docs = state.get("retrieved_docs") or []
    result = await rt.ai.explain(
        mode=mode,
        topic=state.get("current_topic") or "misc",
        query=query,
        excerpts=docs,
    )
    md = result["markdown"]
    cits = result.get("citations") or []
    if state.get("length_only"):
        sentences = [s.strip() for s in md.replace("!", ".").split(".") if s.strip()]
        md = ". ".join(sentences[:3]) + ("." if sentences else "")
    updates.update(
        {
            "draft_answer": md,
            "final_answer": md,
            "citations": cits,
            "response_kind": "explanation",
            "llm_hops": int(state.get("llm_hops") or 0) + (1 if rt.ai.live else 0),
            "last_assistant_sentence_count": max(1, md.count(".") + md.count("!") + md.count("?")),
            "messages": [AIMessage(content=md)],
            "route_reason": state.get("route_reason")
            or ("score_probe" if state.get("intent") == "answer_probe" else "adapt_known"),
        }
    )
    return updates


async def tutor_adaptive(state: AgentState) -> dict:
    out = await generate_explanation(state)
    out["tutor_node"] = "tutor_adaptive"
    if not out.get("explanation_mode"):
        out["explanation_mode"] = "eli5"
    return out


async def tutor_standard(state: AgentState) -> dict:
    st = {**state, "explanation_mode": state.get("explanation_mode") or "technical"}
    out = await generate_explanation(st)
    out["tutor_node"] = "tutor_standard"
    out["explanation_mode"] = "technical"
    return out


async def validator(state: AgentState) -> dict:
    settings = get_settings()
    if state.get("response_kind") != "explanation" or not settings.validator_enabled:
        return {"validator_ok": True, "validator_issues": []}
    ok, issues = True, []
    md = state.get("draft_answer") or state.get("final_answer") or ""
    if not (state.get("retrieved_docs") or []) and "slide không đề cập" not in md.lower():
        ok, issues = False, ["ungrounded"]
    out: dict = {"validator_ok": ok, "validator_issues": issues}
    if (not ok) and int(state.get("rewrite_count") or 0) >= 1:
        out["final_answer"] = "_Một số chi tiết ngoài slide đã được lược._\n\n" + md
    return out


async def tutor_redirect(state: AgentState) -> dict:
    if state.get("intent") == "meta":
        text = (
            "Mình là Adaptive Tutor VLearn (khoá AI Thực Chiến K4). "
            "Mình hỏi 1 câu để đúng tầm, rồi giải thích bám slide."
        )
        kind = "meta"
        reason = "meta"
    else:
        text = "Câu này ngoài phạm vi bài giảng. Bạn hỏi lại một khái niệm trên slide nhé."
        kind = "redirect"
        reason = "off_topic"
    return {
        "response_kind": kind,
        "final_answer": text,
        "route_reason": reason,
        "messages": [AIMessage(content=text)],
    }


async def retrieval_miss(state: AgentState) -> dict:
    text = "Slide không đề cập nội dung này trong kho bài giảng hiện tại."
    return {
        "response_kind": "retrieval_miss",
        "final_answer": text,
        "route_reason": "retrieval_miss",
        "awaiting_probe_answer": False,
        "probe_asked_this_episode": False,
        "pending_original_query": None,
        "pending_topic": None,
        "messages": [AIMessage(content=text)],
    }


async def persist_turn(state: AgentState) -> dict:
    rt = get_runtime()
    conv_id = UUID(state["conversation_id"])
    client = UUID(state["client_turn_id"]) if state.get("client_turn_id") else None
    kind = state.get("response_kind") or "explanation"
    topic = state.get("current_topic")
    payload = None
    if kind == "probe":
        payload = {
            "question": state.get("probe_question"),
            "choices": state.get("probe_choices") or [],
        }
    elif kind == "explanation":
        payload = {
            "citations": state.get("citations") or [],
            "explanation_mode": state.get("explanation_mode"),
        }

    flags: dict = {}
    if kind == "probe":
        flags = {
            "awaiting_probe": True,
            "probe_asked_this_episode": True,
            "pending_original_query": state.get("pending_original_query"),
            "pending_topic": state.get("pending_topic") or topic,
            "last_kind": "probe",
            "last_retrieval_query": state.get("retrieval_query"),
            "last_retrieved_chunk_ids": [d.get("chunk_id") for d in (state.get("retrieved_docs") or []) if d.get("chunk_id")],
        }
    elif kind == "explanation":
        flags = {
            "awaiting_probe": False,
            "probe_asked_this_episode": False,
            "pending_original_query": None,
            "pending_topic": None,
            "last_kind": "explanation",
            "last_explanation_mode": state.get("explanation_mode"),
            "last_assistant_sentence_count": int(state.get("last_assistant_sentence_count") or 0),
            "last_retrieval_query": state.get("retrieval_query"),
            "last_retrieved_chunk_ids": [d.get("chunk_id") for d in (state.get("retrieved_docs") or []) if d.get("chunk_id")],
        }
    elif kind in ("redirect", "meta"):
        flags = {"last_kind": kind}
    elif kind == "retrieval_miss":
        flags = {
            "awaiting_probe": False,
            "probe_asked_this_episode": False,
            "pending_original_query": None,
            "pending_topic": None,
            "last_kind": "retrieval_miss",
            "last_retrieval_query": state.get("retrieval_query"),
            "last_retrieved_chunk_ids": [],
        }

    flags["turn_index"] = int(state.get("turn_index") or 0)
    user_msg = MessageRow(
        id=uuid4(),
        conversation_id=conv_id,
        role="user",
        content=state.get("user_message") or "",
        intent=state.get("intent"),
        topic_key=topic,
        client_turn_id=client,
    )
    asst_msg = MessageRow(
        id=UUID(state["turn_id"]) if state.get("turn_id") else uuid4(),
        conversation_id=conv_id,
        role="assistant",
        content=state.get("final_answer") or "",
        intent=state.get("intent"),
        topic_key=topic,
        explanation_mode=state.get("explanation_mode"),
        response_kind=kind,
        citations=list(state.get("citations") or []),
        payload=payload,
        route_reason=state.get("route_reason"),
        client_turn_id=client,
    )

    await rt.repository.add_messages([user_msg, asst_msg])
    await rt.repository.update_conversation(conv_id, **flags)
    patch = {
        "awaiting_probe_answer": flags.get("awaiting_probe", state.get("awaiting_probe_answer")),
        "probe_asked_this_episode": flags.get("probe_asked_this_episode", state.get("probe_asked_this_episode")),
        "pending_original_query": flags.get("pending_original_query", state.get("pending_original_query")),
        "pending_topic": flags.get("pending_topic", state.get("pending_topic")),
        "last_kind": flags.get("last_kind", kind),
        "last_retrieval_query": flags.get("last_retrieval_query", state.get("retrieval_query")),
        "last_retrieved_chunk_ids": flags.get("last_retrieved_chunk_ids", state.get("last_retrieved_chunk_ids") or []),
        "turn_id": str(asst_msg.id),
    }
    return patch
