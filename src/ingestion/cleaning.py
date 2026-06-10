from __future__ import annotations

from datetime import UTC, datetime
from typing import Iterable

import pandas as pd

from core.utils import normalize_whitespace
from ingestion.crossref import PaperRecord


def _clean_text(value: str | None) -> str:
    if value is None:
        return ""
    return normalize_whitespace(str(value))


def _clean_list(values: Iterable[str] | None) -> list[str]:
    if not values:
        return []

    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = _clean_text(value)
        key = item.casefold()
        if item and key not in seen:
            cleaned.append(item)
            seen.add(key)
    return cleaned


def _parse_date(value: str | None) -> pd.Timestamp | None:
    if not value:
        return None
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(parsed):
        return None
    return parsed


def _run_date_utc(run_date: datetime) -> pd.Timestamp:
    if run_date.tzinfo is None:
        run_date = run_date.replace(tzinfo=UTC)
    return pd.Timestamp(run_date).tz_convert("UTC")


def _embedding_text(
    title: str,
    summary: str,
    authors_joined: str,
    categories_joined: str,
    published: str,
) -> str:
    parts = [
        f"Title: {title}",
        f"Authors: {authors_joined}" if authors_joined else "",
        f"Categories: {categories_joined}" if categories_joined else "",
        f"Published: {published}" if published else "",
        f"Summary: {summary}",
    ]
    return normalize_whitespace(" ".join(part for part in parts if part))


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw paper records into an embedding-ready dataframe."""
    cleaned_rows = []
    run_ts = _run_date_utc(run_date)

    for record in records:
        paper_id = _clean_text(record.paper_id).lower()
        title = _clean_text(record.title)
        summary = _clean_text(record.summary)
        authors = _clean_list(record.authors)
        categories = _clean_list(record.categories)
        primary_category = _clean_text(record.primary_category)
        if primary_category and primary_category.casefold() not in {item.casefold() for item in categories}:
            categories.insert(0, primary_category)

        published_ts = _parse_date(record.published)
        updated_ts = _parse_date(record.updated) or published_ts

        if not paper_id or not title or not summary or published_ts is None:
            continue
        if len(summary) < 40:
            continue

        published = published_ts.strftime("%Y-%m-%d")
        updated = updated_ts.strftime("%Y-%m-%d") if updated_ts is not None else published
        age_days = max(0, int((run_ts.normalize() - published_ts.normalize()).days))
        authors_joined = ", ".join(authors)
        categories_joined = ", ".join(categories)

        cleaned_rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": categories[0] if categories else "unknown",
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "published": published,
                "updated": updated,
                "age_days": age_days,
                "summary_chars": len(summary),
                "abs_url": _clean_text(record.abs_url),
                "pdf_url": _clean_text(record.pdf_url),
                "comment": _clean_text(record.comment),
                "text_for_embedding": _embedding_text(
                    title=title,
                    summary=summary,
                    authors_joined=authors_joined,
                    categories_joined=categories_joined,
                    published=published,
                ),
            }
        )

    columns = [
        "paper_id",
        "title",
        "summary",
        "authors",
        "categories",
        "primary_category",
        "authors_joined",
        "categories_joined",
        "published",
        "updated",
        "age_days",
        "summary_chars",
        "abs_url",
        "pdf_url",
        "comment",
        "text_for_embedding",
    ]
    df = pd.DataFrame(cleaned_rows, columns=columns)
    if df.empty:
        return df

    df = df.drop_duplicates(subset=["paper_id"], keep="first")
    df = df[df["title"].str.len() > 0]
    df = df[df["summary_chars"] >= 40]
    df = df[df["text_for_embedding"].str.len() > 0]
    df = df.sort_values(["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)
    return df
