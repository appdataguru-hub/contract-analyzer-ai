from gigachat import GigaChat
from gigachat.models import Messages, Chat, MessagesRole

from app.config import GIGACHAT_CREDENTIALS, GIGACHAT_SCOPE


def build_prompt(question: str, context: str) -> list[Messages]:
    system_prompt = (
        "Ты — эксперт по анализу договоров и юридических документов. "
        "Отвечай на русском языке, используя только предоставленный контекст. "
        "Если в контексте недостаточно информации для ответа, "
        "напиши: 'В предоставленном документе недостаточно информации для ответа на этот вопрос.' "
        "Не выдумывай факты. Цитируй номера страниц из контекста, если они указаны."
    )

    user_prompt = (
        f"Контекст из договора:\n{context}\n\n"
        f"Вопрос: {question}\n\n"
        f"Ответ на основе контекста:"
    )

    return [
        Messages(role=MessagesRole.SYSTEM, content=system_prompt),
        Messages(role=MessagesRole.USER, content=user_prompt),
    ]


def generate_answer(question: str, context: str) -> str:
    if not GIGACHAT_CREDENTIALS:
        return "Ошибка: не указаны GIGACHAT_CREDENTIALS. Добавьте их в .env файл."

    messages = build_prompt(question, context)

    with GigaChat(
        credentials=GIGACHAT_CREDENTIALS,
        scope=GIGACHAT_SCOPE,
        verify_ssl_certs=False,
    ) as giga:
        payload = Chat(
            model="GigaChat",
            messages=messages,
            temperature=0.3,
            max_tokens=2048,
        )
        response = giga.chat(payload)
        return response.choices[0].message.content
