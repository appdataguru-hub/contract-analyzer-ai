# Contract Analyzer AI — Архитектурный отчёт

**Дата:** 2026-06-22
**Версия:** 1.0.0
**Уровень:** Senior Architecture & Development Review

---

## 1. Executive Summary

Contract Analyzer AI — production-ready RAG (Retrieval-Augmented Generation) сервис для анализа русскоязычных договоров. Реализует полный цикл: загрузка PDF → извлечение текста → гибридный retrieval (векторный + BM25) → генерация ответа через GigaChat → live-оценка качества.

**Оценка зрелости: 8.5/10** — проект близок к production, но имеет архитектурные ограничения, требующие внимания (см. раздел 6).

---

## 2. Архитектура системы

### 2.1 Компонентная диаграмма

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                                     │
│  ┌──────────────────────┐    ┌──────────────────────────────────────┐   │
│  │   Streamlit UI       │    │   curl / HTTP Client / Swagger UI    │   │
│  │   (port 8501)        │    │   (port 8000)                        │   │
│  └──────────┬───────────┘    └────────────────┬─────────────────────┘   │
└─────────────┼────────────────────────────────┼──────────────────────────┘
              │                                │
              │         REST (JSON/HTTP)        │
              ▼                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        API LAYER (FastAPI)                              │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  app/main.py                                                    │   │
│  │                                                                 │   │
│  │  GET  /health   ───  Health check                              │   │
│  │  POST /upload   ───  Upload PDF + ① Ingestion Pipeline          │   │
│  │  POST /ask      ───  Question  + ② Retrieval + ③ Generation    │   │
│  │  POST /evaluate ───  Manual evaluation (④ Evaluation)           │   │
│  │  GET  /metrics  ───  Aggregated live metrics                    │   │
│  │                                                                 │   │
│  │  Security: read_with_limit() | _internal_error() | verify_api   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
              │                        ▲
              │  internal calls        │
              ▼                        │
┌─────────────────────────────────────────────────────────────────────────┐
│                       SERVICE LAYER                                     │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │ ① Ingestion  │  │ ② Retrieval  │  │ ③ Generation │  │ ④ Evalua-  │  │
│  │  ingestion.py │  │  retrieval.py│  │  generation  │  │  tion      │  │
│  │               │  │              │  │  .py         │  │ evalua-    │  │
│  │ pdfplumber    │  │ BM25Cache    │  │ GigaChat SDK │  │ tion.py    │  │
│  │ RecursiveText │  │ QdrantVector │  │ TTL=1500s    │  │            │  │
│  │ Splitter      │  │ Ensemble     │  │ Fallback:    │  │ GigaChat   │  │
│  │ HuggingFace   │  │ Retriever    │  │ raw chunks   │  │ or DeepEval│  │
│  │ Embeddings    │  │ (0.5/0.5)    │  │              │  │ (auto)     │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬─────┘  │
└─────────┼─────────────────┼─────────────────┼─────────────────┼────────┘
          │                 │                 │                 │
          ▼                 ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     INFRASTRUCTURE LAYER                                │
│                                                                         │
│  ┌────────────────────┐  ┌──────────────────┐  ┌───────────────────┐   │
│  │  Qdrant (port 6333)│  │  GigaChat API    │  │  DeepEval         │   │
│  │  Vector DB         │  │  (Сбер LLM)      │  │  (gpt-4o /        │   │
│  │  Collection:       │  │  Russian-optimized│  │   OpenAI proxy)   │   │
│  │  contracts         │  │                  │  │                   │   │
│  └────────────────────┘  └──────────────────┘  └───────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Docker / Docker Compose                                       │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                     │   │
│  │  │ qdrant   │  │ app      │  │ streamlit│                     │   │
│  │  │ container│  │ container│  │ container│                     │   │
│  │  └──────────┘  └──────────┘  └──────────┘                     │   │
│  │  Volumes: qdrant_storage/ | data/ | frontend/                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow: Upload

```
Client                    FastAPI                         Qdrant              BM25Cache
  │                         │                               │                   │
  │  POST /upload (PDF)     │                               │                   │
  │────────────────────────▶│                               │                   │
  │                         │                               │                   │
  │                    ① read_with_limit()                  │                   │
  │                    (streaming, 1MB chunks)              │                   │
  │                         │                               │                   │
  │                    ② file.filename check: .pdf          │                   │
  │                         │                               │                   │
  │                    ③ extract_text_from_pdf_bytes()      │                   │
  │                       ├─ tempfile.TemporaryDirectory()  │                   │
  │                       ├─ pdfplumber.open()              │                   │
  │                       └─ page.extract_text()            │                   │
  │                         │                               │                   │
  │                    ④ RecursiveCharacterTextSplitter     │                   │
  │                       chunk_size=1000, overlap=200      │                   │
  │                         │                               │                   │
  │                    ⑤ HuggingFaceEmbeddings              │                   │
  │                       multilingual-e5-large             │                   │
  │                         │                               │                   │
  │                    ⑥ QdrantVectorStore.from_documents() │                   │
  │                         │──────────────────────────────▶│                   │
  │                         │         store vectors          │                   │
  │                         │◀──────────────────────────────│                   │
  │                         │                               │                   │
  │                    ⑦ lock acquire                       │                   │
  │                       document_store[col] = {docs, vs}  │                   │
  │                       bm25_cache.invalidate(col)         │──────────────────│▶
  │                       lock release                      │                   │
  │                         │                               │                   │
  │  ◄─────────────────────│                               │                   │
  │  {status, filename,    │                               │                   │
  │   chunks, collection}  │                               │                   │
```

### 2.3 Data Flow: Ask

```
Client                    FastAPI                         Qdrant      BM25Cache   GigaChat
  │                         │                               │           │           │
  │  POST /ask (question)   │                               │           │           │
  │────────────────────────▶│                               │           │           │
  │                         │                               │           │           │
  │                    ① document_store[col] exists?        │           │           │
  │                         │                               │           │           │
  │                    ② hybrid_search()                    │           │           │
  │                       ├─ get_vector_store()             │           │           │
  │                       │  └─ similarity search  ────────▶│           │           │
  │                       │     return vector results ◀─────│           │           │
  │                       │                                 │           │           │
  │                       ├─ BM25Cache.get_or_build()       │           │           │
  │                       │  └─ BM25Retriever.invoke()      │──────────▶│           │
  │                       │     return bm25 results ◀───────│           │           │
  │                       │                                 │           │           │
  │                       └─ EnsembleRetriever (0.5/0.5)    │           │           │
  │                          merge & rank results           │           │           │
  │                         │                               │           │           │
  │                    ③ context = retrieved docs           │           │           │
  │                         │                               │           │           │
  │                    ④ generate_answer(question, context) │           │           │
  │                       ├─ build_prompt()                 │           │           │
  │                       │  [system + context + question]  │           │           │
  │                       ├─ _get_client() [TTL check]      │           │           │
  │                       └─ client.chat(payload) ──────────│──────────│──────────▶│
  │                          return answer ◀────────────────│──────────│──────────◀│
  │                         │                               │           │           │
  │                        ⚠ On GigaChat failure:           │           │           │
  │                        generate_answer_fallback()        │           │           │
  │                        (raw chunks + warning)           │           │           │
  │                         │                               │           │           │
  │                    ⑤ evaluate_response() [auto]         │           │           │
  │                       ├─ _evaluate_with_gigachat()      │           │           │
  │                       │  └─ SCORE/REASON parse ◀────────│──────────│──────────▶│
  │                       │                                 │           │           │
  │                       └─ _evaluate_with_deepeval()      │           │           │
  │                          └─ DeepEval (Faithfulness +    │           │           │
  │                             AnswerRelevancy)            │           │           │
  │                         │                               │           │           │
  │                    ⑥ _metrics_store append [LOCK]       │           │           │
  │                         │                               │           │           │
  │  ◄─────────────────────│                               │           │           │
  │  {answer, sources,     │                               │           │           │
  │   faithfulness,        │                               │           │           │
  │   relevancy}           │                               │           │           │
```

---

## 3. Детальный разбор компонентов

### 3.1 API Layer (`app/main.py`)

**Эндпоинты:**

| Эндпоинт | Метод | Request | Response | Сложность |
|---|---|---|---|---|
| `/health` | GET | — | `{"status": "ok"}` | O(1) |
| `/upload` | POST | `UploadFile` (PDF) | `{status, filename, chunks, collection}` | O(n) где n — размер PDF |
| `/ask` | POST | `{question, collection_name?}` | `{answer, sources, faithfulness*, relevancy*}` | O(m × log k) retrieval + O(LLM) generation |
| `/evaluate` | POST | `{question, actual_output, retrieval_context, expected_output?}` | `{faithfulness*, relevancy*}` | O(LLM) |
| `/metrics` | GET | — | `{total_evaluations, faithfulness_mean*, relevancy_mean*, ...}` | O(1) |

**Ключевые архитектурные решения:**

1. **`read_with_limit()`** — Streaming read with 1MB chunks + hard cap. Позволяет отклонить 10GB payload до аллокации памяти. Важный security паттерн для любого file upload endpoint.

2. **`_internal_error()`** — Generic error response + логирование. Предотвращает утечку internals (stack trace, пути, credentials). Должен быть стандартом для всех API.

3. **`document_store` + `_store_lock`** — In-memory dict с thread-safe доступом. **Архитектурный долг:** при multi-worker uvicorn процессы не разделяют состояние (см. раздел 6).

4. **`_metrics_store`** — In-memory накопление с `_metrics_lock`. Не персистентно — теряется при рестарте.

### 3.2 Ingestion Pipeline (`app/ingestion.py`)

```
PDF bytes
  │
  ▼
TemporaryDirectory() ──── auto-cleanup (context manager)
  │
  ▼
pdfplumber.open() ────── извлекает текст постранично
  │                     формат: "[Страница N]\n{text}"
  ▼
RecursiveCharacterTextSplitter
  chunk_size=1000
  chunk_overlap=200
  separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
  │
  ▼
list[Document] ───────── metadata: {source, chunk_index, chunk_count}
  │
  ├──▶ QdrantVectorStore.from_documents()
  │     embedding = HuggingFaceEmbeddings(multilingual-e5-large)
  │     force_recreate = True (configurable)
  │
  └──▶ document_store[collection] (for BM25 in retrieval)
```

**Singleton Embeddings:**
```python
get_embeddings()  # double-checked locking
    if _embeddings is None:
        with _embeddings_lock:
            if _embeddings is None:
                _embeddings = HuggingFaceEmbeddings(...)
```

**Риски:**
- `multilingual-e5-large` — ~2GB RAM на загрузку модели
- `RecursiveCharacterTextSplitter` не понимает семантику документа (разрывает таблицы, списки)
- `force_recreate=True` (по умолчанию) — каждый upload дропает коллекцию

### 3.3 Retrieval System (`app/retrieval.py`)

**Гибридный поиск:**

```
hybrid_search(question, documents, collection, k=TOP_K)
  │
  ├── Vector Search (semantic)
  │   └── QdrantVectorStore.as_retriever(search_type="similarity", k=TOP_K)
  │
  ├── BM25 Search (lexical)
  │   └── BM25Cache.get_or_build(collection, documents, k=TOP_K)
  │       ├── cached? → reuse (update k)
  │       └── not cached? → BM25Retriever.from_documents()
  │
  └── EnsembleRetriever(weights=[0.5, 0.5])
      └── Reciprocal Rank Fusion (RRF)
```

**BM25Cache — Thread-Safe Singleton:**

| Операция | Lock | Сложность |
|---|---|---|
| `get_or_build()` — cache hit | `_lock` | O(1) |
| `get_or_build()` — cache miss | `_lock` | O(d × l) — build BM25 |
| `invalidate()` | `_lock` | O(1) |

**EnsembleRetriever:** Использует `langchain_classic` (форк langchain 0.1.x). RRF с равными весами (0.5/0.5). Не конфигурируется через env.

### 3.4 Generation Pipeline (`app/generation.py`)

**System Prompt:**
```
Ты — эксперт по анализу договоров и юридических документов.
Отвечай на русском языке, используя только предоставленный контекст.
Если в контексте недостаточно информации — напиши:
'В предоставленном документе недостаточно информации для ответа на этот вопрос.'
Не выдумывай факты. Цитируй номера страниц из контекста, если они указаны.
```

**GigaChat Client Singleton:**

```python
_get_client()
    with _giga_lock:
        if _giga_client and (now - _giga_last_used) < 1500:  # TTL
            return _giga_client
        _giga_client = GigaChat(credentials=..., scope=..., verify_ssl_certs=...)
        _giga_last_used = now
        return _giga_client
```

**Parameters:**
- `temperature=0.3` — низкая креативность (юридическая точность)
- `max_tokens=2048` — достаточно для ответа по договору
- `model="GigaChat"` — стандартная модель Сбера

**Fallback механизм:**
```python
try:
    answer = generate_answer(question, context)
except Exception:
    answer = generate_answer_fallback(question, context)
    # "⚠️ GigaChat временно недоступен."
    # + raw fragments from context
```

### 3.5 Evaluation System (`app/evaluation.py`)

**Multi-backend архитектура:**

```
evaluate_response()
  │
  ├── backend == "gigachat"
  │   └── _evaluate_with_gigachat()
  │       ├── _gigachat_evaluate_metric(faithfulness)  → SCORE/REASON
  │       └── _gigachat_evaluate_metric(answer_relevancy) → SCORE/REASON
  │
  ├── backend == "deepeval"
  │   └── _evaluate_with_deepeval()
  │       ├── FaithfulnessMetric(threshold=0.7, model=EVAL_MODEL)
  │       └── AnswerRelevancyMetric(threshold=0.7, model=EVAL_MODEL)
  │
  └── backend == "auto" (default)
      └── try GigaChat → if None → fallback DeepEval
```

**GigaChat Eval Prompts:**

Faithfulness:
```
Оцени Faithfulness (фактическую точность) ответа относительно контекста.
Контекст документа: ...
Вопрос: ...
Ответ AI: ...
Проверь каждое утверждение — подтверждается ли оно контекстом.
Оценка 0.0-1.0.
Ответ строго: SCORE: <...> REASON: <...>
```

Answer Relevancy:
```
Оцени Answer Relevancy (релевантность) ответа относительно вопроса.
Вопрос: ...
Ответ AI: ...
Оцени, насколько ответ напрямую отвечает на вопрос.
Оценка 0.0-1.0.
Ответ строго: SCORE: <...> REASON: <...>
```

**Parser:**
```python
_parse_eval_response(text):
    re.search(r"SCORE:\s*([0-9]*\.?[0-9]+)", ...)   → float 0.0-1.0
    re.search(r"REASON:\s*(.+)", ...)                  → string
```

**Оценка дизайна:**
- ✅ Multi-backend с graceful degradation
- ✅ Парсинг SCORE/REASON — простой, но эффективный
- ⚠️ Два отдельных LLM вызова на одну оценку — latency ×2
- ⚠️ GigaChat eval использует `temperature=0.1` — хорошо для консистентности

### 3.6 Frontend (`frontend/streamlit_app.py`)

| Компонент | Функция | Описание |
|---|---|---|
| Sidebar | `render_sidebar()` | Live metrics, connection settings, health status |
| Upload | `render_upload_section()` | Drag-and-drop PDF, progress, status |
| Q&A | `render_qa_section()` | Question input, answer history, per-answer scoring |
| About | `tab2` | Project info, tech stack |

**State Management:** `st.session_state`:
- `backend_url`, `collection_name` — настройки подключения
- `history` — до 20 вопросов/ответов
- `upload_state` — статус загрузки
- `backend_connected`, `gigachat_warning` — статусные флаги

**Per-answer Scoring:**
```python
f_color = "🟢" if f_score >= 0.7 else "🔴"   # visual threshold
```

### 3.7 Config (`app/config.py`)

| Variable | Default | Type | Security Impact |
|---|---|---|---|
| `GIGACHAT_CREDENTIALS` | `""` | str | HIGH — LLM access |
| `GIGACHAT_VERIFY_SSL` | `true` | bool | MEDIUM — MITM risk if false |
| `QDRANT_HOST` | `localhost` | str | LOW |
| `EMBEDDING_MODEL` | `intfloat/multilingual-e5-large` | str | LOW |
| `TOP_K` | `5` | int | MEDIUM — retrieval quality |
| `MAX_FILE_SIZE_MB` | `20` | int | MEDIUM — DoS protection |
| `CORS_ORIGINS` | `localhost:8501,3000` | list[str] | HIGH — security boundary |
| `EVAL_BACKEND` | `auto` | str | LOW |
| `API_KEY` | `""` | str | HIGH — auth |

---

## 4. Анализ безопасности

### 4.1 Найденные и исправленные уязвимости (из QA Audit)

| ID | Severity | Вектор | Статус |
|---|---|---|---|
| CR-1 | **Critical** | CORS wildcard + credentials (браузеры блокируют) | ✅ Fixed |
| CR-2 | **Critical** | DoS через гигантский файл (OOM) | ✅ Fixed |
| CR-3 | **Critical** | Утечка внутренних путей / credentials в ошибках | ✅ Fixed |
| High-1 | **High** | Race condition в BM25Cache | ✅ Fixed |
| High-2 | **High** | Race condition в GigaChat singleton | ✅ Fixed |
| High-3 | **High** | IndexError на пустых choices LLM | ✅ Fixed |
| High-4 | **High** | Race condition в embeddings init | ✅ Fixed |
| Med-1 | **Medium** | Утечка temp file descriptors | ✅ Fixed |
| Med-2 | **Medium** | Qdrant collection overlap между uploads | ✅ Fixed |

### 4.2 Текущие security measures

- ✅ **Streaming read with cap** — защита от OOM
- ✅ **Error sanitization** — `_internal_error()` не светит stack trace
- ✅ **CORS whitelist** — из env (не `*`)
- ✅ **Optional API key** — Bearer token на `/upload`, `/ask`, `/evaluate`
- ✅ **Content-type check** — только `.pdf` расширение
- ✅ **Thread-safe синглтоны** — double-checked locking
- ✅ **Test coverage** — 21 security-тестов

### 4.3 Остающиеся риски

| Риск | Severity | Описание | Митигация |
|---|---|---|---|
| API key in .env | **High** | Credentials в plain text | Vault / KMS |
| No rate limiting | **Medium** | DDoS на LLM endpoint (дорогой) | slowapi / nginx rate limit |
| No audit log | **Medium** | Нет лога кто и когда задавал вопросы | Добавить middleware |
| No input sanitization | **Low** | XSS payload в question проходит (но не рендерится API) | HTML escape в ответах |
| In-memory secrets | **Medium** | GigaChat token живёт в памяти процесса | Short TTL (1500s) |

---

## 5. Тестовая инфраструктура

### 5.1 Покрытие (162 теста, 80% coverage)

| Модуль | Тестов | Type | Что покрывает |
|---|---|---|---|
| `test_api.py` | 29 | Integration | All 5 endpoints, CORS, OpenAPI, Unicode, response schema |
| `test_security.py` | 21 | Security | Path traversal, XSS, SQL inj, shell inj, null bytes, spoofing, error sanitization |
| `test_stability.py` | 17 | Stress | Concurrent 50x health, upload race, large inputs, BM25 memory, rapid uploads |
| `test_ingestion.py` | 24 | Unit | PDF extraction, chunking, embeddings, tempfile, empty/invalid PDFs |
| `test_retrieval.py` | 16 | Unit | BM25Cache hit/miss/invalidate, multi-collection, Russian text |
| `test_generation.py` | 19 | Unit | Prompt building, GigaChat AuthError, empty choices, TTL refresh |
| `test_models.py` | 20 | Unit | Pydantic: QuestionRequest, AnswerResponse, UploadResponse, Evaluate*, MetricsResponse |
| `test_evaluation.py` | 16 | Unit | DeepEval routing, GigaChat metrics, auto backend, batch, parse |

### 5.2 Test Fixtures (`conftest.py`)

- `client` — `TestClient(app)`
- `valid_pdf_bytes` / `valid_pdf_path` — синтетический PDF с текстом
- `corrupted_pdf_bytes` — битый PDF для error path
- `sample_documents` — 4 pre-built Document с русским текстом
- `clear_document_store` — autouse fixture, чистит state между тестами
- `mock_qdrant_and_gigachat` — полная изоляция внешних зависимостей
- `pdf_with_all_charset_filename` — unicode + кириллица + китайский

### 5.3 Tooling

```
black (line-length=100) → isort (profile=black) → flake8 (E203,W503 ignored)
    → pre-commit hooks → pytest (asyncio_mode=auto) → coverage (fail_under=80)
```

---

## 6. Архитектурные долги и рекомендации

### 6.1 🔴 Critical: Multi-worker State Sharing

**Проблема:** `document_store`, `_metrics_store`, и `BM25Cache._cache` — in-memory singletons. При запуске нескольких uvicorn workers (`--workers N`) каждый worker имеет своё состояние. Upload на worker 1 невидим для worker 2.

**Решение:**
```python
# Вместо in-memory dict:
document_store: dict[str, dict] = {}  # ❌ per-process

# Использовать Redis:
redis_client = Redis.from_url(...)
document_store = RedisDocumentStore(redis_client)  # ✅ shared
```
**Impact:** При одном worker — не актуально. При масштабировании — **blocker**.

### 6.2 🟠 High: Нет Persistence для Metrics

**Проблема:** `_metrics_store` теряется при рестарте. `data/metrics.json` — статический snapshot, не обновляется.

**Решение:** Писать метрики в Qdrant (как payload к collection) или в Redis с TTL.

### 6.3 🟠 High: GigaChat Auth Token Refresh

**Проблема:** `_get_client()` использует TTL 1500s. GigaChat access token может протухнуть раньше (зависит от скоупа). SDK может не обработать 401.

**Решение:**
```python
# Перехватывать 401 и делать retry с новым token
try:
    resp = client.chat(payload)
except GigaChatUnauthorizedError:
    _giga_client = None  # force re-init
    resp = _get_client().chat(payload)  # retry once
```

### 6.4 🟠 High: No Async LLM Calls

**Проблема:** `GigaChat.chat()` — синхронный. Блокирует event loop uvicorn. При 10 concurrent `/ask` — каждый ждёт своей очереди.

**Решение:**
```python
# Использовать asyncio.to_thread() или async GigaChat SDK
loop = asyncio.get_event_loop()
resp = await loop.run_in_executor(None, client.chat, payload)
```

### 6.5 🟡 Medium: Semantic Chunking

**Проблема:** `RecursiveCharacterTextSplitter` режет по символам — разрывает таблицы, списки, юридические clauses.

**Решение:** `SemanticChunker` (langchain-experimental) или LLM-based chunking:
```python
from langchain_experimental.text_splitter import SemanticChunker
semantic_splitter = SemanticChunker(embeddings, breakpoint_threshold_type="percentile")
```

### 6.6 🟡 Medium: No Caching

**Проблема:** Каждый `/ask` → LLM вызов. Одинаковые вопросы от разных users не кэшируются.

**Решение:** Redis cache с TTL (например, 1 час) для пар (question, collection) → answer.

### 6.7 🟡 Medium: Single Embedding Model

**Проблема:** `multilingual-e5-large` — хорош, но ~2GB RAM. Нет fallback, если модель не грузится.

**Решение:** Graceful degradation:
```python
try:
    model = "intfloat/multilingual-e5-large"
    embeddings = HuggingFaceEmbeddings(model_name=model)
except Exception:
    model = "sentence-transformers/all-MiniLM-L6-v2"  # fallback ~400MB
    embeddings = HuggingFaceEmbeddings(model_name=model)
```

### 6.8 🟢 Low: Streamlit + Backend Coupling

**Проблема:** `BACKEND_URL=http://176.108.252.198:8000` зашит в docker-compose. При смене хоста нужно менять в двух местах.

**Решение:** DNS name для бэкенда (например, `api.contract-analyzer.local`).

### 6.9 🟢 Low: No Graceful Shutdown

**Проблема:** Нет обработки сигналов SIGTERM/SIGINT. При рестарте Docker контейнера могут быть оборваны активные LLM запросы.

**Решение:**
```python
async def lifespan(app):
    setup_logging()
    yield
    # Graceful shutdown
    logger.info("Shutting down, waiting for active requests...")
    await asyncio.sleep(5)  # дать время завершить active requests
```

### 6.10 🟢 Low: API Versioning

**Проблема:** Нет префикса `/v1`. При обратно-несовместимых изменениях сломаются клиенты.

**Решение:**
```python
app = FastAPI(...)
app.include_router(api_router, prefix="/v1")
# Старый путь редиректит:
@app.get("/health")
async def legacy_health():
    return RedirectResponse(url="/v1/health")
```

---

## 7. Dependency Graph

```
contract-analyzer-ai
├── fastapi                    # Web framework
│   ├── uvicorn                # ASGI server
│   ├── python-multipart       # File upload parsing
│   └── pydantic               # Data validation
├── langchain                  # RAG orchestration
│   ├── langchain-core         # Base abstractions
│   ├── langchain-community    # BM25Retriever, HuggingFaceEmbeddings
│   ├── langchain-classic      # EnsembleRetriever (legacy compat)
│   ├── langchain-qdrant       # Qdrant vector store connector
│   └── langchain-text-splitters  # RecursiveCharacterTextSplitter
├── pdfplumber                 # PDF text extraction
├── qdrant-client              # Qdrant HTTP/gRPC client
├── gigachat                   # Sber LLM SDK
├── sentence-transformers      # Embeddings model runtime
└── dev
    ├── pytest                 # Test runner
    ├── deepeval               # RAG evaluation metrics
    ├── black / isort / flake8 # Code quality
    └── pre-commit             # Git hooks
```

---

## 8. Performance Characteristics

| Операция | Среднее время | Зависимости | Узкое место |
|---|---|---|---|
| `/health` | <5ms | — | — |
| `/upload` (10pg PDF) | ~3-5s | Disk I/O + Embeddings (GPU) + Qdrant write | Embeddings inference |
| `/upload` (100pg PDF) | ~15-30s | PDF parsing + Embeddings + Qdrant | Embeddings (CPU-bound) |
| `/ask` | ~5-15s | Qdrant search + BM25 + LLM (GigaChat) | GigaChat API latency |
| `/evaluate` | ~3-10s | 2× GigaChat calls / 1× DeepEval | LLM latency |
| `/metrics` | <5ms | — | — |

**Memory footprint:**
- HuggingFace embeddings: ~2 GB RAM
- Qdrant: ~500 MB (variable, depends on indexed documents)
- GigaChat client: ~50 MB
- App process: ~100-300 MB base + embeddings

---

## 9. Production Readiness Checklist

| Категория | Критерий | Статус | Примечание |
|---|---|---|---|
| **Security** | CORS whitelist | ✅ | From env |
| | Input validation | ✅ | Pydantic + file size limit |
| | Error sanitization | ✅ | `_internal_error()` |
| | Auth (API key) | ✅ | Optional Bearer |
| | Rate limiting | ❌ | Missing |
| | Secrets management | ❌ | .env file in production |
| **Reliability** | Thread safety | ✅ | All singletons locked |
| | Graceful degradation | ✅ | GigaChat fallback |
| | Health check | ✅ | `/health` |
| | Startup validation | ✅ | Qdrant health check |
| **Observability** | Logging | ✅ | structured logs |
| | Metrics | ✅ | Live quality metrics |
| | Tracing | ❌ | No distributed tracing |
| | Alerting | ❌ | No monitoring |
| **Scalability** | Horizontal scaling | ❌ | In-memory state per worker |
| | Caching | ❌ | No response cache |
| | Async LLM | ❌ | Sync GigaChat blocks event loop |
| **DevOps** | Docker | ✅ | 3 services |
| | CI/CD | ✅ | GitHub Actions |
| | E2E tests | ✅ | 162 tests |
| | Database migrations | ❌ | N/A (Qdrant schema-free) |

---

## 10. Roadmap Recommendations

### Immediate (production block)
1. ✅ ~~CORS wildcard fix~~ **Done**
2. ✅ ~~File size OOM fix~~ **Done**
3. ✅ ~~Error sanitization~~ **Done**
4. **Redis for shared state** — enable multi-worker scaling
5. **Async LLM calls** — `run_in_executor` или async GigaChat SDK

### Short-term (quality of life)
6. **Response caching** — Redis TTL cache для частых вопросов
7. **Semantic chunker** — вместо RecursiveCharacterTextSplitter
8. **Metrics persistence** — сохранять в Qdrant или Redis

### Medium-term (enterprise features)
9. **JWT auth** — вместо простого API key
10. **Rate limiting** — slowapi / nginx
11. **Multi-format support** — DOCX, XLSX, images (OCR)
12. **Admin dashboard** — для мониторинга использования

### Long-term (scale)
13. **Multiple embedding models** — configurable per collection
14. **A/B testing** — compare GigaChat vs GPT vs YandexGPT
15. **Feedback loop** — thumbs up/down для RLHF / fine-tuning

---

*Отчёт составлен на основе анализа 30+ файлов исходного кода, 162 тестов, полной конфигурации Docker, документации и QA-аудита.*
