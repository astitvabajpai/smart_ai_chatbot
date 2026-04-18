import json
import logging
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from app.core.config import get_settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.validators import Validator
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    EvaluationRequest,
    EvaluationResponse,
    HealthResponse,
    JobResponse,
    UploadResponse,
)
from app.services.chat_service import ChatService
from app.services.document_loader import DocumentProcessor
from app.services.job_manager import JobManager
from app.services.retriever import HybridRetriever
from app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)

router = APIRouter()

settings = get_settings()



@lru_cache
def get_processor() -> DocumentProcessor:
    return DocumentProcessor()


@lru_cache
def get_vector_store_service() -> VectorStoreService:
    return VectorStoreService()


@lru_cache
def get_retriever() -> HybridRetriever:
    return HybridRetriever(get_vector_store_service())


@lru_cache
def get_chat_service() -> ChatService:
    return ChatService(get_retriever())


@lru_cache
def get_job_manager() -> JobManager:
    return JobManager()


class DummyUser:
    id = "default"
    email = "default@example.com"
    full_name = "Default User"

def get_current_user():
    return DummyUser()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        embedding_provider=settings.embedding_provider,
        groq_model=settings.groq_model,
        vector_backend=settings.vector_backend,
    )


@router.post("/documents/upload", response_model=UploadResponse)
async def upload_documents(
    files: list[UploadFile] = File(...),
    user=Depends(get_current_user),
) -> UploadResponse:
    """Upload PDF documents for ingestion."""
    try:
        if not files:
            raise ValidationError("No files uploaded")

        logger.info(f"Upload request from user {user.id} with {len(files)} file(s)")

        processor = get_processor()
        vector_store_service = get_vector_store_service()
        upload_dir = settings.upload_dir / user.id
        upload_dir.mkdir(parents=True, exist_ok=True)

        payloads: list[tuple[str, Path]] = []
        uploaded_files: list[str] = []

        for upload in files:
            try:
                # Validate filename
                filename = Validator.validate_filename(upload.filename)
                logger.info(f"Processing file: {filename}")

                target_path = upload_dir / filename
                payload = await upload.read()

                # Check file size
                if len(payload) / (1024 * 1024) > settings.max_upload_size_mb:
                    raise ValidationError(
                        f"File {filename} exceeds maximum size of {settings.max_upload_size_mb}MB"
                    )

                target_path.write_bytes(payload)
                uploaded_files.append(filename)
                payloads.append((filename, target_path))
            except ValidationError:
                raise
            except Exception as exc:
                logger.error(f"Error processing file {upload.filename}: {str(exc)}", exc_info=True)
                raise ValidationError(f"Failed to process file {upload.filename}") from exc

        def run_ingestion() -> dict:
            """Background ingestion task."""
            indexed_chunks = 0
            for _name, target_path in payloads:
                try:
                    chunks = processor.load_pdf(target_path)
                    indexed_chunks += vector_store_service.add_documents(
                        user_id=user.id,
                        documents=chunks,
                    )
                except Exception as exc:
                    logger.error(f"Error ingesting {target_path}: {str(exc)}", exc_info=True)
                    raise

            return {"files": uploaded_files, "chunks_indexed": indexed_chunks}

        job_id = get_job_manager().submit(user_id=user.id, job_type="ingestion", fn=run_ingestion)
        logger.info(f"Ingestion job created: {job_id} for user {user.id}")

        return UploadResponse(status="queued", files=uploaded_files, chunks_indexed=0, job_id=job_id)
    except ValidationError as exc:
        logger.warning(f"Validation error during upload: {str(exc)}")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"Unexpected error during upload: {str(exc)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Upload failed") from exc


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, user=Depends(get_current_user)) -> ChatResponse:
    """Chat with documents (non-streaming)."""
    try:
        question = Validator.validate_question(request.question)
        top_k = Validator.validate_top_k(request.top_k)

        logger.info(f"Chat request from user {user.id}: {question[:50]}...")

        response = get_chat_service().answer(
            user_id=user.id,
            question=question,
            chat_history=request.chat_history,
            top_k=top_k,
        )

        logger.info(f"Chat completed for user {user.id}")
        return response
    except ValidationError as exc:
        logger.warning(f"Chat validation error: {str(exc)}")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"Chat error: {str(exc)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chat failed") from exc


@router.post("/chat/stream")
def stream_chat(request: ChatRequest, user=Depends(get_current_user)) -> StreamingResponse:
    """Chat with documents (streaming response)."""
    try:
        question = Validator.validate_question(request.question)
        top_k = Validator.validate_top_k(request.top_k)

        logger.info(f"Streaming chat request from user {user.id}: {question[:50]}...")

        def event_stream():
            try:
                for event in get_chat_service().stream_answer(
                    user_id=user.id,
                    question=question,
                    chat_history=request.chat_history,
                    top_k=top_k,
                ):
                    yield f"event: {event['event']}\n"
                    yield f"data: {json.dumps(event['data'])}\n\n"
                logger.info(f"Streaming chat completed for user {user.id}")
            except Exception as exc:
                logger.error(f"Stream error: {str(exc)}", exc_info=True)
                yield f"data: {json.dumps({'error': 'Stream failed'})}\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")
    except ValidationError as exc:
        logger.warning(f"Stream validation error: {str(exc)}")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"Stream setup error: {str(exc)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Stream failed") from exc


@router.get("/jobs", response_model=list[JobResponse])
def list_jobs(user=Depends(get_current_user)) -> list[JobResponse]:
    """List all jobs for the current user."""
    try:
        logger.info(f"Listing jobs for user {user.id}")
        jobs = get_job_manager().list_for_user(user.id)
        return [JobResponse(**job) for job in jobs]
    except Exception as exc:
        logger.error(f"Error listing jobs: {str(exc)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list jobs") from exc


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, user=Depends(get_current_user)) -> JobResponse:
    """Get a specific job by ID."""
    try:
        logger.info(f"Fetching job {job_id} for user {user.id}")
        job = get_job_manager().get(job_id)
        if not job or job["user_id"] != user.id:
            logger.warning(f"Job {job_id} not found for user {user.id}")
            raise HTTPException(status_code=404, detail="Job not found")
        return JobResponse(**job)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error fetching job {job_id}: {str(exc)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch job") from exc


@router.post("/rag/evaluate", response_model=EvaluationResponse)
def evaluate(request: EvaluationRequest, user=Depends(get_current_user)) -> EvaluationResponse:
    """Evaluate RAG quality with metrics."""
    try:
        question = Validator.validate_question(request.question)
        top_k = Validator.validate_top_k(request.top_k)

        logger.info(f"Evaluation request from user {user.id}: {question[:50]}...")

        payload = get_chat_service().evaluate(
            user_id=user.id,
            question=question,
            expected_answer=request.expected_answer,
            chat_history=request.chat_history,
            top_k=top_k,
        )

        logger.info(f"Evaluation completed for user {user.id}")
        return EvaluationResponse(**payload)
    except ValidationError as exc:
        logger.warning(f"Evaluation validation error: {str(exc)}")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"Evaluation error: {str(exc)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Evaluation failed") from exc
