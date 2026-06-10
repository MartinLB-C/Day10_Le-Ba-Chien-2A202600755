from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from html import unescape
from pathlib import Path
import re
import time
from typing import Any

import requests

from core.utils import normalize_whitespace, read_json, write_json
from core.config import Settings

CROSSREF_API_URL = "https://api.crossref.org/works"


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _clean_text(value: Any) -> str:
    if isinstance(value, list):
        value = " ".join(str(item) for item in value if item)
    if value is None:
        return ""
    text = unescape(str(value))
    text = re.sub(r"<[^>]+>", " ", text)
    return normalize_whitespace(text)


def _first_text(value: Any) -> str:
    if isinstance(value, list):
        return _clean_text(value[0]) if value else ""
    return _clean_text(value)


def _date_from_parts(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    date_parts = value.get("date-parts") or []
    if not date_parts or not isinstance(date_parts[0], list):
        return ""
    parts = date_parts[0]
    if not parts:
        return ""
    year = int(parts[0])
    month = int(parts[1]) if len(parts) > 1 else 1
    day = int(parts[2]) if len(parts) > 2 else 1
    return f"{year:04d}-{month:02d}-{day:02d}"


def _published_date(item: dict[str, Any]) -> str:
    for key in ("published-print", "published-online", "published", "issued"):
        parsed = _date_from_parts(item.get(key))
        if parsed:
            return parsed
    return ""


def _updated_date(item: dict[str, Any], fallback: str) -> str:
    for key in ("indexed", "deposited", "updated"):
        value = item.get(key)
        if isinstance(value, dict) and value.get("date-time"):
            return str(value["date-time"])[:10]
        parsed = _date_from_parts(value)
        if parsed:
            return parsed
    return fallback


def _authors(item: dict[str, Any]) -> list[str]:
    authors = []
    for author in item.get("author") or []:
        if not isinstance(author, dict):
            continue
        given = _clean_text(author.get("given"))
        family = _clean_text(author.get("family"))
        name = _clean_text(author.get("name"))
        full_name = normalize_whitespace(" ".join(part for part in [given, family] if part)) or name
        if full_name:
            authors.append(full_name)
    return authors


def _subjects(item: dict[str, Any]) -> list[str]:
    subjects = item.get("subject") or []
    if not isinstance(subjects, list):
        return []
    return [_clean_text(subject) for subject in subjects if _clean_text(subject)]


def _pdf_url(item: dict[str, Any]) -> str:
    for link in item.get("link") or []:
        if not isinstance(link, dict):
            continue
        content_type = str(link.get("content-type") or "").lower()
        url = str(link.get("URL") or "")
        if "pdf" in content_type and url:
            return url
    return ""


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref API payload into normalized paper records."""
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []
    seen_ids: set[str] = set()

    for item in items:
        if not isinstance(item, dict):
            continue

        doi = _clean_text(item.get("DOI")).lower()
        title = _first_text(item.get("title"))
        summary = _clean_text(item.get("abstract"))
        published = _published_date(item)

        if not doi or not title or not summary or not published:
            continue
        if doi in seen_ids:
            continue

        authors = _authors(item)
        categories = _subjects(item)
        primary_category = categories[0] if categories else _clean_text(item.get("type")) or "unknown"
        abs_url = _clean_text(item.get("URL"))
        updated = _updated_date(item, fallback=published)
        comment_parts = [
            f"type={_clean_text(item.get('type'))}" if item.get("type") else "",
            f"publisher={_clean_text(item.get('publisher'))}" if item.get("publisher") else "",
        ]

        records.append(
            PaperRecord(
                paper_id=doi,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=_pdf_url(item),
                comment="; ".join(part for part in comment_parts if part),
            )
        )
        seen_ids.add(doi)

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref records, persist the raw payload, and persist parsed records."""
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
        "sort": "published",
        "order": "desc",
    }
    headers = {
        "User-Agent": "day10-data-observability-lab/0.1 (mailto:student@example.com)",
    }

    last_error: Exception | None = None
    for attempt in range(4):
        try:
            response = requests.get(CROSSREF_API_URL, params=params, headers=headers, timeout=30)
            if response.status_code in {429, 500, 502, 503, 504}:
                response.raise_for_status()
            response.raise_for_status()
            payload = response.json()
            write_json(settings.paths.raw_api_response, payload)

            records = parse_crossref_payload(payload)
            write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
            return records
        except requests.RequestException as exc:
            last_error = exc
            if attempt == 3:
                break
            retry_after = getattr(exc.response, "headers", {}).get("Retry-After") if exc.response else None
            delay = int(retry_after) if retry_after and retry_after.isdigit() else 2**attempt
            time.sleep(delay)

    raise RuntimeError(f"Failed to fetch Crossref records after retries: {last_error}")


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load a parsed raw-record snapshot from JSON."""
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Expected a list of raw records in {path}.")

    records: list[PaperRecord] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        records.append(
            PaperRecord(
                paper_id=str(item.get("paper_id", "")),
                title=str(item.get("title", "")),
                summary=str(item.get("summary", "")),
                authors=list(item.get("authors") or []),
                categories=list(item.get("categories") or []),
                primary_category=str(item.get("primary_category", "")),
                published=str(item.get("published", "")),
                updated=str(item.get("updated", "")),
                abs_url=str(item.get("abs_url", "")),
                pdf_url=str(item.get("pdf_url", "")),
                comment=str(item.get("comment", "")),
            )
        )
    return records
