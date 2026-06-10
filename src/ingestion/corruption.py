from __future__ import annotations

import pandas as pd

from core.utils import normalize_whitespace, write_json


def _rebuild_embedding_text(row) -> str:
    parts = [
        f"Title: {row.get('title', '')}",
        f"Authors: {row.get('authors_joined', '')}" if row.get("authors_joined", "") else "",
        f"Categories: {row.get('categories_joined', '')}" if row.get("categories_joined", "") else "",
        f"Published: {row.get('published', '')}" if row.get("published", "") else "",
        f"Summary: {row.get('summary', '')}",
    ]
    return normalize_whitespace(" ".join(part for part in parts if part))


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Simulate common data quality failures on a cleaned dataframe."""
    if df.empty:
        raise ValueError("Cannot corrupt an empty dataframe.")

    corrupted = df.copy(deep=True).sort_values(["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)
    original_rows = len(corrupted)
    log: dict[str, object] = {
        "original_rows": original_rows,
        "operations": [],
    }

    drop_count = min(3, max(1, original_rows // 10))
    dropped_ids = corrupted.head(drop_count)["paper_id"].astype(str).tolist()
    corrupted = corrupted.iloc[drop_count:].reset_index(drop=True)
    log["operations"].append({"name": "drop_latest_records", "rows": drop_count, "paper_ids": dropped_ids})

    if not corrupted.empty:
        blank_indices = corrupted.index[: min(3, len(corrupted))].tolist()
        corrupted.loc[blank_indices, "summary"] = ""
        log["operations"].append({"name": "blank_summary", "rows": len(blank_indices), "indices": blank_indices})

    if len(corrupted) > 3:
        noise_indices = corrupted.index[3 : min(6, len(corrupted))].tolist()
        noise = " UNRELATED_NOISE_TOKEN repeated repeated telemetry drift"
        corrupted.loc[noise_indices, "summary"] = corrupted.loc[noise_indices, "summary"].astype(str) + noise
        log["operations"].append({"name": "inject_summary_noise", "rows": len(noise_indices), "indices": noise_indices})

    if len(corrupted) > 6:
        truncate_indices = corrupted.index[6 : min(9, len(corrupted))].tolist()
        corrupted.loc[truncate_indices, "title"] = corrupted.loc[truncate_indices, "title"].astype(str).str.slice(0, 18)
        log["operations"].append({"name": "truncate_title", "rows": len(truncate_indices), "indices": truncate_indices})

    if len(corrupted) > 9:
        stale_indices = corrupted.index[9 : min(12, len(corrupted))].tolist()
        published = pd.to_datetime(corrupted.loc[stale_indices, "published"], errors="coerce", utc=True)
        stale_published = published - pd.DateOffset(years=3)
        corrupted.loc[stale_indices, "published"] = stale_published.dt.strftime("%Y-%m-%d")
        if "age_days" in corrupted.columns:
            corrupted.loc[stale_indices, "age_days"] = pd.to_numeric(
                corrupted.loc[stale_indices, "age_days"], errors="coerce"
            ).fillna(0) + 1095
        log["operations"].append({"name": "stale_publication_date", "rows": len(stale_indices), "indices": stale_indices})

    duplicate_count = min(2, len(corrupted))
    if duplicate_count:
        duplicates = corrupted.tail(duplicate_count).copy(deep=True)
        corrupted = pd.concat([corrupted, duplicates], ignore_index=True)
        log["operations"].append(
            {
                "name": "add_duplicate_rows",
                "rows": duplicate_count,
                "paper_ids": duplicates["paper_id"].astype(str).tolist(),
            }
        )

    corrupted["summary_chars"] = corrupted["summary"].fillna("").astype(str).str.len()
    corrupted["text_for_embedding"] = corrupted.apply(_rebuild_embedding_text, axis=1)
    log["final_rows"] = len(corrupted)
    log["blank_summary_rows"] = int(corrupted["summary"].fillna("").astype(str).str.strip().eq("").sum())
    log["duplicate_paper_id_rows"] = int(corrupted["paper_id"].duplicated().sum())

    write_json(output_log_path, log)
    return corrupted.reset_index(drop=True)
