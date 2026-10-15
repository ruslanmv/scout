"""Regression contract for a manual, least-privilege Pages lock repair."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_pages_recovery_is_explicit_and_never_cancels_on_push():
    script = (ROOT / ".github/workflows/recover_pages.yml").read_text()
    assert "workflow_dispatch:" in script
    assert "deployment_sha:" in script
    assert "pages: write" in script
    assert "contents: read" in script
    assert "gh api --method POST" in script
    assert "pages/deployments/${DEPLOYMENT_SHA}/cancel" in script
    assert "[0-9a-fA-F]{40}" in script
    assert "\n  push:" not in script
    assert "\n  schedule:" not in script


def test_pages_recovery_documentation_identifies_the_blocking_sha():
    guide = (ROOT / "docs/PAGES_RECOVERY.md").read_text()
    assert "ddda8f681a2b6086008355269d104994122478bc" in guide
    assert "Re-run failed jobs" in guide
    assert "Pages: write" in guide
