# GitHub Pages branch deployment

Scout uses the traditional GitHub Pages branch model.

## Repository layout

The application source and generated static site live under `scout/` on `master`.
The **contents** of that directory are published at the root of the `gh-pages`
branch:

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
├── index.html
├── assets/
├── vendor/
├── learn/
├── my-learning/
└── report/
```

Do not publish `public/scout/` as a nested directory on `gh-pages`. This
repository is already the `scout` GitHub Pages project, so nesting another
`scout/` directory produces the incorrect `/scout/scout/` URL.

## GitHub Pages settings

In **Settings → Pages → Build and deployment** configure:

- **Source:** Deploy from a branch
- **Branch:** `gh-pages`
- **Folder:** `/(root)`

The expected project URL is:

```text
https://ruslanmv.github.io/scout/
```

The account site uses `ruslanmv.com`, so the project is expected at:

```text
https://ruslanmv.com/scout/
```

Do not add a project-level `CNAME` containing a path. A Pages `CNAME` is a
hostname, not a URL path.

## Publishing

Generate the Scout site, commit any generated changes, and publish the subtree:

```bash
make site
git add scout
git commit -m "build: refresh Scout static site"
git push origin master
make deploy-pages
```

`make deploy-pages` refuses to run when `scout/` has uncommitted changes and then
uses:

```bash
git subtree push --prefix scout origin gh-pages
```

The `scout/.nojekyll` marker becomes `/.nojekyll` on the publishing branch so
GitHub Pages serves the static files without Jekyll processing.
