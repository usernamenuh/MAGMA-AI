from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON, Float
from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ARRAY
from db.session import Base
import uuid

class ChatHistory(Base):
    __tablename__ = "chat_histories"

    chat_id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String,  nullable=True)
    session_id = Column(String, index=True, nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    type = Column(String(50), nullable=True)  # 'api_docs' or 'knowledge_base'
    message = Column(Text, nullable=False)
    api_call = Column(Text, nullable=True)
    references = Column("references", ARRAY(JSON), nullable=True)
    geo_location = Column(ARRAY(Float), nullable=True)
    response = Column(JSON, nullable=True)
    refresh_token = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
