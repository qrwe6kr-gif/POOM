"""프로젝트(협업)·메시지·AI Relay 다이제스트·크레딧·리뷰 라우터.

경로와 JSON 키는 팀 확정 계약 v2(docs/api_spec_v2.md)를 따른다.
내부 모델은 Collab/provider_id를 유지하며, 변환은 app/contract.py 경계에서만 일어난다.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .. import contract
from ..config import LLM_PROVIDER
from ..deps import get_current_user, get_db
from ..engines import ledger
from ..engines.digest import generate_digest, get_provider
from ..engines.relay import should_generate, uncovered_messages
from ..models import Collab, CreditTx, Message, RelayDigest, Review, User
from ..timeutil import aware, get_now

router = APIRouter()


def _get_collab_for(db: Session, project_id: str, me: User) -> Collab:
    c = db.get(Collab, project_id)
    if not c:
        raise HTTPException(404, "no such project")
    if me.id not in (c.requester_id, c.provider_id):
        raise HTTPException(403, "not a participant")
    return c


def _other_id(c: Collab, me: User) -> str:
    return c.provider_id if me.id == c.requester_id else c.requester_id


class ProjectIn(BaseModel):
    worker_id: str
    title: str
    scope: str = ""
    agreed_credits: int
    deadline: Optional[str] = None   # ISO8601


@router.post("/projects")
def request_project(body: ProjectIn, me: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    """건당 확정 견적으로 협업 요청 (requester = 나)."""
    if body.agreed_credits <= 0:
        raise HTTPException(400, "agreed_credits must be positive")
    if not db.get(User, body.worker_id):
        raise HTTPException(404, "no such worker")
    from datetime import datetime, timezone
    deadline = None
    if body.deadline:
        d = datetime.fromisoformat(body.deadline.replace("Z", "+00:00"))
        deadline = d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    c = Collab(requester_id=me.id, provider_id=body.worker_id, title=body.title,
               scope=body.scope, credit_amount=body.agreed_credits, deadline=deadline,
               created_at=get_now(me))
    db.add(c)
    db.commit()
    return {"project_id": c.id, "status": contract.project_status(c.status)}


@router.post("/projects/{project_id}/accept")
def accept(project_id: str, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """작업자 수락 → 의뢰자 크레딧 hold(에스크로 잠금) → IN_PROGRESS."""
    c = _get_collab_for(db, project_id, me)
    if me.id != c.provider_id:
        raise HTTPException(403, "only the worker can accept")
    if c.status != "requested":
        raise HTTPException(400, f"cannot accept in status {contract.project_status(c.status)}")
    try:
        ledger.hold(db, c, get_now(me))
    except ValueError as e:
        raise HTTPException(400, str(e))
    c.status = "agreed"
    c.agreed_at = get_now(me)
    db.commit()
    return {"project_id": c.id, "status": contract.project_status(c.status),
            "escrow_held": c.credit_amount}


@router.post("/projects/{project_id}/complete")
def complete(project_id: str, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """양측 완료 확인 — 두 번째 확인이 들어오는 순간 release(지급)."""
    c = _get_collab_for(db, project_id, me)
    if c.status != "agreed":
        raise HTTPException(400, f"cannot complete in status {contract.project_status(c.status)}")
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
    return {"project_id": c.id, "status": contract.project_status(c.status),
            "settled": settled,
            "released_credits": c.credit_amount if settled else 0,
            "my_balance": ledger.balance(db, me.id),
            "confirmed": {"requester": c.requester_confirmed, "worker": c.provider_confirmed}}


@router.post("/projects/{project_id}/cancel")
def cancel(project_id: str, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = _get_collab_for(db, project_id, me)
    if c.status == "completed":
        raise HTTPException(400, "already completed")
    if c.status == "agreed":
        try:
            ledger.refund(db, c, get_now(me))
        except ValueError as e:
            raise HTTPException(400, str(e))
    c.status = "cancelled"
    db.commit()
    return {"project_id": c.id, "status": contract.project_status(c.status)}


@router.get("/projects/{project_id}")
def project_detail(project_id: str, me: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    c = _get_collab_for(db, project_id, me)
    req, wrk = db.get(User, c.requester_id), db.get(User, c.provider_id)
    return {"project_id": c.id, "title": c.title, "scope": c.scope,
            "status": contract.project_status(c.status),
            "agreed_credits": c.credit_amount,
            "deadline": aware(c.deadline).isoformat() if c.deadline else None,
            "participants": [{"user_id": u.id, "name": u.name, "timezone": u.tz,
                              "country": u.country, "role": role}
                             for u, role in ((req, "requester"), (wrk, "worker"))],
            "my_role": "requester" if c.requester_id == me.id else "worker"}


@router.get("/projects")
def my_projects(me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Collab).where(
        or_(Collab.requester_id == me.id, Collab.provider_id == me.id))).all()
    return {"projects": [{"project_id": c.id, "title": c.title,
                          "status": contract.project_status(c.status),
                          "agreed_credits": c.credit_amount,
                          "my_role": "requester" if c.requester_id == me.id else "worker",
                          "partner_id": _other_id(c, me)} for c in rows]}


# ---------------- messages ----------------

class MessageIn(BaseModel):
    body: str


@router.post("/projects/{project_id}/messages")
def send_message(project_id: str, body: MessageIn, me: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    c = _get_collab_for(db, project_id, me)
    m = Message(collab_id=c.id, sender_id=me.id, body=body.body, created_at=get_now(me))
    db.add(m)
    for d in db.scalars(select(RelayDigest).where(RelayDigest.collab_id == c.id,
                                                  RelayDigest.for_user_id == me.id,
                                                  RelayDigest.is_read == False)):  # noqa: E712
        d.is_read = True
    db.commit()
    return {"message_id": m.id, "created_at": aware(m.created_at).isoformat()}


@router.get("/projects/{project_id}/messages")
def list_messages(project_id: str, me: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    """폴링용 조회. 내게 온 미읽음 메시지는 이 시점에 read 처리된다."""
    c = _get_collab_for(db, project_id, me)
    msgs = db.scalars(select(Message).where(Message.collab_id == c.id)
                      .order_by(Message.id)).all()
    now = get_now(me)
    for m in msgs:
        if m.sender_id != me.id and m.read_at is None:
            m.read_at = now
    db.commit()
    return {"messages": [{"message_id": m.id, "sender_id": m.sender_id, "body": m.body,
                          "created_at": aware(m.created_at).isoformat() if m.created_at else None,
                          "mine": m.sender_id == me.id} for m in msgs]}


# ---------------- relay digest (lazy trigger) ----------------

def _latest_digest(db: Session, collab_id: str, user_id: str) -> Optional[RelayDigest]:
    return db.scalar(select(RelayDigest)
                     .where(RelayDigest.collab_id == collab_id,
                            RelayDigest.for_user_id == user_id)
                     .order_by(RelayDigest.id.desc()))


def _digest_out(d: Optional[RelayDigest], project_id: str, unread: int,
                generated: bool) -> dict:
    """다이제스트 응답의 단일 형태 — 없을 때도 키 집합은 동일하다(프론트 분기 제거).

    payload의 내부 키는 contract.digest_payload()가 v2 필드명으로 바꾼다.
    """
    out = {"digest_id": None, "project_id": project_id, "language": None,
           "trigger": None, "generated": generated, "is_read": False,
           "unread_message_count": unread, "covers_to_message_id": None,
           "digest": None, "created_at": None}
    if d is not None:
        out.update({"digest_id": d.id, "language": d.lang, "trigger": d.trigger,
                    "is_read": d.is_read,
                    "covers_to_message_id": d.covers_to_message_id,
                    "digest": contract.digest_payload(d.payload),
                    "created_at": aware(d.created_at).isoformat() if d.created_at else None})
    return out


def _make_digest(db: Session, c: Collab, me: User, msgs, trigger: str) -> RelayDigest:
    partner = db.get(User, _other_id(c, me))
    payload = generate_digest(get_provider(LLM_PROVIDER), msgs, me, partner.name)
    d = RelayDigest(collab_id=c.id, for_user_id=me.id, lang=me.lang, trigger=trigger,
                    covers_to_message_id=msgs[-1].id, payload=payload, created_at=get_now(me))
    db.add(d)
    db.commit()
    return d


@router.get("/projects/{project_id}/relay-digest")
def get_digest(project_id: str, me: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    """채팅방 진입 시 호출 — 조건 충족 시 그 자리에서 자동 생성(지연 평가)."""
    c = _get_collab_for(db, project_id, me)
    msgs = db.scalars(select(Message).where(Message.collab_id == c.id)
                      .order_by(Message.id)).all()
    last = _latest_digest(db, c.id, me.id)
    fire, unc = should_generate(me.id, msgs, last.covers_to_message_id if last else None,
                                get_now(me))
    if fire:
        return _digest_out(_make_digest(db, c, me, unc, "auto"), c.id, len(unc), True)
    return _digest_out(last, c.id, len(unc), False)


@router.post("/projects/{project_id}/relay-digest")
def manual_digest(project_id: str, me: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    """수동 요약 받기 — 경과 시간과 무관하게 미커버 메시지가 있으면 생성."""
    c = _get_collab_for(db, project_id, me)
    msgs = db.scalars(select(Message).where(Message.collab_id == c.id)
                      .order_by(Message.id)).all()
    last = _latest_digest(db, c.id, me.id)
    unc = uncovered_messages(msgs, last.covers_to_message_id if last else None)
    if not unc:
        return _digest_out(last, c.id, 0, False) | {"note": "no new messages"}
    return _digest_out(_make_digest(db, c, me, unc, "manual"), c.id, len(unc), True)


# ---------------- credits & reviews ----------------

@router.get("/me/credits")
def my_credits(me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    txs = db.scalars(select(CreditTx).where(CreditTx.user_id == me.id)
                     .order_by(CreditTx.id)).all()
    return {"balance": ledger.balance(db, me.id),
            "transactions": [{"id": t.id, "amount": t.amount,
                              "type": contract.tx_type(t.ttype),
                              "project_id": t.collab_id} for t in txs]}


class ReviewIn(BaseModel):
    diligence: int
    quality: int
    communication: int
    comment: str = ""


@router.post("/projects/{project_id}/reviews")
def submit_review(project_id: str, body: ReviewIn, me: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    c = _get_collab_for(db, project_id, me)
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


@router.get("/projects/{project_id}/reviews")
def get_reviews(project_id: str, me: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    """양측 모두 제출한 경우에만 공개(동시 공개 — 보복 평가 방지)."""
    c = _get_collab_for(db, project_id, me)
    rows = db.scalars(select(Review).where(Review.collab_id == c.id)).all()
    if len(rows) < 2:
        return {"visible": False, "submitted": [r.reviewer_id for r in rows]}
    return {"visible": True,
            "reviews": [{"reviewer_id": r.reviewer_id, "diligence": r.diligence,
                         "quality": r.quality, "communication": r.communication,
                         "comment": r.comment} for r in rows]}
