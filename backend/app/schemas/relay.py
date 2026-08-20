from pydantic import BaseModel, Field
from typing import List

class GridCards(BaseModel):
    progress_summary: str = Field(description="진행 상황")
    decisions_made: str = Field(description="결정 사항")
    pending_items: str = Field(description="미결정 사항")
    key_questions: str = Field(description="핵심 질문")

class ActionItem(BaseModel):
    id: str
    text: str
    checked: bool = False

class SuggestedReply(BaseModel):
    text: str
    tag: str = "톤 완충 적용"

class RelayDigestResponse(BaseModel):
    digest_id: str
    analyzed_count: int
    header_title: str
    header_subtitle: str
    grid_cards: GridCards
    action_items: List[ActionItem]
    suggested_reply: SuggestedReply
    workflow_progress: int = 75

class ActionAcceptRequest(BaseModel):
    digest_id: str
    user_id: int
    reply_content: str
    action_ids: List[str]

class ActionAcceptResponse(BaseModel):
    success: bool
    action_status: str
    sent_message: dict
    workflow: dict
    message: str