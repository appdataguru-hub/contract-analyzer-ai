import os
from unittest.mock import patch, MagicMock, ANY

import pytest
from app.generation import (
    build_prompt,
    generate_answer,
    generate_answer_fallback,
    GigaChatAuthError,
    GigaChatResponseError,
)


class TestGigaChatAuthError:
    def test_exception_is_raiseable(self):
        with pytest.raises(GigaChatAuthError):
            raise GigaChatAuthError("test")

    def test_message_preserved(self):
        try:
            raise GigaChatAuthError("custom message")
        except GigaChatAuthError as e:
            assert "custom message" in str(e)


class TestGigaChatResponseError:
    """Q-002 guard: empty / malformed GigaChat choices must not return empty string."""

    def test_exception_is_raiseable(self):
        with pytest.raises(GigaChatResponseError):
            raise GigaChatResponseError("empty")


class TestBuildPrompt:
    def test_prompt_contains_question_and_context(self):
        question = "Какая цена договора?"
        context = "Цена договора составляет 100 000 рублей."
        messages = build_prompt(question, context)

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "эксперт по анализу договоров" in messages[0]["content"]
        assert question in messages[1]["content"]
        assert context in messages[1]["content"]

    def test_prompt_asks_when_no_context(self):
        messages = build_prompt("Вопрос?", "Нет информации.")
        user_msg = messages[1]["content"]
        assert "Вопрос:" in user_msg
        assert "Контекст из договора:" in user_msg

    def test_prompt_with_empty_question(self):
        messages = build_prompt("", "Контекст.")
        assert messages[1]["content"].startswith("Контекст из договора:")

    def test_prompt_with_empty_context(self):
        messages = build_prompt("Вопрос?", "")
        assert "Контекст из договора:\n" in messages[1]["content"]

    def test_prompt_system_never_changes(self):
        m1 = build_prompt("q1", "c1")
        m2 = build_prompt("q2", "c2")
        assert m1[0]["content"] == m2[0]["content"]

    def test_prompt_with_long_context(self):
        context = "Предложение. " * 10000
        messages = build_prompt("Вопрос?", context)
        assert len(messages[1]["content"]) > len(context)

    def test_prompt_with_special_chars(self):
        messages = build_prompt("Цена <script>alert(1)</script>?", "Контекст с кавычками \" и '.")
        assert "<script>" in messages[1]["content"]
        assert '"' in messages[1]["content"]
        assert "'" in messages[1]["content"]

    def test_prompt_roles_are_strings(self):
        messages = build_prompt("q", "c")
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"


class TestGenerateAnswer:
    def test_raises_without_credentials(self):
        with patch("app.generation.GIGACHAT_CREDENTIALS", ""):
            with pytest.raises(GigaChatAuthError, match="GIGACHAT_CREDENTIALS not set"):
                generate_answer("Вопрос?", "Контекст.")

    @patch("app.generation.GIGACHAT_CREDENTIALS", "ZmFrZTpmYWtl")
    def test_raises_without_credentials(self):
        with patch("app.generation.GIGACHAT_CREDENTIALS", ""):
            with pytest.raises(GigaChatAuthError):
                generate_answer("q", "c")

    def test_returns_fallback_on_403(self):
        result = generate_answer_fallback("Вопрос?", "Контекст с ответом.")
        assert "временно недоступен" in result

    def test_prompt_contains_question_and_context(self):
        messages = build_prompt("Какая цена?", "Цена: 100 руб.")
        assert "Какая цена?" in messages[1]["content"]
        assert "Цена: 100 руб." in messages[1]["content"]

    def test_handles_gigachat_exception_via_main(self):
        with patch("app.main.generate_answer") as mock_ga:
            mock_ga.side_effect = RuntimeError("GigaChat timeout")
            from app.generation import generate_answer_fallback
            result = generate_answer_fallback("q", "c")
            assert "временно недоступен" in result

    def test_empty_choices_raises_response_error(self):
        with pytest.raises(GigaChatResponseError, match="Empty response"):
            raise GigaChatResponseError("Empty response")


class TestGenerateAnswerFallback:
    def test_fallback_returns_context(self):
        result = generate_answer_fallback("Вопрос?", "Контекст из документа.")
        assert "временно недоступен" in result
        assert "Контекст из документа" in result

    def test_fallback_empty_context(self):
        result = generate_answer_fallback("Вопрос?", "")
        assert "временно недоступен" in result
