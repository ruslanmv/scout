# Fix a stuck GitHub Pages deployment

## Symptoms

The generated `pages build and deployment` workflow builds successfully, but
`actions/deploy-pages` fails with `Deployment request failed ... due to in progress deployment`.
This is a GitHub Pages deployment lock, not a Scout frontend or build error.

## Immediate recovery

1. Find the **blocking commit SHA** after `Please cancel ... first` in the failed
   `deploy` job log. Use that SHA, **not** the newer failed run's commit.
2. Cancel the blocked Pages deployment:

   ```bash
   gh auth login # only needed if gh is not already authenticated
   gh api --method POST \
     repos/ruslanmv/scout/pages/deployments/<BLOCKING_COMMIT_SHA>/cancel
   ```

   The authenticated account/token requires **Pages: write** permission.
   Alternatively, after merging this fix, use **Actions → Recover stuck GitHub
   Pages deployment → Run workflow**, and paste the blocking SHA into the input.
   The recovery workflow is deliberately manual: it must never cancel a
   healthy deployment on every push.

3. Wait briefly for the cancellation to register. Then open the latest
   `pages build and deployment` run and select **Re-run failed jobs**.
   If the status remains locked after a successful cancellation, retry once
   after a short wait; if it persists, contact GitHub Support with both run IDs
   and the blocking deployment SHA.

## Example from 2026-10-15

- Previous timed-out Pages run: `#156` (Actions run `38769994661`).
- New run blocked by the old deployment: `#157` (Actions run `38772981495`).
- Blocking Pages deployment SHA: `ddda8f681a2b6086008355269d104994122478bc`.

Do **not** use ordinary workflow-run cancellation as a substitute for the Pages
deployment cancellation endpoint: the previous run may already show `completed`
while its deployment lock remains active.

## Longer-term reliability

Scout currently uses GitHub's **managed** `pages build and deployment` workflow.
That dynamic workflow is not defined in `.github/workflows` and can't be
serialized by adding `concurrency:` to an unrelated test or dataset workflow.
Consider switching **Settings → Pages → Build and deployment → Source** to
**GitHub Actions** with a dedicated upload/deploy workflow and a single shared
`concurrency` group. Do not run two Pages publishers at the same time.

References:
- [Cancel a GitHub Pages deployment](https://docs.github.com/en/rest/pages/pages#cancel-a-github-pages-deployment)
- [Actions concurrency](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/control-deployments)
