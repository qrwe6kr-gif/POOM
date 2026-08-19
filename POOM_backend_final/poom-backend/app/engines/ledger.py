"""크레딧 원장 — HOLD / RELEASE / REFUND.

잔액 = Σ(amount). 잔액을 고치는 코드는 존재하지 않는다.
프로젝트당 HOLD/RELEASE/REFUND 각 1회는 DB UNIQUE 제약으로도 이중 차단된다.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import SIGNUP_BONUS
from ..models import CreditTx, Project


def balance(db: Session, user_id: str) -> int:
    val = db.scalar(select(func.coalesce(func.sum(CreditTx.amount), 0))
                    .where(CreditTx.user_id == user_id))
    return int(val or 0)


def _tx_for(db: Session, project_id: str, tx_type: str):
    return db.scalar(select(CreditTx).where(CreditTx.project_id == project_id,
                                            CreditTx.tx_type == tx_type))


def grant_signup_bonus(db: Session, user_id: str, now):
    db.add(CreditTx(user_id=user_id, amount=SIGNUP_BONUS,
                    tx_type="SIGNUP_BONUS", created_at=now))
    db.flush()


def topup(db: Session, user_id: str, amount: int, now):
    if amount <= 0:
        raise ValueError("amount must be positive")
    db.add(CreditTx(user_id=user_id, amount=amount, tx_type="TOPUP", created_at=now))
    db.flush()


def hold(db: Session, project: Project, now):
    """견적 합의 시: 의뢰자 잔액에서 잠금. 실서비스(PG)에서는 요청자 행 잠금 트랜잭션으로 감쌀 것."""
    if _tx_for(db, project.id, "HOLD"):
        raise ValueError("already held")
    if balance(db, project.requester_id) < project.agreed_credits:
        raise ValueError("insufficient credits")
    db.add(CreditTx(user_id=project.requester_id, amount=-project.agreed_credits,
                    tx_type="HOLD", project_id=project.id, created_at=now))
    db.flush()


def release(db: Session, project: Project, now):
    """양측 완료 확인 시: 잠금분을 작업자에게 지급."""
    if not _tx_for(db, project.id, "HOLD"):
        raise ValueError("no hold to release")
    if _tx_for(db, project.id, "RELEASE") or _tx_for(db, project.id, "REFUND"):
        raise ValueError("already settled")
    db.add(CreditTx(user_id=project.worker_id, amount=project.agreed_credits,
                    tx_type="RELEASE", project_id=project.id, created_at=now))
    db.flush()


def refund(db: Session, project: Project, now):
    """협업 취소 시: 잠금분을 의뢰자에게 반환."""
    if not _tx_for(db, project.id, "HOLD"):
        raise ValueError("no hold to refund")
    if _tx_for(db, project.id, "RELEASE") or _tx_for(db, project.id, "REFUND"):
        raise ValueError("already settled")
    db.add(CreditTx(user_id=project.requester_id, amount=project.agreed_credits,
                    tx_type="REFUND", project_id=project.id, created_at=now))
    db.flush()
