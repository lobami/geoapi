import uuid
from datetime import datetime, timezone, timedelta

import bcrypt
import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.intervention import User


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_token(username: str, role: str) -> str:
    payload = {
        "sub": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiry_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def authenticate(db: Session, username: str, password: str) -> User | None:
    row = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if not row or not verify_password(password, row.hashed_password):
        return None
    return row


def ensure_default_user(db: Session) -> None:
    exists = db.execute(select(User).where(User.username == "toroto")).scalar_one_or_none()
    if not exists:
        db.add(User(
            id=str(uuid.uuid4()),
            username="toroto",
            hashed_password=hash_password("toroto573"),
            role="admin",
        ))
        db.commit()
