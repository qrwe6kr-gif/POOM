from pydantic import BaseModel
from typing import List, Optional

class GroundedItem(BaseModel):
    text: str
    source_ids: List[int] = []
    verified: bool = True

class ActionItemDto(BaseModel):
    text: str
    source_ids: List[int] = []
    verified: bool = True
    assignee: Optional[str] = None
    deadline: Optional[str] = None

class DigestPayload(BaseModel):
    summary: List[GroundedItem] = []
    decisions: List[GroundedItem] = []
    pending: List[GroundedItem] = []
    key_questions: List[GroundedItem] = []
    action_items: List[ActionItemDto] = []
    tone_cushioned_message: str = ""

class RelayDigestResponse(BaseModel):
    digest_id: Optional[int] = None
    project_id: str
    language: Optional[str] = None
    trigger: Optional[str] = None
    generated: bool
    is_read: bool
    unread_message_count: int
    covers_to_message_id: Optional[int] = None
    digest: Optional[DigestPayload] = None
    created_at: Optional[str] = None
    note: Optional[str] = None