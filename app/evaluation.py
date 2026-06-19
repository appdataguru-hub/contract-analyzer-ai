from typing import Optional

from deepeval import evaluate
from deepeval.metrics import FaithfulnessMetric, AnswerRelevancyMetric
from deepeval.test_case import LLMTestCase

from app.config import GIGACHAT_CREDENTIALS


def evaluate_response(
    question: str,
    actual_output: str,
    retrieval_context: list[str],
    expected_output: Optional[str] = None,
    verbose: bool = True,
) -> dict:
    if not GIGACHAT_CREDENTIALS:
        return {"error": "GIGACHAT_CREDENTIALS not set"}

    test_case = LLMTestCase(
        input=question,
        actual_output=actual_output,
        retrieval_context=retrieval_context,
        expected_output=expected_output,
    )

    faithfulness = FaithfulnessMetric(
        threshold=0.7,
        model="gpt-4o",
        include_reason=True,
    )

    answer_relevancy = AnswerRelevancyMetric(
        threshold=0.7,
        model="gpt-4o",
        include_reason=True,
    )

    evaluate(
        [test_case],
        metrics=[faithfulness, answer_relevancy],
    )

    return {
        "faithfulness_score": faithfulness.score,
        "faithfulness_reason": faithfulness.reason,
        "answer_relevancy_score": answer_relevancy.score,
        "answer_relevancy_reason": answer_relevancy.reason,
    }


def batch_evaluate(
    test_cases: list[dict],
    verbose: bool = True,
) -> list[dict]:
    results = []
    for tc in test_cases:
        result = evaluate_response(
            question=tc["question"],
            actual_output=tc["actual_output"],
            retrieval_context=tc["retrieval_context"],
            expected_output=tc.get("expected_output"),
            verbose=verbose,
        )
        results.append(result)
    return results
