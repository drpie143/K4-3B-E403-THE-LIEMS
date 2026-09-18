/*
 * Engine giả lập cho mock P3. Hàm thuần (không đụng DOM) để test bằng Node.
 *
 * Quyết định AI trung tâm (duy nhất): decide() — chọn mức + kiểu giải thích,
 * hoặc quyết định cần khảo sát. Ở CP3, phần thân decide()/composeAnswer()
 * được thay bằng 2 lời gọi LLM, còn validator checkFidelity() giữ nguyên.
 */
(function (root) {
  "use strict";

  const C = typeof module !== "undefined" && module.exports ? require("./content.js") : root.P3_CONTENT;
  const RANK = { chua: 0, biet_so: 1, hieu_ro: 2 };
  const LEVELS = ["L1", "L2", "L3", "L4", "L5"];
  const rank = (lvId) => LEVELS.indexOf(lvId);
  const stepLevel = (lvId, delta) => LEVELS[Math.min(LEVELS.length - 1, Math.max(0, rank(lvId) + delta))];
  const cap = (t) => t.charAt(0).toUpperCase() + t.slice(1);

  function norm(s) {
    return String(s || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/đ/g, "d")
      .replace(/Đ/g, "D")
      .toLowerCase();
  }

  const RX = {
    injection: /bo qua (moi |cac |tat ca )?(huong dan|chi dan)|ignore (all |the )?(previous|above)|system_override|system prompt|jailbreak/,
    outOfScope: /viet (mot |1 )?(bai )?blog|diem danh|deadline|han nop|\bxp\b|lam ho|giai ho|nop bai ho|lam bai ho/,
    notInLesson: /\breact\b|\brag\b|\blora\b|fine-?tun|diffusion|\bcnn\b|agent loop|tool call|function call/,
    confused: /chua hieu|khong hieu|ko hieu|k hieu|kho hieu|giai thich lai|chua ro|roi qua|don gian hon|de hieu hon|khong hieu gi/,
    weightedSum: /cong trong so|cong vao dau|tong co trong so|weighted sum/,
    concepts: [
      ["multi_head", /multi.?head|nhieu dau|nhieu con mat/],
      ["similarity", /similarity|diem tuong dong|do tuong dong/],
      ["vector", /\bvector\b|vecto|embedding|\bnhung\b/],
      ["self_attention", /attention|tu chu y|\bquery\b|\bkey\b|\bvalue\b|q\s*,?\s*k\s*,?\s*v|trong so/],
      ["token", /\btoken\b/],
    ],
  };

  /* ---------- 1. Hiểu câu hỏi (không phải quyết định AI, chỉ là tín hiệu) ---------- */
  function detect(text, selection, session) {
    const n = norm(text + " " + (selection || ""));
    const nq = norm(text);
    const out = { raw: text, injection: RX.injection.test(n), outOfScope: RX.outOfScope.test(nq), notInLesson: RX.notInLesson.test(nq) };
    out.confused = RX.confused.test(nq);
    out.weightedSum = RX.weightedSum.test(nq);
    out.concept = null;
    for (const [id, rx] of RX.concepts) {
      if (rx.test(n)) { out.concept = id; break; }
    }
    out.conceptFromPage = false;
    if (!out.concept && (out.confused || selection)) {
      out.concept = (session && session.lastConcept) || C.LESSON.pageConcept;
      out.conceptFromPage = true;
    }
    out.vague = out.confused && !RX.concepts.some(([, rx]) => rx.test(nq));
    const last = session && out.concept && session.answered ? session.answered[out.concept] : 0;
    const now = (session && session.now) || Date.now();
    out.reask = !!(last && !out.confused && now - last < 3 * 60 * 1000);
    return out;
  }

  /* ---------- 2. Quyết định trung tâm ---------- */
  function lv(profile, id) {
    return profile && profile[id] ? profile[id].level : null;
  }

  function confidenceOf(profile, conceptId, memoryOn) {
    if (!memoryOn) return 0.35;
    const ids = [conceptId].concat(C.CONCEPTS[conceptId] ? C.CONCEPTS[conceptId].prerequisites : []);
    const known = ids.filter((id) => lv(profile, id)).length;
    return Math.round((0.35 + 0.55 * (known / ids.length)) * 100) / 100;
  }

  function decide(intent, state) {
    const profile = state.memoryOn ? state.profile || {} : {};
    const base = { concept: intent.concept, in_scope: true, need_survey: false, source_ids: [] };

    if (intent.injection || intent.outOfScope) {
      return Object.assign(base, { in_scope: false, kind: intent.injection ? "injection" : "out_of_scope", confidence: 0.95, reason_for_user: "Yêu cầu này nằm ngoài việc giải thích bài đang học." });
    }
    if (intent.notInLesson) {
      return Object.assign(base, { in_scope: false, kind: "no_source", confidence: 0.9, reason_for_user: "Không tìm thấy đoạn nguồn trong bài Day 1 cho khái niệm này." });
    }
    if (!intent.concept) {
      return Object.assign(base, { kind: "help", confidence: 0.5, reason_for_user: "" });
    }

    const concept = C.CONCEPTS[intent.concept];
    const conf = confidenceOf(profile, concept.id, state.memoryOn);
    const survey = state.survey && state.survey.concept === concept.id ? state.survey : null;
    const prof = Object.assign({}, profile);
    if (survey) Object.keys(survey.levels).forEach((k) => { prof[k] = { level: survey.levels[k] }; });

    // Thang 5 mức (nội bộ): L1 Làm quen · L2 Cơ bản · L3 Hiểu bản chất · L4 Kỹ thuật · L5 Chuyên sâu.
    const missing = concept.prerequisites.find((p) => lv(prof, p) === "chua") || null;
    const cLv = lv(prof, concept.id);
    const baseSolid = concept.prerequisites.every((p) => lv(prof, p) === "hieu_ro");
    let level;
    if (survey && survey.skipped) level = "L2";
    else if (missing) level = "L1";
    else if (cLv === "chua") level = "L2";
    else if (cLv === "hieu_ro") level = baseSolid ? "L5" : "L4";
    else if (cLv === "biet_so") level = baseSolid ? "L4" : "L3";
    else level = "L3";

    const afterExplanation = !!(state.session && state.session.answered && state.session.answered[concept.id]);
    let need_survey = false;
    let reason = "";
    let steppedDown = false;

    if (!survey && (intent.confused || intent.reask)) {
      if (afterExplanation) {
        need_survey = true;
        reason = intent.reask ? "Bạn hỏi lại về " + concept.term + ", nên mình hỏi nhanh để đổi cách giải thích." : "Lời giải thích trước chưa hợp với bạn, nên mình hỏi nhanh để giải thích đúng chỗ.";
      } else if (conf < 0.6) {
        need_survey = true;
        reason = "Mình chưa biết bạn đã quen với " + concept.term + " đến đâu.";
      } else {
        // Có hồ sơ, lần đầu nói chưa hiểu → hạ 1 bậc, không hỏi thêm.
        level = stepLevel(level, -1);
        steppedDown = true;
      }
    }

    const style = (survey && survey.style) || (state.memoryOn && state.preferredStyle) || (rank(level) <= 1 ? "vi_du" : "ngan_gon");

    // Lý do nói bằng lời thường, không lộ tên mức.
    if (!need_survey) {
      const bits = [];
      const missName = missing ? C.CONCEPTS[missing].term : "";
      if (survey) {
        if (survey.skipped) bits.push("bạn bỏ qua khảo sát nên mình giải thích ngắn gọn, dễ hiểu trước");
        else {
          if (missing) bits.push("bạn chọn “" + missName + ": Chưa” nên mình nói phần này trước");
          bits.push("mình giải thích theo kiểu “" + C.STYLE_LABEL[style] + "” như bạn chọn");
        }
      } else if (state.memoryOn && Object.keys(profile).length) {
        if (missing) bits.push("Sổ tay ghi bạn chưa rõ " + missName + " nên mình nói phần này trước");
        else if (rank(level) >= 3) bits.push("Sổ tay ghi bạn đã nắm phần nền nên mình đi thẳng vào chi tiết kỹ thuật");
        if (steppedDown) bits.push("bạn nói chưa hiểu nên mình giải thích đơn giản hơn");
      }
      reason = bits.length ? bits.map(cap).join(". ") + "." : "";
    }

    return Object.assign(base, {
      kind: need_survey ? "survey" : "explain",
      level,
      style,
      prereq_first: missing,
      missing_concepts: missing ? [missing] : [],
      confidence: survey ? 0.9 : conf,
      need_survey,
      weighted_sum: !!intent.weightedSum,
      reason_for_user: reason,
      source_ids: uniq(concept.claims.flatMap((c) => c.src)),
      full: !!survey || intent.confused || afterExplanation,
    });
  }

  /* ---------- 3. Soạn câu trả lời (CP3: thay bằng LLM) ---------- */
  function composeAnswer(d, opts) {
    opts = opts || {};
    const A = C.ANSWERS[d.concept] || {};
    let key;
    const r = rank(d.level);
    if (d.concept !== "self_attention") key = "first";
    else if (r >= 3) key = d.level;
    else if (r === 2) key = d.full ? "L3" : "L3_first";
    else if (d.full && d.style === "vi_du") key = d.level + (opts.altExample ? "_vi_du_alt" : "_vi_du");
    else key = d.level + "_ngan_gon";

    let blocks = (A[key] || A.first || []).slice();
    if (d.prereq_first && C.PRIMERS[d.prereq_first]) {
      const p = C.PRIMERS[d.prereq_first];
      blocks.unshift({ t: "prereq", title: "Trước hết: " + C.CONCEPTS[d.prereq_first].term, html: p.html, src: p.src, claims: [] });
    }
    if (d.weighted_sum && A.weighted_sum && r <= 2) blocks.push(A.weighted_sum);
    return { key, blocks, fidelity: checkFidelity(d.concept, blocks) };
  }

  /* ---------- 4. Validator độ bám bài giảng ---------- */
  // "không đọc lần lượt từng từ" là câu đúng → không tính là hiểu lệch.
  const NEGATIONS = ["khong", "ko", "chang", "chua", "thay vi", "chu khong", "khac voi", "dung nghi", "hieu lam", "sai lam", "nham"];
  function mentionsMisconception(normalized, pattern) {
    let i = normalized.indexOf(pattern);
    while (i !== -1) {
      const before = normalized.slice(Math.max(0, i - 60), i);
      if (!NEGATIONS.some((neg) => before.includes(neg))) return true;
      i = normalized.indexOf(pattern, i + 1);
    }
    return false;
  }

  function checkFidelity(conceptId, blocks) {
    const concept = C.CONCEPTS[conceptId];
    const text = blocks.map((b) => [b.html || "", b.title || "", (b.items || []).join(" "), (b.rows || []).flat().join(" ")].join(" ")).join(" ");
    const plain = text.replace(/<[^>]+>/g, " ");
    const n = norm(plain);
    const covered = uniq(blocks.flatMap((b) => b.claims || []));
    const total = concept.claims.map((c) => c.id);
    const missingClaims = total.filter((id) => !covered.includes(id));
    const missingTerms = concept.requiredTerms.filter((t) => !n.includes(norm(t)));
    const misconceptions = concept.misconceptions.filter((m) => mentionsMisconception(n, m.pattern)).map((m) => m.id);
    const unlabeled = blocks.filter((b) => b.t !== "outside" && b.t !== "formula" && (!b.src || !b.src.length)).length;
    const outside = blocks.filter((b) => b.t === "outside").length;
    const allowed = new Set(Object.keys(C.SOURCE_SUMMARIES));
    const badSources = uniq(blocks.flatMap((b) => b.src || [])).filter((s) => !allowed.has(s));
    return {
      covered: covered.filter((id) => total.includes(id)).length,
      total: total.length,
      missingClaims,
      missingTerms,
      misconceptions,
      unlabeled,
      outside,
      badSources,
      ok: !missingClaims.length && !missingTerms.length && !misconceptions.length && !unlabeled && !badSources.length,
    };
  }

  /* ---------- 5. Câu kiểm tra ---------- */
  function pickCheck(conceptId, attempt) {
    const list = C.CHECKS[conceptId] || [];
    return list.length ? list[Math.min(attempt, list.length - 1)] : null;
  }

  function gradeCheck(check, key) {
    const opt = check.options.find((o) => o.k === key);
    if (!opt) return null;
    if (opt.correct) return { correct: true };
    const concept = Object.values(C.CONCEPTS).find((c) => c.misconceptions.some((m) => m.id === opt.misconception));
    const m = concept ? concept.misconceptions.find((x) => x.id === opt.misconception) : null;
    return { correct: false, misconception: m, right: check.options.find((o) => o.correct) };
  }

  /* ---------- 6. Hồ sơ học: quy tắc cập nhật thận trọng ---------- */
  function applyEvent(profile, ev, now) {
    const p = JSON.parse(JSON.stringify(profile || {}));
    const before = JSON.parse(JSON.stringify(profile || {}));
    const stamp = now || new Date().toISOString();
    const cur = p[ev.concept] || { level: null, streak: 0, evidence: [] };
    cur.evidence = cur.evidence || [];
    cur.streak = cur.streak || 0;
    const name = C.CONCEPTS[ev.concept] ? C.CONCEPTS[ev.concept].term : ev.concept;
    let notice = null;

    if (ev.type === "self_report" || ev.type === "manual") {
      if (cur.level === ev.level) return { profile: p, notice: null, before };
      cur.level = ev.level;
      cur.streak = 0;
      cur.source = ev.type === "manual" ? "tu_doi" : "tu_khai";
      notice = "Đã ghi " + name + ": " + C.PROFILE_LABEL[ev.level] + " (bạn tự khai).";
    } else if (ev.type === "confused" || ev.type === "level_down") {
      const r = cur.level == null ? 1 : RANK[cur.level];
      const next = Object.keys(RANK)[Math.max(0, r - 1)];
      cur.streak = 0;
      if (cur.level !== next) {
        cur.level = next;
        cur.source = "doi_muc";
        notice = "Mình hạ " + name + " xuống “" + C.PROFILE_LABEL[next] + "” để lần sau giải thích dễ hơn.";
      }
    } else if (ev.type === "check_correct") {
      cur.streak += 1;
      const r = cur.level == null ? 0 : RANK[cur.level];
      if (cur.streak >= 2 && r < 2) {
        cur.level = Object.keys(RANK)[r + 1];
        cur.streak = 0;
        cur.source = "kiem_tra";
        notice = "Bạn trả lời đúng 2 lần liên tiếp, mình nâng " + name + " lên “" + C.PROFILE_LABEL[cur.level] + "”. Lần sau mình sẽ bớt giảng lại phần nền.";
      } else if (r >= 2) {
        notice = "Ghi nhận: bạn vẫn nắm chắc " + name + ".";
      } else {
        if (cur.level == null) cur.level = "chua";
        notice = "Ghi nhận 1 lần trả lời đúng về " + name + ". Mức vẫn là “" + C.PROFILE_LABEL[cur.level] + "” — đúng thêm 1 lần nữa mình mới nâng.";
      }
    } else if (ev.type === "check_wrong") {
      cur.streak = 0;
      if (cur.level == null) cur.level = "chua";
      notice = null;
    } else if (ev.type === "delete") {
      delete p[ev.concept];
      return { profile: p, notice: "Đã xoá " + name + " khỏi Sổ tay.", before };
    }
    cur.evidence.push(ev.type + "@" + stamp.slice(0, 10));
    cur.evidence = cur.evidence.slice(-5);
    cur.updated_at = stamp;
    p[ev.concept] = cur;
    return { profile: p, notice, before };
  }

  function nextStyle(style) {
    const order = ["vi_du", "ngan_gon", "chi_tiet"];
    return order[(order.indexOf(style) + 1) % order.length];
  }

  function uniq(a) {
    return Array.from(new Set(a));
  }

  const ENGINE = { norm, detect, decide, composeAnswer, checkFidelity, pickCheck, gradeCheck, applyEvent, confidenceOf, nextStyle, stepLevel, rank, LEVELS };
  if (typeof module !== "undefined" && module.exports) module.exports = ENGINE;
  else root.P3_ENGINE = ENGINE;
})(typeof window !== "undefined" ? window : globalThis);
