from fastapi import APIRouter, HTTPException, Depends
from models import EmbeddingRequest
from auth import verify_token
from config import config
from errors import create_error_response
from services.embeddings_service import handle_embeddings

router = APIRouter()

@router.post("/v1/embeddings")
async def create_embeddings(request: EmbeddingRequest, token: str = Depends(verify_token)):
    """Create embeddings (OpenAI compatible)"""
    if not config.embedding_enabled:
        raise HTTPException(
            status_code=404,
            detail=create_error_response("Embeddings endpoint is not enabled", "feature_not_enabled")
        )
    
    try:
        return handle_embeddings(request)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(f"Error generating embeddings: {str(e)}", "generation_error")
        )
