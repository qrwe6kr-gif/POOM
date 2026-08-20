from pydantic import BaseModel
from typing import List, Optional

class Participant(BaseModel):
    user_id: str
    name: str
    timezone: str
    country: str
    role: str

class ProjectDetailResponse(BaseModel):
    project_id: str
    title: str
    scope: Optional[str] = None
    status: str
    agreed_credits: int
    deadline: Optional[str] = None
    participants: List[Participant]
    my_role: str

class MessageItemDto(BaseModel):
    message_id: int
    sender_id: str
    body: str
    created_at: str
    mine: bool

class MessageListResponse(BaseModel):
    messages: List[MessageItemDto]

class MessageSendRequest(BaseModel):
    body: str

class MessageSendResponse(BaseModel):
    message_id: int
    created_at: str