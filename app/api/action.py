from fastapi import APIRouter
from datetime import datetime
from app.db import storage
from app.schemas.relay import ActionAcceptRequest, ActionAcceptResponse

router = APIRouter()

@router.post("/action/accept", response_model=ActionAcceptResponse)
def accept_action_and_reply(req: ActionAcceptRequest):
    # 1. 메시지 추가
    new_msg = {
        "message_id": f"m{len(storage.messages_db) + 1}",
        "sender_name": "아기 사자",
        "sender_role": "Collaborator",
        "time": datetime.now().strftime("%H:%M"),
        "content": req.reply_content,
        "is_unread": False
    }
    storage.messages_db.append(new_msg)
    
    # 2. 모든 메시지 읽음 처리 및 배너 숨김
    for m in storage.messages_db:
        m["is_unread"] = False
    storage.absence_banner_state["show"] = False

    # 3. 워크플로우 100% 완료로 갱신
    storage.room_state["workflow"]["current_step"] = 4
    storage.room_state["workflow"]["progress_percent"] = 100
    
    return {
        "success": True,
        "action_status": f"{len(req.action_ids)}/2 완료",
        "sent_message": new_msg,
        "workflow": {
            "current_step": 4,
            "progress_percent": 100,
            "step_name": "협업 재개"
        },
        "message": "답변이 전송되고 협업이 정상적으로 재개되었습니다."
    }