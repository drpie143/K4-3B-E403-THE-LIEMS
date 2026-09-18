/*
 * UI của mock P3 — Trợ giảng AI trong trang học VLearn.
 * Toàn bộ "AI" ở đây là giả lập bằng engine.js; không gọi mạng.
 */
(function (root) {
  "use strict";

  const C = root.P3_CONTENT;
  const E = window.P3_ENGINE;
  const LOCAL_SRC = window.VLEARN_SOURCES_LOCAL || null;
  const DEMO_USER = { name: "bạn", initial: "?" };   // thay bằng tên tài khoản sau khi đăng nhập
  const STORE_KEY = "p3-mock-v1";
  const $ = (s, el) => (el || document).querySelector(s);
  const API = window.P3_API;
  const LIVE = !!(API && API.LIVE);
  const LIVE_INFO = { provider: null, personas: null };

  /* ---------------- Trạng thái ---------------- */
  const S = {
    personaId: "trung_binh",
    memoryOn: true,
    devMode: false,
    profiles: {},
    styles: {},
    session: null,
    survey: null,
    selection: "",
  };

  function freshSession() {
    return { answered: {}, lastConcept: null, thumbsDown: {}, checkAttempt: {}, wrong: {}, lastQuestion: "", tried: {} };
  }

  function load() {
    try {
      const raw = localStorage.getItem(STORE_KEY);
      if (raw) Object.assign(S, JSON.parse(raw));
    } catch (e) { /* bỏ qua: trình duyệt chặn storage */ }
    S.session = freshSession();
    S.survey = null;
    S.selection = "";
  }

  function save() {
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify({ personaId: S.personaId, memoryOn: S.memoryOn, devMode: S.devMode, profiles: S.profiles, styles: S.styles }));
    } catch (e) { /* bỏ qua */ }
  }

  function profile() {
    if (!C.PERSONAS[S.personaId]) return {}; // hồ sơ chỉ có ở backend
    if (!S.profiles[S.personaId]) S.profiles[S.personaId] = JSON.parse(JSON.stringify(C.PERSONAS[S.personaId].profile));
    return S.profiles[S.personaId];
  }
  function setProfile(p) { S.profiles[S.personaId] = p; save(); renderNotebook(); }
  function prefStyle() {
    if (!C.PERSONAS[S.personaId]) return null;
    return S.styles[S.personaId] !== undefined ? S.styles[S.personaId] : C.PERSONAS[S.personaId].preferred_style;
  }

  function engineState() {
    return { memoryOn: S.memoryOn, profile: profile(), preferredStyle: prefStyle(), session: S.session, survey: S.survey };
  }

  /* ---------------- Tiện ích DOM ---------------- */
  function h(tag, attrs, children) {
    const el = document.createElement(tag);
    if (attrs) {
      for (const k in attrs) {
        const v = attrs[k];
        if (v == null || v === false) continue;
        if (k === "class") el.className = v;
        else if (k === "html") el.innerHTML = v;
        else if (k === "text") el.textContent = v;
        else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
        else el.setAttribute(k, v === true ? "" : v);
      }
    }
    [].concat(children || []).forEach((c) => {
      if (c == null || c === false) return;
      el.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    });
    return el;
  }
  function icon(id, size) {
    const s = size || 18;
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("width", s);
    svg.setAttribute("height", s);
    svg.setAttribute("aria-hidden", "true");
    const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
    use.setAttribute("href", "#" + id);
    svg.appendChild(use);
    return svg;
  }
  function esc(s) {
    return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  }
  function nowTime() {
    const d = new Date();
    return d.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
  }
  let toastTimer;
  function toast(msg) {
    const t = $("#toast");
    t.textContent = msg;
    t.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove("show"), 2600);
  }

  const chat = $("#chat");
  function scrollDown() { chat.scrollTop = chat.scrollHeight; }

  /* ---------------- Sidebar ---------------- */
  // Danh sách buổi học và các mục do js/lessons.js dựng từ /api/lessons.
  // Hàm này chỉ còn là bản dự phòng khi mở offline (không có backend).
  function renderSidebar() {
    if (root.P3_LESSONS) return;
    const box = $("#sideItems");
    if (!box || box.children.length) return;
    box.appendChild(h("div", { class: "side-empty", text: "Mở trang qua backend (?mode=live) để thấy 6 buổi học." }));
  }

  /* ---------------- Khung chat ---------------- */
  function greeting() {
    const hr = new Date().getHours();
    const part = hr < 11 ? "sáng" : hr < 18 ? "chiều" : "tối";
    chat.innerHTML = "";
    const ctx = root.P3_LESSON_CTX || null;
    const starters = (ctx && ctx.starters && ctx.starters.length)
      ? ctx.starters
      : ["Self-attention là gì?", "Q, K, V khác nhau thế nào?", "Multi-head attention là gì?"];
    chat.appendChild(
      h("div", { class: "empty" }, [
        h("div", { class: "hi", text: "Chào buổi " + part + ", " + DEMO_USER.name.toUpperCase() + "!" }),
        h("div", { class: "ctx", text: "Đang mở: " + ((root.P3_LESSON_CTX && root.P3_LESSON_CTX.title) || C.LESSON.section) }),
        h("div", { class: "starters" }, starters.map((q) => h("button", { class: "chip", text: q, onclick: () => ask(q) }))),
      ])
    );
  }

  function addUser(text, selection) {
    const empty = $(".empty", chat);
    if (empty) empty.remove();
    const b = h("div", { class: "bubble" }, [selection ? h("span", { class: "quote", text: "“" + selection + "”" }) : null, text]);
    chat.appendChild(h("div", { class: "msg user" }, [h("div", null, [b, h("div", { class: "time", text: nowTime() })]), h("div", { class: "avatar sm", text: DEMO_USER.initial })]));
    scrollDown();
  }

  function addAi(cardChildren, opts) {
    opts = opts || {};
    const card = h("div", { class: "ai-card" + (opts.plain ? " plain" : "") }, cardChildren);
    const row = h("div", { class: "msg ai" }, [h("div", { class: "ai-ico" }, [icon("i-spark", 24)]), card]);
    chat.appendChild(row);
    // Tin dài: cuộn tới đầu tin để học viên đọc từ trên xuống.
    if (row.offsetHeight > chat.clientHeight * 0.8) chat.scrollTop = row.offsetTop - chat.offsetTop - 8;
    else scrollDown();
    return card;
  }

  // Một lượt trả lời đi qua 3 bước ở backend (tìm căn cứ → soạn bài → đối chiếu bài giảng)
  // và mất vài giây. Nói ra học viên đang chờ điều gì thay vì để ba chấm nhấp nháy im lặng.
  const WAIT_STEPS = [
    { at: 0, text: "Đang tìm đoạn liên quan trong bài giảng…" },
    { at: 1800, text: "Đang soạn lời giải thích đúng mức của bạn…" },
    { at: 6000, text: "Đang đối chiếu với bài giảng để không nói sai…" },
    { at: 13000, text: "Câu này hơi nặng, mình cần thêm chút thời gian…" },
  ];

  function typing(withSteps) {
    const label = h("span", { class: "typing-label" });
    const el = h("div", { class: "msg ai" }, [
      h("div", { class: "ai-ico" }, [icon("i-spark", 24)]),
      h("div", { class: "typing" }, [h("i"), h("i"), h("i"), label]),
    ]);
    chat.appendChild(el);
    scrollDown();
    // Chỉ chạy khi thật sự chờ backend; bản offline trả lời ngay nên để nguyên ba chấm.
    if (withSteps !== false && LIVE) {
      const timers = WAIT_STEPS.map((s) => setTimeout(() => { label.textContent = s.text; scrollDown(); }, s.at));
      const stop = el.remove.bind(el);
      el.remove = () => { timers.forEach(clearTimeout); stop(); };
    }
    return el;
  }

  function addNotice(text, before, kind) {
    if (!text) return;
    const row = h("div", { class: "notice" + (kind === "down" ? " down" : "") }, [icon(kind === "down" ? "i-info" : "i-check", 16), h("span", { text })]);
    if (before) {
      row.appendChild(
        h("button", {
          class: "undo", text: "Hoàn tác",
          onclick: () => { setProfile(before); row.remove(); toast("Đã hoàn tác thay đổi trong Sổ tay"); },
        })
      );
    }
    chat.appendChild(row);
    scrollDown();
  }

  function applyProfileEvent(ev) {
    if (!S.memoryOn) return;
    const r = E.applyEvent(profile(), ev);
    setProfile(r.profile);
    const down = ev.type === "confused" || ev.type === "level_down";
    addNotice(r.notice, r.notice ? r.before : null, down ? "down" : "up");
  }

  /* ---------------- Chế độ live (backend) ---------------- */
  function liveUser() {
    const acc = root.P3_ACCOUNT;
    return (acc && acc.user_id) || API.userFor(S.personaId);
  }

  function liveFail(err) {
    console.warn(err);
    toast("Không gọi được backend — tạm dùng bản mock cho lượt này");
  }

  function serverNotices(list) {
    (list || []).forEach((n) => {
      const row = h("div", { class: "notice" + (n.kind === "down" ? " down" : "") }, [icon(n.kind === "down" ? "i-info" : "i-check", 16), h("span", { text: n.text })]);
      if (n.event_ids && n.event_ids.length) {
        row.appendChild(h("button", {
          class: "undo", text: "Hoàn tác",
          onclick: () => API.undo(liveUser(), n.event_ids).then(() => { row.remove(); toast("Đã hoàn tác thay đổi trong Sổ tay"); renderNotebook(); }).catch(liveFail),
        }));
      }
      chat.appendChild(row);
    });
    scrollDown();
  }

  function toFid(f) {
    if (!f) return { ok: false, covered: 0, total: 0, missingClaims: [], outside: 0 };
    return { ok: f.ok, covered: f.covered, total: f.total, missingClaims: f.missing_claims || [], outside: f.outside || 0 };
  }

  function withTyping(promise, fn) {
    const t = typing();
    return promise.then((res) => { t.remove(); fn(res); }).catch((err) => { t.remove(); liveFail(err); });
  }

  function renderResp(resp, opts) {
    opts = opts || {};
    if (!resp) return;
    const d = Object.assign({}, resp.decision || {}, { kind: resp.kind, _meta: resp.meta });
    if (resp.kind === "explain") {
      renderAnswer(d, Object.assign({}, opts, { server: resp }));
    } else if (resp.kind === "survey") {
      renderSurvey(d, resp.survey);
    } else if (resp.kind === "help") {
      renderHelp();
    } else {
      renderScopeLive(d, resp.scope);
    }
    serverNotices(resp.notices);
  }

  function liveAdjust(d, kind, lead) {
    withTyping(API.adjust(liveUser(), d.concept, kind), (resp) => { renderResp(resp, { lead }); renderNotebook(); });
  }

  function renderScopeLive(d, scope) {
    scope = scope || { message: "", suggestions: [], nearest: [] };
    const kids = [
      h("div", { class: "why" }, [icon(d.kind === "no_source" ? "i-info" : "i-shield", 16), h("span", { text: scope.message })]),
    ];
    if (scope.nearest && scope.nearest.length) {
      kids.push(h("p", null, ["Đoạn gần nhất trong buổi: "].concat(citeButtons(scope.nearest))));
    }
    if (d.kind === "no_source") {
      kids.push(h("div", { class: "toolbar", style: "border:0" }, [
        h("button", { class: "chip solid", text: "Soạn câu hỏi cho TA", onclick: () => API.handoff(liveUser(), d.concept || null).then((r) => renderHandoff(d.concept, "Câu hỏi nằm ngoài tài liệu buổi này.", r.draft)).catch(liveFail) }),
      ]));
    }
    kids.push(h("p", { text: "Bạn có thể thử:" }));
    kids.push(h("div", { class: "toolbar", style: "border:0" }, (scope.suggestions || []).map((q) => h("button", { class: "chip", text: q, onclick: () => ask(q) }))));
    kids.push(trace(d));
    addAi(kids);
  }

  /* ---------------- Luồng hỏi ---------------- */
  function ask(text, opts) {
    opts = opts || {};
    const selection = opts.selection !== undefined ? opts.selection : S.selection;
    addUser(text, selection);
    if (!opts.keepSurvey) S.survey = null;
    clearSelection();
    S.session.lastQuestion = text;
    if (LIVE) return handle(text, selection, opts);   // handle() tự dựng ô "đang soạn"
    const t = typing(false);
    setTimeout(() => {
      t.remove();
      handle(text, selection, opts);
    }, 550);
  }

  function handle(text, selection, opts) {
    if (LIVE) {
      const t = typing();
      API.chat(liveUser(), {
        text, selection: selection || "",
        action: opts.forceConfused ? "confused" : "ask",
        concept_hint: opts.concept || null,
      }).then((resp) => { t.remove(); renderResp(resp); renderNotebook(); })
        .catch((err) => { t.remove(); liveFail(err); handleLocal(text, selection, opts); });
      return;
    }
    handleLocal(text, selection, opts);
  }

  function handleLocal(text, selection, opts) {
    S.session.now = Date.now();
    const intent = E.detect(text, selection, S.session);
    if (opts.forceConfused) {
      intent.confused = true;
      intent.concept = opts.concept || intent.concept;
    }
    const d = E.decide(intent, engineState());
    d._intent = intent;
    if (d.kind === "survey") return renderSurvey(d);
    if (d.kind === "explain") return renderAnswer(d);
    if (d.kind === "help") return renderHelp();
    return renderScope(d, intent);
  }

  /* ---------------- Câu trả lời ---------------- */
  function citeButtons(src) {
    return (src || []).map((id) => h("button", { class: "cite", text: "[" + id + "]", onclick: () => openSource(id) }));
  }

  function renderBlock(b) {
    const wrap = h("div", { class: "blk " + b.t });
    if (b.t === "outside") wrap.appendChild(h("span", { class: "pill-outside", text: "Ngoài bài giảng" }));
    if (b.title) {
      const ic = b.t === "analogy" ? "i-bulb" : b.t === "prereq" ? "i-info" : b.t === "map" ? "i-doc" : null;
      wrap.appendChild(h("div", { class: "blk-title" }, [ic ? icon(ic, 15) : null, b.title]));
    }
    if (b.t === "map") {
      const table = h("table", { class: "map" });
      b.rows.forEach(([l, r]) => table.appendChild(h("tr", null, [h("td", { html: l }), h("td", { class: "arrow", text: "→" }), h("td", { html: r })])));
      wrap.appendChild(table);
    } else if (b.t === "steps") {
      const ol = h("ol", { class: "steps" });
      b.items.forEach((it) => ol.appendChild(h("li", { html: it })));
      wrap.appendChild(ol);
    } else if (b.t === "key") {
      wrap.appendChild(h("div", { class: "blk-title" }, [icon("i-check", 15), "Chốt lại bằng thuật ngữ"]));
      wrap.appendChild(h("div", { html: b.html }));
    } else if (b.t === "limit") {
      wrap.appendChild(h("div", { class: "blk-title" }, [icon("i-info", 15), "Ví dụ này đơn giản hoá ở chỗ"]));
      wrap.appendChild(h("div", { html: b.html }));
    } else {
      wrap.appendChild(h("span", { html: b.html }));
    }
    const cites = citeButtons(b.src);
    if (cites.length) wrap.appendChild(h("span", null, [" "].concat(cites)));
    return wrap;
  }

  function fidelityBadge(conceptId, f) {
    const concept = C.CONCEPTS[conceptId];
    const ok = f.ok;
    const label = ok ? "Giữ đủ " + f.covered + "/" + f.total + " ý chính của bài giảng" : "Thiếu ý chính — đã chặn";
    const list = h("ul", { class: "fid-list", hidden: true },
      concept.claims.map((c) => h("li", null, [(f.missingClaims.includes(c.id) ? "✗ " : "✓ ") + c.text + " "].concat(citeButtons(c.src))))
        .concat(f.outside ? [h("li", { text: "◇ " + f.outside + " đoạn ngoài bài giảng — đã gắn nhãn" })] : [])
    );
    const btn = h("button", { class: "fid" + (ok ? "" : " warn"), "aria-expanded": "false", onclick: () => { list.hidden = !list.hidden; btn.setAttribute("aria-expanded", String(!list.hidden)); } }, [icon("i-shield", 15), label]);
    return h("div", { style: "margin-top:8px" }, [btn, list]);
  }

  // JSON quyết định chỉ hiện khi bật "chế độ giám khảo" trong bảng demo.
  function trace(d) {
    const pub = {
      level: d.level ? d.level + " · " + C.LEVEL_LABEL[d.level] : null, style: d.style, missing_concepts: d.missing_concepts,
      confidence: d.confidence, need_survey: d.need_survey, reason_for_user: d.reason_for_user, source_ids: d.source_ids, in_scope: d.in_scope,
    };
    if (d.decided_by) pub.decided_by = d.decided_by;
    if (d._meta) pub.meta = d._meta;
    return h("details", { class: "trace dev-only" }, [h("summary", { text: "Xem cách AI quyết định (JSON)" }), h("pre", { text: JSON.stringify(pub, null, 2) })]);
  }

  function renderAnswer(d, opts) {
    opts = opts || {};
    const a = opts.server
      ? { blocks: opts.server.answer.blocks, fidelity: toFid(opts.server.fidelity) }
      : E.composeAnswer(d, opts);
    const concept = C.CONCEPTS[d.concept];
    const kids = [];
    if (opts.lead) kids.push(h("div", { class: "lead", text: opts.lead }));
    if (d.reason_for_user) kids.push(h("div", { class: "why" }, [icon("i-info", 16), h("span", { text: d.reason_for_user })]));

    // Validator: không đạt thì không hiện bản sinh ra, dùng thẻ khái niệm.
    let blocks = a.blocks;
    if (!a.fidelity.ok) {
      blocks = [{ t: "key", html: concept.claims.map((c) => c.text).join(" "), src: concept.claims.flatMap((c) => c.src), claims: concept.claims.map((c) => c.id) }];
    }
    blocks.forEach((b) => kids.push(renderBlock(b)));
    kids.push(fidelityBadge(d.concept, a.fidelity));

    const srcIds = Array.from(new Set(blocks.flatMap((b) => b.src || [])));
    kids.push(h("div", { class: "sources" }, [icon("i-doc", 14), "Nguồn: transcript Day 1"].concat(srcIds.map((id) => h("button", { class: "src-chip", title: "Xem đoạn gốc", onclick: () => openSource(id) }, [id])))));

    // Học viên điều chỉnh bằng lời thường; không thấy tên mức.
    if (d.concept === "self_attention") {
      const r = E.rank(d.level);
      kids.push(h("div", { class: "toolbar" }, [
        h("button", { class: "chip", text: "Dễ hiểu hơn", disabled: r === 0, title: r === 0 ? "Đây đã là cách giải thích dễ nhất" : null, onclick: () => changeLevel(d, -1) }),
        h("button", { class: "chip", text: "Ví dụ khác", onclick: () => correction(d, "example") }),
        h("button", { class: "chip", text: "Ngắn hơn", onclick: () => correction(d, "shorter") }),
        h("button", { class: "chip", text: "Sâu hơn", disabled: r === E.LEVELS.length - 1, title: r === E.LEVELS.length - 1 ? "Đây đã là phần sâu nhất của bài" : null, onclick: () => changeLevel(d, 1) }),
      ]));
    }

    const acts = h("div", { class: "toolbar" });
    const up = h("button", { class: "icon-btn", "aria-label": "Hữu ích", onclick: () => thumbsUp(d, up, down) }, [icon("i-up", 19)]);
    const down = h("button", { class: "icon-btn", "aria-label": "Chưa hữu ích", onclick: () => thumbsDown(d, up, down) }, [icon("i-dn", 19)]);
    acts.append(up, down, h("span", { class: "push" }), h("button", { class: "confused-btn", text: "Mình chưa hiểu", onclick: () => stillConfused(d) }));
    kids.push(acts);
    kids.push(trace(d));

    const card = addAi(kids);
    S.session.answered[d.concept] = Date.now();
    S.session.lastConcept = d.concept;
    S.session.tried[d.concept] = S.session.tried[d.concept] || [];
    S.session.tried[d.concept].push(C.STYLE_LABEL[d.style] || d.style);
    S.lastDecision = d;
    S.lastOpts = opts;
    return card;
  }

  // "Dễ hiểu hơn" (delta −1) / "Sâu hơn" (delta +1): dịch 1 bậc trên thang 5 mức.
  function changeLevel(d, delta) {
    if (LIVE) return liveAdjust(d, delta < 0 ? "easier" : "deeper", delta < 0 ? "Giải thích lại · dễ hiểu hơn" : "Giải thích lại · sâu hơn");
    const lv = E.stepLevel(d.level, delta);
    if (lv === d.level) return;
    const nd = Object.assign({}, d, { level: lv, full: true });
    if (delta < 0) {
      nd.style = E.rank(lv) <= 1 ? "vi_du" : d.style;
      nd.reason_for_user = "Mình giải thích dễ hơn lần trước" + (nd.style === "vi_du" ? ", dùng ví dụ đời thường." : ".");
      applyProfileEvent({ type: "level_down", concept: d.concept });
      renderAnswer(nd, { lead: "Giải thích lại · dễ hiểu hơn" });
    } else {
      nd.style = "chi_tiet";
      nd.prereq_first = null;
      nd.reason_for_user = "Mình đi sâu thêm một bước. Phần nào ngoài bài giảng sẽ có nhãn riêng.";
      renderAnswer(nd, { lead: "Giải thích lại · sâu hơn" });
    }
  }

  function correction(d, kind) {
    if (LIVE) return liveAdjust(d, kind === "example" ? "example" : "shorter", kind === "example" ? "Giải thích lại · ví dụ khác" : "Giải thích lại · ngắn hơn");
    const r = E.rank(d.level);
    const nd = Object.assign({}, d, { full: true, reason_for_user: "" });
    let lead;
    const opts = {};
    if (kind === "example") {
      nd.level = r === 0 ? "L1" : "L2";
      nd.style = "vi_du";
      opts.altExample = !(S.lastOpts && S.lastOpts.altExample);
      lead = "Giải thích lại · ví dụ khác";
      nd.reason_for_user = "Bạn muốn ví dụ khác, nên mình dùng ví dụ giảng viên đã dùng trong bài.";
    } else {
      nd.prereq_first = null;
      if (r >= 2) {
        nd.level = "L3";
        nd.full = false;
      } else {
        nd.style = "ngan_gon";
      }
      lead = "Giải thích lại · ngắn hơn";
      nd.reason_for_user = "Bạn muốn ngắn hơn, nên mình chỉ giữ các ý chính.";
      S.styles[S.personaId] = "ngan_gon";
      save();
    }
    renderAnswer(nd, Object.assign(opts, { lead }));
  }

  function thumbsUp(d, up, down) {
    up.classList.add("on");
    up.disabled = down.disabled = true;
    if (LIVE) {
      API.feedback(liveUser(), d.concept, "up").then((res) => {
        if (res.next === "check" && res.check) renderCheck(d, res.check, "Tuyệt! Thử 1 câu nhỏ để chắc là bạn đã hiểu nhé.");
        else addAi([h("p", { text: "Cảm ơn bạn! Muốn hỏi tiếp phần nào cứ gõ nhé." })], { plain: true });
      }).catch(liveFail);
      return;
    }
    const q = E.pickCheck(d.concept, S.session.checkAttempt[d.concept] || 0);
    if (q) renderCheck(d, q, "Tuyệt! Thử 1 câu nhỏ để chắc là bạn đã hiểu nhé.");
    else addAi([h("p", { text: "Cảm ơn bạn! Muốn hỏi tiếp phần nào cứ gõ nhé." })], { plain: true });
  }

  function thumbsDown(d, up, down) {
    down.classList.add("on");
    up.disabled = down.disabled = true;
    if (LIVE) {
      const pickLive = (reason) => {
        liveRow.querySelectorAll("button").forEach((b) => (b.disabled = true));
        withTyping(API.feedback(liveUser(), d.concept, "down", reason), (res) => {
          serverNotices(res.notices);
          if (res.next === "handoff") renderHandoff(d.concept, "Mình đã thử 2 cách mà vẫn chưa hợp với bạn.", res.handoff);
          else if (res.next === "report") addAi([h("p", { text: "Nếu cần câu trả lời chắc chắn, bạn có thể hỏi TA ngay." }), h("button", { class: "chip", text: "Soạn câu hỏi cho TA", onclick: () => renderHandoff(d.concept, "Bạn báo nội dung có thể sai.", res.handoff) })]);
          else if (res.response) renderResp(res.response, { lead: "Thử cách khác" });
          renderNotebook();
        });
      };
      const liveRow = h("div", { class: "toolbar" }, [
        h("span", { class: "muted", text: "Chưa ổn ở đâu?" }),
        h("button", { class: "chip", text: "Khó hiểu", onclick: () => pickLive("hard") }),
        h("button", { class: "chip", text: "Quá dài", onclick: () => pickLive("long") }),
        h("button", { class: "chip", text: "Có vẻ sai kiến thức", onclick: () => pickLive("wrong") }),
        h("button", { class: "chip ghost", text: "Chỉ đổi cách khác", onclick: () => pickLive(null) }),
      ]);
      addAi([liveRow], { plain: true });
      return;
    }
    S.session.thumbsDown[d.concept] = (S.session.thumbsDown[d.concept] || 0) + 1;
    if (S.session.thumbsDown[d.concept] >= 2) return renderHandoff(d.concept, "Mình đã thử 2 cách mà vẫn chưa hợp với bạn.");
    const pick = (reason) => {
      row.querySelectorAll("button").forEach((b) => (b.disabled = true));
      if (reason === "wrong") {
        addAi([h("p", { text: "Cảm ơn bạn đã báo. Mình đã ghi lại để TA kiểm tra thẻ khái niệm (mock). Nếu cần câu trả lời chắc chắn, bạn có thể hỏi TA ngay." }), h("button", { class: "chip", text: "Soạn câu hỏi cho TA", onclick: () => renderHandoff(d.concept, "Bạn báo nội dung có thể sai.") })]);
        return;
      }
      if (reason === "hard") applyProfileEvent({ type: "level_down", concept: d.concept });
      const nd = Object.assign({}, d, {
        full: true,
        level: reason === "hard" || reason === "long" ? E.LEVELS[Math.max(0, E.LEVELS.indexOf(d.level) - 1)] : d.level,
        prereq_first: reason === "long" ? null : d.prereq_first,
        style: reason === "long" ? "ngan_gon" : E.nextStyle(d.style),
        reason_for_user: reason === "long" ? "Bạn thấy dài, mình chia thành từng bước." : "Mình đổi cách giải thích so với lần trước.",
      });
      renderAnswer(nd, { lead: "Thử cách khác", altExample: true });
    };
    const row = h("div", { class: "toolbar" }, [
      h("span", { class: "muted", text: "Chưa ổn ở đâu?" }),
      h("button", { class: "chip", text: "Khó hiểu", onclick: () => pick("hard") }),
      h("button", { class: "chip", text: "Quá dài", onclick: () => pick("long") }),
      h("button", { class: "chip", text: "Có vẻ sai kiến thức", onclick: () => pick("wrong") }),
    ]);
    addAi([row], { plain: true });
  }

  function stillConfused(d) {
    if (!LIVE) applyProfileEvent({ type: "confused", concept: d.concept });
    ask("Mình chưa hiểu", { forceConfused: true, concept: d.concept, selection: "" });
  }

  /* ---------------- Khảo sát ---------------- */
  function renderSurvey(d, payload) {
    const concept = C.CONCEPTS[d.concept];
    const levels = {};
    let rowInfo;
    let style;
    if (payload) {
      rowInfo = payload.rows.map((r) => ({ id: r.concept, term: r.term, viName: r.vi_name }));
      payload.rows.forEach((r) => { if (r.level) levels[r.concept] = r.level; });
      style = payload.style || "vi_du";
    } else {
      rowInfo = concept.prerequisites.slice(0, 3).map((id) => ({ id, term: C.CONCEPTS[id].term, viName: C.CONCEPTS[id].viName }));
      const prof = S.memoryOn ? profile() : {};
      rowInfo.forEach(({ id }) => { if (prof[id] && prof[id].level) levels[id] = prof[id].level; });
      style = prefStyle() || "vi_du";
    }

    const card = h("div", { class: "survey" });
    card.appendChild(h("div", { class: "why" }, [icon("i-info", 16), h("span", { text: d.reason_for_user })]));
    card.appendChild(h("p", { html: "Để giải thích <b>" + esc(concept.term) + "</b> đúng chỗ bạn vướng, cho mình <b>3 cú bấm</b> nhé." }));
    card.appendChild(h("h5", { text: "1. Bạn đã nắm các khái niệm nền này chưa?" }));
    if (Object.keys(levels).length) card.appendChild(h("div", { class: "muted", text: "Mình điền sẵn theo Sổ tay — bạn sửa nếu chưa đúng." }));

    rowInfo.forEach(({ id, term, viName }) => {
      const seg = h("div", { class: "seg", role: "group", "aria-label": term });
      ["chua", "biet_so", "hieu_ro"].forEach((lv) => {
        const b = h("button", { type: "button", "aria-pressed": String(levels[id] === lv), text: C.PROFILE_LABEL[lv], onclick: () => {
          levels[id] = lv;
          seg.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", "false"));
          b.setAttribute("aria-pressed", "true");
        } });
        seg.appendChild(b);
      });
      card.appendChild(h("div", { class: "srow" }, [h("div", { class: "cname" }, [term, h("small", { text: viName })]), seg]));
    });

    card.appendChild(h("h5", { text: "2. Bạn muốn giải thích theo kiểu nào?", style: "margin-top:12px" }));
    const stylesBox = h("div", { class: "styles" });
    ["vi_du", "ngan_gon", "chi_tiet"].forEach((st) => {
      const b = h("button", { type: "button", class: "chip", "aria-pressed": String(style === st), text: C.STYLE_LABEL[st], onclick: () => {
        style = st;
        stylesBox.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", "false"));
        b.setAttribute("aria-pressed", "true");
      } });
      stylesBox.appendChild(b);
    });
    card.appendChild(stylesBox);
    const note = h("input", { type: "text", placeholder: "3. (Tuỳ chọn) Mình vướng ở chữ…" });
    card.appendChild(note);

    const submit = h("button", { class: "btn primary small", type: "button", text: "Gửi và nhận giải thích" });
    const skip = h("button", { class: "btn small", type: "button", text: "Bỏ qua, giải thích luôn" });
    card.appendChild(h("div", { class: "actions" }, [submit, skip]));
    addAi([card]);

    const lock = (summary) => {
      card.classList.add("done");
      card.querySelectorAll("button, input").forEach((x) => (x.disabled = true));
      card.appendChild(h("div", { class: "muted", style: "margin-top:8px", text: summary }));
    };

    submit.addEventListener("click", () => {
      lock("Đã gửi: " + (Object.keys(levels).map((k) => C.CONCEPTS[k].term + " " + C.PROFILE_LABEL[levels[k]]).join(" · ") || "không chọn mức") + " · " + C.STYLE_LABEL[style]);
      if (LIVE) {
        withTyping(API.survey(liveUser(), { concept: d.concept, levels: Object.assign({}, levels), style, note: note.value.trim() }),
          (resp) => { renderResp(resp, { lead: "Giải thích lại cho bạn" }); renderNotebook(); });
        return;
      }
      if (S.memoryOn) {
        let p = profile();
        let before = null;
        const changed = [];
        Object.keys(levels).forEach((k) => {
          const r = E.applyEvent(p, { type: "self_report", concept: k, level: levels[k] });
          if (r.notice) { before = before || r.before; changed.push(C.CONCEPTS[k].term + ": " + C.PROFILE_LABEL[levels[k]]); }
          p = r.profile;
        });
        setProfile(p);
        S.styles[S.personaId] = style;
        save();
        if (changed.length) addNotice("Đã ghi vào Sổ tay (bạn tự khai): " + changed.join(" · "), before, "up");
      }
      S.survey = { concept: d.concept, levels: Object.assign({}, levels), style, note: note.value.trim() };
      continueAfterSurvey(d);
    });
    skip.addEventListener("click", () => {
      lock("Đã bỏ qua khảo sát.");
      if (LIVE) {
        withTyping(API.survey(liveUser(), { concept: d.concept, skipped: true }), (resp) => renderResp(resp, { lead: "Giải thích lại cho bạn" }));
        return;
      }
      S.survey = { concept: d.concept, levels: {}, style: "ngan_gon", skipped: true };
      continueAfterSurvey(d);
    });
  }

  function continueAfterSurvey(d) {
    const t = typing();
    setTimeout(() => {
      t.remove();
      const intent = Object.assign({}, d._intent, { confused: true, concept: d.concept });
      const nd = E.decide(intent, engineState());
      nd._intent = intent;
      renderAnswer(nd, { lead: "Giải thích lại cho bạn" });
    }, 650);
  }

  /* ---------------- Câu kiểm tra ---------------- */
  function renderCheck(d, q, intro) {
    const kids = [h("p", { text: intro }), h("p", null, [h("b", { text: q.q || q.question })])];
    const opts = q.options.map((o) => h("button", { class: "opt", onclick: () => choose(o.k) }, [h("span", { class: "k", text: o.k }), h("span", { text: o.text })]));
    kids.push.apply(kids, opts);
    const skip = h("button", { class: "chip ghost", text: "Bỏ qua", style: "margin-top:8px", onclick: () => {
      lockAll();
      addAi([h("p", { text: "Không sao, bạn quay lại kiểm tra lúc nào cũng được." })], { plain: true });
    } });
    kids.push(skip);
    const card = addAi(kids);

    function lockAll() { card.querySelectorAll("button").forEach((b) => (b.disabled = true)); }

    function chooseLive(k) {
      lockAll();
      API.check(liveUser(), d.concept, q.id, k).then((res) => {
        const idx = q.options.findIndex((o) => o.k === k);
        const rightIdx = q.options.findIndex((o) => o.k === res.right);
        opts[idx].classList.add(res.correct ? "right" : "wrong");
        if (!res.correct && rightIdx >= 0) opts[rightIdx].classList.add("right");
        if (res.correct) {
          card.appendChild(h("div", { class: "result ok" }, [h("b", { text: "Chính xác! " }), "Bạn đã nắm đúng ý này của bài. "].concat(citeButtons(res.src))));
          serverNotices(res.notices);
          addAi([
            h("p", { text: "Bạn muốn làm gì tiếp?" }),
            h("div", { class: "toolbar", style: "border:0;padding-top:0;margin-top:0" }, [
              h("button", { class: "chip", text: "Xem Lab demo self-attention", onclick: () => openSource("T06-160") }),
              h("button", { class: "chip", text: "Hỏi về multi-head", onclick: () => ask("Multi-head attention là gì?") }),
              h("button", { class: "chip", text: "Thêm 1 câu kiểm tra", onclick: () => API.getCheck(liveUser(), d.concept).then((nq) => nq && renderCheck(d, nq, "Câu tiếp theo:")).catch(liveFail) }),
            ]),
          ], { plain: true });
        } else {
          card.appendChild(h("div", { class: "result no" }, [h("b", { text: res.misconception ? "Chưa đúng — chỗ này hay bị hiểu lệch. " : "Chưa đúng. " }), h("span", { html: res.fix_html || "" }), " "].concat(citeButtons(res.src))));
          serverNotices(res.notices);
          if (res.next === "handoff") renderHandoff(d.concept, "Bạn đã thử 2 câu kiểm tra mà vẫn vướng.", res.handoff);
          else if (res.response) renderResp(res.response, { lead: "Giải thích lại theo cách khác" });
        }
        renderNotebook();
      }).catch(liveFail);
    }

    function choose(k) {
      if (LIVE) return chooseLive(k);
      lockAll();
      const g = E.gradeCheck(q, k);
      const idx = q.options.findIndex((o) => o.k === k);
      const rightIdx = q.options.findIndex((o) => o.correct);
      opts[idx].classList.add(g.correct ? "right" : "wrong");
      if (!g.correct) opts[rightIdx].classList.add("right");
      S.session.checkAttempt[d.concept] = (S.session.checkAttempt[d.concept] || 0) + 1;

      if (g.correct) {
        card.appendChild(h("div", { class: "result ok" }, [h("b", { text: "Chính xác! " }), "Bạn đã nắm đúng ý này của bài. "].concat(citeButtons(q.src))));
        applyProfileEvent({ type: "check_correct", concept: d.concept });
        addAi([
          h("p", { text: "Bạn muốn làm gì tiếp?" }),
          h("div", { class: "toolbar", style: "border:0;padding-top:0;margin-top:0" }, [
            h("button", { class: "chip", text: "Xem Lab demo self-attention", onclick: () => openSource("T06-160") }),
            h("button", { class: "chip", text: "Hỏi về multi-head", onclick: () => ask("Multi-head attention là gì?") }),
            h("button", { class: "chip", text: "Thêm 1 câu kiểm tra", onclick: () => { const nq = E.pickCheck(d.concept, S.session.checkAttempt[d.concept]); renderCheck(d, nq, "Câu tiếp theo:"); } }),
          ]),
        ], { plain: true });
        return;
      }

      S.session.wrong[d.concept] = (S.session.wrong[d.concept] || 0) + 1;
      applyProfileEvent({ type: "check_wrong", concept: d.concept });
      const fix = g.misconception
        ? h("div", { class: "result no" }, [h("b", { text: "Chưa đúng — chỗ này hay bị hiểu lệch. " }), h("span", { html: g.misconception.fix }), " "].concat(citeButtons(g.misconception.src)))
        : h("div", { class: "result no" }, [h("b", { text: "Chưa đúng. " }), "Đáp án là " + g.right.k + ". "].concat(citeButtons(q.src)));
      card.appendChild(fix);

      if (S.session.wrong[d.concept] >= 2) return renderHandoff(d.concept, "Bạn đã thử 2 câu kiểm tra mà vẫn vướng.");
      const nd = Object.assign({}, d, {
        full: true, level: E.rank(d.level) >= 2 ? "L2" : d.level, style: E.nextStyle(d.style), prereq_first: null,
        reason_for_user: "Mình đổi sang cách “" + C.STYLE_LABEL[E.nextStyle(d.style)] + "” để làm rõ đúng chỗ bạn vừa chọn sai.",
      });
      const t = typing();
      setTimeout(() => { t.remove(); renderAnswer(nd, { lead: "Giải thích lại theo cách khác", altExample: true }); }, 600);
    }
  }

  /* ---------------- Chuyển TA ---------------- */
  function renderHandoff(conceptId, why, serverDraft) {
    const concept = C.CONCEPTS[conceptId] || { term: "nội dung này" };
    const tried = (S.session.tried[conceptId] || []).filter((v, i, a) => a.indexOf(v) === i);
    const draft = serverDraft || "Mình đang học " + concept.term + " (Day 1 · LLM Foundation). Mình chưa hiểu: “" + (S.session.lastQuestion || concept.term) + "”." +
      (tried.length ? " Trợ giảng AI đã giải thích theo kiểu: " + tried.join(", ") + "." : "") +
      " Mình cần được giải thích thêm phần này.";
    const ta = h("textarea", { "aria-label": "Câu hỏi soạn sẵn cho TA" });
    ta.value = draft;
    addAi([
      h("div", { class: "why" }, [icon("i-info", 16), h("span", { text: why + " Mình dừng ở đây để không làm bạn mất thêm thời gian." })]),
      h("p", { html: "Bạn nên hỏi <b>TA</b> phần này. Mình đã soạn sẵn câu hỏi — <b>không kèm tên của bạn</b>, bạn sửa rồi tự gửi nhé." }),
      h("div", { class: "handoff" }, [ta]),
      h("div", { class: "toolbar", style: "border:0" }, [
        h("button", { class: "chip solid", text: "Sao chép câu hỏi", onclick: () => copyText(ta.value) }),
        h("button", { class: "chip", text: "Mở kênh hỏi đáp Discord", onclick: () => toast("Mock: không gửi thật — bạn dán câu hỏi vào kênh hỏi đáp của lớp.") }),
        h("button", { class: "chip", text: "Xem đoạn gốc [T06-129]", onclick: () => openSource("T06-129") }),
      ]),
    ]);
  }

  function copyText(t) {
    const done = () => toast("Đã sao chép câu hỏi");
    try {
      navigator.clipboard.writeText(t).then(done, () => toast("Không sao chép được — bạn bôi đen rồi copy nhé"));
    } catch (e) { toast("Không sao chép được — bạn bôi đen rồi copy nhé"); }
  }

  /* ---------------- Ngoài phạm vi / không có nguồn ---------------- */
  function renderScope(d, intent) {
    const suggest = h("div", { class: "toolbar", style: "border:0" }, [
      h("button", { class: "chip", text: "Self-attention là gì?", onclick: () => ask("Self-attention là gì?") }),
      h("button", { class: "chip", text: "Q, K, V khác nhau thế nào?", onclick: () => ask("Q, K, V khác nhau thế nào?") }),
    ]);
    if (d.kind === "no_source") {
      const term = (intent.raw.match(/react|rag|lora|fine-?tun\w*|diffusion|cnn|agent loop|tool call\w*|function call\w*/i) || ["Khái niệm này"])[0];
      addAi([
        h("div", { class: "why" }, [icon("i-info", 16), h("span", { text: d.reason_for_user })]),
        h("p", { html: "<b>" + esc(term) + "</b> chưa có trong bài giảng buổi này, nên mình <b>không giải thích để tránh đoán sai</b>." }),
        h("p", null, ["Gần nhất trong Day 1 là phần “Từ mô hình đến AI agent” (mức tổng quan) "].concat(citeButtons(["T04-073"]), ["."])),
        h("div", { class: "toolbar", style: "border:0" }, [
          h("button", { class: "chip solid", text: "Soạn câu hỏi cho TA", onclick: () => { S.session.lastQuestion = intent.raw; renderHandoff(null, "Câu hỏi nằm ngoài tài liệu buổi này."); } }),
        ]),
        suggest,
        trace(d),
      ]);
      return;
    }
    const inj = d.kind === "injection";
    addAi([
      h("div", { class: "why" }, [icon("i-shield", 16), h("span", { text: inj ? "Tin nhắn có yêu cầu thay đổi hướng dẫn của trợ giảng — mình coi đó là nội dung, không làm theo." : d.reason_for_user })]),
      h("p", { html: "Mình chỉ giúp <b>giải thích nội dung bài đang học</b> (Self-attention, Day 1). " + (inj || /blog/i.test(intent.raw) ? "Viết bài blog hay làm bài thay bạn nằm ngoài phạm vi này." : "Câu hỏi về điểm danh, deadline hay XP bạn xem thông báo chính thức hoặc hỏi TA nhé.") }),
      h("p", { text: "Bạn có thể thử:" }),
      suggest,
      trace(d),
    ]);
  }

  function renderHelp() {
    addAi([
      h("p", { html: "Mình là trợ giảng cho bài <b>Self-attention</b>. Bạn có thể bôi đen một đoạn trong bài rồi bấm <b>Hỏi Trợ giảng AI</b>, hoặc hỏi thẳng:" }),
      h("div", { class: "toolbar", style: "border:0;padding-top:0" }, [
        h("button", { class: "chip", text: "Self-attention là gì?", onclick: () => ask("Self-attention là gì?") }),
        h("button", { class: "chip", text: "Vector là gì?", onclick: () => ask("Vector là gì?") }),
        h("button", { class: "chip", text: "Multi-head attention là gì?", onclick: () => ask("Multi-head attention là gì?") }),
      ]),
    ], { plain: true });
  }

  /* ---------------- Đoạn nguồn ---------------- */
  function openSource(id) {
    const box = $("#srcContent");
    box.innerHTML = "";
    if (LIVE) {
      API.source(id).then((src) => {
        $("#srcTitle").textContent = "Đoạn gốc · " + id;
        box.appendChild(h("div", { class: "src-meta", text: src.section + (src.mode === "local" ? " · nguyên văn từ data pack (chỉ trên máy chạy backend)" : " · tóm tắt") }));
        box.appendChild(h("div", { class: "src-text", text: src.text }));
        openOverlay("#sourceView");
      }).catch(liveFail);
      return;
    }
    const local = LOCAL_SRC && LOCAL_SRC[id];
    $("#srcTitle").textContent = "Đoạn gốc · " + id;
    box.appendChild(h("div", { class: "src-meta", text: (id.startsWith("T04") ? "Transcript Day 1 — Foundation (phần 1)" : "Transcript buổi Foundation — transformer & attention") + (local ? " · nguyên văn từ data pack (chỉ trên máy bạn)" : "") }));
    box.appendChild(h("div", { class: "src-text", text: local ? local.text : C.SOURCE_SUMMARIES[id] || "Không có tóm tắt." }));
    if (!local) box.appendChild(h("p", { class: "muted", html: "Đang hiện <b>tóm tắt</b>. Chạy <code>python scripts/build_local_data.py</code> để xem nguyên văn trên máy (file sinh ra không được commit)." }));
    openOverlay("#sourceView");
  }

  /* ---------------- Sổ tay học tập ---------------- */
  function renderNotebook() {
    const box = $("#nbContent");
    if (!box) return;
    if (LIVE) {
      API.profile(liveUser()).then((prof) => renderNotebookLive(box, prof)).catch(() => {});
      return;
    }
    box.innerHTML = "";
    const p = profile();
    const toggle = h("input", { type: "checkbox", id: "memToggle" });
    toggle.checked = S.memoryOn;
    toggle.addEventListener("change", () => {
      S.memoryOn = toggle.checked;
      save();
      renderDemo();
      toast(S.memoryOn ? "Đã bật ghi nhớ" : "Đã tắt ghi nhớ — trợ giảng coi như chưa có hồ sơ");
    });
    box.appendChild(h("label", { class: "switch", for: "memToggle" }, [toggle, "Cho phép Trợ giảng AI ghi nhớ mức hiểu của mình"]));
    box.appendChild(h("div", { class: "privacy" }, [icon("i-shield", 18), h("span", { html: "Chỉ <b>bạn</b> xem được Sổ tay này. Nó không dùng để chấm điểm và không hiện cho người khác. Mức chỉ <b>tăng</b> khi bạn trả lời đúng 2 lần liên tiếp; bạn nói “chưa hiểu” thì mức <b>giảm ngay</b>." })]));

    const table = h("table", { class: "ptable" }, [h("tr", null, ["Khái niệm", "Mức", "Căn cứ gần nhất", ""].map((t) => h("th", { text: t })))]);
    Object.values(C.CONCEPTS).forEach((c) => {
      const row = p[c.id];
      const sel = h("select", { "aria-label": "Mức " + c.term });
      [["", "— chưa có —"], ["chua", "Chưa"], ["biet_so", "Biết sơ"], ["hieu_ro", "Hiểu rõ"]].forEach(([v, t]) => {
        const o = h("option", { value: v, text: t });
        if ((row && row.level ? row.level : "") === v) o.selected = true;
        sel.appendChild(o);
      });
      sel.addEventListener("change", () => {
        if (!sel.value) return;
        const r = E.applyEvent(profile(), { type: "manual", concept: c.id, level: sel.value });
        setProfile(r.profile);
        toast("Đã đổi " + c.term + " → " + C.PROFILE_LABEL[sel.value]);
      });
      const EV = { self_report: "bạn tự khai", manual: "bạn tự đổi", confused: "bạn nói chưa hiểu", level_down: "bạn hạ mức", check_correct: "trả lời đúng", check_wrong: "trả lời sai" };
      const SRC = { tu_khai: "hồ sơ mẫu · tự khai", kiem_tra: "hồ sơ mẫu · kiểm tra", doi_muc: "đổi mức", tu_doi: "bạn tự đổi" };
      let ev = "—";
      if (row && row.evidence && row.evidence.length) {
        const [type, day] = row.evidence[row.evidence.length - 1].split("@");
        ev = (EV[type] || type) + " · " + day.split("-").reverse().slice(0, 2).join("/");
      } else if (row) ev = SRC[row.source] || "hồ sơ mẫu";
      table.appendChild(h("tr", null, [
        h("td", null, [h("b", { text: c.term }), h("div", { class: "muted", text: c.viName })]),
        h("td", null, [sel]),
        h("td", { class: "muted", text: ev + (row && row.streak ? " · chuỗi đúng: " + row.streak : "") }),
        h("td", null, row ? [h("button", { class: "chip ghost", text: "Xoá", onclick: () => { const r = E.applyEvent(profile(), { type: "delete", concept: c.id }); setProfile(r.profile); toast(r.notice); } })] : []),
      ]));
    });
    box.appendChild(table);

    const styleSel = h("select", { "aria-label": "Kiểu giải thích ưa thích" });
    [["", "— để trợ giảng tự chọn —"], ["vi_du", C.STYLE_LABEL.vi_du], ["ngan_gon", C.STYLE_LABEL.ngan_gon], ["chi_tiet", C.STYLE_LABEL.chi_tiet]].forEach(([v, t]) => {
      const o = h("option", { value: v, text: t });
      if ((prefStyle() || "") === v) o.selected = true;
      styleSel.appendChild(o);
    });
    styleSel.addEventListener("change", () => { S.styles[S.personaId] = styleSel.value || null; save(); toast("Đã lưu kiểu giải thích"); });
    box.appendChild(h("p", { style: "margin-top:14px" }, ["Kiểu giải thích mình thích: ", styleSel]));
    box.appendChild(h("div", { class: "toolbar" }, [
      h("button", { class: "chip ghost", text: "Xoá toàn bộ Sổ tay", onclick: () => { if (confirm("Xoá toàn bộ mức hiểu đã lưu?")) { setProfile({}); S.styles[S.personaId] = null; save(); toast("Đã xoá toàn bộ Sổ tay"); } } }),
    ]));
  }

  const STRATEGY_LABEL = {
    "style:vi_du": "giải thích bằng ví dụ đời thường", "style:ngan_gon": "giải thích ngắn gọn từng bước",
    "style:chi_tiet": "giải thích chi tiết kỹ thuật", "analogy:thu_vien": "ví dụ thư viện",
    "analogy:con_meo": "ví dụ “con mèo ngồi trên bàn”", "analogy:thay_boi": "ví dụ thầy bói xem voi", "analogy:gps": "ví dụ toạ độ GPS",
  };

  function renderNotebookLive(box, prof) {
    const user = liveUser();
    const refresh = (p) => renderNotebookLive(box, p.profile || p);
    box.innerHTML = "";
    const toggle = h("input", { type: "checkbox", id: "memToggle" });
    toggle.checked = prof.memory_on;
    toggle.addEventListener("change", () => API.putProfile({ user_id: user, memory_on: toggle.checked }).then((p) => {
      refresh(p);
      toast(toggle.checked ? "Đã bật ghi nhớ" : "Đã tắt ghi nhớ — trợ giảng coi như chưa có hồ sơ");
    }).catch(liveFail));
    box.appendChild(h("label", { class: "switch", for: "memToggle" }, [toggle, "Cho phép Trợ giảng AI ghi nhớ mức hiểu của mình"]));
    box.appendChild(h("div", { class: "privacy" }, [icon("i-shield", 18), h("span", { html: "Chỉ <b>bạn</b> xem được Sổ tay này. Nó không dùng để chấm điểm. Mức chỉ <b>tăng</b> khi bạn trả lời đúng 2 lần liên tiếp; nói “chưa hiểu” thì <b>giảm ngay</b>. Quá 14 ngày không ôn, trợ giảng sẽ giải thích lại từ nền hơn." })]));

    const EV = { self_report: "bạn tự khai", manual: "bạn tự đổi", confused: "bạn nói chưa hiểu", level_down: "bạn hạ mức", check_correct: "trả lời đúng", check_wrong: "trả lời sai", strategy_worked: "cách giải thích hiệu quả", strategy_failed: "cách giải thích chưa hợp" };
    const table = h("table", { class: "ptable" }, [h("tr", null, ["Khái niệm", "Mức", "Căn cứ gần nhất", ""].map((t) => h("th", { text: t })))]);
    Object.values(C.CONCEPTS).forEach((c) => {
      const row = prof.concepts[c.id];
      const sel = h("select", { "aria-label": "Mức " + c.term });
      [["", "— chưa có —"], ["chua", "Chưa"], ["biet_so", "Biết sơ"], ["hieu_ro", "Hiểu rõ"]].forEach(([v, t]) => {
        const o = h("option", { value: v, text: t });
        if ((row && row.level ? row.level : "") === v) o.selected = true;
        sel.appendChild(o);
      });
      sel.addEventListener("change", () => {
        if (!sel.value) return;
        API.putProfile({ user_id: user, concept: c.id, level: sel.value }).then((p) => { refresh(p); toast("Đã đổi " + c.term + " → " + C.PROFILE_LABEL[sel.value]); }).catch(liveFail);
      });
      let ev = "—";
      if (row && row.evidence && row.evidence.length) {
        const [type, day] = row.evidence[0].split("@");
        ev = (EV[type] || type) + " · " + day.split("-").reverse().slice(0, 2).join("/");
      } else if (row) ev = "hồ sơ mẫu";
      if (row && row.stale) ev += " · đã lâu chưa ôn";
      const strat = prof.strategies[c.id];
      const stratLine = [];
      if (strat) {
        strat.worked.forEach((sname) => stratLine.push(h("span", { class: "lvl hieu_ro", text: "Giúp bạn hiểu: " + (STRATEGY_LABEL[sname] || sname) })));
        strat.failed.forEach((sname) => stratLine.push(h("span", { class: "lvl chua", text: "Tránh: " + (STRATEGY_LABEL[sname] || sname) }, [])));
      }
      table.appendChild(h("tr", null, [
        h("td", null, [h("b", { text: c.term }), h("div", { class: "muted", text: c.viName })].concat(stratLine.length ? [h("div", { style: "display:flex;flex-wrap:wrap;gap:4px;margin-top:4px" }, stratLine.concat([
          h("button", { class: "chip ghost", text: "Xoá cách giải thích", onclick: () => Promise.all(strat.worked.concat(strat.failed).map((sname) => API.deleteStrategy(user, c.id, sname))).then((all) => refresh(all[all.length - 1])).catch(liveFail) }),
        ]))] : [])),
        h("td", null, [sel]),
        h("td", { class: "muted", text: ev + (row && row.streak ? " · chuỗi đúng: " + row.streak : "") }),
        h("td", null, row ? [h("button", { class: "chip ghost", text: "Xoá", onclick: () => API.deleteProfile(user, c.id).then((p) => { refresh(p); toast("Đã xoá " + c.term + " khỏi Sổ tay."); }).catch(liveFail) })] : []),
      ]));
    });
    box.appendChild(table);

    const styleSel = h("select", { "aria-label": "Kiểu giải thích ưa thích" });
    [["", "— để trợ giảng tự chọn —"], ["vi_du", C.STYLE_LABEL.vi_du], ["ngan_gon", C.STYLE_LABEL.ngan_gon], ["chi_tiet", C.STYLE_LABEL.chi_tiet]].forEach(([v, t]) => {
      const o = h("option", { value: v, text: t });
      if ((prof.preferred_style || "") === v) o.selected = true;
      styleSel.appendChild(o);
    });
    styleSel.addEventListener("change", () => API.putProfile(styleSel.value ? { user_id: user, preferred_style: styleSel.value } : { user_id: user, clear_style: true })
      .then((p) => { refresh(p); toast("Đã lưu kiểu giải thích"); }).catch(liveFail));
    box.appendChild(h("p", { style: "margin-top:14px" }, ["Kiểu giải thích mình thích: ", styleSel]));
    box.appendChild(h("div", { class: "toolbar" }, [
      h("button", { class: "chip ghost", text: "Xoá toàn bộ Sổ tay", onclick: () => { if (confirm("Xoá toàn bộ mức hiểu đã lưu?")) API.deleteProfile(user).then((p) => { refresh(p); toast("Đã xoá toàn bộ Sổ tay"); }).catch(liveFail); } }),
    ]));
  }

  function openOverlay(sel) {
    const o = $(sel);
    o.classList.add("open");
    const btn = $("[data-close]", o);
    if (btn) btn.focus();
  }
  document.querySelectorAll(".overlay").forEach((o) => {
    o.addEventListener("click", (e) => { if (e.target === o || e.target.closest("[data-close]")) o.classList.remove("open"); });
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") document.querySelectorAll(".overlay.open").forEach((o) => o.classList.remove("open"));
  });

  /* ---------------- Bảng demo ---------------- */
  function renderDemo() {
    const box = $("#demo");
    box.innerHTML = "";
    if (LIVE) {
      box.appendChild(h("div", { style: "margin:0 0 10px;padding:6px 8px;border-radius:8px;background:#203656;color:#cfe0ff", text: "Đang dùng backend · provider: " + (LIVE_INFO.provider || "…") }));
    }
    if (root.P3_ACCOUNT) {
      box.appendChild(h("div", { style: "margin:0 0 10px;padding:6px 8px;border-radius:8px;background:#e9f6ee;color:#1d7f47" },
        ["Đang dùng tài khoản: " + (root.P3_ACCOUNT.display_name || root.P3_ACCOUNT.email) + " — hồ sơ và bộ nhớ dài hạn lưu theo tài khoản này."]));
    }
    box.appendChild(h("h4", { text: root.P3_ACCOUNT ? "Hồ sơ giả lập (chỉ dùng khi chưa đăng nhập)" : "Hồ sơ giả lập" }));
    const grid = h("div", { class: "personas" });
    Object.entries(C.PERSONAS).forEach(([id, p]) => {
      grid.appendChild(h("button", { "aria-pressed": String(S.personaId === id), onclick: () => switchPersona(id) }, [p.label, h("small", { text: p.note })]));
    });
    if (LIVE && LIVE_INFO.personas) {
      const known = Object.keys(C.PERSONAS).map((k) => API.userFor(k));
      Object.entries(LIVE_INFO.personas).filter(([uid]) => !known.includes(uid)).forEach(([uid, p]) => {
        grid.appendChild(h("button", { "aria-pressed": String(S.personaId === uid), onclick: () => switchPersona(uid) }, [p.label, h("small", { text: "Bộ nhớ dài hạn (backend)" })]));
      });
    }
    box.appendChild(grid);
    box.appendChild(h("div", { style: "margin:-4px 0 10px;color:#93a3ba", text: LIVE ? "Ghi nhớ: xem và đổi trong Sổ tay" : "Ghi nhớ: " + (S.memoryOn ? "đang bật" : "đang tắt") + " · đổi trong Sổ tay" }));
    const dev = h("input", { type: "checkbox", id: "devToggle" });
    dev.checked = S.devMode;
    dev.addEventListener("change", () => { S.devMode = dev.checked; document.body.classList.toggle("dev", S.devMode); save(); });
    box.appendChild(h("label", { for: "devToggle", style: "display:flex;gap:8px;align-items:center;margin:0 0 12px;cursor:pointer" }, [dev, "Chế độ giám khảo: hiện JSON quyết định (mức 1–5)"]));
    box.appendChild(h("h4", { text: "Kịch bản (bấm để hỏi)" }));
    C.SCENARIOS.forEach((sc) => {
      box.appendChild(h("button", { class: "scen", onclick: () => runScenario(sc) }, [h("b", { text: "KB" + sc.id }), sc.label, h("div", { style: "color:#93a3ba;margin-top:2px", text: "“" + sc.text + "”" })]));
    });
    box.appendChild(h("div", { style: "color:#93a3ba;margin-top:6px", html: "KB2: sau câu trả lời đầu, bấm <b>Mình chưa hiểu</b>. KB7: ở câu kiểm tra, chọn sai 2 lần → chuyển TA. Bôi đen đoạn trong bài để hỏi theo ngữ cảnh." }));
    box.appendChild(h("div", { class: "row" }, [
      h("button", { text: "Khôi phục hồ sơ mẫu", onclick: () => {
        if (LIVE) return API.reset(liveUser()).then(() => { renderNotebook(); toast("Đã khôi phục hồ sơ mẫu"); }).catch(liveFail);
        delete S.profiles[S.personaId]; delete S.styles[S.personaId]; save(); renderNotebook(); toast("Đã khôi phục hồ sơ mẫu");
      } }),
      h("button", { text: "Chat mới", onclick: newChat }),
    ]));
  }

  function switchPersona(id) {
    S.personaId = id;
    save();
    renderDemo();
    renderNotebook();
    newChat();
    const label = C.PERSONAS[id] ? C.PERSONAS[id].label : ((LIVE_INFO.personas || {})[id] || {}).label || id;
    toast("Đang dùng hồ sơ: " + label);
  }

  function runScenario(sc) {
    if (sc.persona && sc.persona !== S.personaId) switchPersona(sc.persona);
    else newChat();
    showTutor(true);
    setTimeout(() => ask(sc.text, { selection: "" }), 150);
  }

  /* ---------------- Bôi đen đoạn trong bài để hỏi ---------------- */
  // Bôi đen bất kỳ đoạn nào trong thân bài → hiện nút "Hỏi Trợ giảng AI" ngay trên vùng vừa chọn.
  // Bấm nút thì đoạn đó thành ngữ cảnh cho câu hỏi kế tiếp (gửi kèm ở trường `selection`).
  const pop = $("#selPop");
  const SEL_MAX = 280;              // dài hơn thì cắt bớt, không chặn học viên hỏi
  const lessonBody = $("#lessonBody");

  function clearSelection() {
    S.selection = "";
    $("#selChip").hidden = true;
    const box = $("#input");
    if (box) box.placeholder = "Hỏi bất cứ điều gì...";
  }
  function hidePop() { pop.style.display = "none"; }

  function selectionInLesson() {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || !sel.rangeCount) return null;
    const text = sel.toString().trim().replace(/\s+/g, " ");
    if (text.length < 2) return null;
    // Chỉ nhận vùng bôi đen nằm trong thân bài — bôi đen trong khung chat thì bỏ qua.
    const node = sel.anchorNode;
    if (!node || !lessonBody.contains(node.nodeType === 1 ? node : node.parentNode)) return null;
    return { text, rect: sel.getRangeAt(0).getBoundingClientRect() };
  }

  function showPopForSelection() {
    const found = selectionInLesson();
    if (!found) return hidePop();
    const full = found.text;
    // Bôi đen cả trang vẫn hỏi được: lấy phần đầu làm ngữ cảnh thay vì từ chối.
    pop.dataset.text = full.length > SEL_MAX ? full.slice(0, SEL_MAX).replace(/\s+\S*$/, "") + "…" : full;
    pop.dataset.trimmed = full.length > SEL_MAX ? "1" : "";
    const r = found.rect;
    const w = 170;
    pop.style.display = "inline-flex";
    pop.style.top = (r.top > 110 ? r.top - 44 : r.bottom + 10) + "px";
    pop.style.left = Math.max(12, Math.min(window.innerWidth - w - 12, r.left + r.width / 2 - w / 2)) + "px";
  }

  // mouseup cho chuột, touchend cho điện thoại, keyup cho bôi đen bằng Shift + phím mũi tên.
  ["mouseup", "touchend"].forEach((ev) => lessonBody.addEventListener(ev, () => setTimeout(showPopForSelection, 10)));
  lessonBody.addEventListener("keyup", (e) => { if (e.shiftKey || e.key === "Shift") setTimeout(showPopForSelection, 10); });
  document.addEventListener("mousedown", (e) => { if (!pop.contains(e.target)) hidePop(); });
  document.addEventListener("scroll", hidePop, true);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") hidePop(); });

  function askAboutSelection() {
    S.selection = pop.dataset.text || "";
    if (!S.selection) return;
    $("#selText").textContent = "Đoạn đã chọn: “" + S.selection + "”";
    $("#selChip").hidden = false;
    hidePop();
    showTutor(true);
    if (pop.dataset.trimmed) toast("Đoạn khá dài — mình lấy phần đầu làm ngữ cảnh.");
    const box = $("#input");
    box.placeholder = "Bạn chưa hiểu chỗ nào trong đoạn này?";
    box.focus();
  }
  pop.addEventListener("click", askAboutSelection);
  $("#selClear").addEventListener("click", clearSelection);

  /* ---------------- Khung chat: điều khiển ---------------- */
  function newChat() {
    if (LIVE) API.newSession();
    S.session = freshSession();
    S.survey = null;
    clearSelection();
    greeting();
  }
  function showTutor(on) {
    $("#tutor").hidden = !on;
    $("#askAiBtn").classList.toggle("active", on);
    $("#askAiBtn").setAttribute("aria-pressed", String(on));
  }

  $("#composer").addEventListener("submit", (e) => {
    e.preventDefault();
    const v = $("#input").value.trim();
    if (!v) return;
    $("#input").value = "";
    $("#sendBtn").classList.remove("ready");
    ask(v);
  });
  $("#input").addEventListener("input", (e) => $("#sendBtn").classList.toggle("ready", !!e.target.value.trim()));
  $("#newChat").addEventListener("click", newChat);
  $("#historyBtn").addEventListener("click", () => toast("Lịch sử chat chưa có trong bản mock"));
  $("#wideBtn").addEventListener("click", () => $("#tutor").classList.toggle("wide"));
  $("#closeTutor").addEventListener("click", () => showTutor(false));
  $("#askAiBtn").addEventListener("click", () => showTutor($("#tutor").hidden));
  $("#requestBtn").addEventListener("click", () => toast("Gửi yêu cầu cho BTC — ngoài phạm vi mock"));
  $("#notebookBtn").addEventListener("click", () => { renderNotebook(); openOverlay("#notebook"); });
  $("#openNotebookSide").addEventListener("click", () => { renderNotebook(); openOverlay("#notebook"); });
  $("#demoToggle").addEventListener("click", (e) => {
    const open = $("#demo").classList.toggle("open");
    e.currentTarget.setAttribute("aria-expanded", String(open));
  });

  /* ---------------- Cầu nối cho lessons.js / auth.js ---------------- */
  root.P3_APP = {
    newChat,
    greeting,
    renderNotebook,
    renderDemo,
    showTutor,
    ask,
    openSource,
    user: liveUser,
    setUser(info) {           // gọi khi đăng nhập / đăng xuất
      DEMO_USER.name = (info && info.name) || "bạn";
      DEMO_USER.initial = (info && info.initial) || "?";
      const av = $("#topAvatar");
      if (av) av.textContent = DEMO_USER.initial;
      greeting();
      renderNotebook();
    },
    onLesson() {              // gọi khi đổi buổi học
      newChat();
    },
  };

  /* ---------------- Khởi động ---------------- */
  load();
  document.body.classList.toggle("dev", S.devMode);
  $("#topAvatar").textContent = DEMO_USER.initial;
  renderSidebar();
  renderDemo();
  renderNotebook();
  greeting();
  if (window.innerWidth < 820) showTutor(false);
  if (LIVE) {
    API.health().then((hh) => { LIVE_INFO.provider = hh.provider + (hh.model && hh.model !== "fake" ? " · " + hh.model : ""); renderDemo(); }).catch(liveFail);
    API.personas().then((ps) => { LIVE_INFO.personas = ps; renderDemo(); }).catch(() => {});
  }
})(window);
