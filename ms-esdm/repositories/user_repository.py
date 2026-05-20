from sqlalchemy.orm import Session
from models.users import User


def get_user_by_email(db: Session, email: str):
    """Fetch a user by email."""
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db: Session, user_id: str):
    return db.query(User).filter(User.user_id == user_id).first()

def create_user(db: Session, name: str, email: str, password_hash: str):
    """Create a new user."""
    new_user = User(
        name=name,
        email=email,
        password_hash=password_hash,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def update_user_password(db: Session, email: str, new_password_hash: str):
    """Update a user's password."""
    user = get_user_by_email(db, email)
    if not user:
        return None
    user.password_hash = new_password_hash
    db.commit()
    db.refresh(user)
    return user

def update_refresh_token(db: Session, user_id: str, refresh_token_hashed: str, expiry=None):
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    user.refresh_token = refresh_token_hashed
    user.refresh_token_expiry = expiry
    db.commit()
    db.refresh(user)
    return user

def clear_refresh_token(db: Session, user_id: str):
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    user.refresh_token = None
    user.refresh_token_expiry = None
    db.commit()
    db.refresh(user)
    return user