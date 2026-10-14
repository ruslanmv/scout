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
  technology topics, not direct job-posting frequency.
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
