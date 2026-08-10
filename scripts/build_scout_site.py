#!/usr/bin/env python3
"""
Generate the Scout multi-page site into ``scout/``.

Scout is a real multi-page product: every section is its own route with its own
``index.html`` (no ``?page=`` hidden sections), sharing one design system. The
landing (``scout/index.html``) is the React app; this script generates every
other route:

    report/                     report dashboard
    report/overview/            overview
    report/ai-plan/             AI action plan
    report/local-radar/         local radar
    report/global-pulse/        global pulse
    report/projects/            project ideas
    report/visibility/          visibility plan
    topics/<id>/                one page per topic
    api/                        API documentation
    dataset/                    dataset information
    admin/                      admin area (locked shell)

Dynamic, per-user content (scores, top topic, lists) is hydrated client-side by
scout-site.js from the report state carried in the query string, so pages stay
bookmarkable and shareable. Run:  python scripts/build_scout_site.py
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "scout"

# (id, short label, full name) — mirrors scout-data.js TOPICS (client renders detail)
TOPICS = [
    ("ai-agents", "AI Agents", "AI Agents & Agentic Workflows"),
    ("rag", "RAG Systems", "Retrieval-Augmented Generation"),
    ("llm-evaluation", "LLM Evaluation", "LLM & Agent Evaluation"),
    ("ai-governance", "AI Governance", "AI Governance & Policy Automation"),
    ("cybersecurity-automation", "Security Automation", "Cybersecurity Automation"),
    ("cloud-native-ai", "Cloud-Native AI", "Cloud-Native AI Applications"),
]

# report sections: (slug, label, icon glyph)
SECTIONS = [
    ("overview", "Overview", "◎"),
    ("ai-plan", "AI Plan", "◇"),
    ("local-radar", "Local Radar", "◉"),
    ("global-pulse", "Global Pulse", "◐"),
    ("projects", "Projects", "▣"),
    ("visibility", "Visibility", "◈"),
]
SECTION_DESC = {
    "overview": "The quick summary of your strongest opportunities and confidence.",
    "ai-plan": "A validate → learn → build → publish → grow action plan.",
    "local-radar": "Opportunities, hiring demand, and activity near you.",
    "global-pulse": "What is gaining momentum around the world.",
    "projects": "Portfolio-ready project ideas with stacks and deliverables.",
    "visibility": "How to publish and get noticed for what you build.",
}


def head(rel: str, title: str, desc: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <meta name="theme-color" content="#08170f" />
  <title>{title}</title>
  <meta name="description" content="{desc}" />
  <link rel="icon" type="image/svg+xml" href="{rel}assets/favicon.svg" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600;700;800&family=Newsreader:opsz,wght@6..72,500;6..72,600&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="{rel}scout.css" />
  <link rel="stylesheet" href="{rel}scout-site.css" />
</head>
<body class="site">"""


def tool_header(rel: str) -> str:
    return f"""  <header class="tool-header">
    <div class="tool-header__in">
      <a class="tool-header__back" href="{rel}">← <span>Home</span></a>
      <a class="tool-header__title" href="{rel}" style="color:#fff"><span class="gl">◇</span> Scout</a>
      <div class="tool-header__user"><span class="live"><span class="dot"></span>LIVE</span><span class="avatar">RM</span></div>
    </div>
  </header>"""


def subnav(active: str, rel: str) -> str:
    links = [("report", "Report", f"{rel}report/")]
    links += [(s, lab, f"{rel}report/{s}/") for s, lab, _ in SECTIONS]
    parts = []
    for slug, lab, href in links:
        cls = ' class="active"' if slug == active else ""
        parts.append(f'<a data-keepq href="{href}"{cls}>{lab}</a>')
    return f'  <nav class="subnav"><div class="subnav__in">{"".join(parts)}</div></nav>'


def footer(rel: str) -> str:
    return f"""  <footer class="foot">
    <div class="wrap row">
      <div class="brand"><span style="color:var(--green)">◇</span> Scout</div>
      <div class="links">
        <a href="{rel}api/">API</a>
        <a href="{rel}dataset/">Dataset</a>
        <a href="{rel}admin/">Admin</a>
        <a href="https://github.com/ruslanmv/scout" target="_blank" rel="noreferrer">GitHub</a>
      </div>
      <div class="copy">Public developer layer of Matrix Scout · ruslanmv.com</div>
    </div>
  </footer>"""


# --------------------------------------------------------------------------- #
#  "What do you want to become?" — dynamic learning-path generator
# --------------------------------------------------------------------------- #
def become_widget(rel: str) -> str:
    """The report ending: capture a target role + goal and hand off to the
    Learning Navigator (which runs the real deterministic pipeline, with an
    offline demo fallback) and lands the learner in My Learning.

    Returned as a plain string (not an f-string) so its CSS/JS braces stay
    literal; ``__REL__`` is substituted with the page's relative root.
    """
    html = """
    <section class="section reveal" id="become">
      <div class="section-head">
        <h3>🎯 Create a new learning path</h3>
        <p class="section-lead">Point Scout at what you want to <em>become</em> and it builds a
          verified, step-by-step path — wired straight into
          <a data-keepq href="__REL__my-learning/">My Learning</a>.</p>
      </div>
      <article class="darkpanel" style="padding:clamp(20px,3vw,32px)">
        <form id="becomeForm" novalidate>
          <div class="become-grid">
            <div class="field">
              <label for="become-role">What do you want to become?</label>
              <input id="become-role" list="become-roles" autocomplete="off"
                     placeholder="e.g. AI Engineer" value="AI Engineer" />
              <datalist id="become-roles">
                <option>AI Engineer</option><option>AI Agent Developer</option>
                <option>Machine Learning Engineer</option><option>MLOps Engineer</option>
                <option>Cloud Solutions Architect</option><option>Backend Developer</option>
                <option>Data Engineer</option><option>Platform Engineer</option>
              </datalist>
            </div>
            <div class="field sel">
              <label for="become-goal">Your main objective</label>
              <select id="become-goal">
                <option value="build_portfolio">Build a portfolio</option>
                <option value="career">Land a job</option>
                <option value="startup">Launch a product</option>
                <option value="upskill">Upskill in my role</option>
              </select>
            </div>
          </div>
          <div class="become-focus">
            <span class="become-focus-l">Focus areas (optional)</span>
            <div class="chips" id="become-chips">
              <button type="button" data-f="Multi-agent orchestration">Multi-agent orchestration</button>
              <button type="button" data-f="Tool calling">Tool calling</button>
              <button type="button" data-f="RAG">RAG</button>
              <button type="button" data-f="Vector databases">Vector databases</button>
              <button type="button" data-f="Evaluation">Evaluation</button>
              <button type="button" data-f="Deployment">Deployment</button>
            </div>
          </div>
          <button class="btn primary big on-dark" type="submit">⚡ Generate my learning path →</button>
          <p class="become-note">Uses your report's location automatically. The path is built by
            Scout's deterministic pipeline; prices it can't verify show “Verify on provider”.</p>
        </form>
      </article>
    </section>
    <style>
      #become .become-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
      @media(max-width:560px){#become .become-grid{grid-template-columns:1fr}}
      #become .field label{color:#cfe0d6}
      #become .field input,#become .field select{background:rgba(255,255,255,.06);
        border:1px solid rgba(120,200,160,.28);color:#eaf3ee}
      #become .field input:focus,#become .field select:focus{border-color:var(--green-on-dark);
        box-shadow:0 0 0 4px rgba(84,217,140,.15)}
      #become .field.sel::after{color:var(--green-on-dark)}
      #become .become-focus{margin:16px 0 6px}
      #become .become-focus-l{display:block;font-weight:800;color:#cfe0d6;font-size:11px;
        text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px}
      #become .chips{display:flex;flex-wrap:wrap;gap:8px}
      #become .chips button{background:rgba(255,255,255,.06);border:1px solid rgba(120,200,160,.28);
        color:#cfe0d6;border-radius:999px;padding:7px 13px;font-weight:700;font-size:13px;cursor:pointer}
      #become .chips button.on{background:var(--green);border-color:var(--green);color:#fff}
      #become .btn.big{margin-top:6px}
      #become .become-note{color:#8fb0a0;font-size:12px;margin:12px 0 0}
    </style>
    <script>
    (function(){
      var q = new URLSearchParams(location.search);
      var goalSel = document.getElementById('become-goal');
      var g = q.get('goal');
      if (g) for (var i=0;i<goalSel.options.length;i++){ if (goalSel.options[i].value===g){ goalSel.selectedIndex=i; break; } }
      var focus = [];
      Array.prototype.forEach.call(document.querySelectorAll('#become-chips button'), function(b){
        b.addEventListener('click', function(){
          b.classList.toggle('on');
          var f=b.getAttribute('data-f'); var i=focus.indexOf(f);
          if (i>=0) focus.splice(i,1); else focus.push(f);
        });
      });
      document.getElementById('becomeForm').addEventListener('submit', function(e){
        e.preventDefault();
        var role = (document.getElementById('become-role').value||'').trim() || 'AI Engineer';
        var u = new URL('__REL__learn/', location.href);
        u.searchParams.set('intent','advance_career');
        u.searchParams.set('role', role);
        u.searchParams.set('goal', goalSel.value);
        if (q.get('country')) u.searchParams.set('country', q.get('country'));
        if (q.get('city')) u.searchParams.set('city', q.get('city'));
        if (focus.length) u.searchParams.set('focus', focus.join(','));
        u.searchParams.set('start','1');
        window.location.href = u.toString();
      });
    })();
    </script>
    """
    return html.replace("__REL__", rel)


def scripts(rel: str, cfg: str) -> str:
    return f"""  <script>window.SCOUT_PAGE = {cfg};</script>
  <script src="{rel}scout-data.js"></script>
  <script src="{rel}scout-site.js"></script>
</body>
</html>"""


def crumbs(rel: str, trail: list[tuple[str, str]]) -> str:
    parts = []
    for i, (label, href) in enumerate(trail):
        if href:
            parts.append(f'<a data-keepq href="{href}">{label}</a>')
        else:
            parts.append(f"<span>{label}</span>")
        if i < len(trail) - 1:
            parts.append("<span>/</span>")
    return '<div class="crumbs">' + "".join(parts) + "</div>"


def write(path: str, html: str) -> None:
    out = SITE / path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")


def page(path: str, rel: str, title: str, desc: str, body: str, cfg: str) -> None:
    html = "\n".join([head(rel, title, desc), tool_header(rel), body, footer(rel), scripts(rel, cfg)])
    write(path, html)


# --------------------------------------------------------------------------- #
#  report dashboard
# --------------------------------------------------------------------------- #
def build_report() -> None:
    rel = "../"
    nav = "".join(
        f'<a class="card navcard" data-keepq href="{rel}report/{slug}/">'
        f'<div class="nc-top"><span class="nc-ic">{icon}</span><h3>{lab}</h3></div>'
        f'<p>{SECTION_DESC[slug]}</p><span class="go">Open →</span></a>'
        for slug, lab, icon in SECTIONS
    )
    body = f"""  {subnav("report", rel)}
  <main class="pagewrap">
    <div class="pagehead reveal">
      {crumbs(rel, [("Home", rel), ("Report", "")])}
      <div class="meta">Scout Report</div>
      <h1 data-bind="loc">Your report</h1>
      <p class="lede">Personalized for <b data-bind="profile">Developer</b> · goal <b data-bind="goal">Build portfolio</b>. Here is your opportunity report and every section of the plan.</p>
      <div class="stat-inline">
        <div class="si"><div class="n"><span data-bind="score">—</span><span style="color:var(--faint);font-size:1rem">/100</span></div><div class="l">Opportunity score</div></div>
        <div class="si"><div class="n" data-bind="topicsCount">—</div><div class="l">Topics</div></div>
        <div class="si"><div class="n" data-bind="projectsCount">—</div><div class="l">Project ideas</div></div>
        <div class="si"><div class="n" data-bind="actionsCount">—</div><div class="l">Actions</div></div>
      </div>
    </div>

    <article class="darkpanel move reveal" style="grid-template-columns:1fr;margin-top:24px">
      <div class="move-main">
        <div class="verdict">
          <span class="vbadge"><span class="d"></span>Your strongest opportunity</span>
          <h3 class="vhead">Learn <span class="em" data-bind="topShort">—</span>.</h3>
          <p class="vsub" data-bind="verdict">Loading your report…</p>
        </div>
        <div class="gain" data-bind="topSummary">—</div>
        <div class="move-foot">
          <span class="conf high on-dark"><span class="d"></span>High confidence</span>
          <div class="ctarow"><a class="btn primary small on-dark" data-keepq href="{rel}report/overview/">Open overview →</a></div>
        </div>
      </div>
    </article>

    <section class="section">
      <div class="section-head"><h3>Report sections</h3></div>
      <div class="navgrid">{nav}</div>
    </section>
    {become_widget(rel)}
    <div class="backrow"><a class="btn ghost" href="{rel}">← Start a new report</a></div>
  </main>"""
    page("report/index.html", rel, "Your Scout Report", "Your personalized developer opportunity report.",
         body, '{ type: "report", rel: "../" }')


# --------------------------------------------------------------------------- #
#  report sub-sections
# --------------------------------------------------------------------------- #
def section_shell(slug: str, rel: str, title_h1: str, lede: str, inner: str, cfg_type: str) -> None:
    body = f"""  {subnav(slug, rel)}
  <main class="pagewrap">
    <div class="pagehead reveal">
      {crumbs(rel, [("Home", rel), ("Report", f"{rel}report/"), (dict((s, l) for s, l, _ in SECTIONS)[slug], "")])}
      <div class="meta" data-bind="loc">Scout Report</div>
      <h1>{title_h1}</h1>
      <p class="lede">{lede}</p>
    </div>
    {inner}
    <div class="backrow"><a class="btn ghost" data-keepq href="{rel}report/">← Back to report</a></div>
  </main>"""
    page(f"report/{slug}/index.html", rel, f"{title_h1} — Scout Report",
         f"{title_h1} for your Scout report.", body, f'{{ type: "{cfg_type}", rel: "{rel}" }}')


def build_sections() -> None:
    rel = "../../"

    # Overview
    inner = f"""
    <section class="section"><div class="section-head"><h3>Top opportunities</h3></div>
      <div class="opgrid" id="ov-top"></div></section>
    <div class="split" style="margin-top:26px">
      <article class="card" style="padding:22px">
        <div class="section-head compact"><h3>Opportunity scores</h3><p>How your top topic scores across Scout's signal radar.</p></div>
        <div class="radarbars" id="ov-scores" style="margin-top:14px"></div>
      </article>
      <article class="card" style="padding:22px">
        <div class="section-head compact"><h3>Study → build → publish</h3></div>
        <div class="move-rows" style="border-top:0">
          <div class="vrow"><span class="vk">Study</span><span data-bind="studyNow" style="color:var(--text)">—</span></div>
          <div class="vrow"><span class="vk">Build</span><span data-bind="buildNow" style="color:var(--text)">—</span></div>
          <div class="vrow"><span class="vk">Publish</span><span data-bind="publishNow" style="color:var(--text)">—</span></div>
          <div class="vrow"><span class="vk">Confidence</span><span data-bind="confidence" style="color:var(--green-700);font-weight:700">—</span></div>
        </div>
      </article>
    </div>
    <section class="section"><div class="section-head"><h3>Recommended first action</h3></div>
      <article class="card" style="padding:22px"><p style="margin:0;color:var(--text);font-size:1.05rem" data-bind="firstAction">—</p>
        <div class="ctarow"><a class="btn primary small" data-keepq href="{rel}report/ai-plan/">See the full plan →</a>
        <a class="btn small" data-keepq href="{rel}report/projects/">Browse projects</a></div></article></section>
    <section class="section"><div class="section-head"><h3>Key technology trends</h3></div>
      <ul class="prose"><li><b>Agentic systems</b> are moving from demos to production workflows.</li>
      <li><b>Retrieval</b> stays the most practical way to ground models in real data.</li>
      <li><b>Evaluation &amp; governance</b> grow as teams ship AI to real users.</li></ul></section>"""
    section_shell("overview", rel, "Overview", "The most important findings from your report, at a glance.", inner, "overview")

    # AI Plan
    inner = f"""
    <section class="section" style="margin-top:8px">
      <div class="section-head"><h3>Your action plan</h3><p class="section-lead">Six steps from idea to published, discoverable work.</p></div>
      <div class="plan" id="plan"></div>
    </section>"""
    section_shell("ai-plan", rel, "AI Action Plan", "Turn your report into concrete, time-boxed steps.", inner, "ai-plan")

    # Local Radar
    pins = "".join(
        f'<span class="pin" style="left:{x}%;top:{y}%"></span>'
        for x, y in [(28, 42), (54, 30), (46, 62), (70, 52), (36, 74)]
    )
    inner = f"""
    <div class="mapwrap reveal">{pins}<span class="maplabel" data-bind="loc">Your area</span></div>
    <section class="section"><div class="section-head"><h3>Opportunities near you</h3></div>
      <div class="opgrid" id="local-cards"></div></section>
    <div class="split" style="margin-top:26px">
      <article class="card" style="padding:22px"><div class="section-head compact"><h3>Hiring demand</h3><p>Roles asking for these skills.</p></div>
        <div class="radarbars" id="local-hiring" style="margin-top:14px"></div></article>
      <article class="card" style="padding:22px"><div class="section-head compact"><h3>Recommended local actions</h3></div>
        <ul class="prose" style="margin-top:12px"><li>Join a local AI / developer meetup and present a demo.</li>
        <li>Follow nearby companies hiring for these skills.</li>
        <li>Publish a project tagged to your city to surface local interest.</li></ul></article>
    </div>
    <p class="muted-note">Local indicators are directional; salary and demand figures are shown only where reliable data is available.</p>"""
    section_shell("local-radar", rel, "Local Radar", "Opportunities and demand in your area.", inner, "local-radar")

    # Global Pulse
    inner = f"""
    <div class="worldwrap reveal">{world_svg()}</div>
    <section class="section"><div class="section-head"><h3>Gaining momentum globally</h3></div>
      <div class="opgrid" id="global-cards"></div></section>
    <div class="split" style="margin-top:26px">
      <article class="card" style="padding:22px"><div class="section-head compact"><h3>Fastest growth</h3><p>GitHub growth signal.</p></div>
        <div class="radarbars" id="global-growth" style="margin-top:14px"></div></article>
      <article class="card" style="padding:22px"><div class="section-head compact"><h3>Emerging &amp; sources</h3></div>
        <ul class="prose" style="margin-top:12px"><li>Agent evaluation &amp; observability tooling.</li>
        <li>On-device and cost-aware inference.</li>
        <li>Open-source model ecosystems.</li></ul>
        <p class="muted-note">Signals combine GitHub, Hugging Face, news, jobs, and community activity. Confidence is shown per topic.</p></article>
    </div>"""
    section_shell("global-pulse", rel, "Global Pulse", "What is trending around the world.", inner, "global-pulse")

    # Projects
    inner = """
    <section class="section" style="margin-top:8px"><div class="section-head"><h3>Project ideas for you</h3>
      <p class="section-lead">Each is a portfolio-ready piece: a focused repo, a live demo, and a writeup.</p></div>
      <div class="projgrid" id="proj-grid"></div></section>"""
    section_shell("projects", rel, "Project Ideas", "Personalized, portfolio-ready project recommendations.", inner, "projects")

    # Visibility
    inner = """
    <div class="prose" style="margin-top:8px">
      <h2>Position yourself</h2>
      <p>Pick one focus and make it obvious. Your profile, pinned repos, and posts should all point at the same story.</p>
      <h2>GitHub &amp; portfolio</h2>
      <ul><li>Pin the project from your plan and write a clear README with a demo GIF.</li>
      <li>Add a short bio that names your focus area and location.</li>
      <li>Keep a simple portfolio page linking repo → demo → writeup.</li></ul>
      <h2>Content strategy</h2>
      <ul><li>Publish a build log while you make the project.</li>
      <li>Write one “how I built it” article when you ship.</li>
      <li>Share short updates in relevant communities.</li></ul>
    </div>
    <section class="section"><div class="section-head"><h3>Copy-ready assets</h3></div>
      <article class="card vis reveal"><div class="vis-list" id="vis-copy"></div></article></section>
    <section class="section"><div class="section-head"><h3>Where to publish</h3></div>
      <div class="tagrow"><span class="tag">GitHub</span><span class="tag">Hugging Face</span><span class="tag">Dev.to</span>
      <span class="tag">LinkedIn</span><span class="tag">Reddit</span><span class="tag">Personal blog</span></div></section>"""
    section_shell("visibility", rel, "Visibility Plan", "How to publish and get noticed for your work.", inner, "visibility")


# --------------------------------------------------------------------------- #
#  topic pages
# --------------------------------------------------------------------------- #
def build_topics() -> None:
    rel = "../../"
    for tid, short, name in TOPICS:
        body = f"""  {subnav("report", rel)}
  <main class="pagewrap">
    <div class="pagehead reveal">
      {crumbs(rel, [("Home", rel), ("Report", f"{rel}report/"), ("Topics", ""), (short, "")])}
      <div class="meta">Topic</div>
      <h1 data-bind="topicName">{name}</h1>
    </div>
    <div id="topic-root"></div>
    <div class="backrow"><a class="btn ghost" data-keepq href="{rel}report/overview/">← Back to overview</a></div>
  </main>"""
        page(f"topics/{tid}/index.html", rel, f"{short} — Scout",
             f"Deep dive into {name}.", body, f'{{ type: "topic", id: "{tid}", rel: "{rel}" }}')


# --------------------------------------------------------------------------- #
#  API docs
# --------------------------------------------------------------------------- #
def build_api() -> None:
    rel = "../"
    endpoints = [
        ("GET", "/api/v1/health", "Service health check.", '{ "status": "ok" }'),
        ("GET", "/api/v1/trends?country=Italy&city=Rome", "Ranked trending topics for a location.",
         '{\n  "topics": [\n    { "id": "ai-agents", "score": 94, "trust": "High" }\n  ]\n}'),
        ("GET", "/api/v1/topics/{topic}/deep-dive", "Full detail for one topic: signals, study plan, projects, risks.",
         '{\n  "topic": "ai-agents",\n  "study_plan": ["Tool calling", "Orchestration"],\n  "projects": ["Local trend scout agent"]\n}'),
        ("POST", "/api/v1/ai/plan", "Generate a study → build → publish plan for a topic and profile.",
         'curl -X POST /api/v1/ai/plan \\\n  -H "Content-Type: application/json" \\\n  -d \'{ "topic_id": "ai-agents", "profile": "developer" }\''),
        ("GET", "/api/v1/datasets/latest", "The latest published dataset snapshot.", "{ ... }"),
    ]
    ep_html = "".join(
        f'<article class="card endpoint"><div class="ep-h"><span class="method {m.lower()}">{m}</span>'
        f'<span class="path">{p}</span></div><p>{d}</p><pre class="code">{ex}</pre></article>'
        for m, p, d, ex in endpoints
    )
    body = f"""  <main class="pagewrap">
    <div class="pagehead reveal">
      {crumbs(rel, [("Home", rel), ("API", "")])}
      <div class="meta">Developers</div>
      <h1>API Documentation</h1>
      <p class="lede">Scout is a public REST API and MCP-ready intelligence layer. Explore endpoints, request and response formats, and copy-ready examples.</p>
      <div class="doc-toc"><span class="tag">Getting started</span><span class="tag">Authentication</span><span class="tag">Endpoints</span><span class="tag">Errors</span><span class="tag">Rate limits</span></div>
    </div>
    <div class="prose">
      <h2>Getting started</h2>
      <p>The base URL is your Scout deployment, for example <code style="font-family:var(--mono)">https://your-host/api/v1</code>. All responses are JSON.</p>
      <h2>Authentication</h2>
      <p>Public read endpoints need no key. Admin and write endpoints use an <code style="font-family:var(--mono)">X-Admin-Key</code> header. Never embed secrets in client code.</p>
      <h2>Endpoints</h2>
    </div>
    {ep_html}
    <div class="prose">
      <h2>Errors &amp; status codes</h2>
      <ul><li><b>200</b> — success</li><li><b>400</b> — invalid parameters</li><li><b>401</b> — missing or invalid admin key</li><li><b>404</b> — unknown topic or resource</li><li><b>429</b> — rate limited</li></ul>
      <h2>Rate limits</h2>
      <p>Public endpoints are rate limited per IP. For higher volume, self-host or use the published dataset directly.</p>
      <h2>Dataset &amp; MCP</h2>
      <p>Prefer bulk access? Use the <a data-keepq href="{rel}dataset/">dataset</a> endpoints, or expose Scout as MCP tools for agents.</p>
    </div>
    <div class="backrow"><a class="btn ghost" href="{rel}">← Home</a></div>
  </main>"""
    page("api/index.html", rel, "Scout API Documentation", "REST API and MCP intelligence layer for developers.",
         body, '{ type: "doc", rel: "../" }')


# --------------------------------------------------------------------------- #
#  dataset info
# --------------------------------------------------------------------------- #
def build_dataset() -> None:
    rel = "../"
    fields = [
        ("id", "Stable topic identifier, e.g. ai-agents."),
        ("name / short", "Human-readable topic names."),
        ("summary / why_follow", "Plain-language description and rationale."),
        ("signals", "0–100 indicators: github_activity, github_growth, huggingface_activity, news_mentions, job_demand, community_activity, local_relevance, project_potential, career_value, learning_accessibility, durability, ecosystem_fit."),
        ("study_plan / project_ideas / skills", "Learning steps, buildable projects, and skills shown."),
        ("trust", "Confidence score, label, and hype-risk index."),
        ("sources", "The independent inputs each topic is cross-checked against."),
    ]
    frows = "".join(f'<div class="frow"><div class="fk">{k}</div><div class="fv">{v}</div></div>' for k, v in fields)
    body = f"""  <main class="pagewrap">
    <div class="pagehead reveal">
      {crumbs(rel, [("Home", rel), ("Dataset", "")])}
      <div class="meta">Open data</div>
      <h1>Dataset Information</h1>
      <p class="lede">Scout publishes an open, versioned dataset of developer technology signals. This page explains what is inside, how it is scored, and how to use it.</p>
    </div>
    <div class="prose">
      <h2>Data sources</h2>
      <p>Signals combine public activity from GitHub, Hugging Face, news / RSS, job listings, and community discussion. No private data is used.</p>
      <h2>Data structure</h2>
    </div>
    <div class="fields">{frows}</div>
    <div class="prose">
      <h2>Scoring methodology</h2>
      <p>A composite score weights developer activity, growth, hiring demand, project potential, and ecosystem fit. Per-location relevance adjusts ranking for your city and country.</p>
      <h2 id="trust">Confidence &amp; trust</h2>
      <p>Each topic carries a confidence label and a hype-risk index, derived from source agreement, freshness, and provenance. Treat medium-confidence topics as directional.</p>
      <h2>Updates, version &amp; license</h2>
      <ul><li><b>Update frequency:</b> refreshed on a scheduled snapshot.</li>
      <li><b>Versioning:</b> each snapshot is dated; <code style="font-family:var(--mono)">latest</code> always points at the newest.</li>
      <li><b>License:</b> Apache-2.0 (code) with an open dataset for reuse.</li></ul>
      <h2>Download &amp; access</h2>
      <ul><li>Raw JSON: <a href="{rel}data/latest.json"><code style="font-family:var(--mono)">/data/latest.json</code></a></li>
      <li>Programmatic: see the <a data-keepq href="{rel}api/">API documentation</a>.</li></ul>
      <h2>Known limitations</h2>
      <p>Signals are proxies, not ground truth. Local indicators depend on data availability, and fast-moving topics can shift between snapshots.</p>
    </div>
    <div class="backrow"><a class="btn ghost" href="{rel}">← Home</a></div>
  </main>"""
    page("dataset/index.html", rel, "Scout Dataset", "Open, versioned dataset of developer technology signals.",
         body, '{ type: "doc", rel: "../" }')


# --------------------------------------------------------------------------- #
#  admin
# --------------------------------------------------------------------------- #
def build_admin() -> None:
    rel = "../"
    items = ["Dashboard", "Data management", "Dataset updates", "Topic management",
             "API configuration", "AI provider settings", "Users & access",
             "System health", "Logs", "Analytics", "Deployment"]
    side_parts = []
    for i, it in enumerate(items):
        cls = ' class="active"' if i == 0 else ""
        side_parts.append(f'<a href="#"{cls}>{it}</a>')
    side = "".join(side_parts)
    body = f"""  <main class="pagewrap">
    <div class="pagehead reveal">
      {crumbs(rel, [("Home", rel), ("Admin", "")])}
      <div class="meta">Restricted</div>
      <h1>Admin Area</h1>
      <p class="lede">Manage data, settings, and system configuration. This area is protected and separate from the public product.</p>
    </div>
    <div class="locked reveal"><span class="ri">🔒</span><p><b>Authentication required.</b> Sign in with your admin key to manage Scout. AI provider settings live in the existing secured settings page.</p></div>
    <div class="admin-shell">
      <nav class="admin-side">{side}</nav>
      <div class="admin-panel">
        <article class="card" style="padding:22px"><div class="section-head compact"><h3>Overview</h3></div>
          <div class="stat-inline" style="margin-top:12px">
            <div class="si"><div class="n">6</div><div class="l">Topics</div></div>
            <div class="si"><div class="n">5</div><div class="l">Sources</div></div>
            <div class="si"><div class="n">OK</div><div class="l">Health</div></div>
          </div></article>
        <article class="card" style="padding:22px"><div class="section-head compact"><h3>Quick actions</h3></div>
          <div class="ctarow" style="margin-top:12px">
            <a class="btn small" href="#">Regenerate snapshot</a>
            <a class="btn small" href="#">Publish dataset</a>
            <a class="btn small" href="#">View logs</a>
          </div>
          <p class="muted-note">AI provider &amp; runtime settings are managed in the secured settings page of the backend.</p>
        </article>
      </div>
    </div>
    <div class="backrow"><a class="btn ghost" href="{rel}">← Home</a></div>
  </main>"""
    page("admin/index.html", rel, "Scout Admin", "Protected administration area.",
         body, '{ type: "doc", rel: "../" }')


def world_svg() -> str:
    land = [
        "................................................",
        "........#######..####............#####..........",
        "......##########.#####....#####################.",
        "..##############.####.#..######################.",
        "..###.##########.......#.######################.",
        ".......########........########################.",
        ".......########.........###################.....",
        "........######........#####################.....",
        ".........###.........#####################......",
        "..........###........###################........",
        "...........###.......###########.##..##.........",
        ".............#####.....########......######.....",
        ".............######.....#######.......#######...",
        "..............#####......######.........####....",
        "..............####.......#####.#.......######...",
        "...............###........####.........######...",
        "...............##.........###............####...",
        "...............##.............................#.",
    ]
    dots = []
    for r, row in enumerate(land):
        for c, ch in enumerate(row):
            if ch == "#":
                dots.append(f'<circle cx="{c*10+5}" cy="{r*10+5}" r="2.1" fill="#53f39d" opacity="0.7"/>')
    return f'<svg viewBox="0 0 480 190" width="900" role="img" aria-label="World technology activity">{"".join(dots)}</svg>'


def main() -> None:
    build_report()
    build_sections()
    build_topics()
    build_api()
    build_dataset()
    build_admin()
    generated = ["report/"] + [f"report/{s}/" for s, _, _ in SECTIONS] + \
        [f"topics/{t}/" for t, _, _ in TOPICS] + ["api/", "dataset/", "admin/"]
    print("Generated Scout site pages into", SITE)
    for g in generated:
        print("  ", g)


if __name__ == "__main__":
    main()
