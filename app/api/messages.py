from fastapi import APIRouter
from datetime import datetime
from app.db import storage
from app.schemas.message import MessageListResponse, MessageCreateRequest, MessageCreateResponse, MessageItem

router = APIRouter()

@router.get("/messages", response_model=MessageListResponse)
def get_messages():
    unread = sum(1 for m in storage.messages_db if m.get("is_unread", False))
    return {
        "unread_count": unread,
        "absence_banner": storage.absence_banner_state,
        "messages": storage.messages_db
    }

@router.post("/messages", response_model=MessageCreateResponse)
def send_message(req: MessageCreateRequest):
    new_msg = {
        "message_id": f"m{len(storage.messages_db) + 1}",
        "sender_name": "아기 사자" if req.user_id == 2 else "Alex",
        "sender_role": "Collaborator" if req.user_id == 2 else "Project Lead",
        "time": datetime.now().strftime("%H:%M"),
        "content": req.content,
        "is_unread": False,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    storage.messages_db.append(new_msg)
    return new_msg