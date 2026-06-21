import logging
import threading
import tempfile
import os

import pdfplumber
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from langchain_community.embeddings import HuggingFaceEmbeddings

from app.config import (
    EMBEDDING_MODEL,
    QDRANT_HOST,
    QDRANT_PORT,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    QDRANT_FORCE_RECREATE,
)

logger = logging.getLogger(__name__)


class PDFExtractionError(Exception):
    """Raised when text extraction from a PDF file fails."""


_embeddings_lock = threading.Lock()
_embeddings: HuggingFaceEmbeddings | None = None


def get_embeddings() -> HuggingFaceEmbeddings:
    """Return a process-wide singleton embedding model (thread-safe).

    Without the lock, concurrent first calls could each instantiate
    HuggingFaceEmbeddings, downloading/caching the model N times.
    """
    global _embeddings
    if _embeddings is None:
        with _embeddings_lock:
            if _embeddings is None:  # double-check under the lock
                _embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    return _embeddings


def extract_text_from_pdf(file_path: str) -> str:
    text_parts: list[str] = []
    try:
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    text_parts.append(f"[Страница {page_num}]\n{page_text}")
    except Exception as e:
        raise PDFExtractionError(f"Failed to extract text from '{file_path}': {e}") from e
    if not text_parts:
        raise PDFExtractionError(f"No extractable text found in '{file_path}'")
    return "\n\n".join(text_parts)


def extract_text_from_pdf_bytes(content: bytes) -> str:
    if not content:
        raise PDFExtractionError("Empty PDF content provided")
    # Use TemporaryDirectory context manager — auto-cleans on exception or
    # interpreter shutdown. The previous NamedTemporaryFile(delete=False) +
    # manual os.unlink pattern leaks files on SIGKILL or uncaught exceptions.
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = os.path.join(tmpdir, "upload.pdf")
        with open(tmp_path, "wb") as tmp:
            tmp.write(content)
        return extract_text_from_pdf(tmp_path)


def chunk_documents(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""],
    )
    return splitter.split_text(text)


def create_document_chunks(
    text: str,
    source: str = "",
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[Document]:
    chunks = chunk_documents(text, chunk_size, chunk_overlap)
    documents = []
    for i, chunk in enumerate(chunks):
        doc = Document(
            page_content=chunk,
            metadata={
                "source": source,
                "chunk_index": i,
                "chunk_count": len(chunks),
            },
        )
        documents.append(doc)
    return documents


def create_vector_store(
    documents: list[Document],
    collection_name: str = "contracts",
) -> QdrantVectorStore:
    embeddings = get_embeddings()

    vector_store = QdrantVectorStore.from_documents(
        documents,
        embeddings,
        url=f"http://{QDRANT_HOST}:{QDRANT_PORT}",
        collection_name=collection_name,
        prefer_grpc=False,
        # BEHAVIOR: When QDRANT_FORCE_RECREATE is true (default) the collection
        # is dropped on every upload — the upload endpoint relies on consumers
        # providing unique collection names to keep multiple documents. Set
        # QDRANT_FORCE_RECREATE=false to switch to append-only mode for
        # multi-document collections.
        force_recreate=QDRANT_FORCE_RECREATE,
    )
    return vector_store


def load_pdf_to_store(
    file_path: str,
    collection_name: str = "contracts",
) -> tuple[list[Document], QdrantVectorStore]:
    text = extract_text_from_pdf(file_path)
    docs = create_document_chunks(text, source=os.path.basename(file_path))
    vector_store = create_vector_store(docs, collection_name)
    return docs, vector_store


def load_pdf_bytes_to_store(
    content: bytes,
    filename: str,
    collection_name: str = "contracts",
) -> tuple[list[Document], QdrantVectorStore]:
    text = extract_text_from_pdf_bytes(content)
    docs = create_document_chunks(text, source=filename)
    vector_store = create_vector_store(docs, collection_name)
    return docs, vector_store
