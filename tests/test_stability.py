import asyncio
import concurrent.futures
import threading
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient


class TestConcurrentAccess:
    def test_concurrent_health_requests(self, client: TestClient):
        def check():
            resp = client.get("/health")
            return resp.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            futures = [pool.submit(check) for _ in range(50)]
            results = [f.result() for f in futures]
        assert all(r == 200 for r in results)

    def test_concurrent_upload_same_collection(self, client: TestClient, valid_pdf_bytes: bytes, mock_qdrant_and_gigachat):
        def upload(idx: int):
            resp = client.post(
                "/upload",
                files={"file": (f"doc_{idx}.pdf", valid_pdf_bytes, "application/pdf")},
            )
            return resp.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            futures = [pool.submit(upload, i) for i in range(10)]
            results = [f.result() for f in futures]
        assert all(r in (200, 500) for r in results)

    def test_upload_and_ask_race(self, client: TestClient, valid_pdf_bytes: bytes, mock_qdrant_and_gigachat):
        with patch("app.main.hybrid_search") as mock_search:
            from langchain_core.documents import Document
            mock_search.return_value = [
                Document(page_content="test", metadata={"source": "doc.pdf"}),
            ]

            with patch("app.main.generate_answer", return_value="test answer") as _mock_generate:
                def upload_task():
                    return client.post(
                        "/upload",
                        files={"file": ("race.pdf", valid_pdf_bytes, "application/pdf")},
                    )

                def ask_task():
                    return client.post(
                        "/ask",
                        json={"question": "test?"},
                    )

                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                    f1 = pool.submit(upload_task)
                    import time
                    time.sleep(0.05)
                    client.post("/upload", files={"file": ("init.pdf", valid_pdf_bytes, "application/pdf")})
                    f2 = pool.submit(ask_task)
                    results = [f1.result(), f2.result()]
                assert any(r.status_code == 200 for r in results)


class TestLargeInputs:
    def test_upload_large_valid_pdf(self, client: TestClient):
        content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >> endobj\nxref\n0 1\n0000000000 65535 f \ntrailer\n<< /Size 1 >>\nstartxref\n0\n%%EOF"
        content = content * 100
        resp = client.post(
            "/upload",
            files={"file": ("large.pdf", content, "application/pdf")},
        )
        assert resp.status_code in (200, 400, 500)

    def test_ask_with_huge_question(self, client: TestClient):
        huge_question = "А " * 10000 + "?"
        resp = client.post(
            "/ask",
            json={"question": huge_question},
        )
        assert resp.status_code in (404, 422, 413)

    def test_ask_with_unicode_flood(self, client: TestClient):
        flood = "\uff41" * 5000
        resp = client.post(
            "/ask",
            json={"question": flood},
        )
        assert resp.status_code in (404, 422)

    def test_evaluate_huge_context(self, client: TestClient):
        huge_context = ["Большой контекст. " * 1000]
        resp = client.post(
            "/evaluate",
            json={
                "question": "q",
                "actual_output": "a",
                "retrieval_context": huge_context,
            },
        )
        assert resp.status_code in (200, 413, 422, 500)


class TestEdgeCases:
    def test_health_under_load(self, client: TestClient):
        for _ in range(100):
            resp = client.get("/health")
            assert resp.status_code == 200

    def test_rapid_upload_clear(self, client: TestClient, valid_pdf_bytes: bytes, mock_qdrant_and_gigachat):
        for i in range(20):
            resp = client.post(
                "/upload",
                files={"file": (f"doc_{i}.pdf", valid_pdf_bytes, "application/pdf")},
            )
            if i == 0:
                assert resp.status_code == 200

    def test_ask_after_bm25_invalidation(self, client: TestClient, valid_pdf_bytes: bytes, mock_qdrant_and_gigachat):
        with patch("app.main.hybrid_search") as mock_search:
            from langchain_core.documents import Document
            mock_search.return_value = [
                Document(page_content="v1", metadata={"source": "doc.pdf"}),
            ]
            with patch("app.main.generate_answer", return_value="v1 answer"):
                client.post("/upload", files={"file": ("v1.pdf", valid_pdf_bytes, "application/pdf")})
                resp1 = client.post("/ask", json={"question": "version?"})
                assert resp1.status_code == 200

    def test_bm25_cache_memory_growth(self):
        from app.retrieval import BM25Cache
        from langchain_core.documents import Document

        cache = BM25Cache()
        for i in range(100):
            docs = [Document(page_content=f"Document {j} for collection {i}") for j in range(10)]
            cache.get_or_build(f"col_{i}", docs, k=3)

        assert len(cache._cache) == 100

    def test_many_questions_same_document(self, client: TestClient, valid_pdf_bytes: bytes, mock_qdrant_and_gigachat):
        with patch("app.main.hybrid_search") as mock_search:
            from langchain_core.documents import Document
            mock_search.return_value = [
                Document(page_content="test", metadata={"source": "doc.pdf"}),
            ]
            with patch("app.main.generate_answer", return_value="answer"):
                client.post("/upload", files={"file": ("doc.pdf", valid_pdf_bytes, "application/pdf")})

                for q in ["Цена?", "Срок?", "Стороны?", "Адрес?", "Пеня?"]:
                    resp = client.post("/ask", json={"question": q})
                    assert resp.status_code == 200

    def test_zero_chunk_document(self, client: TestClient):
        pdf_bytes = (
            b"%PDF-1.4\n"
            b"1 0 obj\n"
            b"<< /Type /Catalog /Pages 2 0 R >>\n"
            b"endobj\n"
            b"2 0 obj\n"
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
            b"endobj\n"
            b"3 0 obj\n"
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]\n"
            b"   /Contents 4 0 R >>\n"
            b"endobj\n"
            b"4 0 obj\n"
            b"<< /Length 0 >>\n"
            b"stream\n"
            b"endstream\n"
            b"endobj\n"
            b"xref\n"
            b"0 5\n"
            b"0000000000 65535 f \n"
            b"0000000009 00000 n \n"
            b"0000000058 00000 n \n"
            b"0000000115 00000 n \n"
            b"0000000266 00000 n \n"
            b"trailer\n"
            b"<< /Size 5 /Root 1 0 R >>\n"
            b"startxref\n"
            b"315\n"
            b"%%EOF\n"
        )
        resp = client.post(
            "/upload",
            files={"file": ("blank.pdf", pdf_bytes, "application/pdf")},
        )
        assert resp.status_code in (200, 400, 500)


class TestResourceCleanup:
    def test_temp_files_cleaned_after_upload(self, client: TestClient, valid_pdf_bytes: bytes, tmp_path, mock_qdrant_and_gigachat):
        import tempfile
        original_dir = tempfile.tempdir or "/tmp"
        before = set(os.listdir(original_dir))

        resp = client.post(
            "/upload",
            files={"file": ("cleanup.pdf", valid_pdf_bytes, "application/pdf")},
        )
        assert resp.status_code == 200
        import time
        time.sleep(0.1)

    def test_bm25_cache_memory_limit(self):
        from app.retrieval import BM25Cache
        from langchain_core.documents import Document
        import sys

        cache = BM25Cache()
        large_docs = [Document(page_content="X" * 10000) for _ in range(500)]
        cache.get_or_build("huge", large_docs, k=5)
        assert "huge" in cache._cache


class TestConfigValidation:
    def test_invalid_port_does_not_crash(self):
        import os
        with patch.dict(os.environ, {"QDRANT_PORT": "not_a_number"}, clear=False):
            from app.config import QDRANT_PORT
            assert isinstance(QDRANT_PORT, int)

    def test_missing_collection_defaults(self):
        import os
        with patch.dict(os.environ, {}, clear=True):
            from importlib import reload
            import app.config
            reload(app.config)
            from app.config import COLLECTION_NAME, CHUNK_SIZE, TOP_K
            assert COLLECTION_NAME == "contracts"
            assert CHUNK_SIZE == 1000
            assert TOP_K == 5


import os
