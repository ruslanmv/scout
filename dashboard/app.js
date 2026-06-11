const $ = (id) => document.getElementById(id);
let state = { report: null, local: [], global: [], activeTopic: null, activeDive: null, showAllLocal: false, showAllGlobal: false, advanced: false };

async function fetchJSON(url, options) {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function parseLocation(value) {
  const parts = (value || 'Worldwide').split(',').map(x => x.trim()).filter(Boolean);
  if (parts.length === 1) return { city: null, country: parts[0] };
  return { city: parts[0], country: parts.slice(1).join(', ') };
}

function qs() {
  const loc = parseLocation($('location').value);
  return new URLSearchParams({ country: loc.country || 'Worldwide', city: loc.city || '', goal: $('goal').value, profile: $('profile').value, limit: '10' });
}

function trustLabel(topic) {
  return topic?.trust?.label || topic?.confidence?.label || 'Medium confidence';
}

function score(topic) { return Number(topic?.score || 0).toFixed(1); }

function metric(label, value) {
  const n = Number(value || 0);
  return `<div class="bar"><span>${label}</span><div><i style="width:${Math.max(4, Math.min(100, n))}%"></i></div><b>${n.toFixed(0)}</b></div>`;
}

function card(topic, index) {
  const signals = topic.signals || {};
  const detail = state.advanced ? `
    <div class="metrics">
      ${metric('Local', signals.local_relevance)}
      ${metric('Career', signals.career_value)}
      ${metric('Project', signals.project_potential)}
    </div>` : '';
  const project = (topic.project_ideas || [])[0] || 'Build a practical demo';
  return `<div class="topic-card">
    <div class="topic-top"><span class="rank">#${index + 1}</span><span class="score">${score(topic)}</span></div>
    <h4>${topic.name}</h4>
    <p>${topic.summary || topic.why_follow || ''}</p>
    <p class="muted"><strong>Build:</strong> ${project}</p>
    <div class="topic-footer"><span class="pill">${topic.priority || 'trend'}</span><span class="trust">${trustLabel(topic)}</span></div>
    ${detail}
    <button class="link-btn" onclick="deepDive('${topic.id}')">See evidence</button>
  </div>`;
}

function renderCards(el, topics, showAll) {
  const visible = showAll ? topics : topics.slice(0, 3);
  el.innerHTML = visible.map(card).join('');
}

function renderInsights(report) {
  const top = report.summary || {};
  $('insights').innerHTML = [
    ['Topic to study', top.top_topic || '—'],
    ['Project to build', top.top_project || '—'],
    ['Best next move', top.next_move?.action || '—'],
    ['Trust', top.confidence?.label || 'High confidence']
  ].map(([k,v]) => `<div class="insight"><span>${k}</span><strong>${v}</strong></div>`).join('');
}

function renderVisibility(plan) {
  const rows = [
    ['GitHub repo', plan.github_repo],
    ['Hugging Face Space', plan.huggingface_space],
    ['Blog title', plan.blog_title],
    ['Skills', (plan.skills_to_show || []).join(', ')]
  ];
  $('visibility').innerHTML = rows.map(([label, value]) => `<div class="copy-row"><span>${label}</span><code>${value || '—'}</code><button onclick="copyText('${String(value || '').replace(/'/g, "\\'")}')">Copy</button></div>`).join('') +
    `<ol>${(plan.publish_steps || []).map(s => `<li>${s}</li>`).join('')}</ol>`;
}

function renderProjects(projects) {
  $('projects').innerHTML = (projects || []).slice(0, 5).map(p => `<div class="project"><h4>${p.title}</h4><p>${p.why_it_promotes_you || ''}</p><p class="muted">${p.estimated_time || '1-4 weeks'} · ${(p.deliverables || []).join(' · ')}</p></div>`).join('');
}

function renderReport(data) {
  state.report = data.report;
  state.local = data.local_topics || data.report?.recommendations || [];
  state.global = data.global_topics || [];
  const report = state.report;
  const top = report.recommendations?.[0] || {};
  $('report').classList.remove('hidden');
  $('sticky').classList.remove('hidden');
  $('preview-topic').textContent = top.name || 'Scout Report';
  $('preview-copy').textContent = report.summary?.headline || 'Your report is ready.';
  $('report-title').textContent = `${report.location.city ? report.location.city + ', ' : ''}${report.location.country} · ${labelForGoal(report.goal)} · ${labelForProfile(report.profile)}`;
  $('top-topic').textContent = top.name || '—';
  $('top-summary').textContent = top.why_follow || top.summary || '—';
  $('study-now').textContent = (report.summary?.next_move?.study || [top.name || '—']).slice(0,2).join(' → ');
  $('build-now').textContent = report.summary?.next_move?.build || report.summary?.top_project || '—';
  $('confidence-now').textContent = report.summary?.confidence?.label || trustLabel(top);
  $('sticky-move').textContent = report.summary?.next_move?.build || 'View project plan';
  $('top-evidence').onclick = () => deepDive(top.id);
  $('top-project').onclick = () => deepDive(top.id, 'projects');
  $('sticky-btn').onclick = () => deepDive(top.id, 'projects');
  renderInsights(report);
  renderCards($('local'), state.local, state.showAllLocal);
  renderCards($('global'), state.global, state.showAllGlobal);
  renderProjects(report.projects || []);
  renderVisibility(report.visibility_plan || {});
  window.scrollTo({ top: $('report').offsetTop - 20, behavior: 'smooth' });
}

function labelForGoal(x) {
  return ({career:'Career', build_portfolio:'Build portfolio', create_agents:'Create agents', startup:'Startup', research:'Research'})[x] || x;
}
function labelForProfile(x) {
  return ({developer:'Developer', ai_engineer:'AI engineer', student:'Student', founder:'Founder', enterprise:'Enterprise', agent:'Agent'})[x] || x;
}

async function load() {
  $('load').disabled = true;
  $('load').textContent = 'Generating…';
  try {
    const data = await fetchJSON(`/api/v1/ui/bootstrap?${qs().toString()}`);
    renderReport(data);
  } catch (e) {
    alert('Could not generate report: ' + e.message);
  } finally {
    $('load').disabled = false;
    $('load').textContent = 'Generate Scout Report';
  }
}

async function deepDive(topic, preferred='overview') {
  if (!topic) return;
  const data = await fetchJSON(`/api/v1/topics/${topic}/deep-dive?${qs().toString()}`);
  state.activeDive = data;
  $('drawer-title').textContent = data.topic?.name || data.topic_name || topic;
  $('drawer').classList.remove('hidden');
  setTab(preferred);
}

function setTab(tab) {
  document.querySelectorAll('.tabs button').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  const d = state.activeDive || {};
  const topic = d.topic || {};
  let html = '';
  if (tab === 'overview') html = `<p>${d.executive_summary || topic.why_follow || ''}</p><div class="metrics">${metric('Global', d.global_analysis?.score || topic.trend_score)}${metric('Local', d.local_analysis?.score || topic.signals?.local_relevance)}${metric('Project', topic.signals?.project_potential)}${metric('Career', topic.signals?.career_value)}</div><h3>Risks</h3><ul>${(d.risks || []).map(x=>`<li>${x}</li>`).join('')}</ul>`;
  if (tab === 'evidence') html = `<p>${d.evidence?.source_summary || 'Evidence combines public technology signals.'}</p><pre>${JSON.stringify(d.evidence || {}, null, 2)}</pre>`;
  if (tab === 'study') html = `<ol>${(d.study_plan || topic.study_plan || []).map(x=>`<li>${x}</li>`).join('')}</ol>`;
  if (tab === 'projects') html = (d.project_blueprints || d.project_ideas || []).map(p => typeof p === 'string' ? `<div class="project"><h4>${p}</h4></div>` : `<div class="project"><h4>${p.title}</h4><p>${p.why_it_promotes_you || ''}</p><p class="muted">Stack: ${(p.stack || []).join(', ')}</p></div>`).join('');
  if (tab === 'raw') html = `<pre>${JSON.stringify(d, null, 2)}</pre>`;
  $('drawer-content').innerHTML = html;
}

function copyText(text) { navigator.clipboard?.writeText(text); }

$('load').addEventListener('click', load);
$('show-local').addEventListener('click', () => { state.showAllLocal = !state.showAllLocal; $('show-local').textContent = state.showAllLocal ? 'Show top 3 only' : 'Show all local topics'; renderCards($('local'), state.local, state.showAllLocal); });
$('show-global').addEventListener('click', () => { state.showAllGlobal = !state.showAllGlobal; $('show-global').textContent = state.showAllGlobal ? 'Show top 3 only' : 'Show all global topics'; renderCards($('global'), state.global, state.showAllGlobal); });
$('simple').addEventListener('click', () => { state.advanced = false; $('simple').classList.add('active'); $('advanced').classList.remove('active'); renderCards($('local'), state.local, state.showAllLocal); renderCards($('global'), state.global, state.showAllGlobal); });
$('advanced').addEventListener('click', () => { state.advanced = true; $('advanced').classList.add('active'); $('simple').classList.remove('active'); renderCards($('local'), state.local, state.showAllLocal); renderCards($('global'), state.global, state.showAllGlobal); });
$('save').addEventListener('click', () => window.print());
$('close-drawer').addEventListener('click', () => $('drawer').classList.add('hidden'));
document.querySelectorAll('.tabs button').forEach(b => b.addEventListener('click', () => setTab(b.dataset.tab)));
$('geo').addEventListener('click', () => {
  navigator.geolocation?.getCurrentPosition(() => alert('Location detected. Connect reverse geocoding in production to fill city/country automatically.'), () => alert('Could not access browser location.'));
});

load();
