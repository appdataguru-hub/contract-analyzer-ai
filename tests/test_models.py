import pytest
from pydantic import ValidationError
from app.models import (
    QuestionRequest,
    AnswerResponse,
    UploadResponse,
    EvaluateRequest,
    EvaluateResponse,
    ErrorResponse,
)


class TestQuestionRequest:
    def test_valid_minimal(self):
        req = QuestionRequest(question="Какая цена?")
        assert req.question == "Какая цена?"
        assert req.collection_name == "contracts"

    def test_valid_with_collection(self):
        req = QuestionRequest(question="Вопрос?", collection_name="my_docs")
        assert req.collection_name == "my_docs"

    def test_empty_question_fails(self):
        with pytest.raises(ValidationError):
            QuestionRequest(question="")

    def test_missing_question_fails(self):
        with pytest.raises(ValidationError):
            QuestionRequest()

    def test_very_long_question(self):
        q = "в" * 100000
        req = QuestionRequest(question=q)
        assert len(req.question) == 100000

    def test_question_with_unicode(self):
        req = QuestionRequest(question="🔴 Договор ©®™ €")
        assert req.question == "🔴 Договор ©®™ €"


class TestAnswerResponse:
    def test_valid_response(self):
        resp = AnswerResponse(answer="Цена: 100 руб.", sources=["doc.pdf"])
        assert resp.answer == "Цена: 100 руб."
        assert resp.sources == ["doc.pdf"]

    def test_empty_sources(self):
        resp = AnswerResponse(answer="Ответ", sources=[])
        assert resp.sources == []

    def test_minimal_sources(self):
        resp = AnswerResponse(answer="Ответ", sources=["doc1.pdf", "doc2.pdf"])
        assert len(resp.sources) == 2

    def test_missing_answer_fails(self):
        with pytest.raises(ValidationError):
            AnswerResponse(sources=["doc.pdf"])

    def test_missing_sources_fails(self):
        with pytest.raises(ValidationError):
            AnswerResponse(answer="Ответ")


class TestUploadResponse:
    def test_valid_response(self):
        resp = UploadResponse(
            status="success",
            filename="contract.pdf",
            chunks=47,
            collection_name="contracts",
        )
        assert resp.status == "success"
        assert resp.filename == "contract.pdf"

    def test_zero_chunks(self):
        resp = UploadResponse(
            status="success",
            filename="empty.pdf",
            chunks=0,
            collection_name="contracts",
        )
        assert resp.chunks == 0


class TestEvaluateRequest:
    def test_valid_minimal(self):
        req = EvaluateRequest(
            question="q",
            actual_output="a",
            retrieval_context=["c"],
        )
        assert req.expected_output is None

    def test_valid_with_expected(self):
        req = EvaluateRequest(
            question="q",
            actual_output="a",
            retrieval_context=["c"],
            expected_output="exp",
        )
        assert req.expected_output == "exp"

    def test_missing_retrieval_context_fails(self):
        with pytest.raises(ValidationError):
            EvaluateRequest(question="q", actual_output="a")

    def test_empty_retrieval_context(self):
        req = EvaluateRequest(question="q", actual_output="a", retrieval_context=[])
        assert req.retrieval_context == []


class TestEvaluateResponse:
    def test_all_none(self):
        resp = EvaluateResponse()
        assert resp.faithfulness_score is None
        assert resp.faithfulness_reason is None

    def test_with_values(self):
        resp = EvaluateResponse(
            faithfulness_score=0.85,
            faithfulness_reason="ok",
            answer_relevancy_score=0.9,
            answer_relevancy_reason="good",
        )
        assert resp.faithfulness_score == 0.85


class TestErrorResponse:
    def test_valid(self):
        resp = ErrorResponse(detail="Something went wrong")
        assert resp.detail == "Something went wrong"
