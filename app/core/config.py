from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ========================
    # Application Settings
    # ========================
    app_name: str = "Document Chatbot"
    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4
    log_level: str = "INFO"


    # ========================
    # Security & CORS
    # ========================
    cors_origins: str = "http://localhost:8501,http://localhost:3000"
    max_upload_size_mb: int = 50
    jwt_secret_key: str = "replace-with-a-long-random-secret-min-32-chars"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    user_db_path: Path = Field(default=Path("storage/users.db"))
    password_min_length: int = 8

    # ========================
    # Embedding Configuration
    # ========================
    embedding_provider: str = "huggingface"  # openai or huggingface
    openai_api_key: str | None = None
    openai_embedding_model: str = "text-embedding-3-small"
    hf_embedding_model: str = "BAAI/bge-large-en-v1.5"
    hf_token: str | None = None
    embedding_dimension: int = 1536

    # ========================
    # LLM Configuration (Groq)
    # ========================
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 1024

    # ========================
    # Vector Database
    # ========================
    vector_backend: str = "chroma"  # chroma, pinecone, or qdrant

    # Chroma
    chroma_dir: Path = Field(default=Path("storage/chroma"))

    # Pinecone
    pinecone_api_key: str | None = None
    pinecone_index: str | None = None
    pinecone_namespace_prefix: str = "doc-chat"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection_prefix: str = "doc_chat"

    # ========================
    # Storage Configuration
    # ========================
    upload_dir: Path = Field(default=Path("storage/uploads"))
    index_state_path: Path = Field(default=Path("storage/index_state.json"))
    job_state_path: Path = Field(default=Path("storage/jobs_state.json"))

    # ========================
    # RAG Configuration
    # ========================
    top_k: int = 5
    chunk_size: int = 1200
    chunk_overlap: int = 200
    enable_query_rewrite: bool = True
    enable_hybrid_search: bool = True
    enable_query_expansion: bool = True
    query_expansion_variants: int = 3

    # ========================
    # Rate Limiting
    # ========================
    enable_rate_limiting: bool = True
    rate_limit_requests: int = 100
    rate_limit_period_seconds: int = 60

    # ========================
    # Timeouts
    # ========================
    request_timeout_seconds: int = 120
    upload_timeout_seconds: int = 300
    sqlite_timeout_seconds: int = 5

    # ========================
    # Frontend Configuration
    # ========================
    api_base_url: str = "http://localhost:8000/api"
    streamlit_port: int = 8501

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("api_port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        if v < 1 or v > 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v

    @field_validator("api_workers")
    @classmethod
    def validate_workers(cls, v: int) -> int:
        if v < 1 or v > 16:
            raise ValueError("Workers must be between 1 and 16")
        return v


    @field_validator("vector_backend")
    @classmethod
    def validate_vector_backend(cls, v: str) -> str:
        allowed = {"chroma", "pinecone", "qdrant"}
        if v.lower().strip() not in allowed:
            raise ValueError(f"Vector backend must be one of: {', '.join(allowed)}")
        return v.lower().strip()

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.app_env.lower() in {"prod", "production"}

    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Get settings singleton with validation."""
    settings = Settings()

    if settings.is_production:
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is required!")

    # Create required directories
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.chroma_dir.mkdir(parents=True, exist_ok=True)
    settings.index_state_path.parent.mkdir(parents=True, exist_ok=True)
    settings.job_state_path.parent.mkdir(parents=True, exist_ok=True)

    return settings
