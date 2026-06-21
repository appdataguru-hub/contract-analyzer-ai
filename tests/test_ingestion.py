import os
import tempfile

import pytest
from app.ingestion import (
    chunk_documents,
    create_document_chunks,
    extract_text_from_pdf,
    extract_text_from_pdf_bytes,
    PDFExtractionError,
    get_embeddings,
)


class TestChunkDocuments:
    def test_chunk_empty_string(self):
        chunks = chunk_documents("", chunk_size=100, chunk_overlap=0)
        assert chunks == []

    def test_chunk_short_text(self):
        text = "Короткий текст договора."
        chunks = chunk_documents(text, chunk_size=1000, chunk_overlap=0)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_multiple_parts(self):
        text = "Предложение первое. " * 50
        chunks = chunk_documents(text, chunk_size=200, chunk_overlap=20)
        assert len(chunks) > 1
        assert all(isinstance(c, str) for c in chunks)

    def test_chunk_exact_boundary(self):
        text = "А" * 100
        chunks = chunk_documents(text, chunk_size=50, chunk_overlap=0)
        assert len(chunks) == 2
        assert len(chunks[0]) <= 50
        assert len(chunks[1]) <= 50

    def test_chunk_overlap_exact(self):
        text = "X" * 200
        chunks = chunk_documents(text, chunk_size=100, chunk_overlap=50)
        assert len(chunks) == 3
        assert all(len(c) <= 100 for c in chunks)

    def test_chunk_one_char_chunk_size(self):
        text = "ABC"
        chunks = chunk_documents(text, chunk_size=1, chunk_overlap=0)
        assert len(chunks) >= 2

    def test_chunk_overlap_larger_than_chunk_size_raises(self):
        text = "Текст для проверки устойчивости к неправильным параметрам."
        with pytest.raises(ValueError, match="larger chunk overlap"):
            chunk_documents(text, chunk_size=50, chunk_overlap=100)

    def test_chunk_unicode_text(self):
        text = "🔴 Договор на русском языке с юникодом ©®™."
        chunks = chunk_documents(text, chunk_size=500, chunk_overlap=0)
        assert len(chunks) == 1
        assert "🔴" in chunks[0]

    def test_chunk_only_newlines(self):
        chunks = chunk_documents("\n\n\n\n", chunk_size=10, chunk_overlap=0)
        assert isinstance(chunks, list)


class TestCreateDocumentChunks:
    def test_create_docs_with_source(self):
        text = "Текст договора. Ещё текст."
        docs = create_document_chunks(text, source="test.pdf")
        assert len(docs) == 1
        assert docs[0].metadata["source"] == "test.pdf"
        assert docs[0].metadata["chunk_index"] == 0
        assert "Текст договора" in docs[0].page_content

    def test_chunk_index_increments(self):
        text = "Предложение. " * 20
        docs = create_document_chunks(text, source="doc.pdf", chunk_size=50, chunk_overlap=0)
        for i, doc in enumerate(docs):
            assert doc.metadata["chunk_index"] == i

    def test_create_docs_with_empty_text(self):
        docs = create_document_chunks("", source="empty.pdf")
        assert docs == []

    def test_metadata_chunk_count(self):
        text = "Раз. Два. Три. " * 10
        docs = create_document_chunks(text, source="test.pdf", chunk_size=30, chunk_overlap=0)
        for doc in docs:
            assert doc.metadata["chunk_count"] == len(docs)

    def test_source_inherited_to_all_chunks(self):
        text = "Слово. " * 100
        docs = create_document_chunks(text, source="multi.pdf", chunk_size=50, chunk_overlap=0)
        assert len(docs) > 1
        for doc in docs:
            assert doc.metadata["source"] == "multi.pdf"

    def test_whitespace_only_text(self):
        docs = create_document_chunks("   \n\n   ", source="ws.pdf")
        assert len(docs) >= 0


class TestExtractTextFromPdf:
    def _make_simple_pdf(self) -> str:
        pdf_content = (
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
            b"<< /Length 55 >>\n"
            b"stream\n"
            b"BT /F1 24 Tf 100 700 Td (Hello Contract) Tj ET\n"
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
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp.write(pdf_content)
        tmp.close()
        return tmp.name

    def test_extract_text_from_pdf(self):
        pdf_path = self._make_simple_pdf()
        try:
            text = extract_text_from_pdf(pdf_path)
            assert isinstance(text, str)
            assert len(text) > 0
        finally:
            os.unlink(pdf_path)

    def test_extract_text_from_pdf_bytes(self):
        pdf_path = self._make_simple_pdf()
        try:
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            text = extract_text_from_pdf_bytes(pdf_bytes)
            assert isinstance(text, str)
            assert len(text) > 0
        finally:
            os.unlink(pdf_path)

    def test_extract_empty_bytes_raises(self):
        with pytest.raises(PDFExtractionError):
            extract_text_from_pdf_bytes(b"")

    def test_extract_nonexistent_file_raises(self):
        with pytest.raises(PDFExtractionError):
            extract_text_from_pdf("/tmp/nonexistent_file_12345.pdf")

    def test_corrupted_pdf_bytes_raises(self):
        with pytest.raises(PDFExtractionError):
            extract_text_from_pdf_bytes(b"this is not a pdf at all")

    def test_extract_from_zero_pages_pdf(self):
        content = (
            b"%PDF-1.4\n"
            b"1 0 obj\n"
            b"<< /Type /Catalog /Pages 2 0 R >>\n"
            b"endobj\n"
            b"2 0 obj\n"
            b"<< /Type /Pages /Kids [] /Count 0 >>\n"
            b"endobj\n"
            b"xref\n"
            b"0 3\n"
            b"0000000000 65535 f \n"
            b"0000000009 00000 n \n"
            b"0000000058 00000 n \n"
            b"trailer\n"
            b"<< /Size 3 /Root 1 0 R >>\n"
            b"startxref\n"
            b"107\n"
            b"%%EOF\n"
        )
        with pytest.raises(PDFExtractionError, match="No extractable text"):
            extract_text_from_pdf_bytes(content)

    def test_extract_pdf_with_special_chars_in_path(self):
        pdf_path = self._make_simple_pdf()
        weird_path = pdf_path.replace(".pdf", "_weird_путь_100%.pdf")
        os.rename(pdf_path, weird_path)
        try:
            text = extract_text_from_pdf(weird_path)
            assert isinstance(text, str)
            assert len(text) > 0
        finally:
            if os.path.exists(weird_path):
                os.unlink(weird_path)


class TestGetEmbeddings:
    def test_returns_singleton(self):
        e1 = get_embeddings()
        e2 = get_embeddings()
        assert e1 is e2


class TestLoadPdfBytesToStore:
    def test_rejects_empty_bytes(self):
        with pytest.raises(PDFExtractionError):
            from app.ingestion import load_pdf_bytes_to_store
            load_pdf_bytes_to_store(b"", "empty.pdf")
