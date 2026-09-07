const $ = (id) => document.getElementById(id);
const SS_KEY = 'scout_admin_key';

function show(id) { $(id).classList.remove('hidden'); }
function hide(id) { $(id).classList.add('hidden'); }
function adminKey() { return sessionStorage.getItem(SS_KEY) || ''; }

function message(el, text, kind) {
  const node = $(el);
  node.textContent = text;
  node.className = `msg ${kind}`;
  node.style.display = text ? 'block' : 'none';
}

async function api(path, { method = 'GET', body } = {}) {
  const res = await fetch(`/api/v1${path}`, {
    method,
    headers: { 'Content-Type': 'application/json', 'X-Admin-Key': adminKey() },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
  return data;
}

function fillForm(settings, status) {
  $('ai_enabled').checked = !!settings.ai_enabled;
  $('ai_provider').value = settings.ai_provider || '';
  $('ai_model').value = settings.ai_model || '';
  $('ai_base_url').value = settings.ai_base_url || '';
  $('ai_temperature').value = settings.ai_temperature ?? '';
  $('ai_timeout').value = settings.ai_timeout ?? '';
  $('ai_api_key').value = '';
  $('key-hint').textContent = settings.ai_api_key_set
    ? `A key is set (${settings.ai_api_key_hint}). Leave blank to keep it, or type a new one.`
    : 'No key set — the public gateway works without one. Paste a key to use a premium provider.';
  const badge = $('ai-badge');
  const on = !!settings.ai_enabled;
  badge.textContent = on ? `AI on · ${status.provider} · ${status.model}` : 'AI off · built-in plans';
  badge.className = on ? 'badge' : 'badge off';
}

function formValues() {
  const num = (id) => ($(id).value === '' ? undefined : Number($(id).value));
  const body = {
    ai_enabled: $('ai_enabled').checked,
    ai_provider: $('ai_provider').value.trim() || undefined,
    ai_model: $('ai_model').value.trim() || undefined,
    ai_base_url: $('ai_base_url').value.trim() || undefined,
    ai_temperature: num('ai_temperature'),
    ai_timeout: num('ai_timeout'),
  };
  const key = $('ai_api_key').value;
  if (key) body.ai_api_key = key; // only send when the admin typed one
  return body;
}

async function loadSettings() {
  const data = await api('/admin/settings');
  fillForm(data.settings, data.status);
  hide('login');
  show('settings');
}

async function unlock() {
  const key = $('admin-key').value.trim();
  if (!key) return message('login-msg', 'Enter your admin key.', 'err');
  sessionStorage.setItem(SS_KEY, key);
  $('login-btn').disabled = true;
  try {
    await loadSettings();
    message('login-msg', '', 'err');
  } catch (e) {
    sessionStorage.removeItem(SS_KEY);
    message('login-msg', e.message, 'err');
  } finally {
    $('login-btn').disabled = false;
  }
}

async function setup() {
  const password = $('setup-password').value;
  if (password.length < 12) return message('setup-msg', 'Use at least 12 characters.', 'err');
  if (password !== $('setup-confirm').value) return message('setup-msg', 'Passwords do not match.', 'err');
  $('setup-btn').disabled = true;
  try {
    const res = await fetch('/api/v1/admin/setup', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ password }) });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
    sessionStorage.setItem(SS_KEY, password);
    hide('setup');
    await loadSettings();
  } catch (e) { message('setup-msg', e.message, 'err'); }
  finally { $('setup-btn').disabled = false; }
}

async function changePassword() {
  const password = $('new-password').value;
  if (password.length < 12) return message('password-msg', 'Use at least 12 characters.', 'err');
  if (password !== $('confirm-password').value) return message('password-msg', 'Passwords do not match.', 'err');
  $('password-btn').disabled = true;
  try {
    await api('/admin/password', { method: 'POST', body: { password } });
    sessionStorage.setItem(SS_KEY, password);
    $('new-password').value = '';
    $('confirm-password').value = '';
    message('password-msg', '✓ Password changed. Your current session has been updated.', 'ok');
  } catch (e) { message('password-msg', e.message, 'err'); }
  finally { $('password-btn').disabled = false; }
}

async function save() {
  $('save-btn').disabled = true;
  try {
    const data = await api('/admin/settings', { method: 'POST', body: formValues() });
    const status = await api('/admin/settings');
    fillForm(data.settings, status.status);
    message('settings-msg', '✓ Settings saved. New plans will use these values immediately.', 'ok');
  } catch (e) {
    message('settings-msg', `Could not save: ${e.message}`, 'err');
  } finally {
    $('save-btn').disabled = false;
  }
}

async function test() {
  $('test-btn').disabled = true;
  message('settings-msg', 'Testing connection…', 'ok');
  try {
    const r = await api('/admin/test', { method: 'POST', body: formValues() });
    if (r.ok) {
      message('settings-msg', `✓ Connected to ${r.provider} (${r.model}) in ${r.latency_ms} ms.\nModel replied: "${r.sample}"`, 'ok');
    } else {
      message('settings-msg', `✗ Connection failed: ${r.error}`, 'err');
    }
  } catch (e) {
    message('settings-msg', `✗ ${e.message}`, 'err');
  } finally {
    $('test-btn').disabled = false;
  }
}

async function reset() {
  if (!confirm('Reset all AI settings to the environment-variable defaults?')) return;
  try {
    const data = await api('/admin/reset', { method: 'POST' });
    const status = await api('/admin/settings');
    fillForm(data.settings, status.status);
    message('settings-msg', '✓ Reset to environment defaults.', 'ok');
  } catch (e) {
    message('settings-msg', e.message, 'err');
  }
}

function logout() {
  sessionStorage.removeItem(SS_KEY);
  hide('settings');
  show('login');
  $('admin-key').value = '';
}

async function init() {
  let enabled = false;
  try {
    enabled = (await (await fetch('/api/v1/admin/enabled')).json()).enabled;
  } catch (_) { /* server down */ }
  if (!enabled) return show('setup');
  if (adminKey()) {
    try { return await loadSettings(); } catch (_) { sessionStorage.removeItem(SS_KEY); }
  }
  show('login');
}

$('login-btn').addEventListener('click', unlock);
$('setup-btn').addEventListener('click', setup);
$('password-btn').addEventListener('click', changePassword);
$('admin-key').addEventListener('keydown', (e) => { if (e.key === 'Enter') unlock(); });
$('save-btn').addEventListener('click', save);
$('test-btn').addEventListener('click', test);
$('reset-btn').addEventListener('click', reset);
$('logout-btn').addEventListener('click', logout);
init();
