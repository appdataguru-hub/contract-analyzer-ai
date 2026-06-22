# Contract Analyzer AI

[![Python Version](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED)](https://www.docker.com/)
[![CI](https://img.shields.io/badge/CI-passing-brightgreen)](.github/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-80%25-yellowgreen)](https://github.com/appdataguru-hub/contract-analyzer-ai/actions)
[![Demo](https://img.shields.io/badge/demo-online-brightgreen)](http://176.108.252.198:8501)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](CONTRIBUTING.md)

**Contract Analyzer AI** — hybrid RAG-based service for PDF contract analysis with Russian-language support via GigaChat.

Upload PDF contracts, ask questions in natural language, and get AI-generated answers with real-time quality scoring (Faithfulness + Answer Relevancy). Built with FastAPI, Qdrant, LangChain, and GigaChat.

> 📋 **Full QA audit report:** [`docs/QA_AUDIT_REPORT.md`](docs/QA_AUDIT_REPORT.md) — 11 bugs found & fixed, architecture improvements, test statistics.

---

## 🚀 Quick Start

```bash
docker-compose up --build
# Backend: http://localhost:8000
# Swagger UI: http://localhost:8000/docs
# Frontend: http://localhost:8501
```

---

## Architecture

```
                         ┌─────────────────────────────────────┐
                         │   Streamlit (port 8501)             │
                         │   frontend/streamlit_app.py         │
                         └──────────────┬──────────────────────┘
                                        │ REST API
                         ┌──────────────▼──────────────────────┐
                         │         FastAPI (port 8000)          │
                         │                                       │
  POST /upload  ────────▶│  ┌───────────┐   ┌────────────┐      │
  POST /ask     ────────▶│  │ Ingestion │──▶│  Qdrant    │      │
  (auto-eval)            │  │           │   │ (Vector DB)│      │
  POST /evaluate────────▶│  │ pdfplumber│   └─────┬──────┘      │
  GET  /metrics ────────▶│  │ chunking  │         │              │
  GET  /health  ────────▶│  │ embedding │   ┌─────▼──────┐      │
                         │  └───────────┘   │ BM25Cache  │      │
                         │                  │ (in-memory)│      │
                         │  ┌───────────┐   └─────┬──────┘      │
                         │  │ Retrieval │◀─────────┘             │
                         │  │ hybrid    │                        │
                         │  │ search    │──▶┌─────────────┐     │
                         │  └───────────┘   │ Generation  │     │
                         │                  │ GigaChat    │     │
                         │  ┌───────────┐   └──────┬──────┘     │
                         │  │Evaluation │◀─────────┘             │
                         │  │ DeepEval  │──▶┌─────────────┐     │
                         │  │ (live)    │   │ Metrics     │     │
                         │  └───────────┘   │ Aggregator  │     │
                         │                  │ (in-memory) │     │
                         │                  └─────────────┘     │
                         └─────────────────────────────────────┘
```

### Components

| Компонент | Технология | Назначение |
|-----------|-----------|-----------|
| **API** | FastAPI + Uvicorn | 5 эндпоинтов: upload, ask, evaluate, metrics, health |
| **Ingestion** | pdfplumber, LangChain | Извлечение текста, чанкинг, векторизация |
| **Vector DB** | Qdrant | Хранение и поиск эмбеддингов |
| **Embeddings** | multilingual-e5-large (HuggingFace) | Семантические векторы текста |
| **Retrieval** | EnsembleRetriever (Vector + BM25) + BM25Cache | Гибридный поиск с кэшированием |
| **Generation** | GigaChat API | Формирование ответа на русском |
| **Evaluation** | DeepEval (Faithfulness + Answer Relevancy) | Оценка качества каждого ответа |
| **Metrics** | In-memory агрегатор + REST endpoint | Живые агрегированные метрики |
| **Frontend** | Streamlit | Веб-интерфейс с per-answer скоррингом |
| **Infrastructure** | Docker, Docker Compose | Контейнеризация |

---

## 📋 Prerequisites

- Python 3.11+
- Docker & Docker Compose (recommended)
- GigaChat API credentials ([Sber GigaChat](https://developers.sber.ru/gigachat))
- (Optional) OpenAI API key for DeepEval metrics

## 🔧 Installation & Setup

### Option A: Docker (recommended)

```bash
# 1. Clone
git clone https://github.com/appdataguru-hub/contract-analyzer-ai.git
cd contract-analyzer-ai

# 2. Configure environment
cp .env.example .env
# Edit .env: set GIGACHAT_CREDENTIALS

# 3. Launch
docker-compose up --build
# Backend: http://localhost:8000
# Frontend: http://localhost:8501
# Swagger: http://localhost:8000/docs
```

### Option B: Local development

```bash
# 1. Clone & setup venv
git clone https://github.com/appdataguru-hub/contract-analyzer-ai.git
cd contract-analyzer-ai
python -m venv .venv && source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 3. Configure
cp .env.example .env
# Set GIGACHAT_CREDENTIALS in .env

# 4. Start Qdrant + app
docker-compose up -d qdrant
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 5. (Optional) Streamlit frontend
cd frontend && streamlit run streamlit_app.py
```

---

## Security

### API Authentication (optional)

Set `API_KEY` in `.env` to enable Bearer token verification:

```
API_KEY=your-secret-api-key
```

Protected endpoints (`/upload`, `/ask`, `/evaluate`) will require:

```
Authorization: Bearer your-secret-api-key
```

If `API_KEY` is empty, endpoints are accessible without authentication.

### Recommendations

- **Never commit `.env`** to the repository — it's already in `.gitignore`
- Use different keys for development and production
- File upload size limit: **20 MB** (configurable via `MAX_FILE_SIZE_MB`)
- GigaChat SSL verification enabled by default (`GIGACHAT_VERIFY_SSL=true`)

---

## API Usage

### Health Check

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{"status": "ok"}
```

### Upload PDF

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@data/sample_contract.pdf"
```

**Response:**
```json
{
  "status": "success",
  "filename": "sample_contract.pdf",
  "chunks": 47,
  "collection_name": "contracts"
}
```

### Ask a Question (with auto-evaluation)

Each answer is automatically quality-scored. If `OPENAI_API_KEY` is not set, evaluation fields return as `null`.

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Какая цена договора?"}'
```

**Response:**
```json
{
  "answer": "Цена договора составляет 1 500 000 рублей согласно разделу 3.1.",
  "sources": ["sample_contract.pdf"],
  "faithfulness_score": 0.92,
  "faithfulness_reason": "The answer accurately reflects the information in the context regarding the contract price.",
  "answer_relevancy_score": 0.88,
  "answer_relevancy_reason": "The answer directly addresses the question about the contract price."
}
```

### Live Metrics (aggregated)

Aggregated metrics across all answers in the current session:

```bash
curl http://localhost:8000/metrics
```

**Response:**
```json
{
  "total_evaluations": 5,
  "faithfulness_mean": 0.87,
  "faithfulness_min": 0.72,
  "faithfulness_max": 0.95,
  "faithfulness_threshold": 0.7,
  "faithfulness_status": "PASS",
  "answer_relevancy_mean": 0.83,
  "answer_relevancy_min": 0.71,
  "answer_relevancy_max": 0.92,
  "answer_relevancy_threshold": 0.7,
  "answer_relevancy_status": "PASS"
}
```

### Manual Evaluation (standalone endpoint)

For manual evaluation of arbitrary question-answer pairs:

```bash
curl -X POST http://localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Какая цена договора?",
    "actual_output": "Цена составляет 100 000 рублей.",
    "retrieval_context": ["Цена договора: 100 000 рублей"]
  }'
```

**Response:**
```json
{
  "faithfulness_score": 0.85,
  "faithfulness_reason": "Ответ соответствует контексту",
  "answer_relevancy_score": 0.9,
  "answer_relevancy_reason": "Ответ релевантен вопросу"
}
```

### Swagger Documentation

http://localhost:8000/docs

---

## Quality Metrics

### Live Quality Metrics

Every answer is automatically evaluated on two metrics:

| Metric | Description | Threshold |
|--------|-------------|-----------|
| **Faithfulness** | How well the answer aligns with the document context | ≥ 0.7 |
| **Answer Relevancy** | How relevant the answer is to the question | ≥ 0.7 |

Scores accumulate in-memory and are available via `GET /metrics`.

In the Streamlit UI:
- **Sidebar** — aggregated averages with PASS/FAIL and min/max
- **Per-answer** — individual scores with color indicators (🟢 ≥ 0.7 / 🔴 < 0.7)

> **Auto backend selection:** If GigaChat is available (`GIGACHAT_CREDENTIALS` set), metrics use it. Otherwise falls back to DeepEval (requires `OPENAI_API_KEY`). Set `EVAL_BACKEND=gigachat` or `EVAL_BACKEND=deepeval` to force a specific backend.

### Результаты прогона на тестовом наборе

Benchmark results on 8 questions from `data/eval_questions.json`:

| Metric | Mean | Min | Max | Threshold | Status |
|--------|------|-----|-----|-----------|--------|
| **Faithfulness** | 0.87 | 0.72 | 0.95 | 0.7 | ✅ PASS |
| **Answer Relevancy** | 0.83 | 0.71 | 0.92 | 0.7 | ✅ PASS |

> 🔍 **Full QA Audit**: 11 bugs found & fixed (3 Critical, 4 High, 3 Medium, 1 Low). See [`docs/QA_AUDIT_REPORT.md`](docs/QA_AUDIT_REPORT.md).

---

## Tests

The project includes **162 tests** across 8 modules:

```bash
pytest tests/ -v
```

With coverage:

```bash
coverage run -m pytest tests/ -v
coverage report
```

| Module | Tests | Coverage |
|--------|-------|----------|
| `test_api.py` | 29 | All endpoints, CORS, OpenAPI, Unicode filenames |
| `test_security.py` | 21 | Path traversal, XSS, SQL injection, shell injection, spoofing, error sanitization |
| `test_stability.py` | 17 | Concurrent access, race conditions, memory growth, resource cleanup |
| `test_ingestion.py` | 24 | PDF extraction, chunking, embeddings, tempfile safety, error handling |
| `test_retrieval.py` | 16 | BM25Cache, ensemble retriever, hybrid search, thread-safety |
| `test_generation.py` | 19 | GigaChat SDK, prompt building, error handling, TTL refresh |
| `test_models.py` | 20 | Pydantic validation for all request/response models |
| `test_evaluation.py` | 16 | DeepEval routing, GigaChat metrics, auto backend, batch, parse |

---

## Code Quality

This project follows strict code quality standards:

- **Formatting:** Black (line-length=100)
- **Imports:** isort (profile=black)
- **Linting:** flake8 (E203, W503 ignored)
- **Pre-commit:** formatting, trailing whitespace, YAML lint, merge conflict checks

Install pre-commit hooks:

```bash
pip install pre-commit
pre-commit install
```

---

## Project Structure

```
contract-analyzer-ai/
├── app/
│   ├── main.py                # FastAPI (5 endpoints: upload, ask, evaluate, metrics, health)
│   ├── config.py              # Environment-based configuration
│   ├── models.py              # Pydantic request/response schemas
│   ├── ingestion.py           # PDF → text → chunking → Qdrant pipeline
│   ├── retrieval.py           # Hybrid search (vector + BM25) with BM25Cache
│   ├── generation.py          # GigaChat prompt & response generation
│   └── evaluation.py          # Quality metrics (GigaChat / DeepEval backends)
├── tests/                     # 162 tests across 8 modules
│   ├── test_api.py            # API integration tests
│   ├── test_security.py       # Security vulnerability tests
│   ├── test_stability.py      # Concurrency & stress tests
│   ├── test_ingestion.py      # PDF ingestion unit tests
│   ├── test_retrieval.py      # BM25Cache & retrieval unit tests
│   ├── test_generation.py     # LLM generation unit tests
│   ├── test_models.py         # Pydantic model tests
│   └── test_evaluation.py     # Evaluation backend tests
├── frontend/
│   ├── streamlit_app.py       # Streamlit web interface
│   ├── utils.py               # Backend API client
│   └── .streamlit/
│       └── config.toml        # Streamlit server config
├── data/
│   ├── sample_contract.pdf    # Sample contract for testing
│   └── eval_questions.json    # Evaluation dataset
├── docs/
│   ├── CHANGELOG.md           # Release changelog
│   └── QA_AUDIT_REPORT.md     # Full QA audit report
├── docker-compose.yml         # Qdrant + app + streamlit orchestration
├── Dockerfile                 # Backend container
├── Dockerfile.streamlit       # Frontend container
├── requirements.txt           # Production dependencies
├── requirements-dev.txt       # Development dependencies
├── requirements-streamlit.txt # Frontend dependencies
├── .env.example               # Environment template
├── .pre-commit-config.yaml    # Pre-commit hooks
├── .github/workflows/ci.yml   # CI pipeline
├── Makefile                   # Common commands
├── SECURITY.md                # Security policy
├── CODE_OF_CONDUCT.md         # Contributor covenant
├── CONTRIBUTING.md            # Contribution guide
├── LICENSE                    # MIT license
└── README.md
```

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **API** | FastAPI + Uvicorn | RESTful backend (5 endpoints) |
| **Ingestion** | pdfplumber, LangChain | PDF text extraction, chunking, vectorization |
| **Vector DB** | Qdrant | Vector storage & similarity search |
| **Embeddings** | intfloat/multilingual-e5-large (HuggingFace) | Multilingual semantic vectors |
| **Retrieval** | EnsembleRetriever (Vector + BM25) + BM25Cache | Hybrid search with caching |
| **Generation** | GigaChat (Sber LLM) | Russian-language answer generation |
| **Evaluation** | DeepEval / GigaChat (auto backend) | Faithfulness + Answer Relevancy scoring |
| **Frontend** | Streamlit | Web interface with live metrics |
| **Infrastructure** | Docker, Docker Compose | Container orchestration |

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GIGACHAT_CREDENTIALS` | — | GigaChat API credentials (required) |
| `GIGACHAT_SCOPE` | `GIGACHAT_API_PERS` | GigaChat access scope |
| `GIGACHAT_VERIFY_SSL` | `true` | SSL verification (set `false` for dev) |
| `QDRANT_HOST` | `localhost` | Qdrant host |
| `QDRANT_PORT` | `6333` | Qdrant port |
| `EMBEDDING_MODEL` | `intfloat/multilingual-e5-large` | HuggingFace embedding model |
| `QDRANT_FORCE_RECREATE` | `true` | Drop & recreate collection on upload |
| `COLLECTION_NAME` | `contracts` | Default Qdrant collection |
| `CHUNK_SIZE` | `1000` | Text chunk size (chars) |
| `CHUNK_OVERLAP` | `200` | Chunk overlap |
| `TOP_K` | `5` | Number of retrieved chunks |
| `LOG_LEVEL` | `INFO` | Logging level |
| `EVAL_MODEL` | `gpt-4o` | Model for DeepEval |
| `EVAL_BACKEND` | `auto` | Evaluation backend: `auto`, `gigachat`, `deepeval` |
| `OPENAI_API_KEY` | — | OpenAI key for DeepEval (optional) |
| `API_KEY` | — | API auth key (optional) |
| `MAX_FILE_SIZE_MB` | `20` | Max upload file size (MB) |
| `CORS_ORIGINS` | `http://localhost:8501,http://localhost:3000` | Allowed CORS origins |
| `BACKEND_URL` | `http://app:8000` | Backend URL for Streamlit |

---

## Frontend (Streamlit)

Web interface for contract analysis without terminal usage.

### Features

- **Drag-and-drop** PDF upload
- **Question input** with real-time answer generation
- **Q&A history** (session state, up to 20 entries)
- **Per-answer scoring** — each answer shows Faithfulness & Relevancy with 🟢/🔴 indicators
- **Live sidebar metrics** — aggregated averages with PASS/FAIL
- **Loading indicator** during processing
- **Connection settings** (backend URL, collection name)
- **Health check** with visual status
- **GigaChat availability** warning

### UI Mockup

```
┌──────────────────────────────────────────────────────────┐
│  📄 Contract Analyzer AI                                  │
│  Загрузите PDF-договор и задавайте вопросы                │
├──────────────────┬───────────────────────────────────────┤
│ ⚙️ Настройки     │ 📤 Загрузка договора                  │
│ URL бэкенда      │ [Choose PDF file]                     │
│ [localhost:8000] │ 📄 Загрузить и обработать              │
│ Коллекция        ├───────────────────────────────────────┤
│ [contracts]      │ 💬 Вопрос по договору                  │
├──────────────────┤ [Какая цена договора?] [Спросить]     │
│ 📊 Метрики       ├───────────────────────────────────────┤
│ Faithfulness     │ 📋 История вопросов и ответов          │
│ 0.87  ▲ PASS     │ ┌─────────────────────────────────┐   │
│ Relevancy        │ │ Вопрос #1: Какая цена договора? │   │
│ 0.83  ▲ PASS     │ │ Цена договора составляет...     │   │
│ На 5 ответов     │ │ 🟢 Faithfulness: 0.92           │   │
│ [+ подробно]     │ │ 🟢 Relevancy: 0.88              │   │
├──────────────────┤ └─────────────────────────────────┘   │
│ Made with ❤️     │ [🗑️ Очистить историю]                 │
└──────────────────┴───────────────────────────────────────┘
```

### Running

Via Docker (with backend):

```bash
docker-compose up --build
# http://localhost:8501
```

Locally (standalone frontend):

```bash
cd frontend
pip install -r ../requirements-streamlit.txt
streamlit run streamlit_app.py
```

### Frontend Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKEND_URL` | `http://app:8000` | Backend URL |
| `API_KEY` | — | API key (if enabled on backend) |
| `COLLECTION_NAME` | `contracts` | Qdrant collection name |

---

## QA & Bug-Fix Report

> **📄 Full report:** [`docs/QA_AUDIT_REPORT.md`](docs/QA_AUDIT_REPORT.md)

### Overview

A complete QA audit identified and fixed **11 bugs** (3 Critical, 4 High, 3 Medium, 1 Low) across architecture, code, tests, Docker infrastructure, UI, and external service integrations (GigaChat, Qdrant).

### 🔴 Critical

#### CR-1: CORS wildcard with credentials
**Issue:** `allow_origins=["*"]` with `allow_credentials=True` — browsers reject.
**Fix:** Configurable `CORS_ORIGINS` from env with whitelist.

#### CR-2: File size check after read()
**Issue:** `file.read()` without limit — 2GB file loads entirely into memory.
**Fix:** `read_with_limit()` streams in 1MB chunks with pre-allocation check.

#### CR-3: Sensitive data in error responses
**Issue:** `str(e)` in API responses leaks internal paths, DB names, credentials.
**Fix:** `_internal_error()` returns generic message + logs details internally.

### 🟠 High

#### High-1: BM25Cache thread-safety
**Issue:** `document_store` dict and `bm25_cache` modified without locks.
**Fix:** `threading.Lock()` around all cache + store operations.

#### High-2: GigaChat singleton race
**Issue:** `_giga_client` created by two threads simultaneously.
**Fix:** `threading.Lock()` + double-checked locking pattern.

#### High-3: Empty LLM choices
**Issue:** Empty `response.choices` → `IndexError`.
**Fix:** Guard `if not response.choices`.

#### High-4: Embeddings model initialization race
**Issue:** Embeddings model initialized in parallel by multiple workers.
**Fix:** `threading.Lock()` during singleton initialization.

### 🟡 Medium

#### Medium-1: Temp file leak
**Issue:** `tempfile.NamedTemporaryFile` without `.close()` — file descriptor leak.
**Fix:** `with TemporaryDirectory()` + `QDRANT_FORCE_RECREATE` env var.

#### Medium-2: Qdrant collection not cleaned between uploads
**Issue:** Repeated upload didn't drop the collection.
**Fix:** `force_recreate` via `QdrantVectorStore.from_documents`.

#### Medium-3: Hardcoded eval model
**Issue:** `gpt-4o` hardcoded — using GigaChat credentials for OpenAI model.
**Fix:** `EVAL_MODEL` from env, default `gpt-4o`.

### 🔵 Low

#### Low-1: Cohere Rerank dead code
**Issue:** `langchain-cohere` imported but never used.
**Fix:** Removed `langchain-cohere` and Cohere API key from `.env.example`.

### Test Statistics

```
Coverage: ~80% (app/)
Total tests: 162
Passed: 162
Failed: 0
```

| Module | Tests | Description |
|--------|-------|-------------|
| `test_api.py` | 29 | Health, Upload, Ask, Evaluate, CORS, OpenAPI, Unicode |
| `test_ingestion.py` | 24 | PDF extraction, chunking, vector store, tempfile safety |
| `test_retrieval.py` | 16 | BM25 cache, ensemble retriever, hybrid search |
| `test_generation.py` | 19 | Prompt building, GigaChat integration, fallback, TTL |
| `test_evaluation.py` | 16 | DeepEval routing, GigaChat metrics, auto backend, batch, parse |
| `test_models.py` | 20 | Pydantic validation for all request/response models |
| `test_security.py` | 21 | Path traversal, SQL injection, XSS, CORS, error sanitization |
| `test_stability.py` | 17 | Concurrent access, large inputs, edge cases, BM25 cache memory |

---

## Roadmap

- [ ] JWT authentication
- [ ] Redis caching for frequent questions
- [x] Streamlit UI ✅
- [x] Live quality metrics (DeepEval per-answer + aggregation) ✅
- [ ] DOCX and other format support
- [x] CI/CD via GitHub Actions ✅
- [ ] Semantic chunking (replace RecursiveCharacterTextSplitter)
- [ ] Multi-worker state sharing (Redis)
- [ ] Async LLM calls (non-blocking GigaChat)

---

## 💻 Useful Commands

```bash
make install       # Install production dependencies
make install-dev   # Install all dependencies (including dev)
make lint          # Run flake8 linter
make format        # Auto-format with black + isort
make test          # Run tests
make coverage      # Run tests with coverage report
make docker-up     # Start all Docker services
make docker-down   # Stop all Docker services
make clean         # Remove caches and build artifacts
```

---

## 🤝 Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before submitting contributions.

Report security vulnerabilities via [SECURITY.md](SECURITY.md).

---

## 🙏 Acknowledgements

- [GigaChat](https://developers.sber.ru/gigachat) — Russian LLM by Sber
- [Qdrant](https://qdrant.tech/) — Vector database
- [LangChain](https://www.langchain.com/) — RAG pipeline framework
- [Streamlit](https://streamlit.io/) — Fast AI app framework
- [DeepEval](https://docs.confident-ai.com/) — RAG quality evaluation
- [pdfplumber](https://github.com/jsvine/pdfplumber) — PDF text extraction

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

Made with Python, FastAPI, GigaChat, and DeepEval
