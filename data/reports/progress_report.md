# Day 10 Progress Report

## Initial State

- Project was a starter scaffold for the Day 10 data pipeline and observability lab.
- Data artifact folders under `data/` only contained `.gitkeep` placeholders.
- Several core student tasks were still implemented as `NotImplementedError`.

## Completed Work

### 1. Environment File

- Created `.env` in the project root from `.env.example`.
- Kept API keys empty to avoid committing sensitive credentials.
- Current default provider:
  - `LLM_PROVIDER=gemini`
  - `LLM_MODEL=gemini-2.5-flash`

### 2. Raw Ingestion

Updated `src/ingestion/crossref.py`.

Implemented:

- `parse_crossref_payload`
- `fetch_source_records`
- `load_raw_records`

Behavior added:

- Calls Crossref REST API at `https://api.crossref.org/works`.
- Builds request params from project settings:
  - `source_query`
  - `source_filter`
  - `max_results`
- Parses DOI, title, abstract, authors, subjects, dates, URLs, and PDF links.
- Normalizes basic text fields and strips XML/HTML tags from abstracts.
- Skips invalid records missing DOI, title, abstract, or published date.
- Deduplicates records by DOI.
- Saves raw API payload to `data/raw/crossref_response.json`.
- Saves parsed records to `data/raw/crossref_records.json`.

Execution result:

- Crossref fetch completed successfully.
- Parsed record count: 24.

### 3. Cleaning And Data Modeling

Updated `src/ingestion/cleaning.py`.

Implemented:

- `build_clean_dataframe`

Behavior added:

- Normalizes `paper_id`, `title`, `summary`, authors, categories, URLs, and comments.
- Deduplicates authors and categories while preserving order.
- Adds `primary_category` into categories when missing.
- Parses `published` and `updated` dates.
- Computes `age_days` from the supplied pipeline run date.
- Filters invalid rows missing `paper_id`, `title`, `summary`, or `published`.
- Filters very short summaries.
- Drops duplicate papers by `paper_id`.
- Creates helper columns:
  - `authors_joined`
  - `categories_joined`
  - `summary_chars`
  - `text_for_embedding`
- Sorts cleaned data by newest published date first.

Execution result:

- Cleaning completed successfully from the current raw snapshot.
- Cleaned row count: 24.
- Saved cleaned CSV to `data/clean/papers_clean.csv`.
- Saved cleaned JSON to `data/clean/papers_clean.json`.

### 4. Evaluation Test Set

Updated `src/evaluation/testset.py`.

Implemented:

- `build_test_set`

Behavior added:

- Builds deterministic evaluation questions from cleaned records.
- Creates four question types:
  - `summary`
  - `authors`
  - `date`
  - `categories`
- Uses exact paper titles in questions so retrieval QA can verify against the correct document.
- Saves test set to `data/eval/test_set.json`.

Execution result:

- Generated 32 evaluation samples.

### 5. Data Quality And Freshness

Updated `src/observability/quality.py`.

Implemented:

- `run_data_quality_checks`
- `build_freshness_report`

Behavior added:

- Checks row count, `paper_id` nulls, duplicate `paper_id`, blank title/summary/text, summary length, and freshness threshold.
- Saves quality reports into `data/quality/`.
- Saves freshness reports as JSON.

### 6. Markdown Reporting

Updated `src/observability/reporting.py`.

Implemented:

- `generate_phase1_report`
- `generate_corruption_report`

Behavior added:

- Generates readable baseline report at `data/reports/phase1_report.md`.
- Generates baseline/corrupted/repaired comparison report at `data/reports/corruption_report.md`.

### 7. Baseline Pipeline

Updated `src/pipelines/phase1.py`.

Implemented baseline orchestration:

- Load or fetch raw records.
- Build cleaned dataframe.
- Save cleaned CSV/JSON.
- Build Chroma embedding index.
- Build/load evaluation test set.
- Evaluate retrieval and answer quality.
- Run quality and freshness reports.
- Generate phase 1 markdown report.
- Save demo QA answers.

Execution result:

- Baseline pipeline completed successfully.
- Cleaned rows: 24.
- Evaluation samples: 32.
- Baseline retrieval hit rate: 1.0.
- Baseline mean token F1: 1.0.
- Baseline judge accuracy: 1.0.

### 8. Corruption Simulation

Updated `src/ingestion/corruption.py`.

Implemented:

- `corrupt_clean_dataframe`

Behavior added:

- Drops latest records.
- Blanks some summaries.
- Injects noise into summaries.
- Truncates titles.
- Makes some publication dates stale.
- Adds duplicate rows.
- Rebuilds `summary_chars` and `text_for_embedding`.
- Saves corruption log to `data/results/corruption_log.json`.

### 9. Corruption, Repair, And Comparison Flow

Updated `src/pipelines/corruption_flow.py`.

Implemented comparison orchestration:

- Loads baseline metrics and cleaned data.
- Creates corrupted dataset.
- Saves corrupted CSV/JSON.
- Builds corrupted embedding index.
- Evaluates corrupted dataset against the original test set.
- Runs corrupted quality/freshness checks.
- Repairs by rebuilding cleaned data from raw source records.
- Builds repaired embedding index.
- Evaluates repaired dataset.
- Runs repaired quality/freshness checks.
- Generates comparison markdown report.

Execution result:

- Corruption flow completed successfully.
- Corrupted rows: 24.
- Repaired rows: 24.
- Corrupted retrieval hit rate: 0.75.
- Corrupted mean token F1: 0.6955.
- Corrupted judge accuracy: 0.6875.
- Repaired retrieval hit rate: 1.0.
- Repaired mean token F1: 1.0.
- Repaired judge accuracy: 1.0.

### 10. Entrypoint Fix

Updated:

- `script/run_phase1.py`
- `script/run_corruption_flow.py`

Behavior added:

- Adds `src/` to `sys.path` so scripts can run directly with `venv\\Scripts\\python.exe`.

### 11. Streamlit Dashboard

Added `streamlit_app.py`.

Behavior added:

- Visualizes raw, clean, corrupted, and repaired dataset status.
- Shows baseline, corrupted, and repaired evaluation metrics.
- Displays quality checks and freshness reports.
- Provides markdown report previews.
- Shows corruption operations from `data/results/corruption_log.json`.
- Adds sidebar buttons to rerun baseline and corruption flows.

Updated dependencies:

- Added `streamlit>=1.37.0` to `requirements.txt`.
- Added `streamlit>=1.37.0` to `pyproject.toml`.

Run command:

```powershell
venv\\Scripts\\python.exe -m streamlit run streamlit_app.py
```

## Current Important Artifacts

- `.env`
- `data/raw/crossref_response.json`
- `data/raw/crossref_records.json`
- `data/clean/papers_clean.csv`
- `data/clean/papers_clean.json`
- `data/eval/test_set.json`
- `data/embeddings/papers_embeddings.json`
- `data/embeddings/papers_embeddings_corrupted.json`
- `data/embeddings/papers_embeddings_repaired.json`
- `data/results/baseline_metrics.json`
- `data/results/corrupted_metrics.json`
- `data/results/repaired_metrics.json`
- `data/results/corruption_log.json`
- `data/quality/baseline_quality.json`
- `data/quality/corrupted_quality.json`
- `data/quality/repaired_quality.json`
- `data/reports/phase1_report.md`
- `data/reports/corruption_report.md`
- `data/reports/progress_report.md`
- `streamlit_app.py`

## Remaining Tasks

- Review generated reports and metrics before submission.
- Add optional tests or visualizations for bonus credit.
