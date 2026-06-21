from pydantic import BaseModel, Field

from app.config import COLLECTION_NAME


class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Вопрос по содержимому договора")
    collection_name: str = COLLECTION_NAME


class AnswerResponse(BaseModel):
    answer: str
    sources: list[str]
    faithfulness_score: float | None = None
    faithfulness_reason: str | None = None
    answer_relevancy_score: float | None = None
    answer_relevancy_reason: str | None = None


class UploadResponse(BaseModel):
    status: str
    filename: str
    chunks: int
    collection_name: str


class EvaluateRequest(BaseModel):
    question: str
    actual_output: str
    retrieval_context: list[str]
    expected_output: str | None = None


class EvaluateResponse(BaseModel):
    faithfulness_score: float | None = None
    faithfulness_reason: str | None = None
    answer_relevancy_score: float | None = None
    answer_relevancy_reason: str | None = None


class MetricsResponse(BaseModel):
    total_evaluations: int
    faithfulness_mean: float | None = None
    faithfulness_min: float | None = None
    faithfulness_max: float | None = None
    faithfulness_threshold: float = 0.7
    faithfulness_status: str = "N/A"
    answer_relevancy_mean: float | None = None
    answer_relevancy_min: float | None = None
    answer_relevancy_max: float | None = None
    answer_relevancy_threshold: float = 0.7
    answer_relevancy_status: str = "N/A"


class ErrorResponse(BaseModel):
    detail: str
