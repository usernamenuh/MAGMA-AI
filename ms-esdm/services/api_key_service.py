from fastapi import HTTPException

from db.session import SessionLocal
from repositories import api_keys_repository as repo

def validate_api_key(key: str):
    """Service layer for validating API key with HTTPException handling."""
    with SessionLocal() as db:
        is_valid = repo.validate_api_key(db, key)
        return is_valid


def fetch_api_keys_by_user(user_id: str):
    """Fetch all API keys for a given user."""
    with SessionLocal() as db:
        return repo.fetch_api_keys_by_user(db, user_id)


def fetch_all_api_keys():
    """Fetch all API keys from the system."""
    with SessionLocal() as db:
        return repo.fetch_all_api_keys(db)


def create_api_key(user_id: str, name: str, validity_duration_days: int = 60):
    """Service layer for creating an API key."""
    with SessionLocal() as db:
        api_key = repo.create_api_key(
            db=db,
            user_id=user_id,
            name=name,
            validity_duration_days=validity_duration_days
        )
        return {
            "id": api_key.id,
            "user_id": api_key.user_id,
            "api_key": api_key.api_key,
            "name": api_key.name,
            "valid": api_key.valid,
            "validity_duration_days": api_key.validity_duration_days,
            "created_at": api_key.created_at,
            "updated_at": api_key.updated_at,
        }

def revoke_api_key(api_key: str):
    """Mark an API key as invalid."""
    with SessionLocal() as db:
        success = repo.revoke_api_key(db, api_key)
        if not success:
            raise HTTPException(status_code=404, detail="API key not found")
        return {"message": "API key revoked successfully"}


def remove_api_key(api_key: str):
    """Permanently delete an API key."""
    with SessionLocal() as db:
        success = repo.remove_api_key(db, api_key)
        if not success:
            raise HTTPException(status_code=404, detail="API key not found")
        return {"message": "API key deleted successfully"}
