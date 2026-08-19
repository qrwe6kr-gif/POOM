from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .. import contract
from ..deps import get_current_user, get_db
from ..engines import ledger
from ..engines.status import compute_status, overlap_hours
from ..models import Collab, Need, Skill, User
from ..timeutil import get_now

router = APIRouter()


class SignupIn(BaseModel):
    """v2 계약 키. 내부 모델은 tz/lang을 쓰므로 이 경계에서 한 번만 변환한다."""
    name: str
    email: str
    country: str = ""
    timezone: str = "Asia/Seoul"
    preferred_language: str = "ko"
    work_start: int = 9
    work_end: int = 18


@router.post("/auth/signup")
def signup(body: SignupIn, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == body.email)):
        raise HTTPException(400, "email already registered")
    data = body.model_dump()
    data["tz"] = data.pop("timezone")
    data["lang"] = data.pop("preferred_language")
    u = User(**data)
    u.created_at = get_now()
    db.add(u)
    db.flush()
    ledger.grant_signup_bonus(db, u.id, get_now())   # 초기 지갑 100c
    db.commit()
    return {"user_id": u.id, "note": "이후 요청에 X-User-Id 헤더로 이 값을 넣으세요"}


class LoginIn(BaseModel):
    email: str


@router.post("/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    """비밀번호 없는 해커톤 간이 로그인.

    이메일로 계정을 찾아 프론트가 이후 X-User-Id 헤더에 넣을 값을 돌려준다.
    실서비스 전환 시 signup/login/get_current_user를 한 벌로 Supabase Auth(JWT)로 교체한다.
    """
    u = db.scalar(select(User).where(User.email == body.email))
    if not u:
        raise HTTPException(404, "no account for this email")
    return {"user_id": u.id, "name": u.name, "preferred_language": u.lang}


class SkillIn(BaseModel):
    role: str
    level: str = "junior"
    portfolio_url: str = ""


class NeedIn(BaseModel):
    role: str
    note: str = ""


@router.post("/me/skills")
def add_skill(body: SkillIn, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.add(Skill(user_id=me.id, **body.model_dump()))
    db.commit()
    return {"ok": True}


@router.post("/me/needs")
def add_need(body: NeedIn, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.add(Need(user_id=me.id, **body.model_dump()))
    db.commit()
    return {"ok": True}


def _profile(db: Session, u: User) -> dict:
    skills = db.scalars(select(Skill).where(Skill.user_id == u.id)).all()
    needs = db.scalars(select(Need).where(Need.user_id == u.id)).all()
    return {"user_id": u.id, "name": u.name, "country": u.country, "timezone": u.tz,
            "preferred_language": u.lang, "work": [u.work_start, u.work_end],
            "skills": [{"role": s.role, "level": s.level, "portfolio_url": s.portfolio_url} for s in skills],
            "needs": [{"role": n.role, "note": n.note} for n in needs]}


@router.get("/me")
def me(me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _profile(db, me) | {"is_pro": me.is_pro}


@router.get("/users/{user_id}")
def get_user(user_id: str, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "no such user")
    return _profile(db, u)


@router.get("/matching")
def matching(role: Optional[str] = None, me: User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    """내 필요 역량(needs)을 가진 사람을 시차 겹침 순으로 반환.

    role 파라미터로 특정 역할만 필터 가능. 겹침 시간은 오늘 근무창 기준.
    """
    want = [role] if role else [n.role for n in db.scalars(select(Need).where(Need.user_id == me.id))]
    if not want:
        return {"results": [], "note": "필요 역량(needs)을 먼저 등록하세요"}
    rows = db.scalars(select(Skill).where(Skill.role.in_(want), Skill.user_id != me.id)).all()
    now = get_now(me)
    results, seen = [], set()
    for s in rows:
        if s.user_id in seen:
            continue
        seen.add(s.user_id)
        u = db.get(User, s.user_id)
        results.append({"user": _profile(db, u),
                        "matched_role": s.role,
                        "overlap_hours": overlap_hours(me, u, now)})
    results.sort(key=lambda r: -r["overlap_hours"])
    return {"results": results}


def _has_collab_between(db: Session, a: str, b: str) -> bool:
    q = select(Collab).where(
        or_(Collab.requester_id == a, Collab.provider_id == a),
        or_(Collab.requester_id == b, Collab.provider_id == b),
        Collab.status.in_(["requested", "agreed", "completed"]))
    return db.scalar(q) is not None


@router.get("/users/{user_id}/status")
def user_status(user_id: str, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Timezone Status — 프라이버시 규칙: 본인이거나, 협업 관계가 있는 상대만 조회 가능."""
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "no such user")
    if target.id != me.id and not _has_collab_between(db, me.id, target.id):
        raise HTTPException(403, "status visible to collaboration partners only")
    now = get_now(me)
    st = compute_status(target.tz, target.work_start, target.work_end,
                        target.sleep_start, target.sleep_end, now)
    from ..timeutil import aware
    la = aware(target.last_active_at)
    hours_ago = round((now - la).total_seconds() / 3600, 1) if la else None
    status = contract.user_status(st.state)
    return {"user_id": target.id, "name": target.name, "timezone": target.tz,
            "local_time": contract.local_time_12h(st.local_time),
            "status": status,
            "status_label": contract.status_label(status, me.lang),
            "next_response_utc": st.next_response_utc,
            "last_active_at": la.isoformat() if la else None,
            "last_active_hours_ago": hours_ago}
