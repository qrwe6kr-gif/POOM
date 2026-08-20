from pydantic import BaseModel
from typing import Optional

class UserStatusResponse(BaseModel):
    user_id: str
    name: str
    timezone: str
    local_time: str
    status: str
    status_label: str
    next_response_utc: Optional[str] = None
    last_active_at: Optional[str] = None
    last_active_hours_ago: Optional[float] = None