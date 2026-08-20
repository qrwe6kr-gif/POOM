from pydantic import BaseModel
from typing import List, Optional

class DemoSeedResponse(BaseModel):
    kr_user_id: str
    us_user_id: str
    project_id: str
    virtual_now: str
    demo_steps: List[str]

class DemoTimeRequest(BaseModel):
    user_ids: List[str]
    now: Optional[str] = None