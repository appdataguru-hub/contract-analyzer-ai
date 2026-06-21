import logging
import threading
from typing import Optional

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever

from app.config import TOP_K, QDRANT_HOST, QDRANT_PORT
from app.ingestion import get_embeddings

logger = logging.getLogger(__name__)


def get_vector_store(collection_name: str = "contracts") -> QdrantVectorStore:
    client = QdrantClient(
        host=QDRANT_HOST,
        port=QDRANT_PORT,
    )
    return QdrantVectorStore(
        client=client,
        collection_name=collection_name,
        embedding=get_embeddings(),
    )


class BM25Cache:
    """Cache BM25 indices per collection to avoid rebuilding on every query.

    THREAD-SAFETY: all access to ``self._cache`` is guarded by ``self._lock``
    so concurrent requests cannot observe a half-initialized retriever or
    race an invalidate() against a get_or_build().
    """

    def __init__(self) -> None:
        self._cache: dict[str, BM25Retriever] = {}
        self._lock = threading.Lock()

    def get_or_build(
        self,
        collection_name: str,
        documents: list[Document],
        k: int = TOP_K,
    ) -> BM25Retriever:
        # The lock below serialises *all* reads and writes of the cached
        # retriever, including the per-call `k` reset. This eliminates the
        # concurrent-mutation race that arises when two callers hand
        # different `k` values to the same shared retriever instance.
        with self._lock:
            cached = self._cache.get(collection_name)
            if cached is not None:
                logger.debug("BM25Cache hit for collection '%s'", collection_name)
                cached.k = k
                return cached
            logger.info(
                "Building BM25 index for collection '%s' (%d docs)",
                collection_name,
                len(documents),
            )
            retriever = BM25Retriever.from_documents(documents)
            retriever.k = k
            self._cache[collection_name] = retriever
            return retriever

    def invalidate(self, collection_name: str) -> None:
        with self._lock:
            self._cache.pop(collection_name, None)


bm25_cache = BM25Cache()


def build_ensemble_retriever(
    vector_store: QdrantVectorStore,
    documents: list[Document],
    k: int = TOP_K,
    collection_name: str = "default",
) -> EnsembleRetriever:
    vector_retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k},
    )

    bm25_retriever = bm25_cache.get_or_build(
        collection_name=collection_name,
        documents=documents,
        k=k,
    )

    # Weights are equal by default; ``search_kwargs`` on the vector branch
    # already enforces the top-k per call, so BM25's default (k=4 from
    # ``BM25Retriever.from_documents``) is overridden at the ensemble level
    # below.
    ensemble = EnsembleRetriever(
        retrievers=[vector_retriever, bm25_retriever],
        weights=[0.5, 0.5],
    )
    return ensemble


def build_retriever(
    vector_store: QdrantVectorStore,
    documents: list[Document],
    k: int = TOP_K,
    collection_name: str = "default",
) -> BaseRetriever:
    return build_ensemble_retriever(vector_store, documents, k, collection_name)


def hybrid_search(
    question: str,
    documents: list[Document],
    collection_name: str = "contracts",
    k: int = TOP_K,
) -> list[Document]:
    vector_store = get_vector_store(collection_name)
    retriever = build_retriever(vector_store, documents, k, collection_name)
    return retriever.invoke(question)
