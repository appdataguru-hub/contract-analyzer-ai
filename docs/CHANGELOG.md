# Changelog

## 2026-06-21 — Итерация 4: Live Quality Metrics (161 тест)

### Добавлено

| Компонент | Описание | Файлы |
|-----------|----------|-------|
| Auto-evaluation | Каждый `/ask` ответ автоматически оценивается через DeepEval или GigaChat | `app/main.py:257-271` |
| Live metrics endpoint | `GET /metrics` — агрегированные метрики за сессию (mean/min/max/PASS/FAIL) | `app/main.py:283-320` |
| Metrics aggregator | Thread-safe in-memory накопление Faithfulness и Answer Relevancy | `app/main.py:44-49` |
| MetricsResponse | Новая Pydantic модель с total_evaluations, метриками и статусами | `app/models.py:41-52` |
| Per-answer scoring | Каждый ответ в Streamlit показывает 🟢 Faithfulness / 🟢 Relevancy | `frontend/streamlit_app.py:195-213` |
| Live sidebar metrics | Сайдбар читает `/metrics` вместо статического `metrics.json` | `frontend/streamlit_app.py:69-83` |
| GigaChat evaluation | Кастомные Faithfulness и AnswerRelevancy метрики через GigaChat (без OpenAI) | `app/evaluation.py` |
| EVAL_BACKEND config | Три режима: `auto` (по умолч.), `gigachat`, `deepeval` | `app/config.py:41` |
| fetch_metrics() | Новый API-клиент для `/metrics` (заменил load_metrics) | `frontend/utils.py:85-95` |

### Исправлено

| # | Проблема | Fix |
|---|----------|-----|
| 1 | Статические метрики в `data/metrics.json` не отражали реальное качество ответов | Заменены на живые метрики через REST API |
| 2 | `test_evaluation.py` падал без `OPENAI_API_KEY` | Добавлен `@patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})` |
| 3 | `test_api.py` проверял точный набор ключей ответа (`{"answer", "sources"}`) | Изменён на `.issubset()` — теперь допускает новые eval поля |
| 4 | DeepEval был единственным бэкендом для метрик | Добавлен GigaChat-бэкенд с парсингом SCORE/REASON |
| 5 | `EVAL_BACKEND` захардкожен как `auto` | Настраивается через `.env` |

---

## 2026-06-19 — Итерация 3: Deep QA + Security + Stability (149 тестов)

### Добавлено

| Компонент | Описание | Файлы |
|-----------|----------|-------|
| Security tests | 17 тестов: path traversal, XSS, SQL injection, shell injection, null bytes, content-type spoofing, malformed multipart | `tests/test_security.py` |
| Stability tests | 23 теста: concurrent access, race conditions, memory growth, resource cleanup, edge cases | `tests/test_stability.py` |
| API integration tests | 28 тестов: все эндпоинты, CORS, OpenAPI schema | `tests/test_api.py` |
| Model validation tests | 17 тестов: Pydantic валидация всех моделей | `tests/test_models.py` |
| Evaluation tests | 5 тестов: DeepEval evaluate/batch | `tests/test_evaluation.py` |
| conftest.py | Fixtures: PDF generation, Qdrant/GigaChat mocks, document store cleanup | `tests/conftest.py` |
| sample_contract.pdf | Тестовый договор для ручного тестирования | `data/sample_contract.pdf` |

### Исправлено

| # | Проблема | Fix |
|---|----------|-----|
| 1 | `generate_answer` возвращал error-строку вместо raise | `GigaChatAuthError` exception |
| 2 | `evaluate_response` проверял `GIGACHAT_CREDENTIALS` хотя использует gpt-4o | Убран неверный guard |
| 3 | `QuestionRequest.collection_name` hardcoded `"contracts"` | Заменён на `COLLECTION_NAME` из config |
| 4 | `Dockerfile` устанавливал `curl` без необходимости | Удалён `apt-get install curl` |
| 5 | `AnswerResponse.source_scores` в модели, но не заполнялся | Удалён из модели |

---

## 2026-06-19 — Итерация 2: Senior QA review + hermes fixes

### Hermes — Исправления багов из ARCHITECTURE_BUGS.md

| # | Баг | Статус | Коммит |
|---|-----|--------|--------|
| 1 | BM25 пересоздаётся на каждый запрос | ✅ Fixed | `BM25Cache` (get_or_build / invalidate) |
| 4 | Нет обработки ошибок в ingestion | ✅ Fixed | `PDFExtractionError`, try/except |
| 6 | Нет логгирования | ✅ Fixed | `setup_logging()` |
| 7 | GigaChat SSL verify=False намертво | ✅ Fixed | `GIGACHAT_VERIFY_SSL` env |
| 9 | Пустые тесты | ✅ Fixed | 4 новых теста PDF extraction |
| 10 | .env.example без документации | ✅ Fixed | +3 новых параметра |
| 2 | Semantic Chunker | ❌ Not fixed | Ещё RecursiveCharacterTextSplitter |
| 11 | Hardcoded collection_name | ❌ Not fixed | Default `"contracts"` |
| 3 | Qdrant Import Path | ✅ Already OK | Использовался langchain_qdrant |
| 5 | Docker Compose app | ✅ Already OK | Был добавлен ранее |
| 8 | Upload Response fields | ✅ Already OK | collection_name возвращался |

### Senior QA — Найденные проблемы и исправления

#### REGRESSION: `rank-bm25` удалён из requirements.txt

Hermes удалил зависимость `rank-bm25>=0.2.0` из requirements.txt. Пакет `rank_bm25` — runtime-зависимость `BM25Retriever` из `langchain_community`. Без него при чистой установке (`pip install -r requirements.txt`) BM25 упадёт с `ImportError`.

**Fix:** `rank-bm25>=0.2.0` возвращён в requirements.txt.

**Обоснование:** Нельзя полагаться на то, что пакет уже установлен в окружении. Каждая зависимость должна быть явно указана для воспроизводимости.

---

#### NIT: Race condition в upload — invalidate до store

```python
# main.py — upload endpoint (было)
load_pdf_bytes_to_store(...)       # 1. Qdrant updated
bm25_cache.invalidate(collection)  # 2. cache cleared
document_store[collection] = {...} # 3. store updated
```

Если `/ask` приходит между (2) и (3), `BM25Cache.get_or_build()` получит `documents` из `document_store[collection]`, которые ещё не обновлены -> BM25 будет перестроен со *старыми* документами.

**Fix:** `bm25_cache.invalidate()` перенесён после `document_store[collection] =`:

```python
load_pdf_bytes_to_store(...)       # 1. Qdrant updated
document_store[collection] = {...} # 2. store updated
bm25_cache.invalidate(collection)  # 3. cache cleared
```

Теперь при запросе между (2) и (3) документы уже актуальны, а при обращении после (3) BM25 перестроится с новыми документами.

---

### Senior QA — Атомарные проверки (все модули, все граничные случаи)

**Ingestion:**
- ✅ `extract_text_from_pdf_bytes(b'')` → `PDFExtractionError`
- ✅ `extract_text_from_pdf('/nonexistent')` → `PDFExtractionError`
- ✅ `chunk_documents('', 100, 0)` → `[]`
- ✅ `chunk_documents('x'*1500, 500, 50)` → корректный сплит
- ✅ `create_document_chunks('')` → `[]`
- ✅ `create_document_chunks('T', source='f.pdf')` → metadata корректна

**Retrieval:**
- ✅ `BM25Cache` — cache hit возвращает тот же объект
- ✅ `BM25Cache` — cache hit обновляет `k` на новый
- ✅ `BM25Cache` — invalidate удаляет, следующий get_or_build создаёт новый
- ✅ `BM25Cache` — мультиколлекции не пересекаются
- ✅ `BM25Cache` — invalidate несуществующей коллекции не крашится
- ✅ `BM25Cache` — реальный поиск по русскому тексту работает
- ✅ `bm25_cache` синглтон существует

**Generation:**
- ✅ `build_prompt('', 'ctx')` — пустой вопрос не ломает
- ✅ `build_prompt('q', '')` — пустой контекст не ломает
- ✅ `build_prompt('q', 'Line1\nLine2')` — мультилайн
- ✅ `generate_answer` без credentials → `GigaChatAuthError` (не строка)

**API Models:**
- ✅ `QuestionRequest(question='?')` → `collection_name` из конфига
- ✅ `AnswerResponse.source_scores` — нет (удалён)
- ✅ Все Pydantic поля корректны

**Config:**
- ✅ Все типы корректны (str, int, bool)
- ✅ `setup_logging('invalid')` → fallback на INFO
- ✅ `GIGACHAT_VERIFY_SSL` по умолчанию `True`

**Dockerfile:**
- ✅ Нет `curl`, нет `apt-get`, минимальный слой

**Интеграция:**
- ✅ `from app.main import app` — все модули грузятся
- ✅ `from app.retrieval import bm25_cache` — синглтон доступен

---

## 2026-06-19 — Итерация 1: Начальная реализация

### Реализовано

- FastAPI приложение с эндпоинтами `/upload`, `/ask`, `/health`
- Ingestion pipeline: pdfplumber → RecursiveCharacterTextSplitter → Qdrant
- Hybrid retrieval: EnsembleRetriever (Vector + BM25)
- GigaChat интеграция для генерации ответов
- DeepEval оценка качества (Faithfulness, Answer Relevancy)
- Docker-compose: Qdrant + App
- Базовые тесты (9 тестов)
