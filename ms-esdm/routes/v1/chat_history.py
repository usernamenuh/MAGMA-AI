from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Any
from pydantic import BaseModel, ConfigDict
from db.session import get_db
from models.dto.chat_history_dto import ChatHistoryDTO
from services.auth_service import require_api_key
from services.chat_history_service import ChatHistoryService

router = APIRouter()

# --------------------------
# Pydantic Schemas
# --------------------------
class ChatMessageCreate(BaseModel):
    user_id: str
    session_id: str
    role: str  # 'user' or 'assistant'
    message: str

class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chat_id: str
    session_id: str
    role: str
    message: str
    api_call: Optional[str] = None
    response: Optional[Any] = None
    geo_location: Optional[Any] = None
    created_at: datetime

# --------------------------
# Routes
# --------------------------
@router.post("/message", response_model=ChatMessageResponse)
async def create_message(msg: ChatMessageCreate, db: Session = Depends(get_db), api_key: str = Depends(require_api_key)):
    service = ChatHistoryService(db)
    chat = await service.create_message(
        user_id=msg.user_id,
        session_id=msg.session_id,
        role=msg.role,
        message=msg.message
    )
    return chat


@router.get("/session/{session_id}", response_model=List[ChatHistoryDTO])
async def get_session_messages(
    user_id: str,
    session_id: str,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of messages to skip"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of messages to return"),
    api_key: str = Depends(require_api_key)
):
    """
    Get messages for a session with pagination
    """
    service = ChatHistoryService(db)
    messages = await service.get_session_messages(user_id=user_id, session_id=session_id, limit=skip+limit)
    if not messages:
        raise HTTPException(status_code=404, detail="Session not found")
    # Return the slice based on skip and limit
    return messages[skip:skip+limit]


@router.get("/sessions", response_model=List[ChatHistoryDTO])
async def get_user_sessions(
    user_id: str,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of sessions to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of sessions to return"),
    api_key: str = Depends(require_api_key)
):
    """
    Get recent sessions for a user with pagination
    """
    service = ChatHistoryService(db)
    sessions = await service.get_user_sessions(user_id=user_id, limit=skip+limit)
    return sessions[skip:skip+limit]

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, db: Session = Depends(get_db), api_key: str = Depends(require_api_key)):
    service = ChatHistoryService(db)
    deleted = await service.delete_session(session_id)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"detail": f"Deleted {deleted} messages from session {session_id}"}


@router.delete("/users/{user_id}/history")
async def delete_user_history(user_id: str, db: Session = Depends(get_db), api_key: str = Depends(require_api_key)):
    service = ChatHistoryService(db)
    deleted = await service.delete_user_history(user_id)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="No history found for this user")
    return {"detail": f"Deleted {deleted} messages for user {user_id}"}
