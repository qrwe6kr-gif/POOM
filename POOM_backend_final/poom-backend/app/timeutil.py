"""모든 시간 계산의 단일 관문.

datetime.now()를 직접 호출하지 않는다 — 반드시 get_now(actor)를 경유한다.
데모 모드(계정별 가상 시각)는 이 관문 위에서만 동작한다.
"""
from datetime import datetime, timezone


def aware(dt):
    """SQLite에서 naive로 돌아온 datetime을 UTC aware로 정규화."""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def get_now(actor=None) -> datetime:
    """actor(User)의 demo_now가 설정돼 있으면 그 가상 시각, 아니면 실제 UTC now."""
    if actor is not None and getattr(actor, "demo_now", None) is not None:
        return aware(actor.demo_now)
    return datetime.now(timezone.utc)
