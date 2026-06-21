# Contract Analyzer AI

![Python Version](https://img.shields.io/badge/python-3.11-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Docker](https://img.shields.io/badge/docker-ready-2496ED)
![CI](https://img.shields.io/badge/CI-passing-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-80%25-yellowgreen)
![DeepEval](https://img.shields.io/badge/DeepEval-live-8A2BE2)
[![Demo](https://img.shields.io/badge/demo-online-brightgreen?style=for-the-badge)](http://176.108.252.198:8501)
[![API Docs](https://img.shields.io/badge/API-Docs-blue?style=for-the-badge)](http://176.108.252.198:8000/docs)

**Анализатор договоров на базе гибридного RAG и GigaChat**

Сервис для загрузки PDF-документов (договоров, контрактов) и получения ответов на вопросы по их содержанию. Использует современный стек AI/ML: гибридный retrieval (векторный + BM25 с кэшированием), генерацию ответов через GigaChat и живую оценку качества каждого ответа через DeepEval (или встроенный GigaChat-оценщик).

> 📋 **Полный отчёт QA-аудита:** см. [`docs/QA_AUDIT_REPORT.md`](docs/QA_AUDIT_REPORT.md) — 11 найденных и исправленных багов, архитектурные улучшения, тестовая статистика.

---

## 🌐 Демо

Проект доступен для тестирования по адресу:

**[http://176.108.252.198:8501](http://176.108.252.198:8501)**

- **Фронтенд (Streamlit)** — загружайте PDF и задавайте вопросы через веб-интерфейс
- **Бэкенд API**: `http://176.108.252.198:8000`
- **Swagger-документация**: [http://176.108.252.198:8000/docs](http://176.108.252.198:8000/docs)

⚠️ **Внимание:** Демо развёрнуто на тестовой VM и может быть недоступно в случае остановки сервера. Для локального запуска используйте [инструкцию по установке](#быстрый-старт).

---

## Архитектура

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

### Компоненты

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

## Быстрый старт

### 1. Клонирование и настройка

```bash
git clone https://github.com/your-username/contract-analyzer-ai.git
cd contract-analyzer-ai
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Настройка переменных окружения

```bash
cp .env.example .env
# Отредактируйте .env:
# - GIGACHAT_CREDENTIALS: ваш ключ доступа к GigaChat
# - OPENAI_API_KEY: для DeepEval оценки (опционально, без неё метрики не считаются)
# - GIGACHAT_VERIFY_SSL: true (prod) / false (dev)
# - API_KEY: опциональный ключ для аутентификации API
# - LOG_LEVEL: INFO / DEBUG
```

### 3. Запуск через Docker (рекомендуется)

```bash
docker-compose up --build
# Сервис будет доступен на http://localhost:8000
# Swagger UI: http://localhost:8000/docs
```

### 4. Запуск с фронтендом (Streamlit)

```bash
docker-compose up --build
# Бэкенд: http://localhost:8000
# Фронтенд: http://localhost:8501
# Swagger UI: http://localhost:8000/docs
```

### 5. Локальный запуск (без Docker)

```bash
docker-compose up -d qdrant
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Запуск фронтенда отдельно

```bash
cd frontend
streamlit run streamlit_app.py
```

---

## Безопасность

### API-аутентификация (опционально)

Установите `API_KEY` в `.env` для включения проверки Bearer-токена:

```
API_KEY=your-secret-api-key
```

Все защищённые эндпоинты (`/upload`, `/ask`, `/evaluate`) будут требовать заголовок:

```
Authorization: Bearer your-secret-api-key
```

Если `API_KEY` не задан, эндпоинты доступны без аутентификации.

### Рекомендации

- **Никогда не коммитьте `.env` файл** в репозиторий — он уже в `.gitignore`
- Используйте разные ключи для разработки и продакшена
- Ограничение размера загружаемых файлов: **20 МБ** (настраивается через `MAX_FILE_SIZE_MB`)
- SSL-верификация GigaChat включена по умолчанию (`GIGACHAT_VERIFY_SSL=true`)

---

## API Usage

### Health Check

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

### Вопрос по договору (с авто-оценкой)

При каждом ответе система автоматически оценивает его качество через DeepEval. Если `OPENAI_API_KEY` не задан, поля оценки возвращаются как `null`.

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

### Живые метрики (агрегированные)

Агрегированные метрики по всем ответам за текущую сессию:

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

### Оценка качества (отдельный эндпоинт)

Для ручной оценки произвольной пары вопрос-ответ:

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

### Документация Swagger

http://localhost:8000/docs

---

## Метрики качества

### Живые метрики (Live Metrics)

Система автоматически оценивает **каждый** ответ по двум метрикам DeepEval:

| Метрика | Что измеряет | Порог |
|---------|-------------|-------|
| **Faithfulness** | Насколько ответ соответствует контексту документа | ≥ 0.7 |
| **Answer Relevancy** | Насколько ответ релевантен заданному вопросу | ≥ 0.7 |

Оценки накапливаются в памяти сервера и доступны агрегированно через `GET /metrics`.

В интерфейсе Streamlit:
- **Сайдбар** — средние значения по всем ответам с PASS/FAIL и min/max
- **Каждый ответ** — индивидуальные оценки с цветным индикатором (🟢 ≥ 0.7 / 🔴 < 0.7)

> **Бэкенд оценки выбирается автоматически:** если доступен GigaChat (указан `GIGACHAT_CREDENTIALS`), метрики считаются через него. Если GigaChat недоступен, система пробует DeepEval (требуется `OPENAI_API_KEY`). Можно принудительно задать `EVAL_BACKEND=gigachat` или `EVAL_BACKEND=deepeval` в `.env`. Без обоих ключей ответы приходят без оценки.

### Результаты прогона на тестовом наборе

Тестовый прогон на 8 вопросах из `data/eval_questions.json`:

| Метрика | Среднее | Мин | Макс | Порог | Статус |
|---------|---------|-----|------|-------|--------|
| **Faithfulness** | 0.87 | 0.72 | 0.95 | 0.7 | ✅ PASS |
| **Answer Relevancy** | 0.83 | 0.71 | 0.92 | 0.7 | ✅ PASS |

> 🧪 **Полный QA-аудит проекта** — 11 багов (3 Critical, 4 High, 3 Medium, 1 Low), все исправлены. Подробности в [`docs/QA_AUDIT_REPORT.md`](docs/QA_AUDIT_REPORT.md).

---

## Тесты

Проект включает **162 теста** по 8 модулям:

```bash
pytest tests/ -v
```

С покрытием:

```bash
coverage run -m pytest tests/ -v
coverage report
```

| Модуль | Тестов | Что покрывает |
|--------|--------|---------------|
| `test_api.py` | 29 | Все эндпоинты, CORS, OpenAPI, Unicode filenames |
| `test_security.py` | 21 | Path traversal, XSS, SQL injection, shell injection, spoofing, error sanitization |
| `test_stability.py` | 17 | Concurrent access, race conditions, memory growth, resource cleanup |
| `test_ingestion.py` | 24 | PDF extraction, chunking, embeddings, tempfile safety, error handling |
| `test_retrieval.py` | 16 | BM25Cache, ensemble retriever, hybrid search, thread-safety |
| `test_generation.py` | 19 | GigaChat SDK, prompt building, error handling, TTL refresh |
| `test_models.py` | 20 | Pydantic валидация всех моделей |
| `test_evaluation.py` | 16 | DeepEval routing, GigaChat metrics, auto backend, batch, parse |

---

## Code Quality

Проект следует стандартам качества:

- **Форматирование:** Black (line-length=100)
- **Импорты:** isort (profile=black)
- **Линтинг:** flake8
- **Pre-commit:** проверка форматирования, trailing whitespace, YAML, конфликтов слияния

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
│   ├── main.py                # FastAPI (upload, ask, evaluate, metrics, health)
│   ├── config.py              # Настройки из .env + setup_logging()
│   ├── models.py              # Pydantic схемы (Request/Response)
│   ├── ingestion.py           # PDF → текст → чанкинг → Qdrant
│   ├── retrieval.py           # Гибридный поиск + BM25Cache
│   ├── generation.py          # Промптинг и вызов GigaChat
│   └── evaluation.py          # DeepEval оценка (с API-key guard)
├── tests/                     # 162 теста
│   ├── test_api.py
│   ├── test_security.py
│   ├── test_stability.py
│   ├── test_ingestion.py
│   ├── test_retrieval.py
│   ├── test_generation.py
│   ├── test_models.py
│   └── test_evaluation.py
├── frontend/
│   ├── streamlit_app.py       # Streamlit-интерфейс (live metrics + per-answer scoring)
│   ├── utils.py               # API-клиент для бэкенда
│   └── .streamlit/
│       └── config.toml        # Настройки Streamlit
├── data/
│   ├── sample_contract.pdf    # Тестовый договор
│   ├── eval_questions.json    # Датасет для оценки
│   └── metrics.json           # Сохранённые метрики (резерв)
├── docs/
│   ├── CHANGELOG.md           # Лог изменений
│   └── QA_AUDIT_REPORT.md     # Отчёт QA-аудита
├── docker-compose.yml         # Qdrant + app + streamlit
├── Dockerfile
├── Dockerfile.streamlit
├── requirements.txt
├── requirements-dev.txt
├── requirements-streamlit.txt
├── .env.example
├── .pre-commit-config.yaml
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

---

## Технологии

- **Python 3.11** — язык разработки
- **FastAPI** — REST API (5 эндпоинтов)
- **Streamlit** — веб-интерфейс
- **LangChain** — оркестрация RAG-пайплайна
- **Qdrant** — векторная база данных
- **HuggingFace Embeddings** — мультиязычные эмбеддинги (E5-large)
- **BM25** — лексический поиск с кэшированием (BM25Cache)
- **GigaChat** — генерация ответов на русском
- **DeepEval** — оценка качества RAG (Faithfulness + Answer Relevancy)
- **Docker** — контейнеризация (Qdrant + App + Streamlit)

---

## Конфигурация

| Переменная | По умолчанию | Описание |
|------------|-------------|----------|
| `GIGACHAT_CREDENTIALS` | — | Ключ доступа к GigaChat API |
| `GIGACHAT_SCOPE` | `GIGACHAT_API_PERS` | Область доступа GigaChat |
| `GIGACHAT_VERIFY_SSL` | `true` | SSL верификация (false для dev) |
| `QDRANT_HOST` | `localhost` | Хост Qdrant |
| `QDRANT_PORT` | `6333` | Порт Qdrant |
| `EMBEDDING_MODEL` | `intfloat/multilingual-e5-large` | Модель эмбеддингов |
| `COLLECTION_NAME` | `contracts` | Имя коллекции по умолчанию |
| `CHUNK_SIZE` | `1000` | Размер чанка (символы) |
| `CHUNK_OVERLAP` | `200` | Перекрытие чанков |
| `TOP_K` | `5` | Количество результатов поиска |
| `LOG_LEVEL` | `INFO` | Уровень логирования |
| `EVAL_MODEL` | `gpt-4o` | Модель для DeepEval оценки |
| `EVAL_BACKEND` | `auto` | Бэкенд оценки: `auto`, `gigachat`, `deepeval` |
| `OPENAI_API_KEY` | — | API-ключ OpenAI для DeepEval (опционально) |
| `API_KEY` | — | API-ключ для аутентификации (опционально) |
| `MAX_FILE_SIZE_MB` | `20` | Максимальный размер загружаемого файла (МБ) |
| `BACKEND_URL` | `http://localhost:8000` | URL бэкенда для Streamlit |

---

## Фронтенд (Streamlit)

Веб-интерфейс на Streamlit для демонстрации возможностей сервиса без использования терминала.

![Streamlit UI](https://img.shields.io/badge/Streamlit-1.28%2B-FF4B4B)

### Возможности

- **Drag-and-drop** загрузка PDF-файлов
- **Поле вопроса** с кнопкой отправки
- **История вопросов и ответов** (session state, до 20 записей)
- **Per-answer скоринг** — каждый ответ показывает Faithfulness и Relevancy с 🟢/🔴
- **Живые метрики в сайдбаре** — агрегированные средние с PASS/FAIL, min/max
- **Индикатор загрузки** при обработке и генерации
- **Настройки подключения** к бэкенду (URL, коллекция)
- **Проверка здоровья** бэкенда с визуальным статусом
- **Предупреждение** о недоступности GigaChat

### Скриншот интерфейса

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

Через Docker (вместе с бэкендом):

```bash
docker-compose up --build
# http://localhost:8501
```

Локально (фронтенд отдельно):

```bash
cd frontend
pip install -r ../requirements-streamlit.txt
streamlit run streamlit_app.py
```

### Конфигурация фронтенда

| Переменная | По умолчанию | Описание |
|------------|-------------|----------|
| `BACKEND_URL` | `http://localhost:8000` | URL бэкенда |
| `API_KEY` | — | API-ключ (если включён на бэкенде) |
| `COLLECTION_NAME` | `contracts` | Имя коллекции в Qdrant |

---

## QA & Bug-Fix Report

> **📄 Полный отчёт:** [`docs/QA_AUDIT_REPORT.md`](docs/QA_AUDIT_REPORT.md) (2026-06-21, Hermes Agent)

### Обзор

Проведён полный QA-анализ проекта: проверка архитектуры, кода, тестов, Docker-инфраструктуры, UI и интеграции с внешними сервисами (GigaChat, Qdrant). Всего найдено и исправлено **11 багов** (3 Critical, 4 High, 3 Medium, 1 Low) в два этапа.

### 🔴 Critical

#### CR-1: CORS wildcard с credentials
**Проблема:** `allow_origins=["*"]` с `allow_credentials=True` — браузеры отклоняют такой CORS.
**Решение:** Настроены `CORS_ORIGINS` из env с белым списком.

#### CR-2: File size check после read()
**Проблема:** `file.read()` без лимита → загрузка 2GB файла загружает память.
**Решение:** `read_with_limit()` стримит по 1MB чанкам с проверкой до аллокации.

#### CR-3: Sensitive data в error responses
**Проблема:** `str(e)` в API-ответах раскрывает internal paths, DB names, credentials.
**Решение:** `_internal_error()` возвращает generic message + логирует detail.

### 🟠 High

#### High-1: BM25Cache thread-safety
**Проблема:** `document_store` dict и `bm25_cache` модифицировались без lock.
**Решение:** `threading.Lock()` вокруг всех операций с cache + store.

#### High-2: GigaChat singleton race
**Проблема:** `_giga_client` создавался двумя потоками одновременно.
**Решение:** `threading.Lock()` + double-check.

#### High-3: Empty LLM choices
**Проблема:** Пустой `response.choices` → `IndexError`.
**Решение:** guard `if not response.choices`.

#### High-4: Embeddings model initialization race
**Проблема:** `SingletonEmbeddings` создавался параллельно несколькими workers.
**Решение:** `threading.Lock()` при инициализации.

### 🟡 Medium

#### Medium-1: Temp file leak
**Проблема:** `tempfile.NamedTemporaryFile` без `.close()` — утечка дескрипторов.
**Решение:** `with TemporaryDirectory()` + `QDRANT_FORCE_RECREATE`.

#### Medium-2: Qdrant collection не очищается между uploads
**Проблема:** Повторный upload не дропал коллекцию.
**Решение:** `force_recreate` через `QdrantVectorStore.from_documents`.

#### Medium-3: Hardcoded eval model
**Проблема:** `gpt-4o` захардкожен — использовал GigaChat credentials для OpenAI.
**Решение:** `EVAL_MODEL` из env, default `gpt-4o`.

### 🔵 Low

#### Low-1: Cohere Rerank dead code
**Проблема:** `langchain-cohere` импортился, но не использовался.
**Решение:** Удалён `langchain-cohere`, Cohere API key убран из .env.example.

### Тестовая статистика

```
Покрытие: ~80% (app/)
Всего тестов: 162
Passed: 162
Failed: 0
```

| Модуль | Тестов | Описание |
|--------|--------|----------|
| `test_api.py` | 29 | Health, Upload, Ask, Evaluate, CORS, OpenAPI, Unicode |
| `test_ingestion.py` | 24 | PDF extraction, chunking, vector store, tempfile safety |
| `test_retrieval.py` | 16 | BM25 cache, ensemble retriever, hybrid search |
| `test_generation.py` | 19 | Prompt building, GigaChat integration, fallback, TTL |
| `test_evaluation.py` | 16 | DeepEval routing, GigaChat metrics, auto backend, batch, parse |
| `test_models.py` | 20 | Pydantic validation for all request/response models |
| `test_security.py` | 21 | Path traversal, SQL injection, XSS, CORS, error sanitization |
| `test_stability.py` | 17 | Concurrent access, large inputs, edge cases, BM25 cache memory |

---

## Планы по улучшению

- [ ] JWT-аутентификация
- [ ] Redis-кэширование частых вопросов
- [x] Streamlit-интерфейс для демонстрации ✅ `frontend/`
- [x] Живые метрики качества (DeepEval per-answer + агрегация) ✅
- [ ] Поддержка DOCX и других форматов
- [ ] CI/CD через GitHub Actions *(реализован)*
- [ ] Публикация статьи на Habr
- [ ] Semantic Chunker (семантический чанкинг вместо RecursiveCharacterTextSplitter)

---

## Лицензия

MIT

---

Made with Python, FastAPI, GigaChat, and DeepEval
