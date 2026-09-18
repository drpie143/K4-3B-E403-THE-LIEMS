/*
 * Kết nối mock với backend (codebase/backend).
 * Bật khi trang được mở qua http(s) với ?mode=live (backend phục vụ tại /app/index.html?mode=live).
 * Mở file trực tiếp (file://) hoặc thiếu ?mode=live → mock chạy bằng engine.js như cũ.
 */
(function (root) {
  "use strict";

  const params = new URLSearchParams(root.location ? root.location.search : "");
  const LIVE = params.get("mode") === "live" && /^https?:$/.test(root.location.protocol);
  const BASE = (params.get("api") || "").replace(/\/$/, "");
  const PERSONA_TO_USER = { moi: "demo-moi", trung_binh: "demo-trung-binh", vung: "demo-vung", moi_toanh: "demo-moi-toanh" };

  let sessionId = newId();
  function newId() {
    return "s-" + Math.random().toString(36).slice(2, 10);
  }

  async function call(method, path, body, query) {
    const url = new URL(BASE + path, root.location.href);
    Object.entries(query || {}).forEach(([k, v]) => { if (v !== undefined && v !== null) url.searchParams.set(k, v); });
    const res = await fetch(url, {
      method,
      headers: body ? { "Content-Type": "application/json" } : {},
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      let detail = res.statusText;
      try { detail = (await res.json()).detail || detail; } catch (e) { /* bỏ qua */ }
      throw new Error("API " + res.status + ": " + detail);
    }
    return res.json();
  }

  const API = {
    LIVE,
    userFor: (personaId) => PERSONA_TO_USER[personaId] || personaId,
    session: () => sessionId,
    newSession() {
      const old = sessionId;
      sessionId = newId();
      call("POST", "/api/session/reset", null, { session_id: old }).catch(() => {});
      return sessionId;
    },
    health: () => call("GET", "/health"),
    personas: () => call("GET", "/api/personas"),
    chat: (user, body) => call("POST", "/api/chat", Object.assign({ user_id: user, session_id: sessionId }, body)),
    survey: (user, body) => call("POST", "/api/survey", Object.assign({ user_id: user, session_id: sessionId }, body)),
    adjust: (user, concept, kind) => call("POST", "/api/adjust", { user_id: user, session_id: sessionId, concept, kind }),
    feedback: (user, concept, value, reason) => call("POST", "/api/feedback", { user_id: user, session_id: sessionId, concept, value, reason: reason || null }),
    getCheck: (user, concept) => call("GET", "/api/check", null, { user_id: user, session_id: sessionId, concept }),
    check: (user, concept, questionId, answer) => call("POST", "/api/check", { user_id: user, session_id: sessionId, concept, question_id: questionId, answer }),
    handoff: (user, concept) => call("POST", "/api/handoff", { user_id: user, session_id: sessionId, concept }),
    profile: (user) => call("GET", "/api/profile", null, { user_id: user }),
    putProfile: (body) => call("PUT", "/api/profile", body),
    deleteProfile: (user, concept) => call("DELETE", "/api/profile", null, { user_id: user, concept }),
    deleteStrategy: (user, concept, strategy) => call("DELETE", "/api/profile/strategy", null, { user_id: user, concept, strategy }),
    undo: (user, eventIds) => call("POST", "/api/profile/undo", { user_id: user, event_ids: eventIds }),
    reset: (user) => call("POST", "/api/profile/reset", { user_id: user }),
    source: (id) => call("GET", "/api/sources/" + encodeURIComponent(id)),
  };

  root.P3_API = API;
})(window);
