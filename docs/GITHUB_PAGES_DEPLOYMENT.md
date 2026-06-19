# GitHub Pages Deployment

Scout exports a static dashboard that can be served from the repository root or from `/scout/`.

> The static Pages build has no backend, so live AI plans (`/api/v1/ai/plan`) and the admin Settings page work only on the hosted app; Pages uses the deterministic dataset. See [AI_AND_ADMIN.md](AI_AND_ADMIN.md).

## Local export

```bash
python scripts/export_for_github_pages.py
```

The export writes:

- `public/index.html`
- `public/Scout Report.html`
- `public/data/latest.json`
- `public/scout/index.html`
- `public/scout/Scout Report.html`
- `public/scout/data/latest.json`

## GitHub Actions deployment

The `deploy_pages.yml` workflow publishes the generated `public/` directory to the `gh-pages` branch. This avoids the GitHub Pages API failure that happens when `actions/configure-pages` or `actions/deploy-pages` runs before Pages is enabled for the repository.

After the first successful workflow run, enable Pages once in GitHub:

1. Open **Settings → Pages**.
2. Set **Source** to **Deploy from a branch**.
3. Select branch **gh-pages** and folder **/**.
4. Save.

Future pushes to `main` or `master` will rebuild the static bundle and force-publish `gh-pages` automatically.
