# GitHub Pages Deployment

Scout uses the traditional GitHub Pages branch model.

The static multi-page application lives under `scout/` on `master`. GitHub
Pages must publish the **contents** of that directory at the root of the
`gh-pages` branch so the project is served at `/scout/`, not `/scout/scout/`.

> The static Pages build has no backend, so live API/admin functionality only
> works on the hosted application. Static pages continue to use their bundled
> deterministic data and client-side fallbacks. See [AI_AND_ADMIN.md](AI_AND_ADMIN.md).

## Required branch layout

```text
master
└── scout/
    ├── index.html
    ├── assets/
    ├── vendor/
    ├── learn/
    ├── my-learning/
    └── report/

            git subtree
                 ↓

gh-pages
├── .nojekyll
├── index.html
├── assets/
├── vendor/
├── learn/
├── my-learning/
└── report/
```

Do **not** publish `public/scout/` as a nested directory. This repository is
already the `scout` GitHub Pages project, so another `scout/` directory would
produce the incorrect `/scout/scout/` path.

## GitHub Pages settings

Open **Settings → Pages → Build and deployment** and configure:

1. **Source:** Deploy from a branch
2. **Branch:** `gh-pages`
3. **Folder:** `/(root)`
4. Save

No custom Pages deployment workflow is required.

The normal GitHub project-site URL is:

```text
https://ruslanmv.github.io/scout/
```

Because the account site uses `ruslanmv.com`, the project is expected at:

```text
https://ruslanmv.com/scout/
```

Do not add `ruslanmv.com/scout` to a `CNAME` file. A Pages `CNAME` contains a
hostname, not a URL path.

## Publishing

Generate the Scout static site, review and commit the generated changes, then
publish the subtree:

```bash
make site
git add scout
git commit -m "build: refresh Scout static site"
git push origin master
make deploy-pages
```

`make deploy-pages` checks that `scout/` has no uncommitted changes and runs:

```bash
git subtree push --prefix scout origin gh-pages
```

The `scout/.nojekyll` file becomes `/.nojekyll` on the publishing branch so
GitHub Pages serves the static files without Jekyll processing.

## Legacy full export

`scripts/export_for_github_pages.py` and `make export-pages` still create the
legacy `public/` bundle for local/export use. That bundle contains Scout under
`public/scout/` and is **not** the publishing source for the branch-based Pages
site described above.
