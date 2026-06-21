import logging
import threading
import time
from typing import Any

from gigachat import GigaChat
from gigachat.models import Messages

from app.config import GIGACHAT_CREDENTIALS, GIGACHAT_SCOPE, GIGACHAT_VERIFY_SSL

logger = logging.getLogger(__name__)


class GigaChatAuthError(Exception):
    pass


class GigaChatResponseError(Exception):
    pass


_giga_lock = threading.Lock()
_giga_client: GigaChat | None = None
_giga_last_used: float = 0
_GIGA_CLIENT_TTL = 1500


def _get_client() -> GigaChat:
    global _giga_client, _giga_last_used

    with _giga_lock:
        now = time.monotonic()
        if _giga_client is not None and (now - _giga_last_used) < _GIGA_CLIENT_TTL:
            return _giga_client

        if not GIGACHAT_CREDENTIALS:
            raise GigaChatAuthError("GIGACHAT_CREDENTIALS not set in .env")

        _giga_client = GigaChat(
            credentials=GIGACHAT_CREDENTIALS,
            scope=GIGACHAT_SCOPE,
            verify_ssl_certs=GIGACHAT_VERIFY_SSL,
            model="GigaChat",
        )
        _giga_last_used = now
        logger.info("GigaChat SDK client initialized")
        return _giga_client


_SYSTEM_PROMPT = (
    "Ты — эксперт по анализу договоров и юридических документов. "
    "Отвечай на русском языке, используя только предоставленный контекст. "
    "Если в контексте недостаточно информации для ответа, "
    "напиши: 'В предоставленном документе недостаточно информации для ответа на этот вопрос.' "
    "Не выдумывай факты. Цитируй номера страниц из контекста, если они указаны."
)


def build_prompt(question: str, context: str) -> list[dict[str, Any]]:
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Контекст из договора:\n{context}\n\nВопрос: {question}\n\nОтвет на основе контекста:",
        },
    ]


def generate_answer(question: str, context: str) -> str:
    if not GIGACHAT_CREDENTIALS:
        raise GigaChatAuthError(
            "GIGACHAT_CREDENTIALS not set. Add them to .env to enable the LLM."
        )

    messages = build_prompt(question, context)
    client = _get_client()

    payload = {
        "model": "GigaChat",
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 2048,
    }

    try:
        resp = client.chat(payload)
    except Exception as e:
        logger.error("GigaChat SDK error: %s", e)
        with _giga_lock:
            _giga_client = None
        raise

    choices = getattr(resp, "choices", [])
    if not choices:
        logger.error("GigaChat returned empty choices for question=%r", question)
        raise GigaChatResponseError("Empty response from GigaChat")

    content = getattr(choices[0], "message", None)
    if content is None:
        raise GigaChatResponseError("Empty message in GigaChat response")

    return content.content


def generate_answer_fallback(question: str, context: str) -> str:
    lines = [line.strip() for line in context.split("\n") if line.strip()]
    if lines:
        return (
            f"⚠️ **GigaChat временно недоступен.**\n\n"
            f"Найденные фрагменты документа по вашему вопросу:\n\n"
            + "\n\n".join(lines[:5])
            + "\n\n---\n*Загрузите документ снова или попробуйте позже.*"
        )
    return (
        "⚠️ **GigaChat временно недоступен.**\n\n"
        "Не удалось найти релевантные фрагменты. Попробуйте позже."
    )
