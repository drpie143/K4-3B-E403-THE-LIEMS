/*
 * Kết nối giao diện với backend (backend).
 * Bật khi trang mở qua http(s) với ?mode=live — backend phục vụ sẵn tại /app/index.html?mode=live.
 * Mở bằng file:// hoặc thiếu ?mode=live → chạy offline bằng engine.js.
 *
 * Token đăng nhập lưu ở localStorage và gắn vào header Authorization cho mọi lời gọi;
 * khi đã đăng nhập, backend tự gắn thao tác vào đúng user_id của tài khoản.
 */
(function (root) {
  "use strict";

  const params = new URLSearchParams(root.location ? root.location.search : "");
  const OVER_HTTP = /^https?:$/.test(root.location.protocol);
  // Mở qua http(s) là chạy thật; muốn xem bản offline (engine.js) thì thêm ?mode=mock.
  // Vẫn nhận ?mode=live như cũ để các đường dẫn demo đang dùng không hỏng.
  const LIVE = OVER_HTTP && params.get("mode") !== "mock";
  // Địa chỉ backend, theo thứ tự ưu tiên: ?api=... → config.js (khi deploy) → cùng origin.
  const BASE = (params.get("api") || root.VLEARN_API_BASE || "").replace(/\/$/, "");
  const PERSONA_TO_USER = { moi: "demo-moi", trung_binh: "demo-trung-binh", vung: "demo-vung", moi_toanh: "demo-moi-toanh" };
  const TOKEN_KEY = "vlearn.token";

  let sessionId = newId();
  let lessonId = "day01-foundation-b";
  let token = null;
  try { token = root.localStorage.getItem(TOKEN_KEY); } catch (e) { token = null; }

  function newId() {
    return "s-" + Math.random().toString(36).slice(2, 10);
  }

  async function call(method, path, body, query) {
    const url = new URL(BASE + path, root.location.href);
    Object.entries(query || {}).forEach(([k, v]) => { if (v !== undefined && v !== null) url.searchParams.set(k, v); });
    const headers = {};
    if (body) headers["Content-Type"] = "application/json";
    if (token) headers["Authorization"] = "Bearer " + token;
    const res = await fetch(url, { method, headers, body: body ? JSON.stringify(body) : undefined });
    if (!res.ok) {
      let detail = res.statusText;
      try { detail = (await res.json()).detail || detail; } catch (e) { /* bỏ qua */ }
      const err = new Error(detail);
      err.status = res.status;
      throw err;
    }
    return res.json();
  }

  const withCtx = (user, body) => Object.assign({ user_id: user, session_id: sessionId, lesson_id: lessonId }, body);

  const API = {
    LIVE,
    userFor: (personaId) => PERSONA_TO_USER[personaId] || personaId,
    session: () => sessionId,
    lesson: () => lessonId,
    setLesson(id) { if (id) lessonId = id; },
    newSession() {
      const old = sessionId;
      sessionId = newId();
      call("POST", "/api/session/reset", null, { session_id: old }).catch(() => {});
      return sessionId;
    },

    // ----------------------------------------------------------- tài khoản
    token: () => token,
    setToken(value) {
      token = value || null;
      try {
        if (token) root.localStorage.setItem(TOKEN_KEY, token);
        else root.localStorage.removeItem(TOKEN_KEY);
      } catch (e) { /* trình duyệt chặn localStorage thì vẫn chạy được trong phiên này */ }
    },
    register: (email, password, displayName) => call("POST", "/api/auth/register", { email, password, display_name: displayName || "" }),
    login: (email, password) => call("POST", "/api/auth/login", { email, password }),
    logout: () => call("POST", "/api/auth/logout"),
    me: () => call("GET", "/api/auth/me"),
    updateAccount: (body) => call("PUT", "/api/auth/me", body),
    deleteAccount: () => call("DELETE", "/api/auth/me"),

    // ----------------------------------------------------------- bài giảng
    lessons: () => call("GET", "/api/lessons"),
    lessonBody: (id, section) => call("GET", "/api/lessons/" + encodeURIComponent(id), null, section ? { section } : {}),

    // ------------------------------------------------------------ trợ giảng
    health: () => call("GET", "/health"),
    personas: () => call("GET", "/api/personas"),
    chat: (user, body) => call("POST", "/api/chat", withCtx(user, body)),
    survey: (user, body) => call("POST", "/api/survey", withCtx(user, body)),
    adjust: (user, concept, kind) => call("POST", "/api/adjust", withCtx(user, { concept, kind })),
    feedback: (user, concept, value, reason) => call("POST", "/api/feedback", withCtx(user, { concept, value, reason: reason || null })),
    getCheck: (user, concept) => call("GET", "/api/check", null, { user_id: user, session_id: sessionId, concept }),
    check: (user, concept, questionId, answer) => call("POST", "/api/check", withCtx(user, { concept, question_id: questionId, answer })),
    handoff: (user, concept) => call("POST", "/api/handoff", withCtx(user, { concept })),

    // --------------------------------------------------------------- hồ sơ
    profile: (user) => call("GET", "/api/profile", null, { user_id: user }),
    putProfile: (body) => call("PUT", "/api/profile", body),
    deleteProfile: (user, concept) => call("DELETE", "/api/profile", null, { user_id: user, concept }),
    deleteStrategy: (user, concept, strategy) => call("DELETE", "/api/profile/strategy", null, { user_id: user, concept, strategy }),
    undo: (user, eventIds) => call("POST", "/api/profile/undo", { user_id: user, event_ids: eventIds }),
    reset: (user) => call("POST", "/api/profile/reset", { user_id: user }),
    flushMemory: () => call("POST", "/api/memory/flush"),
    source: (id) => call("GET", "/api/sources/" + encodeURIComponent(id)),
  };

  root.P3_API = API;
})(window);
