/*
 * Danh mục 6 buổi học + phần thân bài, đọc từ backend (/api/lessons).
 * KHÔNG có nội dung bài giảng nào nằm trong repo: trang này chỉ hiển thị dữ liệu
 * mà backend đọc từ máy (codebase/data/chunks.local.json) hoặc từ Supabase.
 */
(function (root) {
  "use strict";

  const API = root.P3_API;
  const $ = (s, el) => (el || document).querySelector(s);
  const LAST_KEY = "vlearn.lesson";

  function h(tag, attrs, kids) {
    const el = document.createElement(tag);
    Object.entries(attrs || {}).forEach(([k, v]) => {
      if (v === null || v === undefined) return;
      if (k === "text") el.textContent = v;
      else if (k === "html") el.innerHTML = v;
      else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v);
    });
    (kids || []).filter(Boolean).forEach((c) => el.appendChild(typeof c === "string" ? document.createTextNode(c) : c));
    return el;
  }

  const SOURCE_LABEL = {
    local: "Dữ liệu bài giảng trên máy",
    supabase: "Dữ liệu bài giảng từ Supabase",
    summary: "Chưa có data pack — đang hiển thị tóm tắt của nhóm",
  };

  const state = { lessons: [], current: null, body: null };

  /* ------------------------------------------------------ danh sách buổi */
  function renderList() {
    const box = $("#lessonList");
    if (!box) return;
    box.innerHTML = "";
    state.lessons.forEach((l) => {
      const active = state.current && l.id === state.current.id;
      box.appendChild(h("button", {
        class: "lesson-row" + (active ? " active" : ""),
        "aria-current": active ? "true" : "false",
        onclick: () => open(l.id),
      }, [
        h("span", { class: "num", text: String(l.order) }),
        h("span", { class: "meta" }, [
          h("span", { class: "day", text: l.day }),
          h("span", { class: "title", text: l.title }),
        ]),
      ]));
    });
  }

  /* ----------------------------------------------------------- mục trong bài */
  function renderSections(data) {
    const box = $("#sideItems");
    if (!box) return;
    box.innerHTML = "";
    data.sections.forEach((s, i) => {
      box.appendChild(h("button", {
        class: "side-item", onclick: () => {
          const target = document.getElementById("sec-" + s.id);
          if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
          box.querySelectorAll(".side-item").forEach((b) => b.classList.remove("active"));
          box.children[i].classList.add("active");
        },
      }, [
        h("span", { class: "num", text: String(i + 1) }),
        h("span", { class: "label", text: s.title }),
        h("span", { class: "state", text: s.paragraphs.length + " đoạn" }),
      ]));
    });
    if (box.firstChild) box.firstChild.classList.add("active");
    const g = $("#sideGroupTitle");
    if (g) g.textContent = data.day + " · " + data.title;
  }

  /* ------------------------------------------------------------- thân bài */
  function renderBody(data) {
    const head = $("#lessonHead");
    if (head) {
      head.innerHTML = "";
      head.appendChild(h("div", { class: "crumb" }, [h("i"), data.day]));
      head.appendChild(h("h2", { text: data.title }));
      head.appendChild(h("span", { class: "tag", text: data.subtitle || "Bài học lý thuyết" }));
      const chips = h("div", { class: "concept-chips" }, data.concepts.map((c) =>
        h("button", { class: "chip", text: c.replace(/_/g, " "), title: "Hỏi trợ giảng về khái niệm này",
          onclick: () => askAbout(c) })));
      head.appendChild(chips);
      head.appendChild(h("div", { class: "data-badge " + data.source, text: SOURCE_LABEL[data.source] || data.source }));
    }
    const body = $("#lessonBody");
    if (!body) return;
    body.innerHTML = "";
    data.sections.forEach((s) => {
      const sec = h("section", { class: "lesson-section", id: "sec-" + s.id });
      sec.appendChild(h("h3", { text: s.title }));
      s.paragraphs.forEach((p) => {
        const para = h("p", {}, [
          p.text,
          h("button", {
            class: "src", title: "Xem đoạn gốc / hỏi trợ giảng về đoạn này", text: "[" + p.id + "]",
            onclick: () => askAboutParagraph(p),
          }),
        ]);
        sec.appendChild(para);
      });
      body.appendChild(sec);
    });
    const topTitle = $("#lessonDay");
    if (topTitle) topTitle.textContent = data.day + " · " + data.title;
    const prog = $(".progress");
    if (prog) {
      prog.childNodes[0].nodeValue = "Buổi " + data.order + "/" + state.lessons.length + " ";
      const bar = prog.querySelector(".bar");
      if (bar) bar.style.setProperty("--p", Math.round((data.order / state.lessons.length) * 100) + "%");
    }
  }

  function askAbout(conceptId) {
    const term = conceptId.replace(/_/g, " ");
    if (root.P3_APP) {
      root.P3_APP.showTutor(true);
      root.P3_APP.ask(term + " là gì?");
    }
  }

  function askAboutParagraph(p) {
    if (!root.P3_APP) return;
    root.P3_APP.showTutor(true);
    const snippet = p.text.slice(0, 160);
    root.P3_APP.ask("Mình chưa hiểu đoạn này, giải thích lại giúp mình.", { selection: snippet });
  }

  /* -------------------------------------------------------------- điều khiển */
  function starters(data) {
    const out = data.concepts.slice(0, 3).map((c) => c.replace(/_/g, " ") + " là gì?");
    return out.length ? out : ["Buổi này nói về gì?"];
  }

  async function open(lessonId) {
    const meta = state.lessons.find((l) => l.id === lessonId) || state.lessons[0];
    if (!meta) return;
    API.setLesson(meta.id);
    try { root.localStorage.setItem(LAST_KEY, meta.id); } catch (e) { /* bỏ qua */ }
    let data;
    try {
      data = await API.lessonBody(meta.id);
    } catch (e) {
      data = { id: meta.id, title: meta.title, day: meta.day, subtitle: meta.subtitle, concepts: [], sections: [], source: "summary" };
    }
    data.order = meta.order;
    state.current = meta;
    state.body = data;
    root.P3_LESSON_CTX = { id: data.id, title: data.title, concepts: data.concepts, starters: starters(data) };
    renderList();
    renderSections(data);
    renderBody(data);
    if (root.P3_APP) root.P3_APP.onLesson(data);
  }

  async function boot() {
    if (!API || !API.LIVE) return;
    try {
      const res = await API.lessons();
      state.lessons = res.lessons || [];
    } catch (e) {
      return;
    }
    renderList();
    let last = null;
    try { last = root.localStorage.getItem(LAST_KEY); } catch (e) { last = null; }
    const first = state.lessons.find((l) => l.id === last) || state.lessons[0];
    if (first) open(first.id);
  }

  root.P3_LESSONS = { boot, open, state };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})(window);
