"""Regression tests for profession recommendations and report combobox."""
from pathlib import Path
import shutil
import subprocess

import pytest

from scripts.build_scout_site import become_widget

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which("node") is None, reason="Node is unavailable")
def test_recommendation_engine_prefers_verified_roles_and_never_invents_rankings():
    js = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const ctx={window:{SCOUT:{
  OCCUPATIONS:[{name:'Data Analyst',domain:'Tech & Data'},{name:'Data Engineer',domain:'Tech & Data'}],
  TOPICS:[{skills:['Python','SQL']},{skills:['Python','Docker']}]
}}};
vm.runInNewContext(fs.readFileSync('scout-ranking.js','utf8'),ctx);
vm.runInNewContext(fs.readFileSync('scout-suggestions.js','utf8'),ctx);
const s=ctx.window.ScoutSuggestions;
const curated=s.professions(null,'Rome','Italy');
assert.equal(curated.observed,false);
assert.equal(curated.recommended,'Developer');
assert.equal(curated.items[0].name,'Developer');
assert.deepEqual(Array.from(s.matches(curated.items,'Data').map(i=>i.name)),['Data Analyst','Data Engineer']);
assert.equal(s.skills(null,'Rome','Italy').source,'curated');
assert.equal(s.skills(null,'Rome','Italy').items[0].name,'Python');
const today=new Date().toISOString();
const measured=Array.from({length:5},(_,i)=>({
  name:i===0?'Registered Nurse':'Profession '+i,
  source:'adzuna',sample_size:100-i,collected_at:today
}));
const live={schema_version:1,generated_at:today,regions:{
  Rome:{status:'measured',items:measured},
  Worldwide:{items:[{name:'Developer',source:'curated'}]}
},skills:[{name:'Python',source:'topic_proxy',score:20}]};
const ranked=s.professions(live,'Rome','Italy');
assert.equal(ranked.observed,true);
assert.equal(ranked.recommended,'Registered Nurse');
assert.equal(ranked.region,'Rome');
assert.equal(s.skills(live,'Rome','Italy').source,'topic_proxy');
const stale={...live,generated_at:'2025-01-01T00:00:00Z'};
assert.equal(s.professions(stale,'Rome','Italy').observed,false);
assert.equal(s.professions(stale,'Rome','Italy').recommended,'Developer');
"""
    subprocess.run(["node", "-e", js], cwd=ROOT, check=True, capture_output=True, text=True)


def test_report_autocomplete_is_generated_into_all_three_static_pages():
    widget = become_widget("../").strip()
    assert 'role="listbox"' in widget
    assert 'id="become-popular-options"' in widget
    assert "window.ScoutSuggestions.mountAutocomplete(" in widget
    assert "roleInput.value = (q.get('profile') || '').trim()" in widget
    assert "if (!roleInput.value) roleInput.value = suggested.recommended" in widget
    assert "manuallyChanged" in widget
    for path in ("report/index.html", "scout/report/index.html", "public/scout/report/index.html"):
        page = (ROOT / path).read_text()
        assert widget in page
        assert 'src="../scout-suggestions.js"' in page
        assert 'src="../scout-ranking.js"' in page


def test_homepage_has_fallback_default_and_source_labels():
    app = (ROOT / "scout-app.jsx").read_text()
    pulse = (ROOT / "scout-pulse.js").read_text()
    assert "window.ScoutSuggestions.professions(null" in app
    assert "userSelectedRole.current" in app
    assert "window.ScoutSuggestions.professions(pulse, city, country).recommended" in app
    assert "Suggested professions · curated" in pulse
    assert "Skills to explore · curated" in pulse
    assert "not a regional popularity or demand ranking" in pulse


@pytest.mark.skipif(shutil.which("node") is None, reason="Node is unavailable")
@pytest.mark.parametrize("path", ["scout-suggestions.js","scout-app.js","scout-landing.js"])
def test_modified_scripts_parse(path):
    subprocess.run(["node","--check",str(ROOT/path)],check=True,capture_output=True,text=True)
