from fastapi import APIRouter, Header, HTTPException
from datetime import datetime, timezone
from typing import Optional
from app.db import storage
from app.schemas.project import MessageListResponse, MessageItemDto, MessageSendRequest, MessageSendResponse

router = APIRouter()

@router.get("/{project_id}/messages", response_model=MessageListResponse)
def list_messages(project_id: str, x_user_id: Optional[str] = Header(None)):
    items = []
    for m in storage.messages_db:
        if m["project_id"] == project_id:
            items.append(MessageItemDto(
                message_id=m["id"],
                sender_id=m["sender_id"],
                body=m["content"],
                created_at=m["sent_at"],
                mine=(m["sender_id"] == x_user_id)
            ))
    return MessageListResponse(messages=items)

@router.post("/{project_id}/messages", response_model=MessageSendResponse)
def send_message(project_id: str, req: MessageSendRequest, x_user_id: Optional[str] = Header(None)):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header required")

    now_iso = storage.get_current_time(x_user_id).isoformat()
    new_id = len(storage.messages_db) + 1
    new_msg = {
        "id": new_id,
        "project_id": project_id,
        "sender_id": x_user_id,
        "content": req.body,
        "sent_at": now_iso,
        "read_at": None
    }
    storage.messages_db.append(new_msg)

    # 확인 완료 규칙: 메시지 전송 시 해당 프로젝트의 미확인 다이제스트 자동 완료
    for d in storage.digests_db:
        if d["project_id"] == project_id and d["recipient_id"] == x_user_id:
            d["is_read"] = True

    return MessageSendResponse(message_id=new_id, created_at=now_iso)