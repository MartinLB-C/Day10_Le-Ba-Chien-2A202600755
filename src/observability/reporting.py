from __future__ import annotations

from typing import Any

from core.utils import write_text


def _metric(metrics: dict[str, Any], key: str) -> str:
    value = metrics.get(key)
    if isinstance(value, float):
        return f"{value:.4f}"
    if value is None:
        return "n/a"
    return str(value)


def _quality_line(quality: dict[str, Any]) -> str:
    status = "PASS" if quality.get("passed") else "FAIL"
    failed = quality.get("failed_checks") or []
    if not failed:
        return f"{status}; failed checks: none"
    return f"{status}; failed checks: {', '.join(failed)}"


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write the baseline phase report as markdown."""
    lines = [
        "# Phase 1 Baseline Report",
        "",
        "## Source",
        "",
        f"- Source API: {source_summary.get('source_api', 'n/a')}",
        f"- Query: {source_summary.get('source_query', 'n/a')}",
        f"- Filter: {source_summary.get('source_filter', 'n/a')}",
        f"- Raw records: {source_summary.get('raw_records', 'n/a')}",
        f"- Clean records: {source_summary.get('clean_records', 'n/a')}",
        "",
        "## Evaluation Metrics",
        "",
        f"- Samples: {_metric(metrics, 'samples')}",
        f"- Retrieval hit rate: {_metric(metrics, 'retrieval_hit_rate')}",
        f"- Mean token F1: {_metric(metrics, 'mean_token_f1')}",
        f"- Judge accuracy: {_metric(metrics, 'judge_accuracy')}",
        f"- Mean judge score: {_metric(metrics, 'mean_judge_score')}",
        f"- Ragas: {metrics.get('ragas', {})}",
        "",
        "## Data Quality",
        "",
        f"- Status: {_quality_line(quality)}",
        f"- Total rows: {quality.get('total_rows', 'n/a')}",
        "",
        "## Freshness",
        "",
        f"- Latest published: {freshness.get('latest_published')}",
        f"- Oldest published: {freshness.get('oldest_published')}",
        f"- Stale rows: {freshness.get('stale_rows')}",
        f"- Is fresh: {freshness.get('is_fresh')}",
        "",
    ]
    write_text(report_path, "\n".join(lines))


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Write a markdown comparison report for baseline/corrupted/repaired runs."""
    metric_keys = [
        "retrieval_hit_rate",
        "mean_token_f1",
        "judge_accuracy",
        "mean_judge_score",
    ]
    lines = [
        "# Corruption And Repair Report",
        "",
        "## Metrics Comparison",
        "",
        "| Metric | Baseline | Corrupted | Repaired |",
        "| --- | ---: | ---: | ---: |",
    ]
    for key in metric_keys:
        lines.append(
            f"| {key} | {_metric(baseline_metrics, key)} | "
            f"{_metric(corrupted_metrics, key)} | {_metric(repaired_metrics, key)} |"
        )

    lines.extend(
        [
            "",
            "## Quality Comparison",
            "",
            f"- Corrupted quality: {_quality_line(corrupted_quality)}",
            f"- Repaired quality: {_quality_line(repaired_quality)}",
            "",
            "## Freshness Comparison",
            "",
            f"- Corrupted stale rows: {corrupted_freshness.get('stale_rows')}",
            f"- Corrupted is fresh: {corrupted_freshness.get('is_fresh')}",
            f"- Repaired stale rows: {repaired_freshness.get('stale_rows')}",
            f"- Repaired is fresh: {repaired_freshness.get('is_fresh')}",
            "",
            "## Interpretation",
            "",
            "- Corrupted data intentionally introduces missing summaries, stale dates, duplicates, truncated titles, and removed latest papers.",
            "- Repaired data is rebuilt from the original raw source snapshot and should recover quality checks and retrieval behavior.",
            "",
        ]
    )
    write_text(report_path, "\n".join(lines))
