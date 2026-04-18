from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings

from app.core.config import get_settings


def build_embeddings() -> Embeddings:
    settings = get_settings()

    if settings.embedding_provider.lower() == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai")
        return OpenAIEmbeddings(
            api_key=settings.openai_api_key,
            model=settings.openai_embedding_model,
        )

    from langchain_huggingface import HuggingFaceEmbeddings

    # Build model kwargs, including HF token if provided
    model_kwargs = {"device": "cpu"}
    if settings.hf_token:
        model_kwargs["token"] = settings.hf_token

    return HuggingFaceEmbeddings(
        model_name=settings.hf_embedding_model,
        model_kwargs=model_kwargs,
        encode_kwargs={"normalize_embeddings": True},
    )
