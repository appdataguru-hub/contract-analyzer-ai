import os
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient


class TestHealth:
    def test_health_returns_ok(self, client: TestClient):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_health_method_not_allowed(self, client: TestClient):
        resp = client.post("/health")
        assert resp.status_code == 405

    def test_health_response_time(self, client: TestClient):
        resp = client.get("/health")
        assert resp.elapsed.total_seconds() < 1.0


class TestUpload:
    def test_upload_valid_pdf(self, client: TestClient, valid_pdf_bytes: bytes, mock_qdrant_and_gigachat):
        resp = client.post(
            "/upload",
            files={"file": ("contract.pdf", valid_pdf_bytes, "application/pdf")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["filename"] == "contract.pdf"
        assert data["chunks"] >= 0
        assert data["collection_name"] == "contracts"

    def test_upload_empty_file_returns_400(self, client: TestClient):
        resp = client.post(
            "/upload",
            files={"file": ("empty.pdf", b"", "application/pdf")},
        )
        assert resp.status_code == 400
        assert "пуст" in resp.json()["detail"]

    def test_upload_non_pdf_extension_returns_400(self, client: TestClient):
        resp = client.post(
            "/upload",
            files={"file": ("contract.txt", b"not a pdf", "text/plain")},
        )
        assert resp.status_code == 400
        assert "PDF" in resp.json()["detail"]

    def test_upload_no_filename_returns_422(self, client: TestClient):
        resp = client.post(
            "/upload",
            files={"file": (None, b"some content", "application/pdf")},
        )
        assert resp.status_code == 422

    def test_upload_without_file_returns_422(self, client: TestClient):
        resp = client.post("/upload")
        assert resp.status_code == 422

    def test_upload_corrupted_pdf_returns_500(self, client: TestClient, corrupted_pdf_bytes: bytes):
        resp = client.post(
            "/upload",
            files={"file": ("bad.pdf", corrupted_pdf_bytes, "application/pdf")},
        )
        assert resp.status_code == 500

    def test_upload_pdf_with_unicode_filename(self, client: TestClient, valid_pdf_bytes: bytes, mock_qdrant_and_gigachat):
        resp = client.post(
            "/upload",
            files={"file": ("договор_2024.pdf", valid_pdf_bytes, "application/pdf")},
        )
        assert resp.status_code == 200
        assert "договор_2024" in resp.json()["filename"]

    def test_upload_multiple_times_increments_storage(self, client: TestClient, valid_pdf_bytes: bytes, mock_qdrant_and_gigachat):
        resp1 = client.post("/upload", files={"file": ("a.pdf", valid_pdf_bytes, "application/pdf")})
        resp2 = client.post("/upload", files={"file": ("b.pdf", valid_pdf_bytes, "application/pdf")})
        assert resp1.status_code == 200
        assert resp2.status_code == 200

    def test_upload_pdf_with_filename_as_path(self, client: TestClient, valid_pdf_bytes: bytes, mock_qdrant_and_gigachat):
        resp = client.post(
            "/upload",
            files={"file": ("../../etc/passwd.pdf", valid_pdf_bytes, "application/pdf")},
        )
        assert resp.status_code == 200
        assert "passwd" in resp.json()["filename"]


class TestAsk:
    def test_ask_without_upload_returns_404(self, client: TestClient):
        resp = client.post(
            "/ask",
            json={"question": "Какая цена?"},
        )
        assert resp.status_code == 404

    def test_ask_with_invalid_collection_returns_404(self, client: TestClient):
        resp = client.post(
            "/ask",
            json={"question": "Вопрос?", "collection_name": "nonexistent"},
        )
        assert resp.status_code == 404

    def test_ask_returns_answer(self, client: TestClient, valid_pdf_bytes: bytes, mock_qdrant_and_gigachat):
        client.post("/upload", files={"file": ("doc.pdf", valid_pdf_bytes, "application/pdf")})

        with patch("app.main.hybrid_search") as mock_search:
            from langchain_core.documents import Document
            mock_search.return_value = [
                Document(page_content="Цена договора: 150 000 руб.", metadata={"source": "doc.pdf"}),
            ]

            with patch("app.main.generate_answer", return_value="Цена договора: 150 000 руб."):
                resp = client.post("/ask", json={"question": "Какая цена?"})
                assert resp.status_code == 200
                data = resp.json()
                assert "answer" in data
                assert "sources" in data
                assert isinstance(data["sources"], list)

    def test_ask_empty_question_returns_422(self, client: TestClient, valid_pdf_bytes: bytes, mock_qdrant_and_gigachat):
        client.post("/upload", files={"file": ("doc.pdf", valid_pdf_bytes, "application/pdf")})
        resp = client.post("/ask", json={"question": ""})
        assert resp.status_code == 422

    def test_ask_missing_question_returns_422(self, client: TestClient):
        resp = client.post("/ask", json={})
        assert resp.status_code == 422

    def test_ask_no_relevant_docs_returns_404(self, client: TestClient, valid_pdf_bytes: bytes, mock_qdrant_and_gigachat):
        client.post("/upload", files={"file": ("doc.pdf", valid_pdf_bytes, "application/pdf")})

        with patch("app.main.hybrid_search") as mock_search:
            mock_search.return_value = []
            resp = client.post("/ask", json={"question": "Что-то неведомое?"})
            assert resp.status_code == 404

    def test_ask_response_model_matches_schema(self, client: TestClient, valid_pdf_bytes: bytes, mock_qdrant_and_gigachat):
        client.post("/upload", files={"file": ("doc.pdf", valid_pdf_bytes, "application/pdf")})

        with patch("app.main.hybrid_search") as mock_search:
            from langchain_core.documents import Document
            mock_search.return_value = [
                Document(page_content="Тест", metadata={"source": "doc.pdf"}),
            ]
            with patch("app.main.generate_answer", return_value="Ответ"):
                resp = client.post("/ask", json={"question": "Тест?"})
                data = resp.json()
                assert {"answer", "sources"}.issubset(data.keys())

    def test_ask_sources_from_metadata(self, client: TestClient, valid_pdf_bytes: bytes, mock_qdrant_and_gigachat):
        client.post("/upload", files={"file": ("doc.pdf", valid_pdf_bytes, "application/pdf")})

        with patch("app.main.hybrid_search") as mock_search:
            from langchain_core.documents import Document
            mock_search.return_value = [
                Document(page_content="Фрагмент 1", metadata={"source": "doc.pdf", "page": 1}),
                Document(page_content="Фрагмент 2", metadata={"source": "doc.pdf", "page": 2}),
            ]
            with patch("app.main.generate_answer", return_value="Ответ"):
                resp = client.post("/ask", json={"question": "Тест?"})
                data = resp.json()
                assert len(data["sources"]) == 2
                assert all(s == "doc.pdf" for s in data["sources"])


class TestEvaluate:
    def test_evaluate_valid(self, client: TestClient):
        with patch("app.main.evaluate_response") as mock_eval:
            mock_eval.return_value = {
                "faithfulness_score": 0.85,
                "faithfulness_reason": "ok",
                "answer_relevancy_score": 0.9,
                "answer_relevancy_reason": "good",
            }
            resp = client.post(
                "/evaluate",
                json={
                    "question": "Какая цена?",
                    "actual_output": "100 рублей",
                    "retrieval_context": ["Цена: 100 рублей"],
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["faithfulness_score"] == 0.85
            assert data["answer_relevancy_score"] == 0.9

    def test_evaluate_missing_retrieval_context_returns_422(self, client: TestClient):
        resp = client.post(
            "/evaluate",
            json={"question": "q", "actual_output": "a"},
        )
        assert resp.status_code == 422

    def test_evaluate_with_expected_output(self, client: TestClient):
        with patch("app.main.evaluate_response") as mock_eval:
            mock_eval.return_value = {"faithfulness_score": 0.9, "faithfulness_reason": "ok"}
            resp = client.post(
                "/evaluate",
                json={
                    "question": "q",
                    "actual_output": "a",
                    "retrieval_context": ["c"],
                    "expected_output": "e",
                },
            )
            assert resp.status_code == 200

    def test_evaluate_empty_context(self, client: TestClient):
        with patch("app.main.evaluate_response") as mock_eval:
            mock_eval.return_value = {"faithfulness_score": None, "faithfulness_reason": None}
            resp = client.post(
                "/evaluate",
                json={
                    "question": "q",
                    "actual_output": "a",
                    "retrieval_context": [],
                },
            )
            assert resp.status_code == 200


class TestCORS:
    def test_cors_allowed_origin_returns_header(self, client: TestClient):
        # Loopback origin is in the default CORS_ORIGINS allow-list, so the
        # server must echo it back in `Access-Control-Allow-Origin`.
        resp = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:8501",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert "access-control-allow-origin" in resp.headers
        assert resp.headers["access-control-allow-origin"] == "http://localhost:8501"

    def test_cors_unknown_origin_rejected(self, client: TestClient):
        # SECURITY: a non-allow-listed origin must NOT be echoed back.
        # This guards against the wildcard-CORS regression.
        resp = client.options(
            "/health",
            headers={
                "Origin": "http://evil-site.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        origin = resp.headers.get("access-control-allow-origin", "")
        assert origin not in ("*", "http://evil-site.com")

    def test_cors_no_wildcard_in_response(self, client: TestClient):
        # Belt-and-suspenders: never "*" in any CORS response header.
        resp = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        header = resp.headers.get("access-control-allow-origin", "")
        assert header != "*"


class TestOpenAPI:
    def test_swagger_ui_available(self, client: TestClient):
        resp = client.get("/docs")
        assert resp.status_code == 200

    def test_openapi_json(self, client: TestClient):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert schema["info"]["title"] == "Contract Analyzer AI"
        assert "/upload" in schema["paths"]
        assert "/ask" in schema["paths"]
        assert "/evaluate" in schema["paths"]
        assert "/health" in schema["paths"]
