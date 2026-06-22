# Contract Analyzer AI

<p align="center">
  <a href="http://176.108.252.198:8501">
    <img src="https://img.shields.io/badge/%F0%9F%8C%90_%D0%94%D0%B5%D0%BC%D0%BE-%D0%BE%D0%BD%D0%BB%D0%B0%D0%B9%D0%BD-brightgreen?style=for-the-badge" alt="Demo">
  </a>
  <a href="http://176.108.252.198:8000/docs">
    <img src="https://img.shields.io/badge/%F0%9F%93%9A_Swagger-%D0%B4%D0%BE%D1%81%D1%82%D1%83%D0%BF%D0%B5%D0%BD-blue?style=for-the-badge" alt="API Docs">
  </a>
  <a href="https://github.com/appdataguru-hub/contract-analyzer-ai">
    <img src="https://img.shields.io/badge/GitHub-Repository-181717?style=for-the-badge&logo=github" alt="GitHub">
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/Docker-ready-2496ED?style=flat-square&logo=docker" alt="Docker">
  <img src="https://img.shields.io/badge/CI-passing-brightgreen?style=flat-square" alt="CI">
  <img src="https://img.shields.io/badge/Coverage-80%25-yellowgreen?style=flat-square" alt="Coverage">
  <img src="https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square" alt="PRs Welcome">
</p>

**Contract Analyzer AI** — гибридная RAG-система для анализа PDF-договоров с поддержкой русского языка через GigaChat. Загрузите PDF, задавайте вопросы на естественном языке и получайте ответы от ИИ с оценкой качества в реальном времени (Faithfulness + Answer Relevancy).

---

## 🚀 Быстрый старт

<p align="center">
  <a href="#-установка-и-настройка"><img src="https://img.shields.io/badge/%F0%9F%90%B3_%D0%97%D0%B0%D0%BF%D1%83%D1%81%D0%BA_%D1%87%D0%B5%D1%80%D0%B5%D0%B7_Docker-%D0%B8%D0%BD%D1%81%D1%82%D1%80%D1%83%D0%BA%D1%86%D0%B8%D1%8F-blue?style=for-the-badge" alt="Docker"></a>
  <a href="#-использование-api"><img src="https://img.shields.io/badge/%F0%9F%93%A1_API_%D0%BF%D1%80%D0%B8%D0%BC%D0%B5%D1%80%D1%8B-curl-success?style=for-the-badge" alt="API"></a>
  <a href="#-фронтенд-streamlit"><img src="https://img.shields.io/badge/%F0%9F%96%A5%EF%B8%8F_%D0%98%D0%BD%D1%82%D0%B5%D1%80%D1%84%D0%B5%D0%B9%D1%81-Streamlit-orange?style=for-the-badge" alt="Streamlit"></a>
</p>

---

## Архитектура

```
                         ┌─────────────────────────────────────┐
                         │   Streamlit (port 8501)             │
                         │   frontend/streamlit_app.py         │
                         └──────────────┬──────────────────────┘
                                        │ REST API
                         ┌──────────────▼──────────────────────┐
                         │         FastAPI (port 8000)         │
                         │                                     │
  POST /upload  ────────▶│  ┌───────────┐   ┌────────────┐     │
  POST /ask     ────────▶│  │ Ingestion │──▶│  Qdrant    │    │
  (auto-eval)            │  │           │    │ (Vector DB)│    │
  POST /evaluate────────▶│  │ pdfplumber│   └─────┬──────┘     │
  GET  /metrics ────────▶│  │ chunking  │         │            │
  GET  /health  ────────▶│  │ embedding │   ┌─────▼──────┐     │
                         │  └───────────┘   │ BM25Cache  │      │
                         │                  │ (in-memory)│      │
                         │  ┌───────────┐   └─────┬──────┘      │
                         │  │ Retrieval │◀── ─────┘            │
                         │  │ hybrid    │                       │
                         │  │ search    │──▶┌─────────────┐    │
                         │  └───────────┘   │ Generation  │     │
                         │                  │ GigaChat    │     │
                         │  ┌───────────┐   └──────┬──────┘     │
                         │  │Evaluation │◀─────────┘           │
                         │  │ DeepEval  │──▶┌─────────────┐    │
                         │  │ (live)    │   │ Metrics     │    │
                         │  └───────────┘   │ Aggregator  │    │
                         │                  │ (in-memory) │    │
                         │                  └─────────────┘    │
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

## 📋 Требования

- Python 3.11+
- Docker & Docker Compose (рекомендуется)
- Учётные данные GigaChat API ([Sber GigaChat](https://developers.sber.ru/gigachat))
- (Опционально) OpenAI API ключ для DeepEval

## 🔧 Установка и настройка

### Вариант A: Docker (рекомендуется)

```bash
# 1. Клонирование
git clone https://github.com/appdataguru-hub/contract-analyzer-ai.git
cd contract-analyzer-ai

# 2. Настройка окружения
cp .env.example .env
# Отредактируйте .env: укажите GIGACHAT_CREDENTIALS

# 3. Запуск
docker-compose up --build
# Бэкенд: http://localhost:8000
# Фронтенд: http://localhost:8501
# Swagger: http://localhost:8000/docs
```

### Вариант B: Локальная разработка

```bash
# 1. Клонирование и venv
git clone https://github.com/appdataguru-hub/contract-analyzer-ai.git
cd contract-analyzer-ai
python -m venv .venv && source .venv/bin/activate

# 2. Установка зависимостей
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 3. Настройка
cp .env.example .env
# Укажите GIGACHAT_CREDENTIALS в .env

# 4. Запуск Qdrant + приложения
docker-compose up -d qdrant
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 5. (Опционально) Streamlit фронтенд
cd frontend && streamlit run streamlit_app.py
```

---

## Безопасность

### API-аутентификация (опционально)

Укажите `API_KEY` в `.env` для включения Bearer token:

```
API_KEY=your-secret-api-key
```

Защищённые эндпоинты (`/upload`, `/ask`, `/evaluate`) требуют заголовок:

```
Authorization: Bearer your-secret-api-key
```

Если `API_KEY` пуст, эндпоинты доступны без аутентификации.

### Рекомендации

- **Никогда не коммитьте `.env`** — файл уже в `.gitignore`
- Используйте разные ключи для разработки и продакшена
- Лимит загрузки: **20 MB** (настраивается через `MAX_FILE_SIZE_MB`)
- SSL-верификация GigaChat включена по умолчанию (`GIGACHAT_VERIFY_SSL=true`)

---

## Использование API

### Проверка здоровья

```bash
curl http://localhost:8000/health
```

**Ответ:**
```json
{"status": "ok"}
```

### Загрузка PDF

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@data/sample_contract.pdf"
```

**Ответ:**
```json
{
  "status": "success",
  "filename": "sample_contract.pdf",
  "chunks": 47,
  "collection_name": "contracts"
}
```

### Задать вопрос (с авто-оценкой)

Каждый ответ автоматически оценивается по качеству. Если `OPENAI_API_KEY` не задан, поля оценки вернутся как `null`.

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Какая цена договора?"}'
```

**Ответ:**
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

### Метрики в реальном времени

Агрегированные метрики по всем ответам текущей сессии:

```bash
curl http://localhost:8000/metrics
```

**Ответ:**
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

### Ручная оценка (отдельный эндпоинт)

Для ручной оценки произвольных пар вопрос-ответ:

```bash
curl -X POST http://localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Какая цена договора?",
    "actual_output": "Цена составляет 100 000 рублей.",
    "retrieval_context": ["Цена договора: 100 000 рублей"]
  }'
```

**Ответ:**
```json
{
  "faithfulness_score": 0.85,
  "faithfulness_reason": "Ответ соответствует контексту",
  "answer_relevancy_score": 0.9,
  "answer_relevancy_reason": "Ответ релевантен вопросу"
}
```

### Swagger-документация

http://localhost:8000/docs

---

## Метрики качества

### Метрики в реальном времени

Каждый ответ автоматически оценивается по двум метрикам:

| Метрика | Описание | Порог |
|---------|----------|-------|
| **Faithfulness** | Насколько ответ соответствует контексту документа | ≥ 0.7 |
| **Answer Relevancy** | Насколько ответ релевантен вопросу | ≥ 0.7 |

Оценки накапливаются в памяти и доступны через `GET /metrics`.

В интерфейсе Streamlit:
- **Сайдбар** — средние значения с PASS/FAIL и min/max
- **По каждому ответу** — индивидуальные оценки с цветовыми индикаторами (🟢 ≥ 0.7 / 🔴 < 0.7)

> **Автовыбор бэкенда:** Если доступен GigaChat (`GIGACHAT_CREDENTIALS` задан), метрики используют его. Иначе — DeepEval (требует `OPENAI_API_KEY`). Укажите `EVAL_BACKEND=gigachat` или `EVAL_BACKEND=deepeval` для принудительного выбора.

### Результаты прогона на тестовом наборе

Benchmark results on 8 questions from `data/eval_questions.json`:

| Metric | Mean | Min | Max | Threshold | Status |
|--------|------|-----|-----|-----------|--------|
| **Faithfulness** | 0.87 | 0.72 | 0.95 | 0.7 | ✅ PASS |
| **Answer Relevancy** | 0.83 | 0.71 | 0.92 | 0.7 | ✅ PASS |

> 🔍 **Полный QA-аудит**: 11 багов найдено и исправлено (3 Critical, 4 High, 3 Medium, 1 Low). См. [`docs/QA_AUDIT_REPORT.md`](docs/QA_AUDIT_REPORT.md).

---

## Тесты

Проект включает **162 теста** в 8 модулях:

```bash
pytest tests/ -v
```

С покрытием:

```bash
coverage run -m pytest tests/ -v
coverage report
```

| Модуль | Тестов | Покрытие |
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

## Качество кода

Проект следует строгим стандартам качества:

- **Форматирование:** Black (line-length=100)
- **Импорты:** isort (profile=black)
- **Линтинг:** flake8 (E203, W503 ignored)
- **Pre-commit:** форматирование, trailing whitespace, YAML lint, проверка merge конфликтов

Установка pre-commit хуков:

```bash
pip install pre-commit
pre-commit install
```

---

## Структура проекта

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

## Стек технологий

| Компонент | Технология | Назначение |
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

## Конфигурация

| Переменная | По умолчанию | Описание |
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

## Фронтенд (Streamlit)

Веб-интерфейс для анализа договоров без использования терминала.

### Возможности

- **Drag-and-drop** загрузка PDF
- **Ввод вопросов** с генерацией ответов в реальном времени
- **История Q&A** (до 20 записей за сессию)
- **Оценка каждого ответа** — Faithfulness и Relevancy с 🟢/🔴 индикаторами
- **Метрики в сайдбаре** — средние значения с PASS/FAIL
- **Индикатор загрузки** во время обработки
- **Настройки подключения** (URL бэкенда, коллекция)
- **Проверка здоровья** с визуальным статусом
- **Предупреждение** о доступности GigaChat

### Скриншот интерфейса

![Streamlit UI](docs/screenshot.png)

> *Реальный вид интерфейса после загрузки договора и задавания вопроса.*

### Макет UI

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

### Запуск

Через Docker (с бэкендом):

```bash
docker-compose up --build
# http://localhost:8501
```

Локально (отдельный фронтенд):

```bash
cd frontend
pip install -r ../requirements-streamlit.txt
streamlit run streamlit_app.py
```

### Конфигурация фронтенда

| Переменная | По умолчанию | Описание |
|------------|-------------|----------|
| `BACKEND_URL` | `http://app:8000` | URL бэкенда |
| `API_KEY` | — | API-ключ (если включён на бэкенде) |
| `COLLECTION_NAME` | `contracts` | Название коллекции Qdrant |

---

## QA и исправление багов

> **📄 Полный отчёт:** [`docs/QA_AUDIT_REPORT.md`](docs/QA_AUDIT_REPORT.md)

### Обзор

Полный QA-аудит выявил и исправил **11 багов** (3 Critical, 4 High, 3 Medium, 1 Low) в архитектуре, коде, тестах, Docker-инфраструктуре, UI и интеграциях с внешними сервисами (GigaChat, Qdrant).

### 🔴 Critical

#### CR-1: CORS wildcard с credentials
**Проблема:** `allow_origins=["*"]` с `allow_credentials=True` — браузеры блокируют.
**Исправление:** Настраиваемый `CORS_ORIGINS` из env с белым списком.

#### CR-2: Проверка размера файла после read()
**Проблема:** `file.read()` без лимита — 2GB файл загружается в память.
**Исправление:** `read_with_limit()` читает чанками по 1MB с предварительной проверкой.

#### CR-3: Утечка данных в ошибках API
**Проблема:** `str(e)` в ответах API раскрывает пути, имена БД, credentials.
**Исправление:** `_internal_error()` возвращает общее сообщение + логирует детали.

### 🟠 High

#### High-1: BM25Cache thread-safety
**Проблема:** `document_store` dict и `bm25_cache` изменялись без блокировок.
**Исправление:** `threading.Lock()` вокруг всех операций с кэшем и хранилищем.

#### High-2: Гонка синглтона GigaChat
**Проблема:** `_giga_client` создавался двумя потоками одновременно.
**Исправление:** `threading.Lock()` + double-checked locking.

#### High-3: Пустые choices LLM
**Проблема:** Пустые `response.choices` → `IndexError`.
**Исправление:** Guard `if not response.choices`.

#### High-4: Гонка инициализации модели эмбеддингов
**Проблема:** Модель эмбеддингов инициализировалась параллельно в нескольких воркерах.
**Исправление:** `threading.Lock()` при инициализации синглтона.

### 🟡 Medium

#### Medium-1: Утечка temp-файлов
**Проблема:** `tempfile.NamedTemporaryFile` без `.close()` — утечка файловых дескрипторов.
**Исправление:** `with TemporaryDirectory()` + `QDRANT_FORCE_RECREATE`.

#### Medium-2: Коллекция Qdrant не очищалась между загрузками
**Проблема:** Повторная загрузка не удаляла коллекцию.
**Исправление:** `force_recreate` через `QdrantVectorStore.from_documents`.

#### Medium-3: Жёстко заданная модель оценки
**Проблема:** `gpt-4o` захардкожен — использование GigaChat credentials для OpenAI.
**Исправление:** `EVAL_MODEL` из env, по умолчанию `gpt-4o`.

### 🔵 Low

#### Low-1: Мёртвый код Cohere Rerank
**Проблема:** `langchain-cohere` импортирован, но не используется.
**Исправление:** Удалены `langchain-cohere` и Cohere API key из `.env.example`.

### Статистика тестов

```
Покрытие: ~80% (app/)
Всего тестов: 162
Пройдено: 162
Упало: 0
```

| Модуль | Тестов | Описание |
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

## План развития

- [ ] JWT-аутентификация
- [ ] Redis-кэширование частых вопросов
- [x] Streamlit UI ✅
- [x] Метрики качества в реальном времени ✅
- [ ] Поддержка DOCX и других форматов
- [x] CI/CD через GitHub Actions ✅
- [ ] Семантический чанкинг (замена RecursiveCharacterTextSplitter)
- [ ] Multi-worker общее состояние (Redis)
- [ ] Асинхронные LLM-вызовы (неблокирующий GigaChat)

---

## 💻 Полезные команды

```bash
make install       # Установка production-зависимостей
make install-dev   # Установка всех зависимостей (включая dev)
make lint          # Запуск flake8 линтера
make format        # Авто-форматирование black + isort
make test          # Запуск тестов
make coverage      # Запуск тестов с отчётом о покрытии
make docker-up     # Запуск всех Docker-сервисов
make docker-down   # Остановка всех Docker-сервисов
make clean         # Очистка кэша и артефактов сборки
```

---

## 🤝 Вклад в проект

Пожалуйста, прочитайте [CONTRIBUTING.md](CONTRIBUTING.md) и [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) перед отправкой изменений.

Сообщайте об уязвимостях через [SECURITY.md](SECURITY.md).

---

## 🙏 Благодарности

- [GigaChat](https://developers.sber.ru/gigachat) — русскоязычная LLM от Сбера
- [Qdrant](https://qdrant.tech/) — векторная база данных
- [LangChain](https://www.langchain.com/) — фреймворк для RAG-пайплайнов
- [Streamlit](https://streamlit.io/) — быстрый фреймворк для AI-интерфейсов
- [DeepEval](https://docs.confident-ai.com/) — оценка качества RAG-систем
- [pdfplumber](https://github.com/jsvine/pdfplumber) — извлечение текста из PDF

---

## Лицензия

MIT — подробнее в [LICENSE](LICENSE).

---

Сделано с Python, FastAPI, GigaChat и DeepEval
