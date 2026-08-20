from fastapi import APIRouter, Header, HTTPException
from datetime import datetime
from typing import Optional
from app.db import storage
from app.core.config import settings
from app.schemas.demo import DemoSeedResponse, DemoTimeRequest

router = APIRouter()

def verify_demo_key(x_demo_key: Optional[str]):
    if settings.DEMO_KEY and x_demo_key != settings.DEMO_KEY:
        raise HTTPException(status_code=403, detail="Invalid Demo Key")

@router.post("/seed", response_model=DemoSeedResponse)
def demo_seed(x_demo_key: Optional[str] = Header(None)):
    verify_demo_key(x_demo_key)
    storage.reset_seed()
    return DemoSeedResponse(
        kr_user_id="kr_user_01",
        us_user_id="us_user_01",
        project_id="proj_landing_01",
        virtual_now="2026-08-19T14:15:00+00:00",
        demo_steps=[
            "1) 민준(KR) 로그인 및 상태 확인 (Alex는 SLEEPING)",
            "2) POST /demo/time 으로 시각 전진",
            "3) 민준 화면에서 GET /relay-digest 호출 시 다이제스트 자동 생성",
            "4) 추천 답변 수정 후 메시지 전송 -> is_read: true 자동 전환 및 협업 재개"
        ]
    )

@router.post("/time")
def demo_time(req: DemoTimeRequest, x_demo_key: Optional[str] = Header(None)):
    verify_demo_key(x_demo_key)
    if req.now:
        dt = datetime.fromisoformat(req.now.replace("Z", "+00:00"))
        for uid in req.user_ids:
            storage.virtual_clock[uid] = dt
    else:
        for uid in req.user_ids:
            storage.virtual_clock.pop(uid, None)
    return {"ok": True, "virtual_now": req.now}