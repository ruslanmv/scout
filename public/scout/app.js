const $ = (id) => document.getElementById(id);
const state = { report: null, local: [], global: [], activeTopic: null, activeDive: null, showAllLocal: false, showAllGlobal: false, advanced: false, staticMode: false };

const labels = {
  goals: { career: 'Career growth', build_portfolio: 'Build portfolio', create_agents: 'Create agents', startup: 'Startup ideas', research: 'Research' },
  profiles: { developer: 'Developer', ai_engineer: 'AI engineer', student: 'Student', founder: 'Founder', enterprise: 'Enterprise leader', agent: 'Agentic AI system' },
};

function esc(value) {
  return String(value ?? '').replace(/[&<>'"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[c]));
}

function setStatus(message) { $('status').textContent = message; }

async function fetchJSON(url, options) {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function parseLocation(value) {
  const parts = (value || 'Worldwide').split(',').map((x) => x.trim()).filter(Boolean);
  if (parts.length === 1) return { city: null, country: parts[0] };
  return { city: parts[0], country: parts.slice(1).join(', ') };
}

function qs() {
  const loc = parseLocation($('location').value);
  return new URLSearchParams({ country: loc.country || 'Worldwide', city: loc.city || '', goal: $('goal').value, profile: $('profile').value, limit: '10' });
}

function apiPath(path) { return `${window.location.origin}${path}`; }

function trustLabel(topic) { return topic?.trust?.label || topic?.confidence?.label || 'Medium confidence'; }
function signal(topic, key) { return Number(topic?.signals?.[key] || 0); }
function topicScore(topic) {
  const score = Number(topic?.score || 0);
  if (score) return score;
  return Math.round((signal(topic, 'github_activity') + signal(topic, 'project_potential') + signal(topic, 'career_value') + signal(topic, 'local_relevance')) / 4);
}
function score(topic) { return topicScore(topic).toFixed(0); }

function metric(label, value) {
  const n = Number(value || 0);
  return `<div class="bar"><span>${esc(label)}</span><div><i style="width:${Math.max(4, Math.min(100, n))}%"></i></div><b>${n.toFixed(0)}</b></div>`;
}

function card(topic, index) {
  const signals = topic.signals || {};
  const detail = state.advanced ? `<div class="metrics">${metric('Local', signals.local_relevance)}${metric('Career', signals.career_value)}${metric('Project', signals.project_potential)}</div>` : '';
  const project = (topic.project_ideas || [])[0] || 'Build a practical demo';
  return `<div class="topic-card">
    <div class="topic-top"><span class="rank">#${index + 1}</span><span class="score">${score(topic)}</span></div>
    <h4>${esc(topic.name)}</h4>
    <p>${esc(topic.summary || topic.why_follow || '')}</p>
    <p class="muted"><strong>Build:</strong> ${esc(project)}</p>
    <div class="topic-footer"><span class="pill">${esc(topic.priority || 'trend')}</span><span class="trust">${esc(trustLabel(topic))}</span></div>
    ${detail}
    <button class="link-btn" data-topic="${esc(topic.id)}">See simple plan</button>
  </div>`;
}

function bindTopicButtons() {
  document.querySelectorAll('[data-topic]').forEach((button) => button.addEventListener('click', () => deepDive(button.dataset.topic)));
}

function renderCards(el, topics, showAll) {
  const visible = showAll ? topics : topics.slice(0, 3);
  el.innerHTML = visible.map(card).join('');
  bindTopicButtons();
}

function renderInsights(report) {
  const top = report.summary || {};
  $('insights').innerHTML = [
    ['Study first', top.top_topic || '—'],
    ['Build next', top.top_project || '—'],
    ['Best move', top.next_move?.action || 'Ship a public demo'],
    ['Trust', top.confidence?.label || 'High confidence'],
  ].map(([k, v]) => `<div class="insight"><span>${esc(k)}</span><strong>${esc(v)}</strong></div>`).join('');
}

function copyValue(value, button) {
  navigator.clipboard?.writeText(value || '');
  if (button) {
    const old = button.textContent;
    button.textContent = 'Copied';
    setTimeout(() => { button.textContent = old; }, 1200);
  }
}

function renderVisibility(plan) {
  const rows = [
    ['GitHub repo', plan.github_repo],
    ['Demo page', plan.huggingface_space || plan.demo],
    ['Blog title', plan.blog_title],
    ['Skills', (plan.skills_to_show || []).join(', ')],
  ];
  $('visibility').innerHTML = rows.map(([label, value]) => `<div class="copy-row"><span>${esc(label)}</span><code>${esc(value || '—')}</code><button class="copy-btn" data-copy="${esc(value || '')}">Copy</button></div>`).join('') +
    `<ol>${(plan.publish_steps || []).map((s) => `<li>${esc(s)}</li>`).join('')}</ol>`;
  document.querySelectorAll('.copy-btn').forEach((button) => button.addEventListener('click', () => copyValue(button.dataset.copy, button)));
}

function renderProjects(projects) {
  $('projects').innerHTML = (projects || []).slice(0, 5).map((p) => `<div class="project"><h4>${esc(p.title || p)}</h4><p>${esc(p.why_it_promotes_you || p.description || '')}</p><p class="muted">${esc(p.estimated_time || '1-4 weeks')} · ${esc((p.deliverables || ['GitHub repo', 'Live demo', 'Short article']).join(' · '))}</p></div>`).join('');
}

function simpleVisibility(topic) {
  const slug = topic.id || 'next-project';
  return {
    github_repo: `github.com/you/${slug}-demo`,
    huggingface_space: `huggingface.co/spaces/you/${slug}`,
    blog_title: `How I built a practical ${topic.name} demo`,
    skills_to_show: topic.skills || ['Python', 'APIs', 'Product thinking'],
    publish_steps: ['Create a focused GitHub README with screenshots.', 'Deploy a tiny working demo.', 'Write a short post explaining the problem, data, and result.'],
  };
}

function simpleProjects(topic) {
  return (topic.project_ideas || ['Practical demo']).slice(0, 5).map((title) => ({
    title,
    why_it_promotes_you: `Shows that you can turn ${topic.name} into a useful product-style workflow.`,
    estimated_time: '1-2 weeks',
    deliverables: ['GitHub repo', 'Demo', 'Write-up'],
  }));
}

function buildStaticReport(dataset) {
  const loc = parseLocation($('location').value);
  const topics = [...(dataset.topics || [])].sort((a, b) => topicScore(b) - topicScore(a));
  const top = topics[0] || {};
  const project = (top.project_ideas || [])[0] || 'Build a practical demo';
  return {
    report: {
      location: { country: loc.country || 'Worldwide', city: loc.city },
      goal: $('goal').value,
      profile: $('profile').value,
      recommendations: topics,
      summary: {
        headline: `${top.name || 'Scout'} is your strongest opportunity right now.`,
        top_topic: top.name,
        top_project: project,
        next_move: { action: `Build and publish: ${project}`, study: (top.study_plan || [top.name]).slice(0, 2), build: project },
        confidence: top.trust || { label: 'Dataset-backed confidence' },
      },
      projects: simpleProjects(top),
      visibility_plan: simpleVisibility(top),
    },
    local_topics: topics,
    global_topics: topics,
  };
}

async function loadStaticFallback() {
  const dataset = await fetchJSON('data/latest.json');
  state.staticMode = true;
  setStatus(`Static GitHub Pages mode · dataset generated ${new Date(dataset.generated_at || Date.now()).toLocaleDateString()}`);
  return buildStaticReport(dataset);
}

function renderReport(data) {
  state.report = data.report;
  state.local = data.local_topics || data.report?.recommendations || [];
  state.global = data.global_topics || [];
  const report = state.report;
  const top = report.recommendations?.[0] || state.local[0] || {};
  $('report').classList.remove('hidden');
  $('sticky').classList.remove('hidden');
  $('preview-topic').textContent = top.name || 'Scout Report';
  $('preview-copy').textContent = report.summary?.headline || 'Your simple plan is ready.';
  $('report-title').textContent = `${report.location?.city ? `${report.location.city}, ` : ''}${report.location?.country || 'Worldwide'} · ${labels.goals[report.goal] || report.goal} · ${labels.profiles[report.profile] || report.profile}`;
  $('top-topic').textContent = top.name || '—';
  $('top-summary').textContent = top.why_follow || top.summary || '—';
  $('study-now').textContent = (report.summary?.next_move?.study || top.study_plan || [top.name || '—']).slice(0, 2).join(' → ');
  $('build-now').textContent = report.summary?.next_move?.build || report.summary?.top_project || (top.project_ideas || [])[0] || '—';
  $('confidence-now').textContent = report.summary?.confidence?.label || trustLabel(top);
  $('sticky-move').textContent = report.summary?.next_move?.build || 'Open project plan';
  $('top-evidence').onclick = () => deepDive(top.id);
  $('top-project').onclick = () => deepDive(top.id, 'projects');
  $('sticky-btn').onclick = () => deepDive(top.id, 'projects');
  renderInsights(report);
  renderCards($('local'), state.local, state.showAllLocal);
  renderCards($('global'), state.global, state.showAllGlobal);
  renderProjects(report.projects || simpleProjects(top));
  renderVisibility(report.visibility_plan || simpleVisibility(top));
  updateUrl();
  loadAiPlan();
  window.scrollTo({ top: $('report').offsetTop - 20, behavior: 'smooth' });
}

function chips(items) { return (items || []).map((s) => `<span class="chip">${esc(s)}</span>`).join(''); }
function olist(items) { return `<ol>${(items || []).map((s) => `<li>${esc(s)}</li>`).join('')}</ol>`; }

function aiBadge(plan) {
  if (plan.source === 'ollabridge-cloud') return `<span class="ai-badge">✨ Live AI · ${esc(plan.provider)} · ${esc(plan.model)}</span>`;
  return `<span class="ai-badge off">Built-in plan · ${esc(plan.provider || 'Scout templates')}</span>`;
}

function renderAiPlan(panel, plan) {
  const build = plan.build || {};
  panel.innerHTML = `
    <div class="ai-head">
      <div>${aiBadge(plan)}<h3>${esc(plan.headline || 'Your AI action plan')}</h3></div>
      <button id="ai-regen" class="secondary small">↻ Regenerate</button>
    </div>
    <p class="ai-why">${esc(plan.why_now || '')}</p>
    <div class="ai-grid">
      <div class="ai-col"><h4>📚 Study</h4>${olist(plan.study)}</div>
      <div class="ai-col"><h4>🛠 Build</h4>
        <p class="ai-build-title">${esc(build.title || '')}</p>
        <p class="muted">${esc(build.description || '')}</p>
        <p class="ai-stack">${chips(build.stack)}</p>
        <p class="muted">Deliverables: ${esc((build.deliverables || []).join(' · '))}</p>
      </div>
      <div class="ai-col"><h4>🚀 Publish</h4>${olist(plan.publish)}</div>
    </div>
    <div class="ai-foot">
      <div><h4>Skills you'll show</h4><p>${chips(plan.skills)}</p></div>
      <div><h4>Watch out for</h4>${olist(plan.risks)}</div>
    </div>
    <p class="ai-confidence">${esc(plan.confidence || '')}${plan.note ? ` — ${esc(plan.note)}` : ''}</p>`;
  document.getElementById('ai-regen')?.addEventListener('click', () => loadAiPlan());
}

function renderAiLoading(panel, status) {
  panel.innerHTML = `<div class="ai-head"><div><span class="ai-badge">✨ ${esc(status.provider)} · ${esc(status.model)}</span><h3>Designing your plan…</h3></div></div><p class="ai-why">Scout is asking the AI to turn your real trend signals into a concrete path. This takes a few seconds.</p>`;
}

function renderAiError(panel, message) {
  panel.innerHTML = `<div class="ai-head"><div><span class="ai-badge off">AI unavailable</span><h3>Showing Scout's built-in plan above</h3></div><button id="ai-regen" class="secondary small">↻ Retry</button></div><p class="ai-why muted">${esc(message)}</p>`;
  document.getElementById('ai-regen')?.addEventListener('click', () => loadAiPlan());
}

async function loadAiPlan() {
  const panel = $('ai-plan');
  if (!panel || state.staticMode) { panel?.classList.add('hidden'); return; }
  let status;
  try { status = await fetchJSON('/api/v1/ai/status'); } catch { panel.classList.add('hidden'); return; }
  if (!status.ai_enabled) { panel.classList.add('hidden'); return; }
  const top = state.report?.recommendations?.[0] || state.local[0];
  if (!top || (!top.id && !top.name)) { panel.classList.add('hidden'); return; }
  panel.classList.remove('hidden');
  renderAiLoading(panel, status);
  try {
    const loc = parseLocation($('location').value);
    const plan = await fetchJSON('/api/v1/ai/plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic_id: top.id, topic: top, country: loc.country || 'Worldwide', city: loc.city || null, goal: $('goal').value, profile: $('profile').value }),
    });
    renderAiPlan(panel, plan);
  } catch (e) {
    renderAiError(panel, e.message || 'The AI engine could not be reached.');
  }
}

async function load() {
  $('load').disabled = true;
  $('load').textContent = 'Generating…';
  try {
    let data;
    try {
      data = await fetchJSON(`/api/v1/ui/bootstrap?${qs().toString()}`);
      state.staticMode = false;
      setStatus('Live API mode · report generated from the Scout backend.');
    } catch (apiError) {
      data = await loadStaticFallback();
    }
    renderReport(data);
  } catch (e) {
    setStatus(`Could not generate report: ${e.message}`);
  } finally {
    $('load').disabled = false;
    $('load').textContent = 'Generate my plan';
  }
}

function staticDeepDive(topicId) {
  const topic = [...state.local, ...state.global].find((t) => t.id === topicId) || state.local[0] || {};
  return {
    topic,
    executive_summary: topic.why_follow || topic.summary,
    evidence: { signals: topic.signals || {}, sources: topic.sources || [], trust: topic.trust || {} },
    study_plan: topic.study_plan || [],
    project_blueprints: simpleProjects(topic),
    risks: topic.risks || [],
  };
}

async function deepDive(topic, preferred = 'overview') {
  if (!topic) return;
  try {
    state.activeDive = state.staticMode ? staticDeepDive(topic) : await fetchJSON(`/api/v1/topics/${topic}/deep-dive?${qs().toString()}`);
  } catch (e) {
    state.activeDive = staticDeepDive(topic);
  }
  $('drawer-title').textContent = state.activeDive.topic?.name || state.activeDive.topic_name || topic;
  $('drawer').classList.remove('hidden');
  setTab(preferred);
}

function setTab(tab) {
  document.querySelectorAll('.tabs button').forEach((b) => b.classList.toggle('active', b.dataset.tab === tab));
  const d = state.activeDive || {};
  const topic = d.topic || {};
  let html = '';
  if (tab === 'overview') html = `<p>${esc(d.executive_summary || topic.why_follow || topic.summary || '')}</p><div class="metrics">${metric('Global', d.global_analysis?.score || topicScore(topic))}${metric('Local', d.local_analysis?.score || topic.signals?.local_relevance)}${metric('Project', topic.signals?.project_potential)}${metric('Career', topic.signals?.career_value)}</div><h3>Risks to watch</h3><ul>${(d.risks || topic.risks || []).map((x) => `<li>${esc(x)}</li>`).join('')}</ul>`;
  if (tab === 'evidence') html = `<p>${esc(d.evidence?.source_summary || 'Evidence combines public technology signals from the Scout dataset.')}</p><pre>${esc(JSON.stringify(d.evidence || {}, null, 2))}</pre>`;
  if (tab === 'study') html = `<ol>${(d.study_plan || topic.study_plan || []).map((x) => `<li>${esc(x)}</li>`).join('')}</ol>`;
  if (tab === 'projects') html = (d.project_blueprints || d.project_ideas || simpleProjects(topic)).map((p) => typeof p === 'string' ? `<div class="project"><h4>${esc(p)}</h4></div>` : `<div class="project"><h4>${esc(p.title)}</h4><p>${esc(p.why_it_promotes_you || '')}</p><p class="muted">Stack: ${esc((p.stack || p.deliverables || []).join(', '))}</p></div>`).join('');
  if (tab === 'raw') html = `<pre>${esc(JSON.stringify(d, null, 2))}</pre>`;
  $('drawer-content').innerHTML = html;
}

function updateUrl() {
  const params = qs();
  const url = `${window.location.pathname}?${params.toString()}`;
  window.history.replaceState({}, '', url);
}

function hydrateFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const city = params.get('city');
  const country = params.get('country');
  if (country) $('location').value = city ? `${city}, ${country}` : country;
  if (params.get('goal')) $('goal').value = params.get('goal');
  if (params.get('profile')) $('profile').value = params.get('profile');
}

function applyPreset(button) {
  $('location').value = button.dataset.location;
  $('profile').value = button.dataset.profile;
  $('goal').value = button.dataset.goal;
  document.querySelectorAll('.preset').forEach((b) => b.classList.toggle('active', b === button));
  load();
}

$('load').addEventListener('click', load);
$('share').addEventListener('click', (event) => { updateUrl(); copyValue(window.location.href, event.currentTarget); });
$('show-local').addEventListener('click', () => { state.showAllLocal = !state.showAllLocal; $('show-local').textContent = state.showAllLocal ? 'Show top 3 only' : 'Show all local topics'; renderCards($('local'), state.local, state.showAllLocal); });
$('show-global').addEventListener('click', () => { state.showAllGlobal = !state.showAllGlobal; $('show-global').textContent = state.showAllGlobal ? 'Show top 3 only' : 'Show all global topics'; renderCards($('global'), state.global, state.showAllGlobal); });
$('simple').addEventListener('click', () => { state.advanced = false; $('simple').classList.add('active'); $('advanced').classList.remove('active'); renderCards($('local'), state.local, state.showAllLocal); renderCards($('global'), state.global, state.showAllGlobal); });
$('advanced').addEventListener('click', () => { state.advanced = true; $('advanced').classList.add('active'); $('simple').classList.remove('active'); renderCards($('local'), state.local, state.showAllLocal); renderCards($('global'), state.global, state.showAllGlobal); });
$('save').addEventListener('click', () => window.print());
$('close-drawer').addEventListener('click', () => $('drawer').classList.add('hidden'));
document.querySelectorAll('.tabs button').forEach((b) => b.addEventListener('click', () => setTab(b.dataset.tab)));
document.querySelectorAll('.preset').forEach((button) => button.addEventListener('click', () => applyPreset(button)));

hydrateFromUrl();
load();
