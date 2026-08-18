from fastapi import APIRouter
from app.db import storage
from app.schemas.room import RoomResponse

router = APIRouter()

@router.get("/room", response_model=RoomResponse)
def get_room_info():
    return storage.room_state