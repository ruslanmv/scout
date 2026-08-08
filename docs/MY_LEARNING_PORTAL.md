# My Learning portal

`/scout/learn/` **generates** a path; **`/scout/my-learning/`** is where you
follow and manage the paths Scout generated for you. It is a client-side portal
persisted entirely in the browser's **localStorage** — no account or backend
required — so saved paths, progress, notes and activity survive reloads.

## Pages

| Route | What it is |
| --- | --- |
| `/scout/learn/` | AI learning-path generator (now with **Save to My Learning** / **Start learning**) |
| `/scout/my-learning/` | Dashboard: active, paused and completed paths, overall progress, continue-learning |
| `/scout/my-learning/path.html?id=…` | Path navigator: map, current stage, progress controls, course drawer, replan |

The header of every learning page links **Generate ⇄ My Learning**, and the
landing nav/footer link to both.

## Dashboard

- **Continue learning** — the most relevant next action across your active paths.
- **Active / Saved & paused / Completed** path cards, each showing the target,
  current stage, completed items, overall percentage, last activity, and the next
  recommended action, plus a `•••` menu (Rename, Pause/Resume, Replan, Archive,
  Delete).
- Search across all paths.

## Path navigator (three columns)

1. **Path map** — every stage with a status icon: `✓` done, `●` current, `◐` in
   progress, `○` not started. Scout marks the recommended next stage.
2. **Current stage** — course cards (with a details drawer), the portfolio
   project, and a "Stage ready to complete" action once required items are done.
3. **This stage / Activity** — weekly effort, next milestone, and an activity log.

### Course cards & the detail drawer

Clicking a course **title** opens a Scout detail drawer first (never straight to
the provider): description, skills taught, access & price, evidence confidence,
last-verified date, why Scout selected it, warnings, an alternative, and your
private notes. The primary action **Go to provider ↗** opens the provider in a
new tab and records `started` — **opening a link never marks a course complete.**

## Completion model

Three completion sources are tracked and the source is always shown:

- **Provider verified** / **Scout assessment** — trustworthy evidence (Release 3).
- **Self-reported** — you click **Mark complete**; a compact dialog optionally
  captures a note, final score and certificate/evidence URL. It is recorded as
  `manual` and labelled "Marked manually", never as provider-verified.

## Progress

Deterministic and understandable: **completed required items ÷ total required
items**. Required items are a stage's required courses plus its project (or
checkpoint); optional resources (community, registration) don't gate progress.
A stage completes when all its required items are done, which unlocks the next.

## Replanning

**Replan** asks why (less time, budget changed, completed elsewhere, different
provider, faster, target changed), then regenerates the path via the live API
with completed-stage skills folded in as known. Progress is keyed by stable
`resource_id`, so **completed courses stay completed after replanning**.

## Data model

Persisted under the localStorage key `scout.myLearning.v1` as
`{ paths: { <id>: record } }`. Each record holds the full generated `plan`, the
originating `request` (for replanning), `progress` keyed by `res:<resource_id>` /
`proj:<stage_id>`, `stageDone`, `activity`, and `status`
(`active` / `paused` / `completed` / `archived`). Every `LearningStage` now
carries a stable `stage_id` (assigned server-side) so the portal and replanning
key on it rather than a shifting stage number.

> This is Release 1 (manual portal) from the product spec. Releases 2–3
> (certificate uploads, Scout assessments, and provider-verified sync via
> PostgreSQL-backed user accounts) build on the same models.
