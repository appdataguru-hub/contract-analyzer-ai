from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware

from app.models import (
    QuestionRequest, AnswerResponse, UploadResponse,
    EvaluateRequest, EvaluateResponse, MetricsResponse,
)
from app.ingestion import load_pdf_bytes_to_store
from app.retrieval import hybrid_search, bm25_cache
from app.generation import generate_answer, generate_answer_fallback
from app.evaluation import evaluate_response
from app.config import (
    COLLECTION_NAME,
    TOP_K,
    API_KEY,
    MAX_FILE_SIZE,
    setup_logging,
    CORS_ORIGINS,
    CORS_ALLOW_CREDENTIALS,
    check_qdrant_health,
    QDRANT_HOST,
    QDRANT_PORT,
)

import logging
import threading
import statistics

logger = logging.getLogger(__name__)

# Concurrency: document_store and bm25_cache are process-local singletons.
# When the app runs under multiple uvicorn workers, requests for the same
# collection may hit different workers — the upload on one worker is invisible
# to the others. A future production fix is to move state to Qdrant (collection
# name persistence) or Redis. For now we at least serialize per-process access
# so two simultaneous uploads cannot leave the cache and store out of sync.
_store_lock = threading.Lock()
document_store: dict[str, dict] = {}

# Live metrics aggregation
_metrics_lock = threading.Lock()
_metrics_store: dict[str, list[dict]] = {
    "faithfulness": [],
    "answer_relevancy": [],
}
_metrics_threshold = 0.7

# Streaming read chunk size (1 MB). Balances memory pressure vs syscalls.
_READ_CHUNK_SIZE = 1024 * 1024


async def read_with_limit(file: UploadFile, max_bytes: int) -> bytes:
    """Read an UploadFile into memory with a hard byte cap.

    SECURITY: rejects payloads > max_bytes *before* allocating memory for them.
    This prevents OOM via a malicious 10 GB upload where the entire body would
    otherwise be loaded before the size check fires.
    """
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_READ_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"Файл превышает максимальный размер {max_bytes // (1024 * 1024)} МБ",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _internal_error(operation: str, exc: Exception) -> HTTPException:
    """Log details internally and return a sanitized 500 to the caller.

    SECURITY: never echo `str(exc)` to the client — it leaks stack traces,
    file paths, library versions, and internal implementation details.
    """
    logger.error("Internal error during %s: %s", operation, exc, exc_info=True)
    return HTTPException(
        status_code=500,
        detail="Internal server error",
    )


security = HTTPBearer(auto_error=False)


async def verify_api_key(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> None:
    if not API_KEY:
        return
    if credentials is None or credentials.credentials != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Contract Analyzer AI запущен")
    if check_qdrant_health():
        logger.info("Qdrant доступен по адресу %s:%s", QDRANT_HOST, QDRANT_PORT)
    else:
        logger.warning("Qdrant НЕ доступен по адресу %s:%s", QDRANT_HOST, QDRANT_PORT)
    yield
    logger.info("Contract Analyzer AI остановлен")


app = FastAPI(
    title="Contract Analyzer AI",
    description="Веб-сервис для анализа договоров с помощью гибридного RAG и GigaChat",
    version="1.0.0",
    lifespan=lifespan,
    contact={
        "name": "Contract Analyzer AI",
        "url": "https://github.com/your-username/contract-analyzer-ai",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    # SECURITY: never "*" + credentials — browsers reject and signals lax posture.
    # Credentials are opt-in per CORS_ALLOW_CREDENTIALS env var.
    allow_credentials=CORS_ALLOW_CREDENTIALS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get(
    "/health",
    summary="Health check",
    tags=["System"],
)
async def health():
    return {"status": "ok"}


@app.post(
    "/upload",
    response_model=UploadResponse,
    summary="Upload a PDF contract",
    tags=["Documents"],
    dependencies=[Depends(verify_api_key)] if API_KEY else [],
)
async def upload_file(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Только PDF файлы поддерживаются",
        )

    content = await read_with_limit(file, MAX_FILE_SIZE)

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
        raise _internal_error("upload_file", e) from e

    # RELIABILITY: invalidate BM25 cache *after* the store is updated and
    # under the same lock that protects subsequent reads so a concurrent
    # /ask is guaranteed to see either the old index or the new one — never
    # a stale retriever pointing at a freshly-loaded Qdrant collection.
    with _store_lock:
        document_store[collection] = {
            "documents": docs,
            "vector_store": vector_store,
            "filename": file.filename,
        }
        bm25_cache.invalidate(collection)

    return UploadResponse(
        status="success",
        filename=file.filename,
        chunks=len(docs),
        collection_name=collection,
    )


@app.post(
    "/ask",
    response_model=AnswerResponse,
    summary="Ask a question about a contract",
    tags=["Documents"],
    dependencies=[Depends(verify_api_key)] if API_KEY else [],
)
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
        raise _internal_error("hybrid_search", e) from e

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
        logger.warning("GigaChat failed, using fallback: %s", e)
        answer = generate_answer_fallback(req.question, context)

    # Auto-evaluate the answer quality
    faithfulness_score = None
    faithfulness_reason = None
    answer_relevancy_score = None
    answer_relevancy_reason = None
    try:
        eval_result = evaluate_response(
            question=req.question,
            actual_output=answer,
            retrieval_context=context_parts,
        )
        faithfulness_score = eval_result["faithfulness_score"]
        faithfulness_reason = eval_result["faithfulness_reason"]
        answer_relevancy_score = eval_result["answer_relevancy_score"]
        answer_relevancy_reason = eval_result["answer_relevancy_reason"]

        with _metrics_lock:
            if faithfulness_score is not None:
                _metrics_store["faithfulness"].append(faithfulness_score)
            if answer_relevancy_score is not None:
                _metrics_store["answer_relevancy"].append(answer_relevancy_score)
    except Exception as e:
        logger.warning("Auto-evaluation failed: %s", e)

    return AnswerResponse(
        answer=answer,
        sources=source_info,
        faithfulness_score=faithfulness_score,
        faithfulness_reason=faithfulness_reason,
        answer_relevancy_score=answer_relevancy_score,
        answer_relevancy_reason=answer_relevancy_reason,
    )


@app.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="Get live aggregated evaluation metrics",
    tags=["Evaluation"],
)
async def get_metrics():
    with _metrics_lock:
        f_scores = list(_metrics_store["faithfulness"])
        r_scores = list(_metrics_store["answer_relevancy"])

    total = len(f_scores)

    def compute(match: list[float], threshold: float) -> dict:
        clean = [s for s in match if s is not None]
        if not clean:
            return {"mean": None, "min": None, "max": None, "status": "N/A"}
        mean = statistics.mean(clean)
        return {
            "mean": round(mean, 2),
            "min": round(min(clean), 2),
            "max": round(max(clean), 2),
            "status": "PASS" if mean >= threshold else "FAIL",
        }

    f = compute(f_scores, _metrics_threshold)
    r = compute(r_scores, _metrics_threshold)

    return MetricsResponse(
        total_evaluations=total,
        faithfulness_mean=f["mean"],
        faithfulness_min=f["min"],
        faithfulness_max=f["max"],
        faithfulness_status=f["status"],
        answer_relevancy_mean=r["mean"],
        answer_relevancy_min=r["min"],
        answer_relevancy_max=r["max"],
        answer_relevancy_status=r["status"],
    )


@app.post(
    "/evaluate",
    response_model=EvaluateResponse,
    summary="Evaluate RAG response quality",
    tags=["Evaluation"],
    dependencies=[Depends(verify_api_key)] if API_KEY else [],
)
async def evaluate(req: EvaluateRequest):
    try:
        result = evaluate_response(
            question=req.question,
            actual_output=req.actual_output,
            retrieval_context=req.retrieval_context,
            expected_output=req.expected_output,
        )
        return EvaluateResponse(**result)
    except Exception as e:
        raise _internal_error("evaluate_response", e) from e
