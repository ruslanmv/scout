"""First-impression and report-context regression coverage."""
from pathlib import Path

from scripts.build_scout_site import become_widget

ROOT = Path(__file__).resolve().parents[1]


def test_readme_hook_and_generated_trends_are_preserved():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert '<img src="docs/assets/scout-hero.svg"' in readme
    assert "https://ruslanmv.com/scout/" in readme
    assert "SCOUT:TRENDS:START" in readme
    assert "## 📈 Trending now — top skills & places" in readme
    assert "SCOUT:TRENDS:END" in readme
    assert readme.index("SCOUT:TRENDS:START") < readme.index("SCOUT:TRENDS:END")
    assert (ROOT / "docs/assets/scout-hero.svg").is_file()


def test_quickstart_assets_and_source_mirrors():
    for path in ("index.html", "quickstart.css", "quickstart.js"):
        src = (ROOT / "scout" / "quickstart" / path).read_bytes()
        assert src == (ROOT / "public" / "scout" / "quickstart" / path).read_bytes()
        assert src == (ROOT / "quickstart" / path).read_bytes()
    page = (ROOT / "scout/quickstart/index.html").read_text(encoding="utf-8")
    assert 'href="../trends/"' in page
    assert 'href="../"' in page
    assert 'role="tablist"' in page
    assert 'id="copy-code"' in page
    assert 'id="theme-toggle"' in page
    assert "codespaces.new/ruslanmv/scout" in page
    landing = (ROOT / "scout-landing.jsx").read_text(encoding="utf-8")
    assert 'href="quickstart/"' in landing
    assert (ROOT / "scout/scout-landing.jsx").read_bytes() == (ROOT / "scout-landing.jsx").read_bytes()


def test_report_profession_goal_and_location_are_not_reset_to_ai_engineer():
    widget = become_widget("../")
    assert 'id="become-role"' in widget
    assert "roleInput.value = (q.get('profile') || '').trim()" in widget
    assert "'AI Engineer';" not in widget
    assert 'placeholder="e.g. Marketing Specialist" required' in widget
    assert 'value="create_agents"' in widget
    assert "u.searchParams.set('country', q.get('country'))" in widget
    assert "u.searchParams.set('city', q.get('city'))" in widget
    for path in ("scout/report/index.html", "public/scout/report/index.html"):
        static = (ROOT / path).read_text(encoding="utf-8")
        assert "roleInput.value = (q.get('profile') || '').trim()" in static
        assert "'AI Engineer';" not in static
        assert "Enter your profession to continue." in static
        assert 'value="create_agents"' in static
