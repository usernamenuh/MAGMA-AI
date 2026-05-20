from sqlalchemy import Column, Integer, Text, DateTime
from sqlalchemy.sql import func

from db.session import Base


class ActivatedMachine(Base):
    __tablename__ = "activated_machines"

    id = Column(Integer, primary_key=True, index=True)
    fingerprint = Column(Text, unique=True, nullable=False, index=True)
    activated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )