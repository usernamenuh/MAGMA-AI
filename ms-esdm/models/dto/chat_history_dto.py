from pydantic import BaseModel
from typing import Optional, List, Any, Union
from datetime import datetime


class ChatHistoryDTO(BaseModel):
    chat_id: str
    user_id: str
    session_id: str
    role: str
    type: Optional[str] = None
    lang: Optional[str] = None
    message: str
    api_call: Optional[str] = None
    geo_location: Optional[Any] = None
    references: Optional[Any] = None
    response: Optional[Any] = None
    created_at: datetime

