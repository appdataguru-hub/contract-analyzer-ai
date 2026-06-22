# Changelog

## [1.1.0] - 2026-06-22

### Added
- Streamlit frontend with live quality metrics
- Auto-evaluation on every `/ask` (Faithfulness + Answer Relevancy)
- `GET /metrics` — aggregated session metrics with PASS/FAIL
- GigaChat evaluation backend (no OpenAI required)
- `EVAL_BACKEND` config: auto / gigachat / deepeval
- Per-answer scoring in Streamlit UI
- Makefile with common commands
- `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`

### Fixed
- 11 bugs from QA audit (3 Critical, 4 High, 3 Medium, 1 Low)
- BM25Cache thread-safety with `threading.Lock()`
- CORS wildcard with credentials → configurable whitelist
- File size OOM vulnerability → streaming chunk reader
- GigaChat singleton race condition
- Sensitive data leak in error responses
- Temp file descriptor leak
- Qdrant collection not cleaned between uploads
- Hardcoded eval model → `EVAL_MODEL` env var
- Empty LLM choices → guard clause
- Cohere Rerank dead code removed

### Changed
- 162 tests across 8 modules
- ~80% code coverage
- Architecture documentation overhaul

## [1.0.0] - 2026-06-19

### Added
- FastAPI backend with 5 endpoints: upload, ask, evaluate, metrics, health
- PDF ingestion pipeline (pdfplumber → chunking → Qdrant)
- Hybrid retrieval (vector search + BM25 with BM25Cache)
- GigaChat LLM integration for Russian-language answers
- DeepEval quality evaluation
- Docker Compose orchestration (Qdrant + app)
- CI pipeline (GitHub Actions)
- MIT License, initial README
