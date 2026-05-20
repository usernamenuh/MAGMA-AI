from fastapi import APIRouter
from config import config

router = APIRouter()

@router.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "OpenAI-compatible API server running",
        "endpoints": {
            "models": "/v1/models",
            "chat_completions": "/v1/chat/completions",
            "embeddings": "/v1/embeddings" if config.embedding_enabled else None,
        },
        "authentication": "required" if config.api_key else "not required"
    }
