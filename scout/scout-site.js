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

  // Curated occupational guidance, deliberately distinct from hiring evidence.
  // Scout's current measured topic feed covers developer technologies; it does
  // not justify recommending AI engineering as the top skill for a nurse.
  var CAREER_GUIDES = [
    { match: /nurs|registered nurse|rn\\b/, focus: "Patient safety & clinical practice",
      learn: ["Clinical assessment", "Care documentation", "Infection prevention"],
      practice: ["Create a fictional patient-assessment simulation", "Draft a de-identified safety checklist", "Review a published clinical guideline with your supervisor"],
      show: "Document accredited training and supervised competencies; never share patient information." },
    { match: /teach|educat|instructor/, focus: "Lesson design & student feedback",
      learn: ["Lesson planning", "Assessment design", "Accessible learning"],
      practice: ["Build a sample lesson plan", "Create an anonymized assessment rubric", "Run a mock classroom activity"],
      show: "Share teaching samples and reflections without identifying pupils." },
    { match: /account|bookkeep|audit|financial analyst|financ/, focus: "Financial reporting & analysis",
      learn: ["Spreadsheet modeling", "Financial statements", "Reconciliation"],
      practice: ["Reconcile an invented ledger", "Build a sample budget dashboard", "Write a fictional financial summary"],
      show: "Present sample reports using synthetic financial data, not client records." },
    { match: /market|growth|content|copywrit/, focus: "Campaign measurement & content",
      learn: ["Audience research", "Campaign analytics", "Content strategy"],
      practice: ["Draft a campaign brief for a sample product", "Build a sample measurement dashboard", "Create an editorial content calendar"],
      show: "Publish a mock campaign case study with clearly labeled hypothetical results." },
    { match: /ux|product design|ui design/, focus: "User research & prototyping",
      learn: ["User research", "Wireframing", "Usability testing"],
      practice: ["Prototype a small user journey", "Write an accessible design critique", "Run a consent-based usability exercise"],
      show: "Publish a portfolio case study while respecting participants' privacy." },
    { match: /electric|technician|mechanical|engineer.*manufactur/, focus: "Electrical safety & practical systems",
      learn: ["Safety regulations", "Technical diagrams", "Testing and diagnostics"],
      practice: ["Interpret a sample circuit diagram", "Document a supervised troubleshooting exercise", "Develop a preventive-maintenance checklist"],
      show: "Keep a competency log with training certificates; perform regulated work only when authorized." },
    { match: /data analyst|data scientist|statistic|business analyst|bi analyst/, technical: true,
      focus: "Data analysis & storytelling",
      learn: ["SQL", "Statistics", "Data visualization"],
      practice: ["Analyze an open dataset", "Build an explanatory dashboard", "Write a reproducible data-quality report"],
      show: "Publish a reproducible project with documented data sources and limitations." },
    { match: /developer|software|programmer|cloud|ai engineer|machine learning|backend|frontend/, technical: true,
      focus: "Reliable software & automation",
      learn: ["Version control", "Testing", "API development"],
      practice: ["Build a small useful application", "Add tests to an existing project", "Document a deployable prototype"],
      show: "Publish code, a working demo and a concise technical write-up." },
    { match: /chef|hospital|service|retail/, focus: "Service quality & operations",
      learn: ["Operational planning", "Customer experience", "Safe work practices"],
      practice: ["Create a sample service improvement plan", "Design a quality checklist", "Document a supervised process review"],
      show: "Share anonymized process improvements and relevant certifications." }
  ];
  function careerGuide(profile) {
    var role = String(profile || "").trim();
    var row = CAREER_GUIDES.find(function (g) { return g.match.test(role); });
    if (row) return row;
    return { focus: "Professional development for " + (role || "your role"),
      learn: ["Role-specific fundamentals", "Industry standards", "Communication"],
      practice: ["Choose one realistic work scenario", "Develop a small evidence-of-skill artifact", "Ask for feedback from a qualified professional"],
      show: "Prepare a concise skills summary and proof of work, respecting confidentiality." };
  }
  function goalFocus(goal, role) {
    if (goal === "career") return "Prepare evidence of competence and map the next role or qualification for " + role + ".";
    if (goal === "create_agents") return "Explore a human-reviewed automation prototype relevant to " + role + "; avoid unsafe or regulated autonomous decisions.";
    if (goal === "startup") return "Interview potential users before prototyping a small service for " + role + ".";
    return "Build a shareable, realistic work sample relevant to " + role + ".";
  }
  function guideSteps(state) {
    var g = careerGuide(state.profile), role = state.profile || "your profession";
    var goal = goalFocus(state.goal, role);
    return [
      {t:"Define your next move",d:goal,out:"One clear, measurable career objective",time:"1 day",skills:role,tools:"Scout · professional resources"},
      {t:"Learn your role's foundations",d:"Start with "+g.learn.join(", ")+". Verify local qualifications and any applicable licensing.",out:"Skill checklist and short study notes",time:"1–2 weeks",skills:g.learn.join(", "),tools:"Official guidance · training"},
      {t:"Practice with a safe example",d:g.practice[0]+".",out:"A first demonstrable practice artifact",time:"1 week",skills:g.learn[0],tools:"Role-appropriate tools"},
      {t:"Build evidence of your skills",d:g.practice[1]+".",out:"Documented work sample",time:"1 week",skills:g.learn[1],tools:"Templates · feedback"},
      {t:"Get seen ethically",d:g.show,out:"A career-ready portfolio or competency log",time:"Ongoing",skills:"Communication",tools:"Portfolio · professional network"},
      {t:"Validate the next step in "+state.city,d:"Check locally relevant qualifications, employers or clients and update your plan. Scout's cross-industry local job data may be incomplete.",out:"A verified next action",time:"Ongoing",skills:"Research",tools:"Official local sources"}
    ];
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
    var guide = careerGuide(state.profile);
    var tech = !!guide.technical;
    bindText({
      loc: state.city + ", " + state.country,
      profile: state.profile,
      goal: goalLabel(state.goal),
      score: tech ? String(S.composite(top)) : "—",
      topicsCount: tech ? String(S.TOPICS.length) : String(guide.learn.length),
      projectsCount: tech ? String(projects) : String(guide.practice.length),
      actionsCount: "6",
      topShort: guide.focus,
      topSummary: guide.learn.join(" · "),
      verdict: goalFocus(state.goal, state.profile) + " Start with a curated " + state.profile +
        " pathway for " + state.city + ", " + state.country +
        ". These suggestions are not verified local hiring rankings."
    });
    if (!tech) {
      var units = document.querySelectorAll(".stat-inline .si");
      if (units.length > 0) units[0].style.display = "none";
      if (units.length > 1) { var k1 = units[1].querySelector(".l"); if (k1) k1.textContent = "Focus skills"; }
      if (units.length > 2) { var k2 = units[2].querySelector(".l"); if (k2) k2.textContent = "Practice examples"; }
    } else {
      var scoreLabel = document.querySelector(".stat-inline .si .l");
      if (scoreLabel) scoreLabel.textContent = "Technology topic score";
    }
  }

  function renderOverview(state, topics, top) {
    var guide = careerGuide(state.profile);
    if (!guide.technical) {
      fill("ov-top", guide.learn.map(function (skill,i) {
        return '<article class="card opcard" style="padding:20px">' +
          '<h4 class="title">' + esc(skill) + '</h4><p>Curated skill to explore for ' +
          esc(state.profile) + '.</p></article>';
      }).join(""));
      fill("ov-scores", '<p class="muted-note">No verified profession-specific hiring score for ' +
        esc(state.city) + '. These are curated learning suggestions.</p>');
      var scores = document.getElementById("ov-scores");
      if (scores) {
        var title = scores.closest("article")?.querySelector("h3");
        if (title) title.textContent = "Source coverage";
      }
      bindText({
        firstAction: goalFocus(state.goal, state.profile),
        confidence: "Curated guide · validate local qualifications",
        studyNow: guide.learn.slice(0,2).join(" · "),
        buildNow: guide.practice[0],
        publishNow: guide.show
      });
      var trends = document.querySelectorAll("main .section");
      trends.forEach(function (section) {
        if (section.querySelector("h3")?.textContent === "Key technology trends") {
          section.innerHTML = '<div class="section-head"><h3>About these suggestions</h3></div>' +
            '<p class="section-lead">This role-specific roadmap is curated. Scout does not currently verify ' +
            esc(state.profile) + ' hiring trends in ' + esc(state.city) + '.</p>';
        }
      });
      return;
    }
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
    var steps = guideSteps(state);
    // The selected profession and career goal determine the learning path.
    // Do not substitute the same AI engineering steps for every occupation.
    /* Legacy topic-only steps retained for technology-topic detail pages:
    var unusedTopicSteps = [
      { t: "Validate the opportunity", d: "Confirm demand for " + top.short + " near " + state.city + " before investing time.", out: "A one-paragraph go/no-go", time: "1 evening", skills: "Research", tools: "Scout · GitHub · Jobs" },
      { t: "Learn the required skills", d: "Work through the essentials: " + top.study_plan.slice(0, 3).join(", ") + ".", out: "Notes + small exercises", time: S.effort(top).learn, skills: top.skills.slice(0, 3).join(", "), tools: "Docs · tutorials" },
      { t: "Build a minimum viable project", d: "Ship " + top.project_ideas[0] + " — small, focused, and real.", out: "A working demo", time: "a weekend", skills: top.skills.slice(0, 4).join(", "), tools: "Python · FastAPI · Git" },
      { t: "Publish the project", d: "Put it on GitHub and a live demo, then write a short post.", out: "Public repo + demo + article", time: "1 evening", skills: "Writing · Git", tools: "GitHub · Hugging Face" },
      { t: "Find initial users or collaborators", d: "Share it in communities and with people hiring for " + top.short + ".", out: "First feedback + contacts", time: "ongoing", skills: "Communication", tools: "Communities · LinkedIn" },
      { t: "Improve with feedback", d: "Iterate on what people actually asked for and re-publish.", out: "A stronger v2", time: "ongoing", skills: "Iteration", tools: "Issues · analytics" }
    ];
    */
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
    var guide = careerGuide(state.profile);
    if (!guide.technical) {
      fill("local-cards", '<article class="card" style="padding:22px"><h4>' +
        esc(state.profile) + ' in ' + esc(state.city) + '</h4><p>Curated career guidance only. ' +
        'Scout has no verified profession-specific local hiring ranking for this role yet.</p>' +
        '<p>Focus skills: ' + esc(guide.learn.join(" · ")) + '</p></article>');
      fill("local-hiring", '<p class="section-lead">Consult official local licensing, qualification and ' +
        'job-market sources before making decisions.</p>');
      return;
    }
    var local = S.TOPICS.slice().sort(function (a, b) { return b.signals.local_relevance - a.signals.local_relevance; }).slice(0, 4);
    fill("local-cards", radarCards(local, state, "Local relevance", "Local"));
    var hires = S.TOPICS.slice().sort(function (a, b) { return b.signals.job_demand - a.signals.job_demand; }).slice(0, 4);
    fill("local-hiring", hires.map(function (t) {
      return '<div class="rb lt"><span class="lab">' + esc(t.short) + '</span><span class="track"><i class="fill" style="width:' + t.signals.job_demand + '%"></i></span><span class="num">' + t.signals.job_demand + "</span></div>";
    }).join(""));
  }

  function renderGlobalPulse(state) {
    var guide = careerGuide(state.profile);
    if (!guide.technical) {
      fill("global-cards", '<article class="card" style="padding:22px"><h4>' +
        esc(state.profile) + ': professional development</h4><p>Skills to explore: ' +
        esc(guide.learn.join(" · ")) + '.</p><p>The technology market pulse is not ' +
        'validated as an occupation-specific forecast for this profession.</p></article>');
      fill("global-growth", '<p class="section-lead">Profession-specific global growth ' +
        'statistics are not yet available for this role.</p>');
      return;
    }
    var global = S.TOPICS.slice().sort(function (a, b) { return S.radar(b)["Global momentum"] - S.radar(a)["Global momentum"]; }).slice(0, 4);
    fill("global-cards", radarCards(global, state, "Global momentum", "Momentum"));
    var growth = S.TOPICS.slice().sort(function (a, b) { return b.signals.github_growth - a.signals.github_growth; }).slice(0, 5);
    fill("global-growth", growth.map(function (t) {
      return '<div class="rb lt"><span class="lab">' + esc(t.short) + '</span><span class="track"><i class="fill" style="width:' + t.signals.github_growth + '%"></i></span><span class="num">+' + t.signals.github_growth + "%</span></div>";
    }).join(""));
  }

  function renderProjects(state, topics) {
    var guide = careerGuide(state.profile);
    if (!guide.technical) {
      fill("proj-grid", guide.practice.map(function (idea, i) {
        return '<article class="card proj"><div class="ph"><span class="ptag">' +
          esc(state.profile) + '</span></div><h4>' + esc(idea) +
          '</h4><p>Curated practice idea. Adapt to professional standards and use only ' +
          'fictional or non-confidential material.</p><a class="btn small" href="' +
          REL + 'report/ai-plan/' + qstring(state) + '">See step-by-step plan →</a></article>';
      }).join(""));
      return;
    }
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
    var guide = careerGuide(state.profile);
    if (!guide.technical) {
      fill("vis-copy", copyRow("Show your skills", guide.show) +
        copyRow("Practice example", guide.practice[0]) +
        copyRow("Competency focus", guide.learn.join(" · ")) +
        copyRow("Next move", goalFocus(state.goal, state.profile)));
      return;
    }
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
    // Successful report-page render is the funnel outcome, not just the CTA
    // click that initiated navigation. No location or role is transmitted.
    if (PAGE.type === "report") {
      var event = { event: "scout_report_viewed", source: "report" };
      if (Array.isArray(window.dataLayer)) window.dataLayer.push(event);
      try { window.dispatchEvent(new CustomEvent("scout:analytics", { detail: event })); } catch (_) {}
    }
  });
})();
