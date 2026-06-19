from typing import Optional

from langchain_qdrant import QdrantVectorStore
from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers.document_compressors import CohereRerank
from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_core.documents import Document
from langchain_core.runnables import Runnable

from app.config import COHERE_API_KEY, TOP_K, QDRANT_HOST, QDRANT_PORT, RERANK_ENABLED
from app.ingestion import get_embeddings


def get_vector_store(collection_name: str = "contracts") -> QdrantVectorStore:
    return QdrantVectorStore(
        url=f"http://{QDRANT_HOST}:{QDRANT_PORT}",
        collection_name=collection_name,
        embeddings=get_embeddings(),
    )


def build_ensemble_retriever(
    vector_store: QdrantVectorStore,
    documents: list[Document],
    k: int = TOP_K,
) -> EnsembleRetriever:
    vector_retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k},
    )

    bm25_retriever = BM25Retriever.from_documents(documents)
    bm25_retriever.k = k

    ensemble = EnsembleRetriever(
        retrievers=[vector_retriever, bm25_retriever],
        weights=[0.5, 0.5],
    )
    return ensemble


def build_compression_retriever(
    base_retriever: EnsembleRetriever,
) -> ContextualCompressionRetriever:
    compressor = CohereRerank(
        cohere_api_key=COHERE_API_KEY,
        model="rerank-multilingual-v3.0",
        top_n=TOP_K,
    )
    return ContextualCompressionRetriever(
        base_compressor=compressor,
        base_retriever=base_retriever,
    )


def build_retriever(
    vector_store: QdrantVectorStore,
    documents: list[Document],
    k: int = TOP_K,
) -> Runnable:
    ensemble = build_ensemble_retriever(vector_store, documents, k)
    if RERANK_ENABLED and COHERE_API_KEY:
        return build_compression_retriever(ensemble)
    return ensemble


def hybrid_search(
    question: str,
    documents: list[Document],
    collection_name: str = "contracts",
    k: int = TOP_K,
) -> list[Document]:
    vector_store = get_vector_store(collection_name)
    retriever = build_retriever(vector_store, documents, k)
    return retriever.invoke(question)
