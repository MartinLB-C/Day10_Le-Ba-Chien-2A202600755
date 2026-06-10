from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build a small deterministic evaluation set from the cleaned corpus."""
    if len(df) < 4:
        raise ValueError("At least 4 cleaned documents are required to build an evaluation set.")

    required_columns = {
        "paper_id",
        "title",
        "summary",
        "authors_joined",
        "categories_joined",
        "published",
    }
    missing = sorted(required_columns - set(df.columns))
    if missing:
        raise ValueError(f"Cleaned dataframe is missing required columns: {missing}")

    candidates = df[df["summary"].astype(str).str.len() >= 40].head(8).reset_index(drop=True)
    if len(candidates) < 4:
        raise ValueError("Not enough valid documents with usable summaries to build a test set.")

    samples: list[dict[str, Any]] = []
    question_templates = [
        (
            "summary",
            "What is the main point of the paper '{title}'?",
            lambda row: first_sentence(str(row["summary"])),
        ),
        (
            "authors",
            "Who authored the paper '{title}'?",
            lambda row: str(row["authors_joined"]) or "No authors listed.",
        ),
        (
            "date",
            "When was the paper '{title}' published on?",
            lambda row: str(row["published"]),
        ),
        (
            "categories",
            "What categories are listed for the paper '{title}'?",
            lambda row: str(row["categories_joined"]) or "No categories listed.",
        ),
    ]

    sample_id = 1
    for _, row in candidates.iterrows():
        for question_type, question_template, answer_builder in question_templates:
            title = str(row["title"])
            samples.append(
                {
                    "id": f"q{sample_id:03d}",
                    "question_type": question_type,
                    "question": question_template.format(title=title),
                    "ground_truth": answer_builder(row),
                    "ground_truth_doc_ids": [str(row["paper_id"])],
                }
            )
            sample_id += 1

    write_json(output_path, samples)
    return samples
