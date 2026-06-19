from pydantic import BaseModel
from typing import Optional


class QuestionRequest(BaseModel):
    question: str
    collection_name: str = "contracts"


class AnswerResponse(BaseModel):
    answer: str
    sources: list[str]
    source_scores: Optional[list[float]] = None


class UploadResponse(BaseModel):
    status: str
    filename: str
    chunks: int
    collection_name: str


class ErrorResponse(BaseModel):
    detail: str
