import time
from fastapi import APIRouter, HTTPException, Depends
from models import ModelList, ModelInfo
from auth import verify_token
from config import config
from errors import create_error_response

router = APIRouter()

@router.get("/v1/models", response_model=ModelList)
async def list_models(token: str = Depends(verify_token)):
    """List available models (OpenAI compatible)"""
    return ModelList(
        object="list",
        data=[
            ModelInfo(
                id=config.model_name,
                object="model",
                created=int(time.time()),
                owned_by="local",
                permission=[],
                root=config.model_name,
                parent=None,
            )
        ]
    )

@router.get("/v1/models/{model_id}")
async def get_model_info(model_id: str, token: str = Depends(verify_token)):
    """Get model information"""
    if model_id != config.model_name:
        raise HTTPException(
            status_code=404, 
            detail=create_error_response(f"Model {model_id} not found", "model_not_found")
        )
    
    return ModelInfo(
        id=config.model_name,
        object="model",
        created=int(time.time()),
        owned_by="local",
        permission=[],
        root=config.model_name,
        parent=None,
    )
