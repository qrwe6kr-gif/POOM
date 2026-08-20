from fastapi import APIRouter, Header, HTTPException
from datetime import datetime, timezone
from typing import Optional
from app.db import storage
from app.services.langchain_relay import generate_ai_digest
from app.schemas.common import RelayDigestResponse

router = APIRouter()

@router.get("/{project_id}/relay-digest", response_model=RelayDigestResponse)
def get_or_evaluate_relay_digest(project_id: str, x_user_id: Optional[str] = Header(None)):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header required")

    proj = storage.projects_db.get(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    user = storage.users_db.get(x_user_id)
    recipient_lang = user["preferred_language"] if user else "ko"

    # 기존 미확인 다이제스트가 있는지 확인
    for d in reversed(storage.digests_db):
        if d["project_id"] == project_id and d["recipient_id"] == x_user_id and not d["is_read"]:
            return RelayDigestResponse(
                digest_id=d["id"],
                project_id=project_id,
                language=d["language"],
                trigger=d["trigger_type"],
                generated=True,
                is_read=d["is_read"],
                unread_message_count=len(d["messages_covered"]),
                covers_to_message_id=d["covers_to_message_id"],
                digest=d["payload"],
                created_at=d["created_at"]
            )

    # 지연 평가: 미커버 메시지 추출 (상대방이 보낸 메시지)
    uncovered = [m for m in storage.messages_db if m["project_id"] == project_id and m["sender_id"] != x_user_id]
    
    if not uncovered:
        return RelayDigestResponse(
            project_id=project_id,
            generated=False,
            is_read=False,
            unread_message_count=0
        )

    # 시간 경과 체크 (3시간 이상 또는 최초)
    payload = generate_ai_digest(uncovered, lang=recipient_lang)
    new_digest_id = len(storage.digests_db) + 1
    created_at_iso = storage.get_current_time(x_user_id).isoformat()

    digest_record = {
        "id": new_digest_id,
        "project_id": project_id,
        "recipient_id": x_user_id,
        "language": recipient_lang,
        "trigger_type": "auto",
        "covers_to_message_id": uncovered[-1]["id"],
        "messages_covered": [m["id"] for m in uncovered],
        "payload": payload,
        "is_read": False,
        "created_at": created_at_iso
    }
    storage.digests_db.append(digest_record)

    return RelayDigestResponse(
        digest_id=new_digest_id,
        project_id=project_id,
        language=recipient_lang,
        trigger="auto",
        generated=True,
        is_read=False,
        unread_message_count=len(uncovered),
        covers_to_message_id=uncovered[-1]["id"],
        digest=payload,
        created_at=created_at_iso
    )

@router.post("/{project_id}/relay-digest", response_model=RelayDigestResponse)
def manual_generate_relay_digest(project_id: str, x_user_id: Optional[str] = Header(None)):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header required")

    user = storage.users_db.get(x_user_id)
    recipient_lang = user["preferred_language"] if user else "ko"
    uncovered = [m for m in storage.messages_db if m["project_id"] == project_id and m["sender_id"] != x_user_id]

    payload = generate_ai_digest(uncovered, lang=recipient_lang)
    new_digest_id = len(storage.digests_db) + 1
    created_at_iso = storage.get_current_time(x_user_id).isoformat()

    return RelayDigestResponse(
        digest_id=new_digest_id,
        project_id=project_id,
        language=recipient_lang,
        trigger="manual",
        generated=True,
        is_read=False,
        unread_message_count=len(uncovered),
        covers_to_message_id=uncovered[-1]["id"] if uncovered else None,
        digest=payload,
        created_at=created_at_iso
    )