/* Scout multi-page runtime.
   Reads the report state (profile / city / country / goal) from the query
   string, personalizes each report page, and preserves that state across
   real-link navigation so every page is bookmarkable and shareable. */
(function () {
  "use strict";
  var S = window.SCOUT;
  var PAGE = window.SCOUT_PAGE || { type: "", rel: "" };
  var REL = PAGE.rel || "";

  function esc(v) {
    return String(v == null ? "" : v).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function getState() {
    var q = new URLSearchParams(window.location.search);
    var goal = q.get("goal") || "build_portfolio";
    if (!S.GOALS.some(function (g) { return g.id === goal; })) goal = "build_portfolio";
    return {
      profile: q.get("profile") || "Developer",
      city: q.get("city") || "Rome",
      country: q.get("country") || "Italy",
      goal: goal
    };
  }

  function qstring(state) {
    return "?" + new URLSearchParams(state).toString();
  }

  function ranked(goal) {
    var w = (S.GOALS.find(function (g) { return g.id === goal; }) || S.GOALS[0]).weight;
    return S.TOPICS.slice().sort(function (a, b) {
      return (S.composite(b) * 0.6 + b.signals[w] * 0.4) - (S.composite(a) * 0.6 + a.signals[w] * 0.4);
    });
  }

  // Append the current report state to every link that should carry it.
  function keepQuery(state) {
    var q = qstring(state);
    document.querySelectorAll("a[data-keepq]").forEach(function (a) {
      var href = a.getAttribute("href") || "";
      if (!href || href.charAt(0) === "#" || /^https?:/.test(href)) return;
      a.setAttribute("href", href.split("?")[0] + q);
    });
  }

  function bindText(map) {
    Object.keys(map).forEach(function (key) {
      document.querySelectorAll('[data-bind="' + key + '"]').forEach(function (el) {
        el.textContent = map[key];
      });
    });
  }

  function goalLabel(goal) {
    var g = S.GOALS.find(function (x) { return x.id === goal; }) || S.GOALS[0];
    return g.label;
  }

  function topicHref(id, state) {
    return REL + "topics/" + id + "/" + qstring(state);
  }

  function opCard(t, state) {
    var diff = S.difficulty(t);
    return '<a class="card opcard" href="' + topicHref(t.id, state) + '">' +
      '<div class="head"><div style="flex:1;min-width:0"><h4 class="title">' + esc(t.short) + "</h4>" +
      '<div class="act">' + esc(S.actionShort(t)) + "</div></div>" +
      '<span class="diff ' + diff + '">' + diff + "</span></div>" +
      '<div class="bestproj"><span class="bp-k">Build</span>' + esc(t.project_ideas[0]) + "</div>" +
      '<div class="foot"><span class="whyrank">' + esc(S.whyRank(t)) + '</span><span class="inspect">Open →</span></div></a>';
  }

  function projCard(idea, t, state) {
    var diff = S.difficulty(t);
    return '<article class="card proj">' +
      '<div class="ph"><span class="ptag">' + esc(t.short) + '</span><span class="diff ' + diff + '" style="margin-left:auto">' + diff + "</span></div>" +
      "<h4>" + esc(idea) + "</h4>" +
      "<p>Turn the " + esc(t.short) + " signal into a portfolio piece — a focused repo, a live demo, and a short writeup.</p>" +
      '<div class="stack">' + t.skills.slice(0, 4).map(function (s) { return '<span class="tag">' + esc(s) + "</span>"; }).join("") + "</div>" +
      '<a class="btn small" style="margin-top:6px" href="' + topicHref(t.id, state) + '">Open full plan →</a></article>';
  }

  function fill(id, html) { var el = document.getElementById(id); if (el) el.innerHTML = html; }

  function renderReport(state, topics, top) {
    var projects = S.TOPICS.reduce(function (n, t) { return n + t.project_ideas.length; }, 0);
    bindText({
      loc: state.city + ", " + state.country,
      profile: state.profile,
      goal: goalLabel(state.goal),
      score: String(S.composite(top)),
      topicsCount: String(S.TOPICS.length),
      projectsCount: String(projects),
      actionsCount: "6",
      topShort: top.short,
      topSummary: top.summary,
      verdict: S.verdict(top, state.profile, state.city)
    });
  }

  function renderOverview(state, topics, top) {
    fill("ov-top", topics.slice(0, 3).map(function (t) { return opCard(t, state); }).join(""));
    var dims = S.radar(top);
    fill("ov-scores", ["Global momentum", "Local relevance", "Career value", "Project potential", "Trust"].map(function (k) {
      var v = dims[k];
      return '<div class="rb lt"><span class="lab">' + k + '</span><span class="track"><i class="fill" style="width:' + v + '%"></i></span><span class="num">' + v + "</span></div>";
    }).join(""));
    bindText({
      firstAction: "Learn " + top.short + " and ship " + top.project_ideas[0] + ".",
      confidence: (top.trust.score >= 0.87 ? "High" : "Medium") + " confidence · " + Math.round(top.trust.score * 100) + "%",
      studyNow: top.study_plan.slice(0, 2).join(" · "),
      buildNow: top.project_ideas[0],
      publishNow: "GitHub + live demo + short article"
    });
  }

  function renderAiPlan(state, topics, top) {
    var steps = [
      { t: "Validate the opportunity", d: "Confirm demand for " + top.short + " near " + state.city + " before investing time.", out: "A one-paragraph go/no-go", time: "1 evening", skills: "Research", tools: "Scout · GitHub · Jobs" },
      { t: "Learn the required skills", d: "Work through the essentials: " + top.study_plan.slice(0, 3).join(", ") + ".", out: "Notes + small exercises", time: S.effort(top).learn, skills: top.skills.slice(0, 3).join(", "), tools: "Docs · tutorials" },
      { t: "Build a minimum viable project", d: "Ship " + top.project_ideas[0] + " — small, focused, and real.", out: "A working demo", time: "a weekend", skills: top.skills.slice(0, 4).join(", "), tools: "Python · FastAPI · Git" },
      { t: "Publish the project", d: "Put it on GitHub and a live demo, then write a short post.", out: "Public repo + demo + article", time: "1 evening", skills: "Writing · Git", tools: "GitHub · Hugging Face" },
      { t: "Find initial users or collaborators", d: "Share it in communities and with people hiring for " + top.short + ".", out: "First feedback + contacts", time: "ongoing", skills: "Communication", tools: "Communities · LinkedIn" },
      { t: "Improve with feedback", d: "Iterate on what people actually asked for and re-publish.", out: "A stronger v2", time: "ongoing", skills: "Iteration", tools: "Issues · analytics" }
    ];
    fill("plan", steps.map(function (s, i) {
      return '<article class="card pstep">' +
        '<span class="pn">' + (i + 1) + "</span>" +
        '<div><div class="pt">' + esc(s.t) + '</div><div class="pd">' + esc(s.d) + "</div>" +
        '<div class="pmeta">' +
        '<div class="pk"><div class="k">Duration</div><div class="v">' + esc(s.time) + "</div></div>" +
        '<div class="pk"><div class="k">Skills</div><div class="v">' + esc(s.skills) + "</div></div>" +
        '<div class="pk"><div class="k">Tools</div><div class="v">' + esc(s.tools) + "</div></div>" +
        '<div class="pk"><div class="k">Output</div><div class="v">' + esc(s.out) + "</div></div>" +
        "</div>" +
        '<div class="pcheck"><span class="box"></span>Mark complete when done</div></div></article>';
    }).join(""));
  }

  function radarCards(list, state, key, note) {
    return list.map(function (t) {
      var v = S.radar(t)[key];
      return '<a class="card opcard" href="' + topicHref(t.id, state) + '">' +
        '<div class="head"><div style="flex:1;min-width:0"><h4 class="title">' + esc(t.short) + "</h4>" +
        '<div class="act">' + note + " " + v + "</div></div></div>" +
        '<div class="metric"><div class="ml">' + key + '</div><div class="mv"><span class="minibar"><i style="width:' + v + '%"></i></span>' + v + "</div></div>" +
        '<div class="bestproj"><span class="bp-k">Build</span>' + esc(t.project_ideas[0]) + "</div>" +
        '<div class="foot"><span class="whyrank">' + esc(S.whyRank(t)) + '</span><span class="inspect">Open →</span></div></a>';
    }).join("");
  }

  function renderLocalRadar(state) {
    var local = S.TOPICS.slice().sort(function (a, b) { return b.signals.local_relevance - a.signals.local_relevance; }).slice(0, 4);
    fill("local-cards", radarCards(local, state, "Local relevance", "Local"));
    var hires = S.TOPICS.slice().sort(function (a, b) { return b.signals.job_demand - a.signals.job_demand; }).slice(0, 4);
    fill("local-hiring", hires.map(function (t) {
      return '<div class="rb lt"><span class="lab">' + esc(t.short) + '</span><span class="track"><i class="fill" style="width:' + t.signals.job_demand + '%"></i></span><span class="num">' + t.signals.job_demand + "</span></div>";
    }).join(""));
  }

  function renderGlobalPulse(state) {
    var global = S.TOPICS.slice().sort(function (a, b) { return S.radar(b)["Global momentum"] - S.radar(a)["Global momentum"]; }).slice(0, 4);
    fill("global-cards", radarCards(global, state, "Global momentum", "Momentum"));
    var growth = S.TOPICS.slice().sort(function (a, b) { return b.signals.github_growth - a.signals.github_growth; }).slice(0, 5);
    fill("global-growth", growth.map(function (t) {
      return '<div class="rb lt"><span class="lab">' + esc(t.short) + '</span><span class="track"><i class="fill" style="width:' + t.signals.github_growth + '%"></i></span><span class="num">+' + t.signals.github_growth + "%</span></div>";
    }).join(""));
  }

  function renderProjects(state, topics) {
    var cards = [];
    topics.forEach(function (t) {
      t.project_ideas.slice(0, 2).forEach(function (idea) { cards.push(projCard(idea, t, state)); });
    });
    fill("proj-grid", cards.join(""));
  }

  function copyRow(label, value) {
    return '<div class="vrow"><span class="vk">' + esc(label) + '</span><div class="copyrow"><code>' + esc(value) +
      '</code><button class="copybtn" data-copy="' + esc(value) + '">Copy</button></div></div>';
  }

  function renderVisibility(state, top) {
    var repo = S.repoName(top);
    var hf = top.short + " Scout Demo";
    var blog = "How I built a local " + top.short.toLowerCase() + " scout for technology trends";
    var handle = "@" + (state.profile || "developer").toLowerCase().replace(/\s+/g, "");
    fill("vis-copy", copyRow("Create this repo", repo) + copyRow("Build this demo", hf) +
      copyRow("Write this post", blog) + copyRow("Post title", "I shipped " + top.project_ideas[0] + " this weekend — here is what I learned"));
    document.querySelectorAll("[data-copy]").forEach(function (b) {
      b.addEventListener("click", function () {
        try { navigator.clipboard && navigator.clipboard.writeText(b.getAttribute("data-copy")); } catch (e) {}
        var t = b.textContent; b.textContent = "✓ Copied"; b.classList.add("done");
        setTimeout(function () { b.textContent = t; b.classList.remove("done"); }, 1400);
      });
    });
  }

  function renderTopic(state) {
    var t = S.TOPICS.find(function (x) { return x.id === PAGE.id; });
    if (!t) return;
    var dims = S.radar(t);
    var high = t.trust.score >= 0.87;
    document.title = t.short + " — Scout";
    bindText({ topicName: t.name, topicShort: t.short });
    fill("topic-root",
      '<article class="darkpanel move" style="grid-template-columns:1fr;margin-top:8px">' +
      '<div class="move-main"><div class="verdict"><span class="vbadge"><span class="d"></span>Topic</span>' +
      '<h3 class="vhead">' + esc(t.name) + '</h3><p class="vsub">' + esc(t.summary) + "</p></div>" +
      '<div class="gain"><b>Why it matters:</b> ' + esc(t.why_follow) + "</div>" +
      '<div class="move-foot"><span class="conf ' + (high ? "high" : "med") + ' on-dark"><span class="d"></span>' + (high ? "High" : "Medium") + " confidence · " + Math.round(t.trust.score * 100) + "%</span></div></div></article>" +

      '<div class="topic-two">' +
      '<div><section class="section" style="margin-top:22px"><div class="section-head"><h3>Signal radar</h3></div>' +
      '<article class="card" style="padding:20px"><div class="radarbars">' +
      Object.keys(dims).map(function (k) { return '<div class="rb lt"><span class="lab">' + k + '</span><span class="track"><i class="fill" style="width:' + dims[k] + '%"></i></span><span class="num">' + dims[k] + "</span></div>"; }).join("") +
      "</div></article></section>" +
      '<section class="section"><div class="section-head"><h3>Study plan</h3></div><article class="card" style="padding:20px"><ol style="margin:0;padding-left:18px;color:var(--muted);line-height:1.9">' +
      t.study_plan.map(function (x) { return "<li>" + esc(x) + "</li>"; }).join("") + "</ol></article></section>" +
      '<section class="section"><div class="section-head"><h3>Project ideas</h3></div><div class="projgrid">' +
      t.project_ideas.map(function (idea) { return projCard(idea, t, state); }).join("") + "</div></section></div>" +

      '<div><section class="section" style="margin-top:22px"><div class="section-head"><h3>Skills to learn</h3></div>' +
      '<div class="tagrow">' + t.skills.map(function (s) { return '<span class="tag">' + esc(s) + "</span>"; }).join("") + "</div></section>" +
      '<section class="section"><div class="section-head"><h3>Evidence &amp; sources</h3></div><article class="card" style="padding:18px">' +
      t.sources.map(function (s) { return '<div class="evline"><span class="en">' + esc(s.name) + '</span><span class="ev">' + esc(s.type) + "</span></div>"; }).join("") + "</article></section>" +
      '<section class="section"><div class="section-head"><h3>Risks &amp; limits</h3></div>' +
      t.risks.map(function (r) { return '<div class="risk"><span class="ri">⚠</span><p>' + esc(r) + "</p></div>"; }).join("") + "</section></div></div>" +

      '<section class="section"><div class="section-head"><h3>Related topics</h3></div><div class="tagrow">' +
      S.TOPICS.filter(function (x) { return x.id !== t.id; }).slice(0, 4).map(function (x) {
        return '<a class="tag" style="text-decoration:none" href="' + topicHref(x.id, state) + '">' + esc(x.short) + " →</a>";
      }).join("") + "</div></section>");
  }

  document.addEventListener("DOMContentLoaded", function () {
    var state = getState();
    keepQuery(state);
    var topics = ranked(state.goal);
    var top = topics[0];
    switch (PAGE.type) {
      case "report": renderReport(state, topics, top); break;
      case "overview": renderReport(state, topics, top); renderOverview(state, topics, top); break;
      case "ai-plan": renderReport(state, topics, top); renderAiPlan(state, topics, top); break;
      case "local-radar": renderReport(state, topics, top); renderLocalRadar(state); break;
      case "global-pulse": renderReport(state, topics, top); renderGlobalPulse(state); break;
      case "projects": renderReport(state, topics, top); renderProjects(state, topics); break;
      case "visibility": renderReport(state, topics, top); renderVisibility(state, top); break;
      case "topic": renderTopic(state); break;
      default: break;
    }
  });
})();
