from fastapi import APIRouter, HTTPException, Depends
from sse_starlette.sse import EventSourceResponse
from models import ChatCompletionRequest
from auth import verify_token
from services.chat_service import handle_chat_completion, generate_stream_response
from config import config
from errors import create_error_response
import uuid

router = APIRouter()

@router.post("/v1/chat/completions")
async def create_chat_completion(request: ChatCompletionRequest, token: str = Depends(verify_token)):
    """Create a chat completion (OpenAI compatible)"""
    request_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
    
    if request.stream:
        return EventSourceResponse(
            generate_stream_response(request, request_id),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )
    
    try:
        return await handle_chat_completion(request, request_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(f"Error generating response: {str(e)}", "generation_error")
        )
