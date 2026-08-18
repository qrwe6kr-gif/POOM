from pydantic import BaseModel
from typing import List

class WorkflowDto(BaseModel):
    current_step: int
    progress_percent: int

class ParticipantDto(BaseModel):
    user_id: int
    name: str
    role: str
    location: str
    status: str
    badge: str

class RoomResponse(BaseModel):
    room_id: str
    project_title: str
    workflow: WorkflowDto
    participants: List[ParticipantDto]
    timezone_gap_text: str