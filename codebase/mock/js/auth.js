/*
 * Tài khoản học viên: đăng ký, đăng nhập, đăng xuất, đổi tên hiển thị, xoá tài khoản.
 * Vì sao cần: hồ sơ mức hiểu và bộ nhớ dài hạn ("cách giải thích nào đã hiệu quả với bạn")
 * được lưu theo user_id của tài khoản, nên mỗi người đăng nhập sẽ thấy đúng dữ liệu của mình.
 */
(function (root) {
  "use strict";

  const API = root.P3_API;
  const $ = (s, el) => (el || document).querySelector(s);

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

  const initial = (acc) => ((acc.display_name || acc.email || "?").trim()[0] || "?").toUpperCase();

  function setAccount(acc) {
    root.P3_ACCOUNT = acc || null;
    const btn = $("#topAvatar");
    if (btn) {
      btn.textContent = acc ? initial(acc) : "?";
      btn.classList.toggle("signed", !!acc);
      btn.title = acc ? acc.display_name + " · " + acc.email : "Đăng nhập";
    }
    if (root.P3_APP) root.P3_APP.setUser(acc ? { name: acc.display_name || acc.email, initial: initial(acc) } : null);
    renderMenu();
  }

  /* ------------------------------------------------------------- menu tài khoản */
  function renderMenu() {
    const box = $("#accountMenu");
    if (!box) return;
    const acc = root.P3_ACCOUNT;
    box.innerHTML = "";
    if (!acc) {
      box.appendChild(h("div", { class: "am-head", text: "Chưa đăng nhập" }));
      box.appendChild(h("p", { class: "am-note", text: "Đăng nhập để lưu mức hiểu và cách giải thích hợp với bạn." }));
      box.appendChild(h("button", { class: "btn primary", text: "Đăng nhập / Đăng ký", onclick: () => openAuth("login") }));
      return;
    }
    box.appendChild(h("div", { class: "am-head" }, [h("b", { text: acc.display_name || acc.email }), h("span", { text: acc.email })]));
    const nameInput = h("input", { id: "accName", value: acc.display_name || "", placeholder: "Tên hiển thị" });
    box.appendChild(h("label", { class: "am-field" }, ["Tên hiển thị", nameInput]));
    box.appendChild(h("button", {
      class: "btn", text: "Lưu tên", onclick: async () => {
        try {
          const res = await API.updateAccount({ display_name: nameInput.value });
          setAccount(res.account);
          toast("Đã lưu tên hiển thị");
        } catch (e) { toast(e.message); }
      },
    }));
    box.appendChild(h("button", {
      class: "btn", text: "Đẩy bộ nhớ lên Supabase", title: "Gửi ngay phần bộ nhớ dài hạn đang chờ",
      onclick: async () => {
        try {
          const res = await API.flushMemory();
          toast(res.memory && res.memory.remote ? "Đã đẩy " + res.pushed + " dòng lên Supabase" : "Chưa cấu hình Supabase — bộ nhớ đang lưu trên máy");
        } catch (e) { toast(e.message); }
      },
    }));
    box.appendChild(h("button", {
      class: "btn", text: "Đăng xuất", onclick: async () => {
        try { await API.logout(); } catch (e) { /* vẫn đăng xuất phía trình duyệt */ }
        API.setToken(null);
        setAccount(null);
        toast("Đã đăng xuất");
      },
    }));
    box.appendChild(h("button", {
      class: "btn danger", text: "Xoá tài khoản và dữ liệu", onclick: async () => {
        if (!root.confirm("Xoá tài khoản này cùng toàn bộ hồ sơ và bộ nhớ dài hạn?")) return;
        try {
          await API.deleteAccount();
          API.setToken(null);
          setAccount(null);
          toast("Đã xoá tài khoản");
        } catch (e) { toast(e.message); }
      },
    }));
  }

  function toast(text) {
    const el = $("#toast");
    if (!el) return;
    el.textContent = text;
    el.classList.add("show");
    setTimeout(() => el.classList.remove("show"), 2600);
  }

  /* --------------------------------------------------------------- form đăng nhập */
  function openAuth(tab) {
    const box = $("#authBody");
    const overlay = $("#authOverlay");
    if (!box || !overlay) return;
    let mode = tab || "login";
    const err = h("div", { class: "auth-err", hidden: "hidden" });

    function render() {
      box.innerHTML = "";
      box.appendChild(h("div", { class: "auth-tabs" }, [
        h("button", { class: mode === "login" ? "active" : "", text: "Đăng nhập", onclick: () => { mode = "login"; render(); } }),
        h("button", { class: mode === "register" ? "active" : "", text: "Đăng ký", onclick: () => { mode = "register"; render(); } }),
      ]));
      const email = h("input", { id: "authEmail", type: "email", placeholder: "email@vinuni.edu.vn", autocomplete: "email" });
      const pass = h("input", { id: "authPass", type: "password", placeholder: "Mật khẩu (ít nhất 8 ký tự)", autocomplete: mode === "login" ? "current-password" : "new-password" });
      const name = h("input", { id: "authName", placeholder: "Tên hiển thị (tuỳ chọn)" });
      const form = h("form", { class: "auth-form", onsubmit: (e) => { e.preventDefault(); submit(); } }, [
        h("label", {}, ["Email", email]),
        h("label", {}, ["Mật khẩu", pass]),
        mode === "register" ? h("label", {}, ["Tên hiển thị", name]) : null,
        err,
        h("button", { class: "btn primary", type: "submit", text: mode === "login" ? "Đăng nhập" : "Tạo tài khoản" }),
      ]);
      box.appendChild(form);
      box.appendChild(h("p", { class: "am-note", text: "Mật khẩu được băm PBKDF2 trước khi lưu. Hồ sơ học tập gắn với tài khoản này." }));
      setTimeout(() => email.focus(), 30);

      async function submit() {
        err.hidden = true;
        try {
          const res = mode === "login"
            ? await API.login(email.value.trim(), pass.value)
            : await API.register(email.value.trim(), pass.value, name.value.trim());
          API.setToken(res.token);
          setAccount(res.account);
          overlay.classList.remove("open");
          toast(mode === "login" ? "Chào bạn trở lại!" : "Đã tạo tài khoản — chúc học vui!");
        } catch (e) {
          err.hidden = false;
          err.textContent = e.message || "Không gọi được backend";
        }
      }
    }
    render();
    overlay.classList.add("open");
  }

  /* ----------------------------------------------------------------- khởi động */
  async function boot() {
    const btn = $("#topAvatar");
    if (btn) {
      btn.addEventListener("click", () => {
        const menu = $("#accountMenu");
        if (!menu) return;
        if (!root.P3_ACCOUNT) return openAuth("login");
        menu.classList.toggle("open");
      });
    }
    document.addEventListener("click", (e) => {
      const menu = $("#accountMenu");
      if (menu && menu.classList.contains("open") && !menu.contains(e.target) && e.target !== btn) menu.classList.remove("open");
    });
    if (!API || !API.LIVE) return;
    // Mở sẵn form đăng nhập khi vào bằng ?auth=1 (tiện khi demo)
    const wantAuth = new URLSearchParams(root.location.search).get("auth") === "1";
    if (!API.token()) {
      setAccount(null);
      if (wantAuth) openAuth("login");
      return;
    }
    try {
      const res = await API.me();
      setAccount(res.account);
    } catch (e) {
      API.setToken(null);
      setAccount(null);
    }
  }

  root.P3_AUTH = { openAuth, setAccount, boot };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})(window);
