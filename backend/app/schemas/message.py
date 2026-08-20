from pydantic import BaseModel
from typing import List, Optional

class MessageItem(BaseModel):
    message_id: str
    sender_name: str
    sender_role: str
    time: str
    content: str
    is_unread: bool

class AbsenceBanner(BaseModel):
    show: bool
    text: str

class MessageListResponse(BaseModel):
    unread_count: int
    absence_banner: AbsenceBanner
    messages: List[MessageItem]

class MessageCreateRequest(BaseModel):
    user_id: int
    content: str

class MessageCreateResponse(BaseModel):
    message_id: str
    sender_name: str
    time: str
    content: str
    created_at: str