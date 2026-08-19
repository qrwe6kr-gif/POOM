"""데모 모드 — 시연 인프라.

시차 단절을 5분 안에 보여주기 위한 '가상 세계 시각'.
두 계정에 동일한 가상 시각을 설정하고 함께 전진시키는 방식으로 사용한다.
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..deps import get_db
from ..engines import ledger
from ..models import Message, Need, Project, Skill, User
from ..timeutil import get_now

router = APIRouter()


class TimeIn(BaseModel):
    user_ids: List[str]
    now: Optional[str] = None   # ISO8601, null이면 해제(실시간 복귀)


@router.post("/demo/time")
def set_time(body: TimeIn, db: Session = Depends(get_db)):
    dt = None
    if body.now:
        dt = datetime.fromisoformat(body.now.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    for uid in body.user_ids:
        u = db.get(User, uid)
        if not u:
            raise HTTPException(404, f"no such user {uid}")
        u.demo_now = dt
    db.commit()
    return {"ok": True, "virtual_now": dt.isoformat() if dt else None}


@router.post("/demo/seed")
def seed(db: Session = Depends(get_db)):
    """한국 개발자 ↔ 미국 서부 디자이너 시연 시나리오를 생성한다."""
    tag = get_now().strftime("%H%M%S")
    kr = User(name="민준(KR·Dev)", email=f"kr_{tag}@demo.poom", country="KR",
              timezone="Asia/Seoul", preferred_language="ko", created_at=get_now())
    us = User(name="Alex(US·Design)", email=f"us_{tag}@demo.poom", country="US",
              timezone="America/Los_Angeles", preferred_language="en", created_at=get_now())
    db.add_all([kr, us]); db.flush()
    ledger.grant_signup_bonus(db, kr.id, get_now())
    ledger.grant_signup_bonus(db, us.id, get_now())
    db.add_all([Skill(user_id=kr.id, skill="dev", level="mid"),
                Need(user_id=kr.id, skill="design", note="인디 게임 로고·키비주얼"),
                Skill(user_id=us.id, skill="design", level="mid"),
                Need(user_id=us.id, skill="dev", note="portfolio site")])

    # 가상 시각 기준선: KST 저녁, LA 새벽 직전 구도를 만들기 좋은 시각
    base = get_now().replace(minute=0, second=0, microsecond=0)
    c = Project(requester_id=kr.id, worker_id=us.id, title="랜딩페이지 UI 제작",
                scope="모바일 메인 화면 시안 제작", agreed_credits=60,
                created_at=base, updated_at=base, deadline=base + timedelta(hours=34))
    db.add(c); db.flush()
    ledger.hold(db, c, base)
    c.status = "IN_PROGRESS"; c.agreed_at = base

    script = ["Hi! Ready to start on the landing page.",                # US
              "메인 화면 시안을 만들어 주세요. 모바일 화면을 먼저 제작해 주세요.",  # KR
              "메인 컬러는 파란색으로 결정했습니다",                       # KR — 결정
              "버튼은 라운드형과 사각형 중 어떤 것이 좋을까요?",           # KR — 질문
              "내일 오전까지 초안을 부탁드립니다"]                         # KR — 액션
    senders = [us.id, kr.id, kr.id, kr.id, kr.id]
    for i, (sid, text) in enumerate(zip(senders, script)):
        db.add(Message(project_id=c.id, sender_id=sid, content=text,
                       sent_at=base + timedelta(minutes=5 * i)))
    for u in (kr, us):
        u.demo_now = base + timedelta(minutes=30)
    db.commit()
    return {"kr_user_id": kr.id, "us_user_id": us.id, "project_id": c.id,
            "virtual_now": (base + timedelta(minutes=30)).isoformat(),
            "demo_steps": [
                "1) KR 화면: GET /api/v1/matching → Alex 매칭·겹침 시간 확인, "
                "협업은 이미 IN_PROGRESS(60c 잠김)",
                "2) POST /api/v1/demo/time 으로 두 계정을 +11h 전진 → "
                "KR이 GET /api/v1/users/{us}/status → SLEEPING",
                "3) KR이 메시지 추가 전송 (US는 수면 중)",
                "4) POST /api/v1/demo/time 으로 +17h 지점 이동(US 오전) → "
                "US가 GET /api/v1/projects/{id}/relay-digest → 자동 생성",
                "5) 양측 POST /api/v1/projects/{id}/complete → 60c 지급, 리뷰 → 동시 공개"]}
