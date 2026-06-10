# Corruption And Repair Report

## Metrics Comparison

| Metric | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| retrieval_hit_rate | 1.0000 | 0.7500 | 1.0000 |
| mean_token_f1 | 1.0000 | 0.6955 | 1.0000 |
| judge_accuracy | 1.0000 | 0.6875 | 1.0000 |
| mean_judge_score | 5 | 3.7500 | 5 |

## Quality Comparison

- Corrupted quality: FAIL; failed checks: paper_id_unique, summary_not_blank, summary_min_length, freshness_threshold
- Repaired quality: PASS; failed checks: none

## Freshness Comparison

- Corrupted stale rows: 3
- Corrupted is fresh: False
- Repaired stale rows: 0
- Repaired is fresh: True

## Interpretation

- Corrupted data intentionally introduces missing summaries, stale dates, duplicates, truncated titles, and removed latest papers.
- Repaired data is rebuilt from the original raw source snapshot and should recover quality checks and retrieval behavior.
