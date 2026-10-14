# Daily landing Pulse tags

The homepage renders **five profession chips**, **five skill chips**, and
**five tool chips**. Clicking a profession fills the existing free-text
occupation field; visitors can still enter any occupation.

## Freshness and provenance

The scheduled job runs `scripts/build_pulse.py` after collecting signals.
It publishes `scout/data/pulse/latest.json` for the project site and
`datasets/pulse/latest.json`, plus dated
`datasets/pulse/snapshots/YYYY-MM-DD.json` and a rebuildable
`datasets/pulse/history.csv` for analysis and future forecasts.

- **Measured profession rankings** require five or more observed role signals
  for the *same* region, sorted by job-posting sample size. Country signals
  are used only for that country; worldwide Adzuna samples are **not** treated
  as globally representative observations. Sparse or missing observations
  display explicitly curated profession suggestions instead.
- **Skills** are ranked by weighted associations with Scout's tracked
  technology topics, with city-level topic boosts where available, not direct
  job-posting frequency.
- **Tools** are a controlled subset of those topic-associated skills.
- **Shuffling** only changes presentation of the five measured professions;
  for curated professions it samples five of eight starters. It does not alter
  the saved measurements or claim new daily evidence.
- Date labels show the dataset's generation date. A missing feed is an
  explicitly marked offline fallback, not a pretend live ranking.

Do not infer employment totals or forecasts from these values. Train future
time-series models only on comparable observed series, not curated rows or
topic-proxy values mixed with job-posting counts. The history is rebuilt from
daily snapshots so re-running the job on a date does not duplicate rows.

For local development: `python scripts/build_pulse.py`; then open
`/scout/` (or the root landing page with the generated data path present).
GitHub Pages export copies the feed to both site roots.

## Scout Pulse dashboard and funnel design

The new `/trends/` public dashboard mirrors the dark emerald visual identity
of Scout's landing page. The landing page now presents **only** three suggested
profession chips and three skill exploration links beneath the primary CTA.
Changing profession fills the original field; location and career goals remain
editable. Trend cards navigate back with `?profile=&city=&country=&goal=`
so readers do not lose their intent.

The Pulse page includes a 7-day moving-average index chart, career/skills
selection, location and period filters, historical trend lines, clearly
marked exploratory 14-day scenarios, a top-five ranking, skill associations,
a city comparison grid when coverage allows, and a call to action for a career
roadmap. The JS charts use native SVG without a third-party charting CDN.

Daily pipeline: `scripts/build_pulse.py` rebuilds
`datasets/pulse/series.json` and `scout/data/pulse/series.json` from
dated snapshots. `scripts/export_for_github_pages.py` publishes series to
both site roots. Series observations carry a measurement key, source,
location, date, name and value. Posting counts and topic-associated skill
proxy scores **must never be combined into a single demand measure**.

**Data integrity:** Real lines require two series with >=14 valid observation
dates each. An unvalidated 14-day extrapolation is only visible with >=56
observation dates per line. Missing measured history shows an explicitly
labeled **DEMO PREVIEW**, and modeled historical curves must not be described
as observed market activity. Projections show an experimental, uncalibrated
range, never certified confidence intervals. No claims are made that demo
values represent jobs available or verified growth.

Analytics integration points: `scout_plan_cta_clicked`,
`scout_report_navigation_started and scout_report_viewed`, `scout_chart_view`,
`scout_region_selected`, `scout_profession_selected` and
`scout_skill_selected`. They push to an existing `window.dataLayer`
or dispatch a local `scout:analytics` CustomEvent. This PR intentionally
does not add third-party trackers or send personal data.

Test: `pytest tests/test_landing_pulse.py` and
`node --check scout/trends/pulse.js`. Run the exporter to regenerate
`public/scout/trends/` and the published time-series feed.


## Current observed profession rankings (no random suggestions)

The landing **Top professions** and Scout Pulse **Top 5 professions**
share one `scout-ranking.js` evidence gate over the most recently published
`data/pulse/latest.json`:

- Require **five distinct, source-attributed role observations** for the
  selected city, or its country when no city sample exists.
- The published feed **and each underlying observation** must have been
  collected within the last 48 hours. Republishing stale data does not renew
  it. Rank only by source-reported posting mentions.
- **Worldwide curated suggestions, incomplete and stale samples, missing API
  credentials, and demo scores never appear as top roles.**
  When no verified ranking exists, display an honest no-data state, leave the
  profession editable, and never auto-select Developer, Teacher or Nurse.
- If the visitor has not chosen a profession, automatically prefill the first
  current observed role when available. User edits and explicit `?profile=`
  deep links take priority. Changing location updates the suggestion only
  when the user has not edited it.
- The typeahead list also contains only the current observed top five.
- Skills use **Scout topic-association scores**, not measured employer skill
  requests. No stale or fabricated skill rankings are shown.
- This is a **daily published snapshot**, not live browser API queries.
  Configure `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` repository secrets for
  the scheduled collector to publish observed profession demand.

Run `node tests/current_roles.test.cjs` to validate freshness, region
matching, sources, ordering, incomplete data, and shared UI behavior.
