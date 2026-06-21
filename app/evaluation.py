import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)

from app.config import EVAL_MODEL, EVAL_BACKEND
from app.generation import (
    GigaChatAuthError,
    GigaChatResponseError,
    _get_client,
    build_prompt,
)

# ---------------------------------------------------------------------------
# GigaChat-based metrics (custom, no DeepEval dependency)
# ---------------------------------------------------------------------------

_EVAL_SYSTEM_PROMPT = (
    "Ты — эксперт по оценке качества RAG-систем (Retrieval-Augmented Generation). "
    "Твоя задача — оценивать ответы AI-ассистента по двум метрикам: "
    "Faithfulness (фактическая точность) и Answer Relevancy (релевантность ответа). "
    "Отвечай строго в формате:\n"
    "SCORE: <0.0-1.0>\n"
    "REASON: <краткое объяснение на русском>"
)


def _parse_eval_response(text: str) -> tuple[float | None, str]:
    score = None
    reason = text.strip()

    m = re.search(r"SCORE:\s*([0-9]*\.?[0-9]+)", text, re.IGNORECASE)
    if m:
        try:
            val = float(m.group(1))
            score = max(0.0, min(1.0, val))
        except ValueError:
            pass

    m = re.search(r"REASON:\s*(.+)", text, re.IGNORECASE | re.DOTALL)
    if m:
        reason = m.group(1).strip()

    return score, reason


def _gigachat_evaluate_metric(
    question: str,
    actual_output: str,
    retrieval_context: list[str],
    metric_type: str,
) -> tuple[float | None, str]:
    if metric_type == "faithfulness":
        user_prompt = (
            f"Оцени Faithfulness (фактическую точность) ответа относительно контекста.\n\n"
            f"Контекст документа:\n{chr(10).join(retrieval_context)}\n\n"
            f"Вопрос: {question}\n\n"
            f"Ответ AI: {actual_output}\n\n"
            f"Проверь каждое утверждение в ответе — подтверждается ли оно контекстом.\n"
            f"Если ответ содержит информацию, отсутствующую в контексте — это снижает оценку.\n"
            f"Поставь оценку от 0.0 до 1.0, где 1.0 — идеальное соответствие контексту."
        )
    elif metric_type == "answer_relevancy":
        user_prompt = (
            f"Оцени Answer Relevancy (релевантность) ответа относительно вопроса.\n\n"
            f"Вопрос: {question}\n\n"
            f"Ответ AI: {actual_output}\n\n"
            f"Оцени, насколько ответ напрямую отвечает на вопрос.\n"
            f"Если ответ не по теме, содержит лишнюю информацию или уходит от вопроса — оценка снижается.\n"
            f"Поставь оценку от 0.0 до 1.0, где 1.0 — ответ полностью релевантен вопросу."
        )
    else:
        logger.warning("Unknown metric type: %s", metric_type)
        return None, f"Unknown metric: {metric_type}"

    messages = [
        {"role": "system", "content": _EVAL_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        client = _get_client()
        payload = {
            "model": "GigaChat",
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 512,
        }
        resp = client.chat(payload)
        choices = getattr(resp, "choices", [])
        if not choices:
            logger.warning("GigaChat eval returned empty choices")
            return None, "Empty response from GigaChat"
        content = getattr(choices[0], "message", None)
        if content is None:
            return None, "Empty message in GigaChat response"
        text = content.content
        return _parse_eval_response(text)
    except (GigaChatAuthError, GigaChatResponseError) as e:
        logger.warning("GigaChat eval failed: %s", e)
        return None, str(e)
    except Exception as e:
        logger.warning("Unexpected error in GigaChat eval: %s", e)
        return None, str(e)


def _evaluate_with_gigachat(
    question: str,
    actual_output: str,
    retrieval_context: list[str],
) -> dict:
    f_score, f_reason = _gigachat_evaluate_metric(
        question, actual_output, retrieval_context, "faithfulness"
    )
    r_score, r_reason = _gigachat_evaluate_metric(
        question, actual_output, retrieval_context, "answer_relevancy"
    )
    return {
        "faithfulness_score": f_score,
        "faithfulness_reason": f_reason,
        "answer_relevancy_score": r_score,
        "answer_relevancy_reason": r_reason,
    }


# ---------------------------------------------------------------------------
# DeepEval-based metrics (requires OPENAI_API_KEY)
# ---------------------------------------------------------------------------

def _evaluate_with_deepeval(
    question: str,
    actual_output: str,
    retrieval_context: list[str],
    expected_output: Optional[str] = None,
) -> dict:
    if not os.getenv("OPENAI_API_KEY"):
        logger.warning("OPENAI_API_KEY not set — cannot use DeepEval")
        return {
            "faithfulness_score": None,
            "faithfulness_reason": "DeepEval unavailable: OPENAI_API_KEY not set",
            "answer_relevancy_score": None,
            "answer_relevancy_reason": "DeepEval unavailable: OPENAI_API_KEY not set",
        }

    from deepeval import evaluate as deepeval_run
    from deepeval.metrics import FaithfulnessMetric, AnswerRelevancyMetric
    from deepeval.test_case import LLMTestCase

    test_case = LLMTestCase(
        input=question,
        actual_output=actual_output,
        retrieval_context=retrieval_context,
        expected_output=expected_output,
    )

    faithfulness = FaithfulnessMetric(
        threshold=0.7,
        model=EVAL_MODEL,
        include_reason=True,
    )

    answer_relevancy = AnswerRelevancyMetric(
        threshold=0.7,
        model=EVAL_MODEL,
        include_reason=True,
    )

    deepeval_run(
        [test_case],
        metrics=[faithfulness, answer_relevancy],
    )

    return {
        "faithfulness_score": faithfulness.score,
        "faithfulness_reason": faithfulness.reason,
        "answer_relevancy_score": answer_relevancy.score,
        "answer_relevancy_reason": answer_relevancy.reason,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def evaluate_response(
    question: str,
    actual_output: str,
    retrieval_context: list[str],
    expected_output: Optional[str] = None,
) -> dict:
    backend = EVAL_BACKEND.lower()

    if backend == "gigachat":
        logger.info("Using GigaChat evaluation backend")
        return _evaluate_with_gigachat(question, actual_output, retrieval_context)

    if backend == "deepeval":
        logger.info("Using DeepEval evaluation backend")
        return _evaluate_with_deepeval(question, actual_output, retrieval_context, expected_output)

    # auto: try GigaChat, fallback to DeepEval, fallback to None
    if backend == "auto":
        logger.info("Auto backend: trying GigaChat first")
        try:
            result = _evaluate_with_gigachat(question, actual_output, retrieval_context)
            if result.get("faithfulness_score") is not None:
                return result
            logger.info("GigaChat returned None scores, falling back to DeepEval")
        except Exception as e:
            logger.warning("GigaChat evaluation failed: %s. Falling back to DeepEval", e)

        return _evaluate_with_deepeval(question, actual_output, retrieval_context, expected_output)

    logger.warning("Unknown EVAL_BACKEND=%r, skipping evaluation", backend)
    return {
        "faithfulness_score": None,
        "faithfulness_reason": f"Unknown EVAL_BACKEND: {backend}",
        "answer_relevancy_score": None,
        "answer_relevancy_reason": f"Unknown EVAL_BACKEND: {backend}",
    }


def batch_evaluate(
    test_cases: list[dict],
) -> list[dict]:
    results = []
    for tc in test_cases:
        result = evaluate_response(
            question=tc["question"],
            actual_output=tc["actual_output"],
            retrieval_context=tc["retrieval_context"],
            expected_output=tc.get("expected_output"),
        )
        results.append(result)
    return results
