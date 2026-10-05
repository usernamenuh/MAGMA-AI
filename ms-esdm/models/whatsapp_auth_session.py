from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from db.session import Base


class WhatsAppAuthSession(Base):
    __tablename__ = "whatsapp_auth_sessions"

    session_id = Column(String, primary_key=True)
    state = Column(String, nullable=False, default="anonymous")
    pending_email = Column(String, nullable=True)
    user_id = Column(String, nullable=True)
    failed_attempts = Column(Integer, nullable=False, default=0)
    authenticated_until = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
