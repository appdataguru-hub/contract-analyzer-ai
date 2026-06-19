import pytest
from app.generation import build_prompt


class TestBuildPrompt:
    def test_prompt_contains_question_and_context(self):
        question = "Какая цена договора?"
        context = "Цена договора составляет 100 000 рублей."
        messages = build_prompt(question, context)

        assert len(messages) == 2
        assert messages[0].role == "system"
        assert messages[1].role == "user"
        assert "эксперт по анализу договоров" in messages[0].content
        assert question in messages[1].content
        assert context in messages[1].content

    def test_prompt_asks_when_no_context(self):
        messages = build_prompt("Вопрос?", "Нет информации.")
        user_msg = messages[1].content
        assert "Вопрос:" in user_msg
        assert "Контекст из договора:" in user_msg
