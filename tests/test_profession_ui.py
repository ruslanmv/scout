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


def test_profession_search_is_keyboard_accessible_and_has_catalog_fallback():
    source = (ROOT / "scout-landing.jsx").read_text()
    assert 'role: "combobox"' in source
    assert '"aria-autocomplete": "list"' in source
    assert 'role: "listbox"' in source
    assert 'event.key === "ArrowDown"' in source
    assert 'event.key === "Escape"' in source
    assert "window.ScoutSuggestions.matches(occupations, value, 5)" in source
    assert "const expanded = open && (occupations.length > 0" in source
    assert "Observed job-posting mentions" in source
    assert "Occupation catalog" in source
    assert "No matching profession in the catalog" in source
    assert '"scout-occs"' not in source


def test_trend_chart_supports_comparison_without_synthetic_history():
    page = (ROOT / "trends/index.html").read_text()
    script = (ROOT / "trends/pulse.js").read_text()
    for identifier in ("compare-form", "compare-input", "compare-options",
                       "series-show-all", "series-hide-all", "series-reset",
                       "chart-legend"):
        assert f'id="{identifier}"' in page
    assert 'state.hidden[state.kind]' in script
    assert 'state.selected[state.kind]' in script
    assert 'setAttribute("aria-pressed"' in script
    assert '"NO VERIFIED TREND"' in script
    assert "demoValues" not in script
    assert "scenario(" not in script
    assert '"job_postings"' in script
    assert "chartCatalog()" in script
    assert '"../scout-data.js"' in page


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is not available")
@pytest.mark.parametrize("file", ["scout-landing.js", "trends/pulse.js"])
def test_ui_scripts_have_valid_javascript_syntax(file):
    subprocess.run(["node", "--check", str(ROOT / file)], check=True, capture_output=True, text=True)


def test_profession_dropdown_reserves_layout_space_without_obscuring_cta():
    """The suggestions panel must push the CTA/chips down, not overlay them."""
    stylesheet = (ROOT / "scout-landing.css").read_text()
    assert ".l-form{display:grid;align-items:start;" in stylesheet
    assert ".l-occ-options{position:relative;" in stylesheet
    assert "max-height:min(240px,36vh)" in stylesheet
    assert "overscroll-behavior:contain" in stylesheet
    assert ".l-occ-options{position:absolute;" not in stylesheet
    assert "bottom:calc(100% + 6px)" not in stylesheet
    assert "@media(max-width:640px){.l-occ-options{max-height:min(216px,38vh)}}" in stylesheet


def test_landing_carousel_never_invents_market_growth_percentages():
    jsx=(ROOT/"scout-landing.jsx").read_text()
    compiled=(ROOT/"scout-landing.js").read_text()
    for source in (jsx,compiled):
        assert "+142%" not in source
        assert "+113%" not in source
        assert "+87%" not in source
        assert "No verified regional job-posting observations this week" in source
        assert "sample_size.toLocaleString" in source
    assert "L_SLIDES[idx].render({observed,pulseStatus})" in jsx
