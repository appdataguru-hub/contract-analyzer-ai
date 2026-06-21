import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "contracts")
TIMEOUT_SECONDS = 120


def _headers() -> dict[str, str]:
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    return headers


def check_health(backend_url: str | None = None) -> bool:
    url = f"{backend_url or BACKEND_URL}/health"
    try:
        with httpx.Client(timeout=5) as client:
            resp = client.get(url)
            return resp.status_code == 200 and resp.json().get("status") == "ok"
    except Exception:
        return False


def upload_pdf(
    file_bytes: bytes,
    filename: str,
    backend_url: str | None = None,
) -> dict[str, Any]:
    url = f"{backend_url or BACKEND_URL}/upload"
    headers = {}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"

    with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
        resp = client.post(url, files={"file": (filename, file_bytes, "application/pdf")}, headers=headers)

    if resp.status_code == 413:
        raise ValueError("Файл превышает максимальный размер")
    if resp.status_code == 400:
        detail = resp.json().get("detail", "Некорректный файл")
        raise ValueError(detail)
    if resp.status_code == 500:
        detail = resp.json().get("detail", "Ошибка сервера при обработке PDF")
        raise RuntimeError(detail)

    resp.raise_for_status()
    return resp.json()


def ask_question(
    question: str,
    collection_name: str = COLLECTION_NAME,
    backend_url: str | None = None,
) -> dict[str, Any]:
    url = f"{backend_url or BACKEND_URL}/ask"
    payload = {"question": question, "collection_name": collection_name}

    with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
        resp = client.post(url, json=payload, headers=_headers())

    if resp.status_code == 404:
        detail = resp.json().get("detail", "Коллекция не найдена. Загрузите документ.")
        raise ValueError(detail)
    if resp.status_code == 500:
        detail = resp.json().get("detail", "Ошибка генерации ответа")
        raise RuntimeError(detail)

    resp.raise_for_status()
    return resp.json()


def fetch_metrics(backend_url: str | None = None) -> dict[str, Any] | None:
    url = f"{backend_url or BACKEND_URL}/metrics"
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.json()
    except Exception:
        return None


def get_app_info() -> dict[str, str]:
    return {
        "name": "Contract Analyzer AI",
        "version": "1.0.0",
        "backend": BACKEND_URL,
    }
