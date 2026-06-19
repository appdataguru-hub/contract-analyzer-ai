# Contract Analyzer AI

**Анализатор договоров на базе гибридного RAG и GigaChat**

Сервис для загрузки PDF-документов (договоров, контрактов) и получения ответов на вопросы по их содержанию. Использует современный стек AI/ML: семантический поиск, гибридный retrieval (векторный + BM25), ре-ранжирование и генерацию ответов через GigaChat.

---

## Архитектура

```
┌────────────┐     ┌──────────────────┐     ┌──────────────┐
│  FastAPI   │────▶│  Ingestion:      │────▶│  Qdrant      │
│  /upload   │     │  PDF → Text      │     │  (Vector DB) │
│  /ask      │     │  → Chunks        │     │              │
└────────────┘     │  → Embeddings    │     └──────┬───────┘
       │           └──────────────────┘            │
       │           ┌──────────────────┐            │
       └──────────▶│  Retrieval:      │◀───────────┘
                    │  Vector Search   │
                    │  + BM25          │
                    │  + Rerank (opt)  │
                    └──────┬───────────┘
                           ▼
                    ┌──────────────────┐
                    │  Generation:     │
                    │  GigaChat API    │
                    └──────────────────┘
```

### Компоненты

| Компонент | Технология | Назначение |
|-----------|-----------|-----------|
| **API** | FastAPI + Uvicorn | Приём файлов, обработка запросов |
| **Ingestion** | pdfplumber, LangChain | Извлечение текста, чанкинг, векторизация |
| **Vector DB** | Qdrant | Хранение и поиск эмбеддингов |
| **Embeddings** | multilingual-e5-large (HuggingFace) | Семантические векторы текста |
| **Retrieval** | EnsembleRetriever (Vector + BM25) | Гибридный поиск |
| **Reranking** | Cohere Rerank (опционально) | Повторное ранжирование результатов |
| **Generation** | GigaChat API | Формирование ответа на русском |
| **Evaluation** | DeepEval | Оценка качества (Faithfulness, Relevancy) |
| **Infrastructure** | Docker, Docker Compose | Контейнеризация |

---

## Быстрый старт

### 1. Клонирование и настройка

```bash
git clone https://github.com/your-username/contract-analyzer-ai.git
cd contract-analyzer-ai
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

### 2. Настройка переменных окружения

```bash
cp .env.example .env
# Отредактируйте .env:
# - GIGACHAT_CREDENTIALS: ваш ключ доступа к GigaChat
# - COHERE_API_KEY: опционально, для ре-ранжирования
```

### 3. Запуск Qdrant (через Docker)

```bash
docker-compose up -d qdrant
# Проверка: curl http://localhost:6333/collections
```

### 4. Запуск приложения

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Или полный Docker-запуск:

```bash
docker-compose up --build
```

---

## API Usage

### Health Check

```bash
curl http://localhost:8000/health
```

### Загрузка PDF

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@contract.pdf"
```

**Ответ:**
```json
{
  "status": "success",
  "filename": "contract.pdf",
  "chunks": 47,
  "collection_name": "contracts"
}
```

### Вопрос по договору

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Какая цена договора?"}'
```

**Ответ:**
```json
{
  "answer": "Цена договора составляет 1 500 000 рублей согласно разделу 3.1.",
  "sources": ["contract.pdf", "contract.pdf"]
}
```

### Документация Swagger

http://localhost:8000/docs

---

## Оценка качества

```python
python -c "
from app.evaluation import evaluate_response
result = evaluate_response(
    question='Какая цена договора?',
    actual_output='Цена составляет 100 000 рублей.',
    retrieval_context=['Цена договора: 100 000 рублей'],
)
print(result)
"
```

Метрики:
- **Faithfulness** — насколько ответ соответствует контексту
- **Answer Relevancy** — насколько ответ релевантен вопросу

---

## Структура проекта

```
contract-analyzer-ai/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI приложение
│   ├── config.py            # Настройки из .env
│   ├── models.py            # Pydantic схемы
│   ├── ingestion.py         # PDF → текст → чанкинг → Qdrant
│   ├── retrieval.py         # Гибридный поиск + ре-ранжирование
│   ├── generation.py        # Промптинг и вызов GigaChat
│   └── evaluation.py        # DeepEval оценка
├── tests/
│   ├── test_ingestion.py
│   ├── test_retrieval.py
│   └── test_generation.py
├── data/                    # Тестовые PDF
├── docker-compose.yml       # Qdrant + приложение
├── Dockerfile
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Технологии

- **Python 3.11** — язык разработки
- **FastAPI** — веб-фреймворк
- **LangChain** — оркестрация RAG-пайплайна
- **Qdrant** — векторная база данных
- **HuggingFace Embeddings** — мультиязычные эмбеддинги (E5-large)
- **BM25** — лексический поиск
- **Cohere Rerank** — нейросетевой ре-ранкер
- **GigaChat** — генерация ответов на русском
- **DeepEval** — оценка качества RAG
- **Docker** — контейнеризация

---

## Планы по улучшению

- [ ] JWT-аутентификация
- [ ] Redis-кэширование частых вопросов
- [ ] Streamlit-интерфейс для демонстрации
- [ ] Поддержка DOCX и других форматов
- [ ] CI/CD через GitHub Actions
- [ ] Публикация статьи на Habr

---

## Лицензия

MIT
