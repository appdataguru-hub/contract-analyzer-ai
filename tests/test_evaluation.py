import os
import pytest
from unittest.mock import patch, MagicMock


class TestEvaluateResponseWithDeepEval:
    @patch("app.evaluation.EVAL_BACKEND", "deepeval")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("app.evaluation._evaluate_with_deepeval")
    def test_deepeval_routing(self, mock_deepeval):
        mock_deepeval.return_value = {
            "faithfulness_score": 0.85,
            "faithfulness_reason": "Answer is faithful to context",
            "answer_relevancy_score": 0.92,
            "answer_relevancy_reason": "Answer is relevant to question",
        }

        from app.evaluation import evaluate_response
        result = evaluate_response(
            question="Какая цена?",
            actual_output="100 рублей",
            retrieval_context=["Цена: 100 рублей"],
        )

        assert result["faithfulness_score"] == 0.85
        assert result["answer_relevancy_score"] == 0.92
        mock_deepeval.assert_called_once()

    @patch("app.evaluation.EVAL_BACKEND", "deepeval")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("app.evaluation._evaluate_with_deepeval")
    def test_deepeval_passes_expected_output(self, mock_deepeval):
        mock_deepeval.return_value = {"faithfulness_score": 0.9}

        from app.evaluation import evaluate_response
        result = evaluate_response(
            question="q",
            actual_output="a",
            retrieval_context=["c"],
            expected_output="expected answer",
        )
        assert result["faithfulness_score"] == 0.9
        mock_deepeval.assert_called_once_with(
            "q", "a", ["c"], "expected answer",
        )


class TestEvaluateResponseWithGigaChat:
    @patch("app.evaluation.EVAL_BACKEND", "gigachat")
    @patch("app.evaluation._get_client")
    def test_gigachat_parses_score_and_reason(self, mock_get_client):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_choice = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = "SCORE: 0.87\nREASON: Ответ соответствует контексту"
        mock_choice.message = mock_msg
        mock_resp.choices = [mock_choice]
        mock_client.chat.return_value = mock_resp
        mock_get_client.return_value = mock_client

        from app.evaluation import evaluate_response
        result = evaluate_response(
            question="Какая цена?",
            actual_output="100 рублей",
            retrieval_context=["Цена: 100 рублей"],
        )

        assert result["faithfulness_score"] == 0.87
        assert "соответствует" in (result.get("faithfulness_reason") or "")
        assert result["answer_relevancy_score"] == 0.87
        assert "соответствует" in (result.get("answer_relevancy_reason") or "")

    @patch("app.evaluation.EVAL_BACKEND", "gigachat")
    @patch("app.evaluation._get_client")
    def test_gigachat_handles_low_score(self, mock_get_client):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_choice = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = "SCORE: 0.35\nREASON: Ответ содержит информацию, отсутствующую в контексте"
        mock_choice.message = mock_msg
        mock_resp.choices = [mock_choice]
        mock_client.chat.return_value = mock_resp
        mock_get_client.return_value = mock_client

        from app.evaluation import evaluate_response
        result = evaluate_response(
            question="q",
            actual_output="a",
            retrieval_context=["c"],
        )

        assert result["faithfulness_score"] == 0.35
        assert result["answer_relevancy_score"] == 0.35

    @patch("app.evaluation.EVAL_BACKEND", "gigachat")
    @patch("app.evaluation._get_client")
    def test_gigachat_handles_empty_response(self, mock_get_client):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices = []
        mock_client.chat.return_value = mock_resp
        mock_get_client.return_value = mock_client

        from app.evaluation import evaluate_response
        result = evaluate_response(
            question="q",
            actual_output="a",
            retrieval_context=["c"],
        )

        assert result["faithfulness_score"] is None
        assert result["answer_relevancy_score"] is None

    @patch("app.evaluation.EVAL_BACKEND", "gigachat")
    @patch("app.evaluation._get_client", side_effect=Exception("GigaChat down"))
    def test_gigachat_handles_exception(self, mock_get_client):
        from app.evaluation import evaluate_response
        result = evaluate_response(
            question="q",
            actual_output="a",
            retrieval_context=["c"],
        )

        assert result["faithfulness_score"] is None
        assert result["answer_relevancy_score"] is None


class TestAutoBackend:
    @patch("app.evaluation.EVAL_BACKEND", "auto")
    @patch("app.evaluation._get_client")
    def test_auto_tries_gigachat_first(self, mock_get_client):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_choice = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = "SCORE: 0.91\nREASON: Хорошо"
        mock_choice.message = mock_msg
        mock_resp.choices = [mock_choice]
        mock_client.chat.return_value = mock_resp
        mock_get_client.return_value = mock_client

        from app.evaluation import evaluate_response
        result = evaluate_response(
            question="q",
            actual_output="a",
            retrieval_context=["c"],
        )

        assert result["faithfulness_score"] == 0.91

    @patch("app.evaluation.EVAL_BACKEND", "auto")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("app.evaluation._evaluate_with_deepeval")
    @patch("app.evaluation._get_client", side_effect=Exception("GigaChat down"))
    def test_auto_fallsback_to_deepeval(
        self, mock_get_client, mock_deepeval
    ):
        mock_deepeval.return_value = {
            "faithfulness_score": 0.75,
            "faithfulness_reason": "ok",
        }

        from app.evaluation import evaluate_response
        result = evaluate_response(
            question="q",
            actual_output="a",
            retrieval_context=["c"],
        )

        assert result["faithfulness_score"] == 0.75
        mock_deepeval.assert_called_once()

    @patch("app.evaluation.EVAL_BACKEND", "auto")
    @patch.dict(os.environ, {"OPENAI_API_KEY": ""})
    @patch("app.evaluation._get_client", side_effect=Exception("GigaChat down"))
    def test_auto_returns_none_when_both_fail(self, mock_get_client):
        from app.evaluation import evaluate_response
        result = evaluate_response(
            question="q",
            actual_output="a",
            retrieval_context=["c"],
        )

        assert result["faithfulness_score"] is None
        assert result["answer_relevancy_score"] is None


class TestEvalWithoutKeyInDepevalMode:
    @patch("app.evaluation.EVAL_BACKEND", "deepeval")
    @patch.dict(os.environ, {"OPENAI_API_KEY": ""})
    def test_deepeval_returns_none_without_key(self):
        from app.evaluation import evaluate_response
        result = evaluate_response(
            question="q",
            actual_output="a",
            retrieval_context=[],
        )
        assert result["faithfulness_score"] is None
        assert "OPENAI_API_KEY" in (result.get("faithfulness_reason") or "")

    @patch("app.evaluation.EVAL_BACKEND", "deepeval")
    @patch.dict(os.environ, {"OPENAI_API_KEY": ""})
    def test_deepeval_reason_without_key(self):
        from app.evaluation import evaluate_response
        result = evaluate_response(
            question="q",
            actual_output="a",
            retrieval_context=[],
        )
        assert "OPENAI_API_KEY" in (result.get("answer_relevancy_reason") or "")

    @patch("app.evaluation.EVAL_BACKEND", "deepeval")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "real-key"})
    @patch("deepeval.evaluate")
    @patch("deepeval.metrics.FaithfulnessMetric")
    @patch("deepeval.metrics.AnswerRelevancyMetric")
    def test_deepeval_integration_with_mocks(
        self, mock_arm, mock_fm, mock_eval
    ):
        mock_f = MagicMock()
        mock_f.score = 0.88
        mock_f.reason = "ok"
        mock_fm.return_value = mock_f
        mock_arm.return_value = mock_f

        from app.evaluation import evaluate_response
        result = evaluate_response(
            question="q",
            actual_output="a",
            retrieval_context=["c"],
        )
        assert result["faithfulness_score"] == 0.88


class TestBatchEvaluate:
    @patch("app.evaluation.evaluate_response")
    def test_batch_evaluate_processes_all(self, mock_er):
        mock_er.return_value = {"faithfulness_score": 0.8, "faithfulness_reason": "ok"}

        from app.evaluation import batch_evaluate
        cases = [
            {"question": "q1", "actual_output": "a1", "retrieval_context": ["c1"]},
            {"question": "q2", "actual_output": "a2", "retrieval_context": ["c2"]},
        ]
        results = batch_evaluate(cases)
        assert len(results) == 2
        assert mock_er.call_count == 2

    @patch("app.evaluation.evaluate_response")
    def test_batch_with_expected_output(self, mock_er):
        mock_er.return_value = {"faithfulness_score": 0.9}
        from app.evaluation import batch_evaluate
        cases = [
            {"question": "q", "actual_output": "a", "retrieval_context": ["c"], "expected_output": "e"},
        ]
        batch_evaluate(cases)
        assert mock_er.call_args[1]["expected_output"] == "e"


class TestParseEvalResponse:
    @patch("app.evaluation.EVAL_BACKEND", "gigachat")
    @patch("app.evaluation._get_client")
    def test_parse_without_reason(self, mock_get_client):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_choice = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = "SCORE: 0.75"
        mock_choice.message = mock_msg
        mock_resp.choices = [mock_choice]
        mock_client.chat.return_value = mock_resp
        mock_get_client.return_value = mock_client

        from app.evaluation import evaluate_response
        result = evaluate_response(question="q", actual_output="a", retrieval_context=["c"])

        assert result["faithfulness_score"] == 0.75

    @patch("app.evaluation.EVAL_BACKEND", "gigachat")
    @patch("app.evaluation._get_client")
    def test_parse_clamps_score(self, mock_get_client):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_choice = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = "SCORE: 1.5\nREASON: Тест"
        mock_choice.message = mock_msg
        mock_resp.choices = [mock_choice]
        mock_client.chat.return_value = mock_resp
        mock_get_client.return_value = mock_client

        from app.evaluation import evaluate_response
        result = evaluate_response(question="q", actual_output="a", retrieval_context=["c"])

        assert result["faithfulness_score"] == 1.0
