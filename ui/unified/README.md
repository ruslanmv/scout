# Scout Unified UI — source

This directory holds the **editable source** for the unified Scout frontend that
is served as the site landing at <https://ruslanmv.com/scout/>.

The page shipped to GitHub Pages is a single, fully self-contained bundle:

- **Served file:** [`dashboard/index.html`](../../dashboard/index.html) —
  exported to `public/index.html` (and `public/404.html`) by
  [`scripts/export_for_github_pages.py`](../../scripts/export_for_github_pages.py).
- It inlines React, the design-canvas runtime and all assets as `data:` URIs, so
  it needs **no CDN and no backend** and works offline — the same self-contained
  approach the rest of the site uses (see `scout/vendor/`).

## Files here

| File | Purpose |
| --- | --- |
| `Scout Unified UI.dc.html` | Design-canvas source (`<x-dc>` markup + the `text/x-dc` app script). Edit this to change the UI. |
| `Scout Unified UI - standalone.html` | Un-bundled standalone variant (references `support.js` / `scout-globe.js`). |
| `support.js` | Design-canvas runtime (`dc-runtime`). Renders the `<x-dc>` markup with React. |
| `scout-globe.js` | Landing globe animation. |

## Rebuilding the served bundle

The served `dashboard/index.html` was produced by bundling the standalone export
(inlining every asset) and then adjusting the outer `<head>` for production:

1. A proper `<title>`, `<meta name="description">`, Open Graph tags and a
   `<link rel="canonical">`.
2. A small favicon (green Scout diamond, `data:` URI).
3. A tiny persistent script — its timer survives the bundler's `documentElement`
   replacement — that re-applies the title, description and favicon onto the
   `<head>` the runtime rebuilds on unpack.

When regenerating from source, re-apply those `<head>` adjustments (the block
between `<title>` and the first `__bundler` script in `dashboard/index.html`).

## Previous landing

The earlier one-page dashboard landing is preserved (deprecated) at
[`dashboard/classic.html`](../../dashboard/classic.html) → served at
`/scout/classic.html`.
