from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..config import LLM_PROVIDER
from ..deps import get_current_user, get_db
from ..engines import ledger
from ..engines.digest import generate_digest, get_provider
from ..engines.relay import should_generate, uncovered_messages
from ..models import Collab, CreditTx, Message, RelayDigest, Review, User
from ..timeutil import get_now

router = APIRouter()


def _get_collab_for(db: Session, collab_id: str, me: User) -> Collab:
    c = db.get(Collab, collab_id)
    if not c:
        raise HTTPException(404, "no such collab")
    if me.id not in (c.requester_id, c.provider_id):
        raise HTTPException(403, "not a participant")
    return c


def _other_id(c: Collab, me: User) -> str:
    return c.provider_id if me.id == c.requester_id else c.requester_id


class CollabIn(BaseModel):
    provider_id: str
    title: str
    scope: str = ""
    credit_amount: int


@router.post("/collabs")
def request_collab(body: CollabIn, me: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    """건당 확정 견적으로 협업 요청 (requester = 나)."""
    if body.credit_amount <= 0:
        raise HTTPException(400, "credit_amount must be positive")
    if not db.get(User, body.provider_id):
        raise HTTPException(404, "no such provider")
    c = Collab(requester_id=me.id, created_at=get_now(me), **body.model_dump())
    db.add(c)
    db.commit()
    return {"collab_id": c.id, "status": c.status}


@router.post("/collabs/{collab_id}/accept")
def accept(collab_id: str, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """공급자 수락 → 의뢰자 크레딧 hold(에스크로 잠금) → agreed."""
    c = _get_collab_for(db, collab_id, me)
    if me.id != c.provider_id:
        raise HTTPException(403, "only provider can accept")
    if c.status != "requested":
        raise HTTPException(400, f"cannot accept in status {c.status}")
    try:
        ledger.hold(db, c, get_now(me))
    except ValueError as e:
        raise HTTPException(400, str(e))
    c.status = "agreed"
    c.agreed_at = get_now(me)
    db.commit()
    return {"status": c.status, "escrow_held": c.credit_amount}


@router.post("/collabs/{collab_id}/complete")
def complete(collab_id: str, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """양측 완료 확인 — 두 번째 확인이 들어오는 순간 release(지급)."""
    c = _get_collab_for(db, collab_id, me)
    if c.status != "agreed":
        raise HTTPException(400, f"cannot complete in status {c.status}")
    if me.id == c.requester_id:
        c.requester_confirmed = True
    else:
        c.provider_confirmed = True
    settled = False
    if c.requester_confirmed and c.provider_confirmed:
        try:
            ledger.release(db, c, get_now(me))
        except ValueError as e:
            raise HTTPException(400, str(e))
        c.status = "completed"
        c.completed_at = get_now(me)
        settled = True
    db.commit()
    return {"status": c.status, "settled": settled,
            "confirmed": {"requester": c.requester_confirmed, "provider": c.provider_confirmed}}


@router.post("/collabs/{collab_id}/cancel")
def cancel(collab_id: str, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = _get_collab_for(db, collab_id, me)
    if c.status == "completed":
        raise HTTPException(400, "already completed")
    if c.status == "agreed":
        try:
            ledger.refund(db, c, get_now(me))
        except ValueError as e:
            raise HTTPException(400, str(e))
    c.status = "cancelled"
    db.commit()
    return {"status": c.status}


@router.get("/collabs")
def my_collabs(me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Collab).where(
        or_(Collab.requester_id == me.id, Collab.provider_id == me.id))).all()
    return {"collabs": [{"id": c.id, "title": c.title, "status": c.status,
                         "credit_amount": c.credit_amount,
                         "role": "requester" if c.requester_id == me.id else "provider",
                         "partner_id": _other_id(c, me)} for c in rows]}


# ---------------- messages ----------------

class MessageIn(BaseModel):
    body: str


@router.post("/collabs/{collab_id}/messages")
def send_message(collab_id: str, body: MessageIn, me: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    c = _get_collab_for(db, collab_id, me)
    m = Message(collab_id=c.id, sender_id=me.id, body=body.body, created_at=get_now(me))
    db.add(m)
    db.commit()
    return {"message_id": m.id, "created_at": m.created_at.isoformat()}


@router.get("/collabs/{collab_id}/messages")
def list_messages(collab_id: str, me: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    """폴링용 조회. 내게 온 미읽음 메시지는 이 시점에 read 처리된다."""
    c = _get_collab_for(db, collab_id, me)
    msgs = db.scalars(select(Message).where(Message.collab_id == c.id)
                      .order_by(Message.id)).all()
    now = get_now(me)
    for m in msgs:
        if m.sender_id != me.id and m.read_at is None:
            m.read_at = now
    db.commit()
    return {"messages": [{"id": m.id, "sender_id": m.sender_id, "body": m.body,
                          "created_at": m.created_at.isoformat() if m.created_at else None,
                          "mine": m.sender_id == me.id} for m in msgs]}


# ---------------- relay digest (lazy trigger) ----------------

def _latest_digest(db: Session, collab_id: str, user_id: str) -> Optional[RelayDigest]:
    return db.scalar(select(RelayDigest)
                     .where(RelayDigest.collab_id == collab_id,
                            RelayDigest.for_user_id == user_id)
                     .order_by(RelayDigest.id.desc()))


def _digest_out(d: Optional[RelayDigest]) -> dict:
    if d is None:
        return {"digest": None}
    return {"digest": d.payload, "id": d.id, "lang": d.lang, "trigger": d.trigger,
            "covers_to_message_id": d.covers_to_message_id,
            "created_at": d.created_at.isoformat() if d.created_at else None}


def _make_digest(db: Session, c: Collab, me: User, msgs, trigger: str) -> RelayDigest:
    partner = db.get(User, _other_id(c, me))
    payload = generate_digest(get_provider(LLM_PROVIDER), msgs, me, partner.name)
    d = RelayDigest(collab_id=c.id, for_user_id=me.id, lang=me.lang, trigger=trigger,
                    covers_to_message_id=msgs[-1].id, payload=payload, created_at=get_now(me))
    db.add(d)
    db.commit()
    return d


@router.get("/collabs/{collab_id}/digest")
def get_digest(collab_id: str, me: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    """채팅방 진입 시 호출 — 조건 충족 시 그 자리에서 자동 생성(지연 평가)."""
    c = _get_collab_for(db, collab_id, me)
    msgs = db.scalars(select(Message).where(Message.collab_id == c.id)
                      .order_by(Message.id)).all()
    last = _latest_digest(db, c.id, me.id)
    fire, unc = should_generate(me.id, msgs, last.covers_to_message_id if last else None,
                                get_now(me))
    if fire:
        return _digest_out(_make_digest(db, c, me, unc, "auto")) | {"generated": True}
    return _digest_out(last) | {"generated": False}


@router.post("/collabs/{collab_id}/digest")
def manual_digest(collab_id: str, me: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    """수동 '요약 받기' — 경과 시간과 무관하게 미커버 메시지가 있으면 생성."""
    c = _get_collab_for(db, collab_id, me)
    msgs = db.scalars(select(Message).where(Message.collab_id == c.id)
                      .order_by(Message.id)).all()
    last = _latest_digest(db, c.id, me.id)
    unc = uncovered_messages(msgs, last.covers_to_message_id if last else None)
    if not unc:
        return _digest_out(last) | {"generated": False, "note": "no new messages"}
    return _digest_out(_make_digest(db, c, me, unc, "manual")) | {"generated": True}


# ---------------- credits & reviews ----------------

@router.get("/me/credits")
def my_credits(me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    txs = db.scalars(select(CreditTx).where(CreditTx.user_id == me.id)
                     .order_by(CreditTx.id)).all()
    return {"balance": ledger.balance(db, me.id),
            "transactions": [{"id": t.id, "amount": t.amount, "type": t.ttype,
                              "collab_id": t.collab_id} for t in txs]}


class ReviewIn(BaseModel):
    diligence: int
    quality: int
    communication: int
    comment: str = ""


@router.post("/collabs/{collab_id}/reviews")
def submit_review(collab_id: str, body: ReviewIn, me: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    c = _get_collab_for(db, collab_id, me)
    if c.status != "completed":
        raise HTTPException(400, "review after completion only")
    for v in (body.diligence, body.quality, body.communication):
        if not 1 <= v <= 5:
            raise HTTPException(400, "scores must be 1..5")
    if db.scalar(select(Review).where(Review.collab_id == c.id, Review.reviewer_id == me.id)):
        raise HTTPException(400, "already reviewed")
    db.add(Review(collab_id=c.id, reviewer_id=me.id, created_at=get_now(me),
                  **body.model_dump()))
    db.commit()
    return {"ok": True}


@router.get("/collabs/{collab_id}/reviews")
def get_reviews(collab_id: str, me: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    """양측 모두 제출한 경우에만 공개(동시 공개 — 보복 평가 방지)."""
    c = _get_collab_for(db, collab_id, me)
    rows = db.scalars(select(Review).where(Review.collab_id == c.id)).all()
    if len(rows) < 2:
        return {"visible": False, "submitted": [r.reviewer_id for r in rows]}
    return {"visible": True,
            "reviews": [{"reviewer_id": r.reviewer_id, "diligence": r.diligence,
                         "quality": r.quality, "communication": r.communication,
                         "comment": r.comment} for r in rows]}
