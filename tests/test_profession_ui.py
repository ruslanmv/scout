"""Contracts for Scout's profession autocomplete and trend-series management."""
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("relative", [
    "scout-landing.jsx", "scout-landing.js", "scout-landing.css",
    "scout-data.js", "trends/index.html", "trends/pulse.js", "trends/pulse.css",
])
def test_profession_ui_is_mirrored_for_static_hosts(relative):
    base = (ROOT / relative).read_bytes()
    assert base == (ROOT / "scout" / relative).read_bytes()
    assert base == (ROOT / "public/scout" / relative).read_bytes()


def test_profession_search_is_keyboard_accessible_and_not_limited_to_verified_roles():
    source = (ROOT / "scout-landing.jsx").read_text()
    assert 'role: "combobox"' in source
    assert '"aria-autocomplete": "list"' in source
    assert 'role: "listbox"' in source
    assert 'event.key === "ArrowDown"' in source
    assert 'event.key === "Escape"' in source
    assert ".slice(0, 5)" in source
    assert "[...occupations, ...L_OCCS]" in source
    assert 'o.observed ? "Observed regional signal"' in source
    assert '"scout-occs"' not in source


def test_trend_chart_supports_compare_visibility_and_distinguishes_demo_data():
    page = (ROOT / "trends/index.html").read_text()
    script = (ROOT / "trends/pulse.js").read_text()
    for identifier in ("compare-form", "compare-input", "compare-options",
                       "series-show-all", "series-hide-all", "series-reset",
                       "chart-legend"):
        assert f'id="{identifier}"' in page
    assert 'state.hidden[state.kind]' in script
    assert 'state.selected[state.kind]' in script
    assert 'setAttribute("aria-pressed"' in script
    assert '"DEMO PREVIEW"' in script
    assert '"job_postings"' in script
    assert "chartCatalog()" in script
    assert '"../scout-data.js"' in page


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is not available")
@pytest.mark.parametrize("file", ["scout-landing.js", "trends/pulse.js"])
def test_ui_scripts_have_valid_javascript_syntax(file):
    subprocess.run(["node", "--check", str(ROOT / file)], check=True, capture_output=True, text=True)
