# Scout Daily Workflow

Scout is designed so the frontend never needs to run heavy analysis in the browser.
A scheduled job generates the basic elements required by the dashboard every day.

## Pipeline

```text
1. Collect public signals
   GitHub, committers-style location presets, Hugging Face, news, jobs, community.

2. Normalize signals
   Convert source-specific data into topic-level 0-100 signal fields.

3. Score topics
   Compute trend_score, actionability_score, matrix_value_score, semantic/ml_fit_score.

4. Generate analyses in batches
   For each location × goal × profile, create a Scout Report.

5. Generate deep dives
   For each topic, write evidence, study plan, projects, risks, and visibility plan.

6. Publish datasets
   Write JSON snapshots under datasets/ and optionally publish to Hugging Face.

7. Export dashboard
   Copy the frontend and latest dataset bundle to public/scout for GitHub Pages.
```

## Main command

```bash
python scripts/collect_all.py
```

## Frontend contract

The frontend starts with:

```text
GET /api/v1/ui/bootstrap
```

If served as static GitHub Pages, it can read the exported JSON files in `public/scout/data/`.

## Batch reports

Reports are written to:

```text
datasets/batches/latest.json
```

They cover default locations, goals, and profiles defined in `app/services/analysis_generator.py`.

## Optional ML/LLM enrichment

The workflow is deterministic by default. Enable optional models with:

```text
SCOUT_USE_SENTENCE_TRANSFORMERS=1
SCOUT_ENABLE_LLM=1
SCOUT_LLM_PROVIDER=<provider>
SCOUT_DESCRIPTION_MODEL=<model>
```

If enrichment fails, the workflow falls back to deterministic templates and still publishes usable data.
