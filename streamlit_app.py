from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"


PATHS = {
    "raw_records": DATA_DIR / "raw" / "crossref_records.json",
    "clean": DATA_DIR / "clean" / "papers_clean.json",
    "corrupted_clean": DATA_DIR / "clean" / "papers_clean_corrupted.json",
    "repaired_clean": DATA_DIR / "clean" / "papers_clean_repaired.json",
    "test_set": DATA_DIR / "eval" / "test_set.json",
    "baseline_metrics": DATA_DIR / "results" / "baseline_metrics.json",
    "corrupted_metrics": DATA_DIR / "results" / "corrupted_metrics.json",
    "repaired_metrics": DATA_DIR / "results" / "repaired_metrics.json",
    "baseline_quality": DATA_DIR / "quality" / "baseline_quality.json",
    "corrupted_quality": DATA_DIR / "quality" / "corrupted_quality.json",
    "repaired_quality": DATA_DIR / "quality" / "repaired_quality.json",
    "freshness": DATA_DIR / "quality" / "freshness_report.json",
    "corrupted_freshness": DATA_DIR / "quality" / "corrupted_freshness_report.json",
    "repaired_freshness": DATA_DIR / "quality" / "repaired_freshness_report.json",
    "phase1_report": DATA_DIR / "reports" / "phase1_report.md",
    "corruption_report": DATA_DIR / "reports" / "corruption_report.md",
    "progress_report": DATA_DIR / "reports" / "progress_report.md",
    "corruption_log": DATA_DIR / "results" / "corruption_log.json",
}


st.set_page_config(
    page_title="Day 10 Data Observability",
    page_icon="D10",
    layout="wide",
)


@st.cache_data(show_spinner=False)
def read_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def as_dataframe(path: Path) -> pd.DataFrame:
    payload = read_json(path)
    if isinstance(payload, list):
        return pd.DataFrame(payload)
    return pd.DataFrame()


def metrics_frame() -> pd.DataFrame:
    rows = []
    for label, key in [
        ("Baseline", "baseline_metrics"),
        ("Corrupted", "corrupted_metrics"),
        ("Repaired", "repaired_metrics"),
    ]:
        payload = read_json(PATHS[key]) or {}
        rows.append(
            {
                "run": label,
                "samples": payload.get("samples"),
                "retrieval_hit_rate": payload.get("retrieval_hit_rate"),
                "mean_token_f1": payload.get("mean_token_f1"),
                "judge_accuracy": payload.get("judge_accuracy"),
                "mean_judge_score": payload.get("mean_judge_score"),
            }
        )
    return pd.DataFrame(rows)


def quality_summary_frame() -> pd.DataFrame:
    rows = []
    for label, key in [
        ("Baseline", "baseline_quality"),
        ("Corrupted", "corrupted_quality"),
        ("Repaired", "repaired_quality"),
    ]:
        payload = read_json(PATHS[key]) or {}
        rows.append(
            {
                "run": label,
                "passed": payload.get("passed"),
                "total_rows": payload.get("total_rows"),
                "failed_checks": ", ".join(payload.get("failed_checks") or []),
            }
        )
    return pd.DataFrame(rows)


def freshness_frame() -> pd.DataFrame:
    rows = []
    for label, key in [
        ("Baseline", "freshness"),
        ("Corrupted", "corrupted_freshness"),
        ("Repaired", "repaired_freshness"),
    ]:
        payload = read_json(PATHS[key]) or {}
        rows.append(
            {
                "run": label,
                "latest_published": payload.get("latest_published"),
                "oldest_published": payload.get("oldest_published"),
                "stale_rows": payload.get("stale_rows"),
                "is_fresh": payload.get("is_fresh"),
            }
        )
    return pd.DataFrame(rows)


def status_badge(exists: bool) -> str:
    return "Ready" if exists else "Missing"


def format_pct(value: Any) -> str:
    if isinstance(value, int | float):
        return f"{value:.1%}"
    return "n/a"


def run_command(command: list[str]) -> tuple[int, str]:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    output = "\n".join(part for part in [completed.stdout, completed.stderr] if part)
    return completed.returncode, output


st.title("Day 10 Data Pipeline Observability")
st.caption("Local dashboard for Crossref ingestion, cleaning, RAG evaluation, data quality, and corruption repair.")

with st.sidebar:
    st.header("Pipeline Controls")
    st.write("Run from the current virtual environment.")
    if st.button("Run Baseline Pipeline", width="stretch"):
        with st.spinner("Running baseline pipeline..."):
            code, output = run_command([sys.executable, "script/run_phase1.py"])
        st.code(output or f"Exit code: {code}", language="text")
        st.cache_data.clear()

    if st.button("Run Corruption Flow", width="stretch"):
        with st.spinner("Running corruption flow..."):
            code, output = run_command([sys.executable, "script/run_corruption_flow.py"])
        st.code(output or f"Exit code: {code}", language="text")
        st.cache_data.clear()

    if st.button("Reload Artifacts", width="stretch"):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.header("Artifacts")
    artifact_rows = [
        {"artifact": name, "status": status_badge(path.exists())}
        for name, path in PATHS.items()
    ]
    st.dataframe(pd.DataFrame(artifact_rows), hide_index=True, width="stretch")


raw_df = as_dataframe(PATHS["raw_records"])
clean_df = as_dataframe(PATHS["clean"])
corrupted_df = as_dataframe(PATHS["corrupted_clean"])
repaired_df = as_dataframe(PATHS["repaired_clean"])
test_set = read_json(PATHS["test_set"]) or []
metrics_df = metrics_frame()

top_cols = st.columns(5)
top_cols[0].metric("Raw Records", len(raw_df))
top_cols[1].metric("Clean Records", len(clean_df))
top_cols[2].metric("Eval Samples", len(test_set))
baseline_hit = metrics_df.loc[metrics_df["run"] == "Baseline", "retrieval_hit_rate"].iloc[0]
corrupted_hit = metrics_df.loc[metrics_df["run"] == "Corrupted", "retrieval_hit_rate"].iloc[0]
top_cols[3].metric("Baseline Hit Rate", format_pct(baseline_hit))
top_cols[4].metric("Corrupted Hit Rate", format_pct(corrupted_hit))

tabs = st.tabs(
    [
        "Overview",
        "Dataset",
        "Metrics",
        "Quality",
        "Freshness",
        "Reports",
        "Corruption Log",
    ]
)

with tabs[0]:
    st.subheader("Pipeline Flow")
    flow = pd.DataFrame(
        [
            {"step": "1. Ingest Crossref", "output": "raw records", "rows": len(raw_df), "status": status_badge(not raw_df.empty)},
            {"step": "2. Clean data", "output": "clean dataset", "rows": len(clean_df), "status": status_badge(not clean_df.empty)},
            {"step": "3. Build test set", "output": "evaluation samples", "rows": len(test_set), "status": status_badge(bool(test_set))},
            {"step": "4. Evaluate baseline", "output": "baseline metrics", "rows": None, "status": status_badge(PATHS["baseline_metrics"].exists())},
            {"step": "5. Corrupt data", "output": "corrupted dataset", "rows": len(corrupted_df), "status": status_badge(not corrupted_df.empty)},
            {"step": "6. Repair data", "output": "repaired dataset", "rows": len(repaired_df), "status": status_badge(not repaired_df.empty)},
        ]
    )
    st.dataframe(flow, hide_index=True, width="stretch")

    st.subheader("Metrics Snapshot")
    chart_data = metrics_df.set_index("run")[["retrieval_hit_rate", "mean_token_f1", "judge_accuracy"]]
    st.bar_chart(chart_data)
    st.dataframe(metrics_df, hide_index=True, width="stretch")

with tabs[1]:
    st.subheader("Clean Dataset")
    if clean_df.empty:
        st.warning("Clean dataset is missing. Run the baseline pipeline first.")
    else:
        visible_columns = [
            column
            for column in [
                "paper_id",
                "title",
                "published",
                "age_days",
                "summary_chars",
                "authors_joined",
                "categories_joined",
            ]
            if column in clean_df.columns
        ]
        st.dataframe(clean_df[visible_columns], hide_index=True, width="stretch")

        st.subheader("Summary Length Distribution")
        if "summary_chars" in clean_df.columns:
            st.bar_chart(clean_df["summary_chars"])

    st.subheader("Evaluation Test Set")
    if test_set:
        test_df = pd.DataFrame(test_set)
        st.dataframe(test_df, hide_index=True, width="stretch")
    else:
        st.info("No evaluation test set found.")

with tabs[2]:
    st.subheader("Baseline vs Corrupted vs Repaired")
    st.dataframe(metrics_df, hide_index=True, width="stretch")
    st.bar_chart(metrics_df.set_index("run")[["retrieval_hit_rate", "mean_token_f1", "judge_accuracy"]])
    st.line_chart(metrics_df.set_index("run")[["mean_judge_score"]])

with tabs[3]:
    st.subheader("Quality Summary")
    qdf = quality_summary_frame()
    st.dataframe(qdf, hide_index=True, width="stretch")

    selected_quality = st.selectbox("Quality report", ["baseline_quality", "corrupted_quality", "repaired_quality"])
    payload = read_json(PATHS[selected_quality]) or {}
    checks = payload.get("checks") or []
    if checks:
        expanded = pd.DataFrame(
            [
                {
                    "check": item.get("name"),
                    "passed": item.get("passed"),
                    "detail": item.get("detail"),
                }
                for item in checks
            ]
        )
        st.dataframe(expanded, hide_index=True, width="stretch")
    else:
        st.info("No check details found.")

with tabs[4]:
    st.subheader("Freshness")
    fdf = freshness_frame()
    st.dataframe(fdf, hide_index=True, width="stretch")
    chart_fdf = fdf.copy()
    chart_fdf["stale_rows"] = pd.to_numeric(chart_fdf["stale_rows"], errors="coerce").fillna(0)
    st.bar_chart(chart_fdf.set_index("run")[["stale_rows"]])

with tabs[5]:
    st.subheader("Markdown Reports")
    report_choice = st.selectbox(
        "Report",
        ["phase1_report", "corruption_report", "progress_report"],
    )
    content = read_text(PATHS[report_choice])
    if content:
        st.markdown(content)
    else:
        st.warning("Report file is missing.")

with tabs[6]:
    st.subheader("Corruption Operations")
    log = read_json(PATHS["corruption_log"]) or {}
    operations = log.get("operations") or []
    if operations:
        st.dataframe(pd.DataFrame(operations), hide_index=True, width="stretch")
    else:
        st.info("No corruption log found.")
    st.json(log)
