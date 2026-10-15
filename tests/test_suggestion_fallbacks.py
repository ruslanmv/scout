"""Weekly source-backed profession suggestions and no redundant chips."""
from pathlib import Path
import shutil
import subprocess
import pytest
from scripts.build_scout_site import become_widget

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.skipif(shutil.which("node") is None, reason="Node is unavailable")
def test_only_verified_weekly_professions_appear():
    code = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const ctx={window:{SCOUT:{OCCUPATIONS:[{name:'Fake Engineer'}],TOPICS:[{skills:['Python']}]}}};
vm.runInNewContext(fs.readFileSync('scout-suggestions.js','utf8'),ctx);
const s=ctx.window.ScoutSuggestions;
assert.equal(s.professions(null,'Rome','Italy').recommended,'');
assert.equal(s.professions(null,'Rome','Italy').items.length,0);
assert.equal(s.skills(null,'Rome','Italy').items.length,0);
const now=Date.parse('2026-10-15T12:00:00Z'),recent='2026-10-11T12:00:00Z';
const feed={schema_version:1,generated_at:'2026-10-15T10:00:00Z',
  regions:{Worldwide:{status:'curated',items:[{name:'Developer',source:'curated'}]}},
  role_observations:[
    {name:'Nurse',region:'Italy',sample_size:12,source:'adzuna',collected_at:recent},
    {name:'Data Analyst',region:'Italy',sample_size:29,source:'adzuna',collected_at:recent},
    {name:'Invented',region:'Italy',sample_size:100,source:'curated',collected_at:recent},
    {name:'Stale',region:'Italy',sample_size:200,source:'adzuna',collected_at:'2026-09-01T00:00:00Z'},
    {name:'Paris Engineer',region:'France',sample_size:400,source:'adzuna',collected_at:recent}
  ]};
const ranked=s.professions(feed,'Rome','Italy',now);
assert.equal(ranked.recommended,'Data Analyst');
assert.deepEqual(Array.from(ranked.items,x=>x.name),['Data Analyst']);
assert.equal(ranked.region,'Italy');
assert.equal(s.professions(feed,'Berlin','Germany',now).items.length,0);
assert.deepEqual(Array.from(s.matches(ranked.items,'Data').map(x=>x.name)),['Data Analyst','Nurse']);
assert.equal(s.professions({...feed,generated_at:'2026-09-01T00:00:00Z'},'Rome','Italy',now).items.length,0);
"""
    subprocess.run(["node", "-e", code], cwd=ROOT, check=True, capture_output=True, text=True)

def test_report_keeps_only_inline_autocomplete():
    widget=become_widget("../").strip()
    assert 'role="listbox"' in widget
    assert "ScoutSuggestions.mountAutocomplete(" in widget
    assert 'id="become-popular-options"' not in widget
    assert "Suggested professions · curated" not in widget
    assert "roleInput.value = (q.get('profile') || '').trim()" in widget
    assert "if (!roleInput.value) roleInput.value = suggested.recommended" not in widget
    for path in ("report/index.html","scout/report/index.html","public/scout/report/index.html"):
        page=(ROOT/path).read_text()
        assert widget in page
        assert 'src="../scout-suggestions.js"' in page

def test_landing_has_no_duplicate_recommendation_chips():
    app=(ROOT/"scout-app.jsx").read_text()
    pulse=(ROOT/"scout-pulse.js").read_text()
    suggest=(ROOT/"scout-suggestions.js").read_text()
    assert 'const [profile, setProfile] = uS(() => (query.get("profile") || "").trim());' in app
    assert "ScoutSuggestions.professions(pulse, city, country)" in app
    assert "l-quick-chip" not in pulse
    assert "CURATED" not in suggest
    assert "FALLBACK_ROLES" not in suggest

@pytest.mark.skipif(shutil.which("node") is None, reason="Node is unavailable")
@pytest.mark.parametrize("path",["scout-suggestions.js","scout-app.js","scout-landing.js","trends/pulse.js"])
def test_changed_scripts_parse(path):
    subprocess.run(["node","--check",str(ROOT/path)],check=True,capture_output=True,text=True)
