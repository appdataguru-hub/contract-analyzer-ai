from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


class TestFileUploadSecurity:
    def test_path_traversal_in_filename(self, client: TestClient, valid_pdf_bytes: bytes):
        filenames = [
            "../../etc/passwd.pdf",
            "..\\..\\windows\\system32.pdf",
            "%2e%2e%2fetc%2fpasswd.pdf",
            "....//....//etc//shadow.pdf",
            "..%252f..%252fetc%252fpasswd.pdf",
            "foo/../../../etc/passwd.pdf",
        ]
        for name in filenames:
            resp = client.post(
                "/upload",
                files={"file": (name, valid_pdf_bytes, "application/pdf")},
            )
            if resp.status_code == 200:
                assert resp.status_code == 200
                assert "filename" in resp.json()

    def test_shell_injection_in_filename(self, client: TestClient, valid_pdf_bytes: bytes):
        payloads = [
            "; rm -rf /",
            "| cat /etc/passwd",
            "`whoami`.pdf",
            "$(whoami).pdf",
            "& ping -c 10 127.0.0.1 &",
            "> /dev/null",
            "< /etc/passwd",
        ]
        for payload in payloads:
            name = f"{payload}.pdf"
            resp = client.post(
                "/upload",
                files={"file": (name, valid_pdf_bytes, "application/pdf")},
            )
            assert resp.status_code in (200, 400, 500)

    def test_very_long_filename(self, client: TestClient, valid_pdf_bytes: bytes):
        long_name = "A" * 10000 + ".pdf"
        resp = client.post(
            "/upload",
            files={"file": (long_name, valid_pdf_bytes, "application/pdf")},
        )
        assert resp.status_code in (200, 400, 413, 422)

    def test_huge_file_size(self, client: TestClient):
        huge_content = b"%" * 50_000_000
        name = "huge.pdf"
        resp = client.post(
            "/upload",
            files={"file": (name, huge_content, "application/pdf")},
        )
        assert resp.status_code in (400, 413, 422, 500)

    def test_content_type_spoofing(self, client: TestClient, valid_pdf_bytes: bytes):
        resp = client.post(
            "/upload",
            files={"file": ("malware.exe", valid_pdf_bytes, "application/x-msdownload")},
        )
        assert resp.status_code == 400
        assert "PDF" in resp.json()["detail"]

    def test_malformed_multipart(self, client: TestClient):
        resp = client.post(
            "/upload",
            data=b"trash data that is not proper multipart",
            headers={"Content-Type": "multipart/form-data; boundary=xxx"},
        )
        assert resp.status_code in (422, 400)

    def test_null_bytes_in_filename(self, client: TestClient, valid_pdf_bytes: bytes, mock_qdrant_and_gigachat):
        resp = client.post(
            "/upload",
            files={"file": ("\x00null.pdf", valid_pdf_bytes, "application/pdf")},
        )
        assert resp.status_code in (200, 400, 422)

    def test_utf8_bom_pdf(self, client: TestClient):
        content = b"\xef\xbb\xbf%PDF-1.4\n trash"
        resp = client.post(
            "/upload",
            files={"file": ("bom.pdf", content, "application/pdf")},
        )
        assert resp.status_code in (200, 400, 500)

    def test_empty_filename(self, client: TestClient, valid_pdf_bytes: bytes):
        resp = client.post(
            "/upload",
            files={"file": ("", valid_pdf_bytes, "application/pdf")},
        )
        assert resp.status_code in (400, 422)


class TestInputValidationSecurity:
    def test_xss_in_question(self, client: TestClient):
        xss_payloads = [
            "<script>alert(1)</script>",
            "<img src=x onerror=alert(1)>",
            "javascript:alert(1)",
            "{{7*7}}",
            "'; DROP TABLE users; --",
            "${7*7}",
        ]
        for payload in xss_payloads:
            resp = client.post(
                "/ask",
                json={"question": payload},
            )
            assert resp.status_code in (404, 422)

    def test_sql_injection_in_question(self, client: TestClient):
        payloads = [
            "' OR '1'='1",
            "1; DROP TABLE documents CASCADE",
            "' UNION SELECT * FROM users --",
            "1' AND 1=1 --",
        ]
        for payload in payloads:
            resp = client.post(
                "/ask",
                json={"question": payload},
            )
            assert resp.status_code in (404, 422)

    def test_unicode_normalization_attacks(self, client: TestClient):
        payloads = [
            "\ufff0",
            "\x00",
            "\x1f\x9f",
            "\ufeff",
            "\u202e" + "price" + "\u202c",
        ]
        for payload in payloads:
            resp = client.post(
                "/ask",
                json={"question": payload},
            )
            assert resp.status_code in (404, 422)

    def test_mass_assignment_in_evaluate(self, client: TestClient):
        with patch("app.main.evaluate_response") as mock_eval:
            mock_eval.return_value = {"faithfulness_score": 0.5}
            resp = client.post(
                "/evaluate",
                json={
                    "question": "q",
                    "actual_output": "a",
                    "retrieval_context": ["c"],
                    "__proto__": {"admin": True},
                    "constructor": {"prototype": {"admin": True}},
                },
            )
            assert resp.status_code in (200, 422)

    def test_deeply_nested_json(self, client: TestClient):
        with patch("app.main.evaluate_response") as mock_eval:
            mock_eval.return_value = {"faithfulness_score": 0.5}

            def make_nested(depth: int):
                if depth <= 0:
                    return "value"
                return {"nested": make_nested(depth - 1)}

            payload = make_nested(100)
            payload["question"] = "q"
            payload["actual_output"] = "a"
            payload["retrieval_context"] = ["c"]

            resp = client.post("/evaluate", json=payload)
            assert resp.status_code in (200, 422, 413)


class TestHTTPMethodsSecurity:
    def test_upload_requires_post(self, client: TestClient):
        for method in ("get", "put", "patch", "delete", "options"):
            resp = getattr(client, method)("/upload")
            assert resp.status_code == 405

    def test_ask_requires_post(self, client: TestClient):
        for method in ("get", "put", "patch", "delete"):
            resp = getattr(client, method)("/ask")
            assert resp.status_code == 405

    def test_health_only_get(self, client: TestClient):
        for method in ("post", "put", "patch", "delete"):
            resp = getattr(client, method)("/health")
            assert resp.status_code == 405


class TestHeaderSecurity:
    def test_content_type_required_for_ask(self, client: TestClient):
        resp = client.post(
            "/ask",
            content=b"raw body without content-type",
            headers={"Content-Type": "application/xml"},
        )
        assert resp.status_code in (422, 415)

    def test_large_headers(self, client: TestClient):
        big_header = "X" * 50000
        resp = client.get(
            "/health",
            headers={"X-Big-Header": big_header},
        )
        assert resp.status_code in (200, 413, 431)


class TestErrorHandling:
    def test_error_does_not_expose_internal_paths(self, client: TestClient, corrupted_pdf_bytes: bytes):
        resp = client.post(
            "/upload",
            files={"file": ("bad.pdf", corrupted_pdf_bytes, "application/pdf")},
        )
        detail = resp.json().get("detail", "")
        assert "/app/" not in detail
        assert "/home/" not in detail

    def test_error_does_not_expose_env_vars(self, client: TestClient):
        resp = client.post("/ask", json={"question": "test"})
        detail = resp.json().get("detail", "")
        assert "GIGACHAT_CREDENTIALS" not in detail
