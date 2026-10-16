"""Weekly source-backed profession suggestions and no redundant chips."""
from pathlib import Path
import shutil
import subprocess
import pytest
from scripts.build_scout_site import become_widget

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.skipif(shutil.which("node") is None, reason="Node is unavailable")
def test_profession_catalog_is_always_available_without_faking_market_rank():
    code = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const ctx={window:{SCOUT:{OCCUPATIONS:[
  {name:'Data Analyst',domain:'Tech & Data'},
  {name:'Data Scientist',domain:'Tech & Data'},
  {name:'Data Engineer',domain:'Tech & Data'},
  {name:'Business Intelligence Analyst',domain:'Tech & Data'},
  {name:'Nurse',domain:'Health'},
  {name:'Data Analyst',domain:'Duplicate'}
]}}};
vm.runInNewContext(fs.readFileSync('scout-suggestions.js','utf8'),ctx);
const s=ctx.window.ScoutSuggestions;
const offline=s.professions(null,'Rome','Italy');
assert.equal(offline.observed,false);
assert.equal(offline.recommended,'');
assert.equal(offline.items.length,5);
assert.ok(offline.items.every(x=>x.catalog && !x.observed));
assert.deepEqual(Array.from(s.matches(offline.items,'Data'),x=>x.name),
  ['Data Analyst','Data Scientist','Data Engineer']);
assert.deepEqual(Array.from(s.matches(offline.items,'analyst'),x=>x.name),
  ['Data Analyst','Business Intelligence Analyst']);
assert.equal(s.matches(offline.items,'unknown profession').length,0);
assert.equal(s.skills(null,'Rome','Italy').items.length,0);
const now=Date.parse('2026-10-15T12:00:00Z'),recent='2026-10-11T12:00:00Z';
const feed={schema_version:1,generated_at:'2026-10-15T10:00:00Z',
  regions:{Worldwide:{status:'curated',items:[{name:'Developer',source:'curated'}]}},
  role_observations:[
    {name:'Nurse',region:'Italy',sample_size:12,source:'adzuna',collected_at:recent},
    {name:'Data Engineer',region:'Italy',sample_size:29,source:'adzuna',collected_at:recent},
    {name:'Invented',region:'Italy',sample_size:100,source:'curated',collected_at:recent},
    {name:'Stale',region:'Italy',sample_size:200,source:'adzuna',collected_at:'2026-09-01T00:00:00Z'},
    {name:'Other City',region:'France',sample_size:400,source:'adzuna',collected_at:recent}
  ]};
const ranked=s.professions(feed,'Rome','Italy',now);
assert.equal(ranked.observed,true);
assert.equal(ranked.recommended,'Data Engineer');
assert.equal(ranked.region,'Italy');
assert.equal(ranked.items.filter(x=>x.name==='Data Engineer').length,1);
assert.equal(ranked.items[0].observed,true);
assert.equal(ranked.items[1].name,'Nurse');
assert.deepEqual(Array.from(s.matches(ranked.items,'Data'),x=>x.name),
  ['Data Engineer','Data Analyst','Data Scientist']);
assert.ok(!ranked.items.some(x=>x.name==='Invented'||x.name==='Stale'||x.name==='Other City'));
assert.equal(s.professions(feed,'Berlin','Germany',now).observed,false);
assert.equal(s.professions(feed,'Berlin','Germany',now).items.length,5);
const stale=s.professions({...feed,generated_at:'2026-09-01T00:00:00Z'},'Rome','Italy',now);
assert.equal(stale.observed,false);
assert.equal(stale.recommended,'');
assert.equal(stale.items.length,5);
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

def test_landing_uses_catalog_dropdown_without_duplicate_recommendation_chips():
    app=(ROOT/"scout-app.jsx").read_text()
    pulse=(ROOT/"scout-pulse.js").read_text()
    suggest=(ROOT/"scout-suggestions.js").read_text()
    assert 'const [profile, setProfile] = uS(() => (query.get("profile") || "").trim());' in app
    assert "ScoutSuggestions.professions(pulse, city, country)" in app
    assert "l-quick-chip" not in pulse
    assert "catalogProfessions()" in suggest
    assert "FALLBACK_ROLES" not in suggest
    assert "Observed job-posting mentions" in (ROOT / "scout-landing.jsx").read_text()
    assert "Occupation catalog" in (ROOT / "scout-landing.jsx").read_text()

@pytest.mark.skipif(shutil.which("node") is None, reason="Node is unavailable")
@pytest.mark.parametrize("path",["scout-suggestions.js","scout-app.js","scout-landing.js","trends/pulse.js"])
def test_changed_scripts_parse(path):
    subprocess.run(["node","--check",str(ROOT/path)],check=True,capture_output=True,text=True)
