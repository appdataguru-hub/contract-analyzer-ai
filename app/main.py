from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.models import QuestionRequest, AnswerResponse, UploadResponse
from app.ingestion import load_pdf_bytes_to_store
from app.retrieval import hybrid_search
from app.generation import generate_answer
from app.config import COLLECTION_NAME, TOP_K

import logging

logger = logging.getLogger(__name__)

document_store: dict[str, dict] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Contract Analyzer AI запущен")
    yield
    logger.info("Contract Analyzer AI остановлен")


app = FastAPI(
    title="Contract Analyzer AI",
    description="Веб-сервис для анализа договоров с помощью гибридного RAG и GigaChat",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Только PDF файлы поддерживаются",
        )

    content = await file.read()

    if len(content) == 0:
        raise HTTPException(
            status_code=400,
            detail="Файл пуст",
        )

    collection = COLLECTION_NAME

    try:
        docs, vector_store = load_pdf_bytes_to_store(
            content=content,
            filename=file.filename,
            collection_name=collection,
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке PDF: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при обработке PDF: {str(e)}",
        )

    document_store[collection] = {
        "documents": docs,
        "vector_store": vector_store,
        "filename": file.filename,
    }

    return UploadResponse(
        status="success",
        filename=file.filename,
        chunks=len(docs),
        collection_name=collection,
    )


@app.post("/ask", response_model=AnswerResponse)
async def ask_question(req: QuestionRequest):
    collection = req.collection_name

    if collection not in document_store:
        raise HTTPException(
            status_code=404,
            detail=f"Коллекция '{collection}' не найдена. Сначала загрузите документ через /upload",
        )

    store_data = document_store[collection]
    docs = store_data["documents"]

    try:
        retrieved_docs = hybrid_search(
            question=req.question,
            documents=docs,
            collection_name=collection,
            k=TOP_K,
        )
    except Exception as e:
        logger.error(f"Ошибка при поиске: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при поиске: {str(e)}",
        )

    if not retrieved_docs:
        raise HTTPException(
            status_code=404,
            detail="Не удалось найти релевантные фрагменты в документе",
        )

    context_parts = []
    source_info = []
    for doc in retrieved_docs:
        context_parts.append(doc.page_content)
        src = doc.metadata.get("source", "unknown")
        source_info.append(src)

    context = "\n\n---\n\n".join(context_parts)

    try:
        answer = generate_answer(req.question, context)
    except Exception as e:
        logger.error(f"Ошибка при генерации ответа GigaChat: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при генерации ответа: {str(e)}",
        )

    return AnswerResponse(
        answer=answer,
        sources=source_info,
    )
