from fastapi import APIRouter
from app.db import storage
from app.schemas.relay import RelayDigestResponse
from app.services.langchain_relay import generate_relay_digest

router = APIRouter()

@router.post("/relay-digest", response_model=RelayDigestResponse)
def get_or_create_relay_digest():
    digest = generate_relay_digest(storage.messages_db)
    storage.latest_digest_cache = digest
    storage.room_state["workflow"]["current_step"] = 3
    storage.room_state["workflow"]["progress_percent"] = 75
    return digest