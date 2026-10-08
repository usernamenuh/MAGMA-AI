from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String, Text

from db.session import Base


class WhatsAppAuthSession(Base):
    __tablename__ = "whatsapp_auth_sessions"

    session_id = Column(String, primary_key=True)
    state = Column(String, nullable=False, default="anonymous")
    pending_email = Column(String, nullable=True)
    user_id = Column(String, nullable=True)
    failed_attempts = Column(Integer, nullable=False, default=0)
    authenticated_until = Column(DateTime, nullable=True)
    conversation_mode = Column(String(24), nullable=False, default="auto")
    voice_mode = Column(Boolean, nullable=False, default=False)
    last_route = Column(String(24), nullable=True)
    pending_follow_up = Column(Text, nullable=True)
    recent_follow_ups = Column(JSON, nullable=False, default=list)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

