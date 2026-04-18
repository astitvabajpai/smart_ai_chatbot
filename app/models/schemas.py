from typing import Any

from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str


class UploadResponse(BaseModel):
    status: str
    files: list[str]
    chunks_indexed: int
    job_id: str | None = None


class SourceChunk(BaseModel):
    document_id: str
    file_name: str
    page: int | None = None
    chunk_id: str
    excerpt: str


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=3)
    chat_history: list[dict[str, str]] = Field(default_factory=list)
    top_k: int | None = None


class ChatResponse(BaseModel):
    answer: str
    rewritten_query: str | None = None
    query_variants: list[str] = Field(default_factory=list)
    sources: list[SourceChunk]
    retrieval_debug: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str
    app_name: str
    embedding_provider: str
    groq_model: str
    vector_backend: str


class JobResponse(BaseModel):
    job_id: str
    user_id: str
    job_type: str
    status: str
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    created_at: str
    updated_at: str


class EvaluationRequest(BaseModel):
    question: str = Field(..., min_length=3)
    expected_answer: str | None = None
    chat_history: list[dict[str, str]] = Field(default_factory=list)
    top_k: int | None = None


class EvaluationResponse(BaseModel):
    answer: str
    rewritten_query: str | None = None
    query_variants: list[str] = Field(default_factory=list)
    metrics: dict[str, float]
    sources: list[SourceChunk]
    retrieval_debug: dict[str, Any] = Field(default_factory=dict)
