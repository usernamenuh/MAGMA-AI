import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Type
from sqlalchemy.orm import Session
from models.api_keys import ApiKey


def create_api_key(
    db: Session,
    user_id: str,
    name: str = "Default Key",
    validity_duration_days: Optional[int] = 30,
    prefix: str = "sk-tagflow-"
) -> ApiKey:
    """Generate and store a new API key."""
    unique_part = uuid.uuid4().hex
    new_key = f"{prefix}{unique_part}"
    now = datetime.utcnow()

    api_key_entry = ApiKey(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name=name,
        api_key=new_key,
        valid=True,
        validity_duration_days=validity_duration_days,
        created_at=now,
        updated_at=now,
    )

    db.add(api_key_entry)
    db.commit()
    db.refresh(api_key_entry)

    return api_key_entry


def validate_api_key(db: Session, key: str) -> bool:
    """Check if API key exists, valid, and not expired."""
    record = db.query(ApiKey).filter(ApiKey.api_key == key).first()

    if not record or not record.valid:
        return False

    if record.validity_duration_days:
        expires_at = record.created_at + timedelta(days=record.validity_duration_days)
        if datetime.utcnow() > expires_at:
            record.valid = False
            record.updated_at = datetime.utcnow()
            db.commit()
            return False

    return True


def fetch_api_keys_by_user(db: Session, user_id: str) -> list[Type[ApiKey]]:
    """Return all API keys for a user."""
    return db.query(ApiKey).filter(ApiKey.user_id == user_id).all()


def revoke_api_key(db: Session, key: str) -> bool:
    """Invalidate a key without deleting it."""
    record = db.query(ApiKey).filter(ApiKey.api_key == key).first()
    if not record:
        return False

    record.valid = False
    record.updated_at = datetime.utcnow()
    db.commit()
    return True


def remove_api_key(db: Session, key: str) -> bool:
    """Completely remove an API key."""
    record = db.query(ApiKey).filter(ApiKey.api_key == key).first()
    if not record:
        return False

    db.delete(record)
    db.commit()
    return True


def fetch_all_api_keys(db: Session) -> list[Type[ApiKey]]:
    """List all stored API keys."""
    return db.query(ApiKey).all()
