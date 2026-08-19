"""프로젝트·메시지·AI Relay 다이제스트·크레딧·리뷰 라우터.

경로와 JSON 키는 팀 확정 계약 v2(docs/api_spec_v2.md)를 따르고,
모델·컬럼명은 팀 확정 스키마 v2(docs/schema_v2.sql)를 따른다.
둘이 다른 표현(다이제스트 payload 키 등)은 app/contract.py 경계에서만 변환한다.
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
from ..models import CreditTx, Message, Project, RelayDigest, Review, User
from ..timeutil import aware, get_now

router = APIRouter()


def _get_project_for(db: Session, project_id: str, me: User) -> Project:
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "no such project")
    if me.id not in (p.requester_id, p.worker_id):
        raise HTTPException(403, "not a participant")
    return p


def _other_id(p: Project, me: User) -> str:
    return p.worker_id if me.id == p.requester_id else p.requester_id


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
    now = get_now(me)
    p = Project(requester_id=me.id, worker_id=body.worker_id, title=body.title,
                scope=body.scope, agreed_credits=body.agreed_credits, deadline=deadline,
                created_at=now, updated_at=now)
    db.add(p)
    db.commit()
    return {"project_id": p.id, "status": p.status}


@router.post("/projects/{project_id}/accept")
def accept(project_id: str, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """작업자 수락 → 의뢰자 크레딧 HOLD(에스크로 잠금) → IN_PROGRESS."""
    p = _get_project_for(db, project_id, me)
    if me.id != p.worker_id:
        raise HTTPException(403, "only the worker can accept")
    if p.status != "MATCHED":
        raise HTTPException(400, f"cannot accept in status {p.status}")
    now = get_now(me)
    try:
        ledger.hold(db, p, now)
    except ValueError as e:
        raise HTTPException(400, str(e))
    p.status = "IN_PROGRESS"
    p.agreed_at = now
    p.updated_at = now
    db.commit()
    return {"project_id": p.id, "status": p.status, "escrow_held": p.agreed_credits}


@router.post("/projects/{project_id}/complete")
def complete(project_id: str, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """양측 완료 확인 — 두 번째 확인이 들어오는 순간 RELEASE(지급)."""
    p = _get_project_for(db, project_id, me)
    if p.status != "IN_PROGRESS":
        raise HTTPException(400, f"cannot complete in status {p.status}")
    now = get_now(me)
    if me.id == p.requester_id:
        p.requester_completed = True
    else:
        p.worker_completed = True
    settled = False
    if p.requester_completed and p.worker_completed:
        try:
            ledger.release(db, p, now)
        except ValueError as e:
            raise HTTPException(400, str(e))
        p.status = "COMPLETED"
        p.completed_at = now
        settled = True
    p.updated_at = now
    db.commit()
    return {"project_id": p.id, "status": p.status,
            "settled": settled,
            "released_credits": p.agreed_credits if settled else 0,
            "my_balance": ledger.balance(db, me.id),
            "confirmed": {"requester": p.requester_completed, "worker": p.worker_completed}}


@router.post("/projects/{project_id}/cancel")
def cancel(project_id: str, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = _get_project_for(db, project_id, me)
    if p.status == "COMPLETED":
        raise HTTPException(400, "already completed")
    now = get_now(me)
    if p.status == "IN_PROGRESS":
        try:
            ledger.refund(db, p, now)
        except ValueError as e:
            raise HTTPException(400, str(e))
    p.status = "CANCELLED"
    p.updated_at = now
    db.commit()
    return {"project_id": p.id, "status": p.status}


@router.get("/projects/{project_id}")
def project_detail(project_id: str, me: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    p = _get_project_for(db, project_id, me)
    req, wrk = db.get(User, p.requester_id), db.get(User, p.worker_id)
    return {"project_id": p.id, "title": p.title, "scope": p.scope,
            "status": p.status,
            "agreed_credits": p.agreed_credits,
            "deadline": aware(p.deadline).isoformat() if p.deadline else None,
            "participants": [{"user_id": u.id, "name": u.name, "timezone": u.timezone,
                              "country": u.country, "role": role}
                             for u, role in ((req, "requester"), (wrk, "worker"))],
            "my_role": "requester" if p.requester_id == me.id else "worker"}


@router.get("/projects")
def my_projects(me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Project).where(
        or_(Project.requester_id == me.id, Project.worker_id == me.id))).all()
    return {"projects": [{"project_id": p.id, "title": p.title,
                          "status": p.status,
                          "agreed_credits": p.agreed_credits,
                          "my_role": "requester" if p.requester_id == me.id else "worker",
                          "partner_id": _other_id(p, me)} for p in rows]}


# ---------------- messages ----------------

class MessageIn(BaseModel):
    """계약 키는 body, DB 컬럼은 content(docs/schema_v2.sql)."""
    body: str


@router.post("/projects/{project_id}/messages")
def send_message(project_id: str, body: MessageIn, me: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    p = _get_project_for(db, project_id, me)
    m = Message(project_id=p.id, sender_id=me.id, content=body.body, sent_at=get_now(me))
    db.add(m)
    for d in db.scalars(select(RelayDigest).where(RelayDigest.project_id == p.id,
                                                  RelayDigest.recipient_id == me.id,
                                                  RelayDigest.is_read == False)):  # noqa: E712
        d.is_read = True
    db.commit()
    return {"message_id": m.id, "created_at": aware(m.sent_at).isoformat()}


@router.get("/projects/{project_id}/messages")
def list_messages(project_id: str, me: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    """폴링용 조회. 내게 온 미읽음 메시지는 이 시점에 read 처리된다."""
    p = _get_project_for(db, project_id, me)
    msgs = db.scalars(select(Message).where(Message.project_id == p.id)
                      .order_by(Message.id)).all()
    now = get_now(me)
    for m in msgs:
        if m.sender_id != me.id and m.read_at is None:
            m.read_at = now
    db.commit()
    return {"messages": [{"message_id": m.id, "sender_id": m.sender_id, "body": m.content,
                          "created_at": aware(m.sent_at).isoformat() if m.sent_at else None,
                          "mine": m.sender_id == me.id} for m in msgs]}


# ---------------- relay digest (lazy trigger) ----------------

def _latest_digest(db: Session, project_id: str, user_id: str) -> Optional[RelayDigest]:
    return db.scalar(select(RelayDigest)
                     .where(RelayDigest.project_id == project_id,
                            RelayDigest.recipient_id == user_id)
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
        out.update({"digest_id": d.id, "language": d.language, "trigger": d.trigger_type,
                    "is_read": d.is_read,
                    "covers_to_message_id": d.covers_to_message_id,
                    "digest": contract.digest_payload(d.payload),
                    "created_at": aware(d.created_at).isoformat() if d.created_at else None})
    return out


def _make_digest(db: Session, p: Project, me: User, msgs, trigger: str) -> RelayDigest:
    partner = db.get(User, _other_id(p, me))
    payload = generate_digest(get_provider(LLM_PROVIDER), msgs, me, partner.name)
    d = RelayDigest(project_id=p.id, recipient_id=me.id, language=me.preferred_language,
                    trigger_type=trigger, covers_to_message_id=msgs[-1].id,
                    payload=payload, created_at=get_now(me))
    db.add(d)
    db.commit()
    return d


@router.get("/projects/{project_id}/relay-digest")
def get_digest(project_id: str, me: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    """채팅방 진입 시 호출 — 조건 충족 시 그 자리에서 자동 생성(지연 평가)."""
    p = _get_project_for(db, project_id, me)
    msgs = db.scalars(select(Message).where(Message.project_id == p.id)
                      .order_by(Message.id)).all()
    last = _latest_digest(db, p.id, me.id)
    fire, unc = should_generate(me.id, msgs, last.covers_to_message_id if last else None,
                                get_now(me))
    if fire:
        return _digest_out(_make_digest(db, p, me, unc, "auto"), p.id, len(unc), True)
    return _digest_out(last, p.id, len(unc), False)


@router.post("/projects/{project_id}/relay-digest")
def manual_digest(project_id: str, me: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    """수동 요약 받기 — 경과 시간과 무관하게 미커버 메시지가 있으면 생성."""
    p = _get_project_for(db, project_id, me)
    msgs = db.scalars(select(Message).where(Message.project_id == p.id)
                      .order_by(Message.id)).all()
    last = _latest_digest(db, p.id, me.id)
    unc = uncovered_messages(msgs, last.covers_to_message_id if last else None)
    if not unc:
        return _digest_out(last, p.id, 0, False) | {"note": "no new messages"}
    return _digest_out(_make_digest(db, p, me, unc, "manual"), p.id, len(unc), True)


# ---------------- credits & reviews ----------------

@router.get("/me/credits")
def my_credits(me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    txs = db.scalars(select(CreditTx).where(CreditTx.user_id == me.id)
                     .order_by(CreditTx.id)).all()
    return {"balance": ledger.balance(db, me.id),
            "transactions": [{"id": t.id, "amount": t.amount,
                              "type": t.tx_type,
                              "project_id": t.project_id} for t in txs]}


class ReviewIn(BaseModel):
    diligence: int
    quality: int
    communication: int
    comment: str = ""


@router.post("/projects/{project_id}/reviews")
def submit_review(project_id: str, body: ReviewIn, me: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    p = _get_project_for(db, project_id, me)
    if p.status != "COMPLETED":
        raise HTTPException(400, "review after completion only")
    for v in (body.diligence, body.quality, body.communication):
        if not 1 <= v <= 5:
            raise HTTPException(400, "scores must be 1..5")
    if db.scalar(select(Review).where(Review.project_id == p.id, Review.reviewer_id == me.id)):
        raise HTTPException(400, "already reviewed")
    db.add(Review(project_id=p.id, reviewer_id=me.id, created_at=get_now(me),
                  **body.model_dump()))
    db.commit()
    return {"ok": True}


@router.get("/projects/{project_id}/reviews")
def get_reviews(project_id: str, me: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    """양측 모두 제출한 경우에만 공개(동시 공개 — 보복 평가 방지)."""
    p = _get_project_for(db, project_id, me)
    rows = db.scalars(select(Review).where(Review.project_id == p.id)).all()
    if len(rows) < 2:
        return {"visible": False, "submitted": [r.reviewer_id for r in rows]}
    return {"visible": True,
            "reviews": [{"reviewer_id": r.reviewer_id, "diligence": r.diligence,
                         "quality": r.quality, "communication": r.communication,
                         "comment": r.comment} for r in rows]}
