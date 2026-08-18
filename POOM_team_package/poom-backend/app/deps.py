from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session
from .db import SessionLocal
from .models import User


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(x_user_id: str = Header(...), db: Session = Depends(get_db)) -> User:
    """해커톤용 간이 인증: X-User-Id 헤더.

    실서비스 전환 시 이 함수만 Supabase Auth(JWT 검증)로 교체하면 된다.
    """
    user = db.get(User, x_user_id)
    if not user:
        raise HTTPException(401, "unknown user (X-User-Id)")
    return user
