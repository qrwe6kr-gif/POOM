from pydantic import BaseModel

class SimulateGapRequest(BaseModel):
    user_id: int
    hours_ago: float

class SimulateGapResponse(BaseModel):
    status: str
    hours_passed: float
    target_user_status: str
    ready_for_relay: bool
    message: str