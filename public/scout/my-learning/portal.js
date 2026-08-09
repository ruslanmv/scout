/* ============================================================
   Scout — My Learning portal logic.
   Persistence is client-side localStorage (no backend/auth needed):
   generated paths, per-resource progress, stage completion, notes
   and activity all live under one key. The deterministic pipeline
   still runs server-side; the portal is the place to *follow* a path.
   Drives both the dashboard (body[data-portal=dashboard]) and the
   path navigator (body[data-portal=navigator]).
   ============================================================ */
(function () {
  "use strict";
  var KEY = "scout.myLearning.v1";
  var API = (location.protocol.indexOf("http") === 0) ? location.origin + "/api/v1" : null;

  /* ---------------- store ---------------- */
  function load() {
    try { return JSON.parse(localStorage.getItem(KEY)) || { paths: {} }; }
    catch (e) { return { paths: {} }; }
  }
  function save(state) { localStorage.setItem(KEY, JSON.stringify(state)); }
  function listPaths() {
    var s = load();
    return Object.keys(s.paths).map(function (k) { return s.paths[k]; })
      .sort(function (a, b) { return (b.lastActivityAt || "").localeCompare(a.lastActivityAt || ""); });
  }
  function getPath(id) { return load().paths[id] || null; }
  function putPath(rec) { var s = load(); s.paths[rec.id] = rec; save(s); return rec; }
  function removePath(id) { var s = load(); delete s.paths[id]; save(s); }
  function nowISO() { return new Date().toISOString(); }
  function uid() { return "ul_" + Math.random().toString(36).slice(2, 10); }

  // Create a portal record from a generated plan (used by the learn page too).
  function recordFromPlan(plan, request, name) {
    return {
      id: uid(), plan: plan, request: request || null,
      name: name || (plan.resolved_goal && plan.resolved_goal.title) || "Learning path",
      status: "active", revision: 1,
      progress: {}, stageDone: {}, activity: [{ at: nowISO(), text: "Saved to My Learning" }],
      savedAt: nowISO(), lastActivityAt: nowISO()
    };
  }
  function touch(rec, text) {
    rec.lastActivityAt = nowISO();
    if (text) { rec.activity = rec.activity || []; rec.activity.unshift({ at: nowISO(), text: text }); rec.activity = rec.activity.slice(0, 40); }
  }

  /* ---------------- progress model ---------------- */
  // Resources that are optional / final and do not count toward required progress.
  var NON_REQUIRED = { community: 1, registration: 1 };

  function requiredKeys(stage) {
    var keys = [];
    (stage.resources || []).forEach(function (sr) {
      var r = sr.primary && sr.primary.resource; if (!r) return;
      if (!NON_REQUIRED[r.resource_type]) keys.push("res:" + r.id);
    });
    if (stage.project) keys.push("proj:" + stage.stage_id);
    else if (stage.assessment) keys.push("assess:" + stage.stage_id);
    return keys;
  }
  function itemDone(rec, key) {
    var p = rec.progress[key];
    return !!(p && (p.status === "completed" || p.status === "skipped" && key.indexOf("res:") === 0 && p.status === "skipped"));
  }
  function isCompleted(rec, key) { var p = rec.progress[key]; return !!(p && p.status === "completed"); }
  function stageStats(rec, stage) {
    var keys = requiredKeys(stage);
    var done = keys.filter(function (k) { return isCompleted(rec, k) || (rec.progress[k] && rec.progress[k].status === "skipped"); }).length;
    var explicit = !!rec.stageDone[stage.stage_id];
    var ready = keys.length > 0 && done >= keys.length;
    return { total: keys.length, done: done, pct: keys.length ? Math.round(done / keys.length * 100) : (explicit ? 100 : 0), ready: ready, complete: explicit || (keys.length > 0 && ready) };
  }
  function pathProgress(rec) {
    var total = 0, done = 0;
    (rec.plan.stages || []).forEach(function (st) { var s = stageStats(rec, st); total += s.total; done += Math.min(s.done, s.total); });
    return { total: total, done: done, pct: total ? Math.round(done / total * 100) : 0 };
  }
  function stageStatus(rec, stage) {
    var s = stageStats(rec, stage);
    if (s.complete) return "done";
    if (s.done > 0) return "prog";
    return "todo";
  }
  function currentStage(rec) {
    var stages = rec.plan.stages || [];
    for (var i = 0; i < stages.length; i++) { if (stageStatus(rec, stages[i]) !== "done") return stages[i]; }
    return stages[stages.length - 1] || null;
  }
  function nextAction(rec) {
    var st = currentStage(rec); if (!st) return null;
    var srs = st.resources || [];
    for (var i = 0; i < srs.length; i++) {
      var r = srs[i].primary && srs[i].primary.resource; if (!r) continue;
      if (NON_REQUIRED[r.resource_type]) continue;
      var p = rec.progress["res:" + r.id];
      if (!p || (p.status !== "completed" && p.status !== "skipped")) return { type: "course", stage: st, resource: r, ranked: srs[i].primary };
    }
    if (st.project && !isCompleted(rec, "proj:" + st.stage_id)) return { type: "project", stage: st };
    if (st.assessment && !st.project && !isCompleted(rec, "assess:" + st.stage_id)) return { type: "assessment", stage: st };
    return { type: "stage", stage: st };
  }
  function overallProgress() {
    var recs = listPaths(); if (!recs.length) return 0;
    var t = 0, d = 0; recs.forEach(function (r) { var p = pathProgress(r); t += p.total; d += p.done; });
    return t ? Math.round(d / t * 100) : 0;
  }

  /* ---------------- helpers ---------------- */
  function esc(s) { return (s == null ? "" : String(s)).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function fmtDate(s) { if (!s) return "—"; try { return new Date(s).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" }); } catch (e) { return s; } }
  function mins(m) { if (!m) return "—"; return m >= 60 ? (m / 60).toFixed(m % 60 ? 1 : 0) + " h" : m + " min"; }
  function accessText(res) {
    var a = res.access || {};
    if ((a.type === "free" || a.type === "free_audit") && a.observed_at) return "Free";
    if (a.price != null && a.observed_at) return a.price + " " + (a.currency || "");
    return "Verify on provider";
  }
  function el(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function toast(msg) {
    var t = document.getElementById("toast"); if (!t) { t = el("div", "toast"); t.id = "toast"; document.body.appendChild(t); }
    t.textContent = msg; t.classList.add("show"); clearTimeout(t._h); t._h = setTimeout(function () { t.classList.remove("show"); }, 2200);
  }
  var TYPE_LABEL = { course: "Course", video: "Video", path: "Learning path", docs: "Docs", project: "Project", lab: "Lab", exam_guide: "Exam guide", practice_exam: "Practice", community: "Community", registration: "Register", article: "Article" };

  function theme() {
    var b = document.getElementById("theme"); if (!b) return;
    b.onclick = function () {
      var cur = document.documentElement.getAttribute("data-theme") || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
      document.documentElement.setAttribute("data-theme", cur === "dark" ? "light" : "dark");
    };
  }

  /* ================= DASHBOARD ================= */
  function renderDashboard() {
    var recs = listPaths().filter(function (r) { return r.status !== "archived"; });
    var active = recs.filter(function (r) { return r.status === "active"; });
    var paused = recs.filter(function (r) { return r.status === "paused"; });
    var completed = recs.filter(function (r) { return r.status === "completed" || pathProgress(r).pct === 100; });

    document.getElementById("stat-line").innerHTML =
      "<b>" + active.length + "</b> active " + (active.length === 1 ? "path" : "paths") +
      " · <b>" + completed.length + "</b> completed · <b>" + overallProgress() + "%</b> overall progress";

    // continue card = most recent active path with a next action
    var cont = document.getElementById("continue");
    var top = active[0];
    if (top) {
      var na = nextAction(top), pp = pathProgress(top);
      var label = na ? (na.type === "course" ? na.resource.title : na.type === "project" ? (na.stage.project ? na.stage.project.title : "Project") : "Complete " + na.stage.title) : "Review";
      cont.style.display = "";
      cont.innerHTML =
        '<div class="info"><div class="t">' + esc(top.name) + '</div>' +
        '<div class="n">Next: ' + esc(label) + '</div>' +
        '<div class="row" style="margin-top:8px"><span class="pct tnum">' + pp.pct + '%</span><span class="bar"><i style="width:' + pp.pct + '%"></i></span></div></div>' +
        '<a class="btn primary" href="path.html?id=' + top.id + '">Continue learning →</a>';
    } else { cont.style.display = "none"; }

    renderCards("active-cards", active, "No active paths yet. Generate one to get started.");
    renderCards("paused-cards", paused, "Nothing paused.");
    renderCompleted(completed);
  }

  function renderCards(hostId, recs, emptyMsg) {
    var host = document.getElementById(hostId); if (!host) return; host.innerHTML = "";
    if (!recs.length) { host.appendChild(el("div", "empty", emptyMsg)); return; }
    recs.forEach(function (rec) {
      var pp = pathProgress(rec), cur = currentStage(rec), na = nextAction(rec);
      var stages = rec.plan.stages || [];
      var curIdx = cur ? stages.indexOf(cur) + 1 : stages.length;
      var g = rec.plan.resolved_goal || {};
      var nextLabel = na ? (na.type === "course" ? na.resource.title : na.type === "project" ? "Portfolio project" : "Complete the stage") : "Review";
      var c = el("div", "pcard");
      c.innerHTML =
        '<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px">' +
          '<div><div class="kind">' + esc((g.type || "path").replace(/_/g, " ")) + '</div>' +
          '<h4>' + esc(rec.name) + '</h4></div>' +
          '<span class="pill ' + rec.status + '">' + esc(rec.status) + '</span></div>' +
        '<div class="meta">Stage ' + curIdx + ' of ' + stages.length + ' · ' + pp.done + '/' + pp.total + ' items · updated ' + fmtDate(rec.lastActivityAt) + '</div>' +
        '<div class="row"><span class="pct tnum">' + pp.pct + '%</span><span class="bar"><i style="width:' + pp.pct + '%"></i></span></div>' +
        '<div class="next">Next: <b>' + esc(nextLabel) + '</b></div>' +
        '<div class="foot"><a class="btn primary small" href="path.html?id=' + rec.id + '">Continue path</a>' +
        '<div class="menu"><button class="menu__btn" aria-label="Path menu">•••</button>' +
        '<div class="menu__list">' +
          '<button data-act="rename">Rename</button>' +
          '<button data-act="toggle">' + (rec.status === "paused" ? "Resume" : "Pause") + '</button>' +
          '<button data-act="replan">Replan</button>' +
          '<button data-act="archive">Archive</button>' +
          '<button data-act="delete" class="danger">Delete</button>' +
        '</div></div></div>';
      wireMenu(c, rec);
      host.appendChild(c);
    });
  }

  function renderCompleted(recs) {
    var host = document.getElementById("completed-cards"); if (!host) return; host.innerHTML = "";
    if (!recs.length) { host.appendChild(el("div", "empty", "No completed paths yet — finish a path to earn your first.")); return; }
    recs.forEach(function (rec) {
      var skills = {};
      (rec.plan.stages || []).forEach(function (st) { (st.skills || []).forEach(function (s) { skills[s] = 1; }); });
      var c = el("div", "pcard");
      c.innerHTML =
        '<div class="kind">Completed · ' + fmtDate(rec.completedAt || rec.lastActivityAt) + '</div>' +
        '<h4>' + esc(rec.name) + '</h4>' +
        '<div class="meta">Skills gained: ' + Object.keys(skills).slice(0, 6).map(esc).join(", ") + '</div>' +
        '<div class="foot"><a class="btn small" href="path.html?id=' + rec.id + '">Review</a></div>';
      host.appendChild(c);
    });
  }

  function wireMenu(card, rec) {
    var menu = card.querySelector(".menu"); if (!menu) return;
    menu.querySelector(".menu__btn").onclick = function (e) { e.stopPropagation(); menu.classList.toggle("open"); };
    menu.querySelectorAll("[data-act]").forEach(function (b) {
      b.onclick = function () {
        var act = b.getAttribute("data-act"); var r = getPath(rec.id); if (!r) return;
        if (act === "rename") { var n = prompt("Rename path", r.name); if (n) { r.name = n.trim(); touch(r, "Renamed"); putPath(r); } }
        else if (act === "toggle") { r.status = r.status === "paused" ? "active" : "paused"; touch(r, r.status === "paused" ? "Paused" : "Resumed"); putPath(r); }
        else if (act === "archive") { r.status = "archived"; putPath(r); }
        else if (act === "replan") { location.href = "path.html?id=" + r.id + "&replan=1"; return; }
        else if (act === "delete") { if (confirm("Delete this path? This cannot be undone.")) removePath(r.id); }
        renderDashboard();
      };
    });
  }

  /* ================= NAVIGATOR ================= */
  var CUR_REC = null, CUR_STAGE_IDX = 0;

  function renderNavigator() {
    var id = new URLSearchParams(location.search).get("id");
    var rec = getPath(id);
    var root = document.getElementById("nav-root");
    if (!rec) { root.innerHTML = '<div class="empty" style="margin-top:30px">Path not found. <a href="./">Back to My Learning</a>.</div>'; document.getElementById("phead-title").textContent = "Path not found"; return; }
    CUR_REC = rec;
    var cur = currentStage(rec); CUR_STAGE_IDX = (rec.plan.stages || []).indexOf(cur);
    paintHead(rec);
    paintNav(rec);
    if (new URLSearchParams(location.search).get("replan")) openReplan();
  }

  function paintHead(rec) {
    var pp = pathProgress(rec), d = rec.plan.duration || {};
    document.getElementById("phead-title").textContent = rec.name;
    document.getElementById("phead-sub").innerHTML =
      '<span class="statline"><span><b>' + pp.pct + '%</b> complete</span>' +
      '<span><b>' + (d.estimated_weeks || "—") + '</b> weeks</span>' +
      '<span><b>' + (d.hours_per_week || 8) + '</b> h/week</span>' +
      '<span><b>' + pp.done + '/' + pp.total + '</b> required items</span></span>';
  }

  function paintNav(rec) {
    var stages = rec.plan.stages || [];
    // path map
    var map = document.getElementById("path-map"); map.innerHTML = "";
    stages.forEach(function (st, i) {
      var status = stageStatus(rec, st);
      var icon = status === "done" ? "✓" : status === "prog" ? "◐" : (i === CUR_STAGE_IDX ? "●" : "○");
      var b = el("button", "mapitem " + (status === "done" ? "done " : status === "prog" ? "prog " : "") + (i === CUR_STAGE_IDX ? "cur" : ""));
      b.innerHTML = '<span class="ic">' + icon + '</span><span class="tx">' + esc(st.title) + '<small>Stage ' + st.stage + '</small></span>';
      b.onclick = function () { CUR_STAGE_IDX = i; paintNav(rec); };
      map.appendChild(b);
    });
    var recStage = currentStage(rec);
    document.getElementById("map-recommend").innerHTML = recStage ? "▸ Recommended next: " + esc(recStage.title) : "";

    // center: current stage
    var st = stages[CUR_STAGE_IDX]; var center = document.getElementById("stage-content"); center.innerHTML = "";
    if (!st) { center.innerHTML = '<div class="empty">Select a stage.</div>'; return; }
    var ss = stageStats(rec, st);
    center.appendChild(el("div", "", '<div class="stagehdr"><div><div class="t">Stage ' + st.stage + ': ' + esc(st.title) + '</div>' +
      '<div class="o">' + esc(st.outcome || "") + '</div></div><div class="pct tnum">' + ss.pct + '%</div></div>'));
    (st.resources || []).forEach(function (sr) { center.appendChild(courseCard(rec, st, sr)); });
    if (st.project) center.appendChild(projectCard(rec, st));
    // stage ready / complete
    if (ss.ready && !ss.complete) {
      var box = el("div", "stageready", '<div class="t">Stage ready to complete ✓</div>' +
        '<div style="font-size:13px;color:var(--muted)">You finished all required items in this stage.</div>');
      var b = el("button", "btn primary small", "Complete stage"); b.style.marginTop = "10px";
      b.onclick = function () { rec.stageDone[st.stage_id] = true; touch(rec, "Completed stage: " + st.title); maybeComplete(rec); putPath(rec); renderNavigator(); toast("Stage complete — next stage unlocked"); };
      box.appendChild(b); center.appendChild(box);
    } else if (ss.complete) {
      center.appendChild(el("div", "stageready", '<div class="t">Stage complete ✓</div>'));
    }
    paintRight(rec, st);
  }

  function courseCard(rec, st, sr) {
    var r = sr.primary.resource, ranked = sr.primary;
    var key = "res:" + r.id, p = rec.progress[key] || { status: "not_started" };
    var done = p.status === "completed";
    var card = el("div", "course" + (done ? " done" : ""));
    var pct = p.pct != null ? p.pct : (done ? 100 : 0);
    var src = p.source ? sourceLabel(p.source) : "";
    card.innerHTML =
      '<div class="course__top"><div style="min-width:0">' +
        '<div class="course__prov">' + esc(r.provider || "") + ' · <span class="rtype">' + (TYPE_LABEL[r.resource_type] || r.resource_type) + '</span></div>' +
        '<div class="course__t" role="button" tabindex="0">' + esc(r.title) + '</div>' +
        '<div class="course__meta">' + esc(r.level || "unknown") + ' · ' + mins(r.duration_minutes) + ' · ' + esc(accessText(r)) + '</div>' +
      '</div></div>' +
      ((ranked.reasons && ranked.reasons[0]) ? '<div class="course__reason">' + esc(ranked.reasons[0]) + '</div>' : '') +
      (done ? '<div class="donetag" style="margin-top:10px">✓ Completed <small>· ' + esc(src) + '</small></div>' :
        (p.status !== "not_started" ? '<div class="cprog"><span class="bar"><i style="width:' + pct + '%"></i></span><span class="tnum" style="font-size:12px;color:var(--muted)">' + pct + '%</span></div>' : '')) +
      '<div class="cactions"></div>';
    // title -> drawer
    var title = card.querySelector(".course__t");
    title.onclick = function () { openDrawer(rec, st, sr); };
    title.onkeydown = function (e) { if (e.key === "Enter") openDrawer(rec, st, sr); };
    var actions = card.querySelector(".cactions");
    if (!done) {
      var cont = el("button", "btn primary small", (p.status === "not_started" ? "Start course ↗" : "Continue course ↗"));
      cont.onclick = function () { openProvider(rec, r); };
      var mark = el("button", "btn small", "Mark complete");
      mark.onclick = function () { openComplete(rec, "res:" + r.id, r.title); };
      var alt = el("button", "btn ghost small", "Details & alternatives");
      alt.onclick = function () { openDrawer(rec, st, sr); };
      actions.appendChild(cont); actions.appendChild(mark); actions.appendChild(alt);
    } else {
      var undo = el("button", "btn ghost small", "Undo"); undo.onclick = function () { delete rec.progress[key]; touch(rec, "Reopened: " + r.title); putPath(rec); renderNavigator(); };
      actions.appendChild(undo);
    }
    return card;
  }

  function projectCard(rec, st) {
    var key = "proj:" + st.stage_id, done = isCompleted(rec, key);
    var box = el("div", "projbox");
    box.innerHTML = '<div class="pl">Portfolio project' + (done ? ' · ✓ done' : '') + '</div>' +
      '<div class="pt">' + esc(st.project.title) + '</div>' +
      '<ul>' + (st.project.acceptance_criteria || []).map(function (c) { return '<li>' + esc(c) + '</li>'; }).join("") + '</ul>' +
      '<div class="cactions" style="margin-top:10px"></div>';
    var actions = box.querySelector(".cactions");
    if (!done) { var b = el("button", "btn primary small", "Mark project complete"); b.onclick = function () { openComplete(rec, key, st.project.title); }; actions.appendChild(b); }
    else { var u = el("button", "btn ghost small", "Undo"); u.onclick = function () { delete rec.progress[key]; touch(rec, "Reopened project"); putPath(rec); renderNavigator(); }; actions.appendChild(u); }
    return box;
  }

  function paintRight(rec, st) {
    var d = rec.plan.duration || {}, target = d.hours_per_week || 8;
    document.getElementById("week-widget").innerHTML =
      '<div class="wk tnum">' + (st.estimated_hours || 0) + '<small>/ ' + target + ' h this stage</small></div>' +
      '<div class="milestone">Next milestone: <b>Complete stage ' + st.stage + '</b></div>';
    var acts = (rec.activity || []).slice(0, 8);
    document.getElementById("activity-widget").innerHTML = acts.length ?
      acts.map(function (a) { return '<div class="a"><b>' + fmtDate(a.at) + '</b> ' + esc(a.text) + '</div>'; }).join("") :
      '<div class="a">No activity yet.</div>';
  }

  /* ---- actions ---- */
  function openProvider(rec, r) {
    var key = "res:" + r.id, p = rec.progress[key] || {};
    if (p.status !== "completed") { rec.progress[key] = { status: "started", source: "outbound_link", startedAt: p.startedAt || nowISO() }; touch(rec, "Started: " + r.title); putPath(rec); }
    window.open(r.url, "_blank", "noopener");
    // opening a link NEVER auto-completes (acceptance criterion 4)
    renderNavigator();
  }

  var COMPLETE_KEY = null, COMPLETE_LABEL = null;
  function openComplete(rec, key, label) {
    COMPLETE_KEY = key; COMPLETE_LABEL = label;
    document.getElementById("cm-title").textContent = "Mark complete: " + label;
    document.getElementById("cm-note").value = ""; document.getElementById("cm-score").value = ""; document.getElementById("cm-evidence").value = "";
    document.getElementById("complete-modal").classList.add("open");
  }
  function confirmComplete() {
    var rec = CUR_REC; if (!rec || !COMPLETE_KEY) return;
    var note = document.getElementById("cm-note").value.trim();
    var score = document.getElementById("cm-score").value.trim();
    var evidence = document.getElementById("cm-evidence").value.trim();
    rec.progress[COMPLETE_KEY] = {
      status: "completed", source: "manual", pct: 100,
      note: note || null, score: score ? Number(score) : null, evidenceUrl: evidence || null,
      completedAt: nowISO()
    };
    touch(rec, "Marked complete: " + COMPLETE_LABEL);
    maybeComplete(rec); putPath(rec);
    document.getElementById("complete-modal").classList.remove("open");
    renderNavigator(); toast("Marked complete");
  }
  function maybeComplete(rec) {
    var pp = pathProgress(rec);
    if (pp.total > 0 && pp.pct === 100 && rec.status !== "completed") { rec.status = "completed"; rec.completedAt = nowISO(); touch(rec, "Path completed 🎉"); }
  }

  function sourceLabel(src) {
    return { manual: "Marked manually", provider_verified: "Verified by provider", scout_assessment: "Verified by Scout assessment", credential_import: "Imported credential", outbound_link: "Opened" }[src] || src;
  }

  /* ---- course-detail drawer ---- */
  function openDrawer(rec, st, sr) {
    var r = sr.primary.resource, ranked = sr.primary, alt = sr.alternative;
    var key = "res:" + r.id, p = rec.progress[key];
    var conf = Math.round((r.quality && r.quality.evidence_confidence || 0.5) * 100);
    var body = document.getElementById("drawer-body");
    body.innerHTML =
      '<div class="course__prov">' + esc(r.provider || "") + ' · <span class="rtype">' + (TYPE_LABEL[r.resource_type] || r.resource_type) + '</span></div>' +
      '<h3>' + esc(r.title) + '</h3>' +
      (r.description ? '<p style="color:var(--muted);font-size:13.5px">' + esc(r.description) + '</p>' : '') +
      '<dl class="dl">' +
        '<dt>Access</dt><dd>' + esc(accessText(r)) + '</dd>' +
        '<dt>Duration</dt><dd>' + mins(r.duration_minutes) + '</dd>' +
        '<dt>Level</dt><dd>' + esc(r.level || "unknown") + '</dd>' +
        '<dt>Evidence</dt><dd>' + conf + '% confidence</dd>' +
        '<dt>Last verified</dt><dd>' + fmtDate(r.provenance && r.provenance.last_verified_at) + '</dd>' +
        (p && p.completedAt ? '<dt>Completed</dt><dd>' + fmtDate(p.completedAt) + ' · ' + esc(sourceLabel(p.source)) + '</dd>' : '') +
      '</dl>' +
      (r.skills_taught && r.skills_taught.length ? '<h5>Skills taught</h5><div class="taglist">' + r.skills_taught.map(function (s) { return '<span class="tag">' + esc(s.replace("skill:", "")) + '</span>'; }).join("") + '</div>' : '') +
      (ranked.reasons && ranked.reasons.length ? '<h5>Why Scout selected it</h5><ul class="reasons">' + ranked.reasons.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join("") + '</ul>' : '') +
      (ranked.warnings && ranked.warnings.length ? '<h5>Warnings</h5><ul class="reasons warns">' + ranked.warnings.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join("") + '</ul>' : '') +
      (alt && alt.primary && alt.primary.resource ? '<h5>Alternative</h5><div class="altcard"><div class="at">' + esc(alt.primary.resource.title) + '</div><div class="ar">' + esc(alt.primary.resource.provider) + ' · ' + esc(accessText(alt.primary.resource)) + '</div></div>' : '') +
      '<h5>Your notes</h5><textarea id="drawer-note" rows="3" placeholder="Private notes…">' + esc((p && p.note) || "") + '</textarea>';
    var cta = document.getElementById("drawer-cta");
    cta.innerHTML = "";
    var go = el("button", "btn primary", "Go to provider ↗"); go.onclick = function () { saveNote(rec, key); openProvider(rec, r); };
    var mk = el("button", "btn", (p && p.status === "completed") ? "Completed ✓" : "Mark complete");
    mk.disabled = !!(p && p.status === "completed"); if (!mk.disabled) mk.onclick = function () { saveNote(rec, key); closeDrawer(); openComplete(rec, key, r.title); };
    cta.appendChild(go); cta.appendChild(mk);
    document.getElementById("scrim").classList.add("open");
    document.getElementById("drawer").classList.add("open");
  }
  function saveNote(rec, key) {
    var ta = document.getElementById("drawer-note"); if (!ta) return;
    var p = rec.progress[key] || { status: "not_started" }; p.note = ta.value.trim() || null; rec.progress[key] = p; putPath(rec);
  }
  function closeDrawer() { document.getElementById("scrim").classList.remove("open"); document.getElementById("drawer").classList.remove("open"); }

  /* ---- replan ---- */
  function openReplan() { document.getElementById("replan-modal").classList.add("open"); }
  function closeReplan() { document.getElementById("replan-modal").classList.remove("open"); }
  function doReplan() {
    var rec = CUR_REC; if (!rec) return;
    if (!API) { toast("Replanning needs the live Scout API"); closeReplan(); return; }
    var reason = (document.querySelector('input[name="replan-reason"]:checked') || {}).value || "other";
    // completed stages -> their skills become known, so the new path skips them
    var learned = [];
    (rec.plan.stages || []).forEach(function (st) { if (stageStatus(rec, st) === "done") (st.skills || []).forEach(function (s) { learned.push({ name: s, level: "intermediate" }); }); });
    var req = Object.assign({}, rec.request || {});
    req.current_skills = (req.current_skills || []).concat(learned);
    var btn = document.getElementById("replan-go"); btn.disabled = true; btn.innerHTML = '<span class="spin"></span> Replanning…';
    fetch(API + "/learning/paths", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ request: req }) })
      .then(function (r) { if (!r.ok) throw 0; return r.json(); })
      .then(function (plan) {
        rec.plan = plan; rec.revision = (rec.revision || 1) + 1;
        rec.stageDone = {}; // stage ids changed; resource progress (keyed by resource_id) is preserved
        touch(rec, "Replanned (" + reason.replace(/_/g, " ") + ") — completed courses kept");
        putPath(rec); closeReplan(); renderNavigator(); toast("Path updated — completed courses preserved");
      })
      .catch(function () { toast("Replan failed — is the API reachable?"); btn.disabled = false; btn.textContent = "Replan"; });
  }

  /* ---------------- boot ---------------- */
  function wireNavigatorChrome() {
    var s = document.getElementById("scrim"); if (s) s.onclick = function () { closeDrawer(); };
    var dc = document.getElementById("drawer-close"); if (dc) dc.onclick = closeDrawer;
    var cc = document.getElementById("cm-cancel"); if (cc) cc.onclick = function () { document.getElementById("complete-modal").classList.remove("open"); };
    var ck = document.getElementById("cm-confirm"); if (ck) ck.onclick = confirmComplete;
    var rb = document.getElementById("replan-btn"); if (rb) rb.onclick = openReplan;
    var rc = document.getElementById("replan-cancel"); if (rc) rc.onclick = closeReplan;
    var rg = document.getElementById("replan-go"); if (rg) rg.onclick = doReplan;
  }
  function wireDashboardChrome() {
    var q = document.getElementById("search");
    if (q) q.oninput = function () {
      var v = q.value.toLowerCase();
      document.querySelectorAll("#active-cards .pcard, #paused-cards .pcard, #completed-cards .pcard").forEach(function (c) {
        c.style.display = c.textContent.toLowerCase().indexOf(v) >= 0 ? "" : "none";
      });
    };
    document.addEventListener("click", function (e) { if (!e.target.closest(".menu")) document.querySelectorAll(".menu.open").forEach(function (m) { m.classList.remove("open"); }); });
  }

  document.addEventListener("DOMContentLoaded", function () {
    theme();
    var page = document.body.getAttribute("data-portal");
    if (page === "dashboard") { renderDashboard(); wireDashboardChrome(); }
    else if (page === "navigator") { renderNavigator(); wireNavigatorChrome(); }
  });

  // Public API (used by the learn page to save a generated path).
  window.ScoutPortal = {
    recordFromPlan: recordFromPlan, putPath: putPath, listPaths: listPaths, getPath: getPath
  };
})();
