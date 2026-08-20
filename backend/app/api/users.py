from fastapi import APIRouter, Header, HTTPException
from typing import Optional
from app.services.status_service import calculate_user_status
from app.schemas.user import UserStatusResponse
from app.db import storage

router = APIRouter()

@router.get("/{user_id}/status", response_model=UserStatusResponse)
def get_user_status(user_id: str, x_user_id: Optional[str] = Header(None)):
    viewer_lang = "ko"
    if x_user_id and x_user_id in storage.users_db:
        viewer_lang = storage.users_db[x_user_id]["preferred_language"]
    
    try:
        return calculate_user_status(user_id, viewer_lang=viewer_lang)
    except ValueError:
        raise HTTPException(status_code=404, detail="User not found")