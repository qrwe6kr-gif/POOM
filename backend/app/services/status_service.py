from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from app.db import storage
from app.schemas.user import UserStatusResponse

STATUS_LABELS = {
    "ko": {"WORKING": "업무 가능", "SLEEPING": "비근무", "STARTING_SOON": "근무 시작 예정", "AWAY": "자리 비움"},
    "en": {"WORKING": "Available", "SLEEPING": "Off hours", "STARTING_SOON": "Starting soon", "AWAY": "Away"}
}

def calculate_user_status(target_user_id: str, viewer_lang: str = "ko") -> UserStatusResponse:
    user = storage.users_db.get(target_user_id)
    if not user:
        raise ValueError("User not found")

    now_utc = storage.get_current_time(target_user_id)
    tz = ZoneInfo(user["timezone"])
    local_dt = now_utc.astimezone(tz)
    local_hour = local_dt.hour + local_dt.minute / 60.0

    w_start, w_end = user["work_start"], user["work_end"]
    s_start, s_end = user["sleep_start"], user["sleep_end"]

    # 1. 상태 판정 로직
    is_sleep = (local_hour >= s_start or local_hour < s_end) if s_start > s_end else (s_start <= local_hour < s_end)
    is_work = (w_start <= local_hour < w_end)

    next_response_utc = None

    if is_work:
        status = "WORKING"
    elif is_sleep:
        status = "SLEEPING"
        # 다음 출근 시간 계산
        target_day = local_dt.date() if local_hour < w_start else local_dt.date() + timedelta(days=1)
        next_work_local = datetime(target_day.year, target_day.month, target_day.day, w_start, 0, tzinfo=tz)
        next_response_utc = next_work_local.astimezone(timezone.utc).isoformat()
    elif (w_start - 3) <= local_hour < w_start:
        status = "STARTING_SOON"
        target_day = local_dt.date()
        next_work_local = datetime(target_day.year, target_day.month, target_day.day, w_start, 0, tzinfo=tz)
        next_response_utc = next_work_local.astimezone(timezone.utc).isoformat()
    else:
        status = "AWAY"

    last_active = user.get("last_active_at")
    hours_ago = (now_utc - last_active).total_seconds() / 3600.0 if last_active else None

    labels = STATUS_LABELS.get(viewer_lang, STATUS_LABELS["ko"])
    
    return UserStatusResponse(
        user_id=user["id"],
        name=user["name"],
        timezone=user["timezone"],
        local_time=local_dt.strftime("%I:%M %p"),
        status=status,
        status_label=labels.get(status, status),
        next_response_utc=next_response_utc,
        last_active_at=last_active.isoformat() if last_active else None,
        last_active_hours_ago=round(hours_ago, 1) if hours_ago is not None else None
    )