# Báo cáo Lab 10 - Data Pipeline, Data Observability và RAG Evaluation

Sinh viên: Le Ba Chien - 2A202600755  
Ngày kiểm tra: 10/06/2026  
Dự án: Day 10 - Data Pipeline And Data Observability

## 1. Mục tiêu bài lab

Bài lab xây dựng một pipeline dữ liệu nhỏ cho hệ thống RAG, gồm các bước chính:

- Lấy dữ liệu học thuật từ Crossref REST API.
- Parse và lưu raw response/raw records.
- Làm sạch dữ liệu thành cleaned dataset có schema ổn định.
- Tạo embedding bằng `sentence-transformers/all-MiniLM-L6-v2`.
- Lưu và truy vấn vector store bằng ChromaDB.
- Tạo bộ câu hỏi đánh giá deterministic.
- Đánh giá baseline, dữ liệu bị corrupt và dữ liệu repaired.
- Theo dõi data quality, freshness và sinh báo cáo markdown.
- Cung cấp dashboard Streamlit để quan sát artifact và metrics.

## 2. Kiểm tra cấu trúc dự án

| Thành phần | Vai trò | Trạng thái |
| --- | --- | --- |
| `src/core/` | Cấu hình, đường dẫn, utility đọc/ghi file | Đã có và dùng nhất quán |
| `src/ingestion/` | Fetch Crossref, cleaning, corruption simulation | Đã hoàn thành |
| `src/retrieval/` | Embedding, Chroma index, LLM provider, agent/QA | Đã hoàn thành |
| `src/evaluation/` | Test set và metrics evaluation | Đã hoàn thành |
| `src/observability/` | Data quality, freshness, markdown report | Đã hoàn thành |
| `src/pipelines/` | Baseline flow và corruption/repair flow | Đã hoàn thành |
| `script/` | Entrypoint chạy pipeline | Đã hoàn thành |
| `data/` | Raw, clean, embeddings, eval, results, quality, reports | Đã có artifact thực tế |
| `streamlit_app.py` | Dashboard local quan sát pipeline | Đã có |

Nhìn chung dự án được chia module rõ ràng, đúng cấu trúc của đề bài. Pipeline có thể chạy qua hai entrypoint:

```powershell
venv\Scripts\python.exe script\run_phase1.py
venv\Scripts\python.exe script\run_corruption_flow.py
```

Dashboard có thể chạy bằng:

```powershell
venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

## 3. Nguồn dữ liệu và ingestion

Nguồn dữ liệu được dùng là Crossref REST API tại `https://api.crossref.org/works`.

Thiết lập chính:

- Query: `agentic retrieval augmented generation large language model`
- Filter: `from-pub-date:2025-12-12,has-abstract:true`
- Số record tối đa: 24
- Raw response: `data/raw/crossref_response.json`
- Raw records đã parse: `data/raw/crossref_records.json`

Kết quả kiểm tra artifact:

| Artifact | Số lượng |
| --- | ---: |
| Raw records | 24 |
| Clean records | 24 |
| Evaluation samples | 32 |
| Baseline answers | 32 |
| Corrupted answers | 32 |
| Repaired answers | 32 |

Schema raw record gồm các trường quan trọng: `paper_id`, `title`, `summary`, `authors`, `categories`, `primary_category`, `published`, `updated`, `abs_url`, `pdf_url`, `comment`.

## 4. Cleaning và data modeling

Module `src/ingestion/cleaning.py` chuẩn hóa dữ liệu thành dataframe có 16 cột:

- `paper_id`
- `title`
- `summary`
- `authors`
- `categories`
- `primary_category`
- `authors_joined`
- `categories_joined`
- `published`
- `updated`
- `age_days`
- `summary_chars`
- `abs_url`
- `pdf_url`
- `comment`
- `text_for_embedding`

Các bước cleaning chính:

- Chuẩn hóa whitespace và text.
- Ép `paper_id` về lowercase.
- Loại record thiếu `paper_id`, `title`, `summary` hoặc `published`.
- Loại summary quá ngắn dưới 40 ký tự.
- Deduplicate theo `paper_id`.
- Tính `age_days`.
- Tạo `text_for_embedding` từ title, authors, categories, published date và summary.
- Sort theo ngày publish mới nhất.

Kết quả: cleaned dataset có 24 dòng và được lưu ở:

- `data/clean/papers_clean.csv`
- `data/clean/papers_clean.json`

## 5. Embedding, vector store và truy vấn RAG

Embedding được tạo bằng model:

```text
sentence-transformers/all-MiniLM-L6-v2
```

Vector store dùng ChromaDB persistent client tại:

```text
data/chroma/
```

Ba collection được dùng cho ba giai đoạn:

- Baseline: `papers-baseline`
- Corrupted: `papers-corrupted`
- Repaired: `papers-repaired`

Các manifest embedding được lưu tại:

- `data/embeddings/papers_embeddings.json`
- `data/embeddings/papers_embeddings_corrupted.json`
- `data/embeddings/papers_embeddings_repaired.json`

Truy vấn RAG hỗ trợ:

- Semantic search theo embedding.
- Lookup chính xác theo `paper_id` hoặc title.
- Trả lời deterministic theo loại câu hỏi: summary, authors, published date, categories.

Ngoài QA deterministic để chấm điểm ổn định, dự án còn có LangChain agent trong `src/retrieval/agent.py` với hai tool:

- `semantic_search_papers`
- `lookup_paper`

LLM provider hỗ trợ: Gemini, OpenAI, Anthropic, OpenRouter, Ollama và custom OpenAI-compatible endpoint.

## 6. Evaluation set và metrics

Bộ test được sinh từ 8 paper đầu tiên của cleaned dataset. Mỗi paper tạo 4 loại câu hỏi:

- `summary`
- `authors`
- `date`
- `categories`

Tổng số câu hỏi:

```text
8 papers x 4 question types = 32 samples
```

Metrics được tính:

- `retrieval_hit_rate`
- `mean_token_f1`
- `judge_accuracy`
- `mean_judge_score`
- `ragas`

Ragas hiện được skip theo mặc định và chỉ chạy khi bật `RUN_RAGAS=1`.

## 7. Kết quả baseline

Baseline pipeline đã chạy thành công và sinh các artifact:

- `data/results/baseline_metrics.json`
- `data/results/baseline_answers.json`
- `data/quality/baseline_quality.json`
- `data/quality/freshness_report.json`
- `data/reports/phase1_report.md`

Metrics baseline:

| Metric | Giá trị |
| --- | ---: |
| Samples | 32 |
| Retrieval hit rate | 1.0000 |
| Mean token F1 | 1.0000 |
| Judge accuracy | 1.0000 |
| Mean judge score | 5.0000 |

Data quality baseline:

| Check | Kết quả |
| --- | --- |
| Tổng số dòng | 24 |
| `paper_id` không null | PASS |
| `paper_id` unique | PASS |
| `title` không blank | PASS |
| `summary` không blank | PASS |
| `text_for_embedding` không blank | PASS |
| Summary >= 40 ký tự | PASS |
| Freshness threshold 180 ngày | PASS |

Freshness baseline:

| Chỉ số | Giá trị |
| --- | --- |
| Latest published | 2027-05-07 |
| Oldest published | 2026-12-01 |
| Stale rows | 0 |
| Missing published rows | 0 |
| Is fresh | true |

## 8. Corruption simulation

Module `src/ingestion/corruption.py` mô phỏng lỗi dữ liệu thường gặp trong pipeline:

| Operation | Số dòng ảnh hưởng |
| --- | ---: |
| Drop latest records | 2 |
| Blank summary | 3 |
| Inject summary noise | 3 |
| Truncate title | 3 |
| Stale publication date | 3 |
| Add duplicate rows | 2 |

Corruption log được lưu tại:

```text
data/results/corruption_log.json
```

Sau corruption:

- Số dòng ban đầu: 24
- Số dòng cuối: 24
- Blank summary rows: 3
- Duplicate `paper_id` rows: 2

## 9. Tác động của corrupted data

Khi đánh giá lại trên corrupted dataset, hiệu năng giảm rõ rệt:

| Metric | Baseline | Corrupted | Mức giảm |
| --- | ---: | ---: | ---: |
| Retrieval hit rate | 1.0000 | 0.7500 | -0.2500 |
| Mean token F1 | 1.0000 | 0.6955 | -0.3045 |
| Judge accuracy | 1.0000 | 0.6875 | -0.3125 |
| Mean judge score | 5.0000 | 3.7500 | -1.2500 |

Data quality corrupted bị fail ở các check:

- `paper_id_unique`
- `summary_not_blank`
- `summary_min_length`
- `freshness_threshold`

Freshness corrupted:

| Chỉ số | Giá trị |
| --- | --- |
| Latest published | 2026-12-31 |
| Oldest published | 2023-12-29 |
| Stale rows | 3 |
| Missing published rows | 0 |
| Is fresh | false |

Nhận xét: các lỗi blank summary, duplicate ID, stale date và xóa record mới làm giảm khả năng retrieval đúng tài liệu, đồng thời làm câu trả lời bị thiếu hoặc lệch so với ground truth.

## 10. Repair và phục hồi chất lượng

Repair flow rebuild lại cleaned dataset từ raw source snapshot ban đầu:

- Raw snapshot: `data/raw/crossref_records.json`
- Repaired clean CSV: `data/clean/papers_clean_repaired.csv`
- Repaired clean JSON: `data/clean/papers_clean_repaired.json`
- Repaired metrics: `data/results/repaired_metrics.json`
- Repaired quality: `data/quality/repaired_quality.json`

Metrics sau repair:

| Metric | Corrupted | Repaired | Kết quả |
| --- | ---: | ---: | --- |
| Retrieval hit rate | 0.7500 | 1.0000 | Phục hồi |
| Mean token F1 | 0.6955 | 1.0000 | Phục hồi |
| Judge accuracy | 0.6875 | 1.0000 | Phục hồi |
| Mean judge score | 3.7500 | 5.0000 | Phục hồi |

Data quality repaired:

- Tổng số dòng: 24
- Failed checks: không có
- Stale rows: 0
- Is fresh: true

Kết quả này chứng minh rằng khi dữ liệu được repair từ raw snapshot sạch, chất lượng data checks và hiệu năng RAG đều phục hồi về mức baseline.

## 11. Data observability

Dự án đã có các lớp observability sau:

- Quality checks ở `src/observability/quality.py`.
- Freshness report theo ngưỡng 180 ngày.
- Markdown report ở `src/observability/reporting.py`.
- Dashboard Streamlit để xem artifact, metrics, quality, freshness và corruption log.

Các báo cáo chính:

- `data/reports/phase1_report.md`
- `data/reports/corruption_report.md`
- `data/reports/progress_report.md`
- `report.md`

Dashboard hiển thị:

- Số lượng raw/clean/eval samples.
- Metrics baseline/corrupted/repaired.
- Bảng quality summary.
- Bảng freshness.
- Markdown reports.
- Corruption operations.

## 12. Đánh giá theo rubric

| Mục | Nhận xét | Ước lượng |
| --- | --- | ---: |
| Code structure và organization | Module rõ ràng, đúng đề bài | Tốt |
| Raw data ingestion | Fetch, parse, deduplicate, lưu raw đầy đủ | Tốt |
| Cleaning và data modeling | Schema rõ, có `text_for_embedding`, date/freshness fields | Tốt |
| Embedding và vector store | MiniLM + ChromaDB hoạt động, có manifest | Tốt |
| Agent và multi-provider LLM | Có abstraction provider và LangChain agent tools | Tốt |
| Evaluation và scoring | 32 samples, metrics/answers đầy đủ | Tốt |
| Data observability | Quality/freshness/report/dashboard đầy đủ | Tốt |
| Corruption và comparison | Có corrupted/repaired metrics và impact rõ | Tốt |

## 13. Hạn chế và lưu ý

- Ragas chưa chạy trong artifact hiện tại vì `RUN_RAGAS` chưa được bật.
- Dự án có dependency `great-expectations`, nhưng quality checks hiện tại là lightweight checks tự viết, chưa có expectation suite GX hoàn chỉnh trong `data/quality/gx/`.
- Chưa thấy bộ test tự động kiểu `pytest`; nếu cần bonus có thể bổ sung test cho cleaning, corruption và metrics.
- Artifact hiện có chứa một số ngày publish trong tương lai so với ngày kiểm tra 10/06/2026. Code đang dùng `age_days = max(0, ...)`, nên các record này vẫn được xem là fresh.
- Không nên commit `.env` nếu có API key thật. File `.env.example` nên được dùng làm mẫu cấu hình.

## 14. Kết luận

Dự án đã hoàn thành đầy đủ luồng chính của Lab 10. Baseline pipeline tạo được dữ liệu sạch, embedding index, test set, metrics và quality/freshness report. Corruption flow mô phỏng lỗi dữ liệu có ý nghĩa và chứng minh được tác động xấu lên hiệu năng RAG. Repair flow rebuild từ raw snapshot và phục hồi cả metrics lẫn data quality về mức baseline.

Kết quả quan trọng nhất:

| Run | Retrieval hit rate | Mean token F1 | Judge accuracy | Quality |
| --- | ---: | ---: | ---: | --- |
| Baseline | 1.0000 | 1.0000 | 1.0000 | PASS |
| Corrupted | 0.7500 | 0.6955 | 0.6875 | FAIL |
| Repaired | 1.0000 | 1.0000 | 1.0000 | PASS |

Với artifact hiện tại, bài lab đáp ứng tốt yêu cầu về data pipeline, RAG evaluation, data observability, corruption impact analysis và repair comparison.
