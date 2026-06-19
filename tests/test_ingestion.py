import pytest
from app.ingestion import chunk_documents, create_document_chunks


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
