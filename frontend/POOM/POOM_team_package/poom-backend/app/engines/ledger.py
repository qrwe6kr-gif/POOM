"""크레딧 원장 — hold / release / refund.

잔액 = Σ(amount). 잔액을 고치는 코드는 존재하지 않는다.
협업당 hold/release/refund 각 1회는 DB UNIQUE 제약으로도 이중 차단된다.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import SIGNUP_BONUS
from ..models import Collab, CreditTx


def balance(db: Session, user_id: str) -> int:
    val = db.scalar(select(func.coalesce(func.sum(CreditTx.amount), 0))
                    .where(CreditTx.user_id == user_id))
    return int(val or 0)


def _tx_for(db: Session, collab_id: str, ttype: str):
    return db.scalar(select(CreditTx).where(CreditTx.collab_id == collab_id,
                                            CreditTx.ttype == ttype))


def grant_signup_bonus(db: Session, user_id: str, now):
    db.add(CreditTx(user_id=user_id, amount=SIGNUP_BONUS,
                    ttype="signup_bonus", created_at=now))
    db.flush()


def topup(db: Session, user_id: str, amount: int, now):
    if amount <= 0:
        raise ValueError("amount must be positive")
    db.add(CreditTx(user_id=user_id, amount=amount, ttype="topup", created_at=now))
    db.flush()


def hold(db: Session, collab: Collab, now):
    """견적 합의 시: 의뢰자 잔액에서 잠금. 실서비스(PG)에서는 요청자 행 잠금 트랜잭션으로 감쌀 것."""
    if _tx_for(db, collab.id, "hold"):
        raise ValueError("already held")
    if balance(db, collab.requester_id) < collab.credit_amount:
        raise ValueError("insufficient credits")
    db.add(CreditTx(user_id=collab.requester_id, amount=-collab.credit_amount,
                    ttype="hold", collab_id=collab.id, created_at=now))
    db.flush()


def release(db: Session, collab: Collab, now):
    """양측 완료 확인 시: 잠금분을 공급자에게 지급."""
    if not _tx_for(db, collab.id, "hold"):
        raise ValueError("no hold to release")
    if _tx_for(db, collab.id, "release") or _tx_for(db, collab.id, "refund"):
        raise ValueError("already settled")
    db.add(CreditTx(user_id=collab.provider_id, amount=collab.credit_amount,
                    ttype="release", collab_id=collab.id, created_at=now))
    db.flush()


def refund(db: Session, collab: Collab, now):
    """협업 취소 시: 잠금분을 의뢰자에게 반환."""
    if not _tx_for(db, collab.id, "hold"):
        raise ValueError("no hold to refund")
    if _tx_for(db, collab.id, "release") or _tx_for(db, collab.id, "refund"):
        raise ValueError("already settled")
    db.add(CreditTx(user_id=collab.requester_id, amount=collab.credit_amount,
                    ttype="refund", collab_id=collab.id, created_at=now))
    db.flush()
