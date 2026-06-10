from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run lightweight data quality checks and persist the result."""
    total_rows = len(df)
    checks: list[dict[str, Any]] = []

    def add_check(name: str, passed: bool, detail: dict[str, Any]) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    add_check(
        "row_count_positive",
        total_rows > 0,
        {"total_rows": total_rows},
    )

    if "paper_id" in df.columns:
        non_null = int(df["paper_id"].notna().sum())
        duplicates = int(df["paper_id"].duplicated().sum())
        add_check(
            "paper_id_not_null",
            non_null == total_rows,
            {"non_null": non_null, "total_rows": total_rows},
        )
        add_check(
            "paper_id_unique",
            duplicates == 0,
            {"duplicate_rows": duplicates},
        )
    else:
        add_check("paper_id_exists", False, {"missing_column": "paper_id"})

    for column in ("title", "summary", "text_for_embedding"):
        if column not in df.columns:
            add_check(f"{column}_exists", False, {"missing_column": column})
            continue
        empty_count = int(df[column].fillna("").astype(str).str.strip().eq("").sum())
        add_check(
            f"{column}_not_blank",
            empty_count == 0,
            {"empty_rows": empty_count, "total_rows": total_rows},
        )

    if "summary_chars" in df.columns:
        short_summary_count = int((pd.to_numeric(df["summary_chars"], errors="coerce").fillna(0) < 40).sum())
    elif "summary" in df.columns:
        short_summary_count = int((df["summary"].fillna("").astype(str).str.len() < 40).sum())
    else:
        short_summary_count = total_rows
    add_check(
        "summary_min_length",
        short_summary_count == 0,
        {"min_chars": 40, "short_rows": short_summary_count},
    )

    if "age_days" in df.columns:
        age_days = pd.to_numeric(df["age_days"], errors="coerce")
        stale_rows = int((age_days > settings.freshness_threshold_days).sum())
        missing_age_rows = int(age_days.isna().sum())
        add_check(
            "freshness_threshold",
            stale_rows == 0 and missing_age_rows == 0,
            {
                "threshold_days": settings.freshness_threshold_days,
                "stale_rows": stale_rows,
                "missing_age_rows": missing_age_rows,
            },
        )
    else:
        add_check("age_days_exists", False, {"missing_column": "age_days"})

    payload = {
        "report_name": report_name,
        "total_rows": total_rows,
        "passed": all(check["passed"] for check in checks),
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "checks": checks,
    }
    write_json(settings.paths.quality_dir / report_name, payload)
    return payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Build and persist a freshness summary for a cleaned dataframe."""
    published = pd.to_datetime(df.get("published"), errors="coerce", utc=True) if "published" in df else pd.Series([])
    age_days = pd.to_numeric(df.get("age_days"), errors="coerce") if "age_days" in df else pd.Series([])
    stale_rows = int((age_days > settings.freshness_threshold_days).sum()) if not age_days.empty else len(df)
    missing_published = int(published.isna().sum()) if not published.empty else len(df)

    payload = {
        "latest_published": published.max().strftime("%Y-%m-%d") if not published.empty and not pd.isna(published.max()) else None,
        "oldest_published": published.min().strftime("%Y-%m-%d") if not published.empty and not pd.isna(published.min()) else None,
        "stale_rows": stale_rows,
        "missing_published_rows": missing_published,
        "total_rows": len(df),
        "freshness_threshold_days": settings.freshness_threshold_days,
        "is_fresh": stale_rows == 0 and missing_published == 0 and len(df) > 0,
    }
    write_json(report_path, payload)
    return payload
