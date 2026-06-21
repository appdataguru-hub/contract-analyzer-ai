import io
import os
import tempfile
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from langchain_core.documents import Document
from langchain_core.runnables import Runnable

from app.main import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


def _make_simple_pdf_bytes(text: str = "Hello Contract") -> bytes:
    escaped = text.encode("ascii", errors="replace")
    stream_data = b"BT /F1 24 Tf 100 700 Td (" + escaped + b") Tj ET"
    content = (
        b"%PDF-1.4\n"
        b"1 0 obj\n"
        b"<< /Type /Catalog /Pages 2 0 R >>\n"
        b"endobj\n"
        b"2 0 obj\n"
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
        b"endobj\n"
        b"3 0 obj\n"
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]\n"
        b"   /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\n"
        b"endobj\n"
        b"4 0 obj\n"
        b"<< /Length " + str(len(stream_data)).encode() + b" >>\n"
        b"stream\n" + stream_data + b"\n"
        b"endstream\n"
        b"endobj\n"
        b"5 0 obj\n"
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\n"
        b"endobj\n"
        b"xref\n"
        b"0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000266 00000 n \n"
        b"0000000370 00000 n \n"
        b"trailer\n"
        b"<< /Size 6 /Root 1 0 R >>\n"
        b"startxref\n"
        b"453\n"
        b"%%EOF\n"
    )
    return content


@pytest.fixture
def valid_pdf_bytes() -> bytes:
    return _make_simple_pdf_bytes("Test Contract Document v2")


@pytest.fixture
def valid_pdf_path(valid_pdf_bytes: bytes) -> Generator[str, None, None]:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp.write(valid_pdf_bytes)
    tmp.close()
    yield tmp.name
    os.unlink(tmp.name)


@pytest.fixture
def corrupted_pdf_bytes() -> bytes:
    return b"%PDF-1.4\ncorrupted\n%%EOF"


@pytest.fixture
def empty_pdf_bytes() -> bytes:
    return b""


@pytest.fixture
def sample_documents() -> list[Document]:
    return [
        Document(page_content="Арендатор обязуется оплачивать арендную плату ежемесячно.", metadata={"source": "doc.pdf", "chunk_index": 0}),
        Document(page_content="Стороны пришли к соглашению о расторжении договора.", metadata={"source": "doc.pdf", "chunk_index": 1}),
        Document(page_content="Цена договора составляет 1 500 000 рублей.", metadata={"source": "doc.pdf", "chunk_index": 2}),
        Document(page_content="Срок действия договора: с 1 января по 31 декабря 2024 года.", metadata={"source": "doc.pdf", "chunk_index": 3}),
    ]


@pytest.fixture(autouse=True)
def clear_document_store():
    from app.main import document_store
    document_store.clear()
    yield
    document_store.clear()


@pytest.fixture
def mock_qdrant_and_gigachat():
    with patch("app.ingestion.QdrantVectorStore.from_documents") as mock_store:
        mock_vs = MagicMock()
        mock_store.return_value = mock_vs

        with patch("app.retrieval.get_vector_store") as mock_get_vs:
            mock_get_vs.return_value = mock_vs
            mock_vector_retriever = MagicMock(spec=Runnable)
            mock_vector_retriever.invoke.return_value = []
            mock_vs.as_retriever.return_value = mock_vector_retriever

            yield mock_store, mock_get_vs


@pytest.fixture
def pdf_with_all_charset_filename() -> str:
    return "déjà_vu_合约_договор_100%.pdf"
