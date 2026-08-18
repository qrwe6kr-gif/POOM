from fastapi import APIRouter
from app.db import storage
from app.schemas.demo import SimulateGapRequest, SimulateGapResponse

router = APIRouter()

@router.post("/demo/simulate-gap", response_model=SimulateGapResponse)
def simulate_gap(req: SimulateGapRequest):
    storage.absence_banner_state["show"] = True
    storage.absence_banner_state["text"] = f"{int(req.hours_ago)}시간 동안 답장이 없어 새 메시지 5개가 쌓였습니다."
    storage.room_state["workflow"]["current_step"] = 2
    storage.room_state["workflow"]["progress_percent"] = 50
    return {
        "status": "gap_simulated",
        "hours_passed": req.hours_ago,
        "target_user_status": "online",
        "ready_for_relay": True,
        "message": f"{req.hours_ago}시간 전으로 활동 시간이 변경되어 AI Relay 조건이 충족되었습니다."
    }