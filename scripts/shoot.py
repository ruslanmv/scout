#!/usr/bin/env python3
"""
Capture high-quality screenshots of the local Scout dashboard.

Scout is a single-page dashboard served at ``/dashboard`` plus an admin-only
settings page at ``/dashboard/admin.html``. This script drives both with
Playwright Chromium and writes crisp, retina-scale PNGs suitable for the
README, docs, and PRs.

Usage:
    python scripts/shoot.py \
        --base-url http://127.0.0.1:8000 \
        --out docs/assets/screenshots \
        --admin-key scout-demo-admin

Keep Playwright as a transient sandbox dependency:
    python -m pip install playwright
    # (Chromium is pre-installed in AI coding sandboxes; otherwise run
    #  `python -m playwright install chromium`.)
"""

import argparse
import asyncio
import os
from pathlib import Path

from playwright.async_api import (
    async_playwright,
    TimeoutError as PlaywrightTimeoutError,
)


async def settle(page, ms: int = 900):
    """Give animations, transitions and loading states time to settle."""
    await page.wait_for_timeout(ms)


async def screenshot(page, out_dir: Path, name: str, full_page: bool = False):
    """Capture a screenshot of the page (or the full scrollable page)."""
    await settle(page)
    path = out_dir / f"{name}.png"
    await page.screenshot(path=str(path), full_page=full_page)
    print(f"shot: {path}")


async def screenshot_element(page, selector: str, out_dir: Path, name: str):
    """Capture a single element, scrolled into view."""
    try:
        el = page.locator(selector).first
        await el.scroll_into_view_if_needed(timeout=4000)
        await settle(page, 500)
        path = out_dir / f"{name}.png"
        await el.screenshot(path=str(path))
        print(f"shot: {path}")
    except Exception as exc:  # noqa: BLE001 - defensive, keep the run going
        print(f"skipped {name}: {exc}")


async def wait_for_report(page):
    """Wait until the dashboard finishes generating its report."""
    try:
        # The report section drops its `hidden` class once data renders.
        await page.wait_for_selector("#report:not(.hidden)", timeout=20000)
    except PlaywrightTimeoutError:
        print("warning: report did not un-hide in time; capturing anyway")
    # Give the live AI panel a chance to answer (falls back to the built-in
    # plan if the gateway is unreachable — either way the panel renders).
    await settle(page, 2500)


async def capture_dashboard(page, base_url: str, out_dir: Path):
    """Capture the main report page (auto-generates on load)."""
    await page.goto(f"{base_url}/dashboard/", wait_until="networkidle")
    await wait_for_report(page)

    # Hide the floating "Next move" dock so it doesn't overlap the crops.
    await page.add_style_tag(content="#sticky{display:none!important}")

    # Report header: location + study/build/publish outcome cards.
    await page.locator("#report").scroll_into_view_if_needed(timeout=4000)
    await screenshot(page, out_dir, "hero", full_page=False)

    # The live AI plan panel on its own.
    await screenshot_element(page, "#ai-plan", out_dir, "ai-plan")

    # Topic intelligence: local radar + global pulse cards.
    try:
        await page.locator(".split").first.scroll_into_view_if_needed(timeout=4000)
        # Reveal the "Local radar" / "Global pulse" section headers.
        await page.evaluate("window.scrollBy(0, -150)")
        await screenshot(page, out_dir, "report", full_page=False)
    except Exception as exc:  # noqa: BLE001
        print(f"skipped report: {exc}")


async def capture_admin(page, base_url: str, out_dir: Path, admin_key: str | None):
    """Unlock and capture the admin AI-settings page."""
    await page.goto(f"{base_url}/dashboard/admin.html", wait_until="networkidle")
    await settle(page, 500)

    if admin_key:
        try:
            await page.fill("#admin-key", admin_key, timeout=3000)
            await page.click("#login-btn", timeout=3000)
            # Settings form replaces the login card once the key validates.
            await page.wait_for_selector("#settings:not(.hidden)", timeout=8000)
            await settle(page, 700)
        except PlaywrightTimeoutError:
            print("admin unlock skipped: could not validate key / find form")
    else:
        print("admin: no key provided, capturing locked view")

    await screenshot(page, out_dir, "admin", full_page=True)


async def main():
    parser = argparse.ArgumentParser(
        description="Capture high-quality screenshots of the local Scout app."
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000",
                        help="Base URL of the running Scout app.")
    parser.add_argument("--out", default="docs/assets/screenshots",
                        help="Directory where screenshots will be written.")
    parser.add_argument("--admin-key", default=None,
                        help="Admin key (SCOUT_ADMIN_KEY) to unlock the admin page.")
    parser.add_argument("--width", type=int, default=1440, help="Viewport width.")
    parser.add_argument("--height", type=int, default=900, help="Viewport height.")
    parser.add_argument("--scale", type=int, default=2,
                        help="Device scale factor. Use 2 for crisp retina screenshots.")
    parser.add_argument("--light", action="store_true",
                        help="Use light color scheme instead of dark.")
    parser.add_argument("--executable-path", default=os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE"),
                        help="Path to a Chromium binary. Defaults to Playwright's "
                             "bundled build, or PLAYWRIGHT_CHROMIUM_EXECUTABLE if set. "
                             "Handy in sandboxes that pre-install Chromium.")
    args = parser.parse_args()

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as playwright:
        launch_kwargs = {"headless": True}
        if args.executable_path:
            launch_kwargs["executable_path"] = args.executable_path
        browser = await playwright.chromium.launch(**launch_kwargs)
        context = await browser.new_context(
            viewport={"width": args.width, "height": args.height},
            device_scale_factor=args.scale,
            color_scheme="light" if args.light else "dark",
        )
        page = await context.new_page()

        await capture_dashboard(page, args.base_url, out_dir)
        await capture_admin(page, args.base_url, out_dir, args.admin_key)

        await browser.close()

    print("done")


if __name__ == "__main__":
    asyncio.run(main())
