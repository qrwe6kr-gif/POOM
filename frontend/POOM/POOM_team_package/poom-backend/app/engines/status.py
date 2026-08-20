"""Timezone Status 엔진 — 순수 함수. DB·프레임워크 의존 없음."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from ..config import SOON_HOURS


@dataclass
class Status:
    local_time: str          # "HH:MM"
    state: str               # working | sleeping | soon | away
    next_response_utc: Optional[str]  # 예상 응답 가능 시각(ISO), working이면 None


def in_window(hour: float, start: int, end: int) -> bool:
    """[start, end) 구간 포함 여부. 자정을 넘는 구간(예: 23~7)도 처리."""
    if start == end:
        return False
    if start < end:
        return start <= hour < end
    return hour >= start or hour < end


def next_work_start_utc(local_now: datetime, work_start: int) -> datetime:
    cand = local_now.replace(hour=work_start, minute=0, second=0, microsecond=0)
    if cand <= local_now:
        cand += timedelta(days=1)
    return cand.astimezone(timezone.utc)


def compute_status(tz: str, work_start: int, work_end: int,
                   sleep_start: int, sleep_end: int, now_utc: datetime) -> Status:
    local = now_utc.astimezone(ZoneInfo(tz))
    h = local.hour + local.minute / 60

    if in_window(h, work_start, work_end):
        return Status(local.strftime("%H:%M"), "working", None)

    nxt = next_work_start_utc(local, work_start)
    if in_window(h, sleep_start, sleep_end):
        state = "sleeping"
    else:
        hours_to = (nxt - now_utc).total_seconds() / 3600
        state = "soon" if hours_to <= SOON_HOURS else "away"
    return Status(local.strftime("%H:%M"), state, nxt.isoformat())


def working_at(user, t_utc: datetime) -> bool:
    local = t_utc.astimezone(ZoneInfo(user.tz))
    return in_window(local.hour + local.minute / 60, user.work_start, user.work_end)


def overlap_hours(a, b, now_utc: datetime) -> float:
    """오늘 24시간 동안 두 사람의 근무 시간이 겹치는 시간(시간 단위, 15분 해상도)."""
    base = now_utc.replace(minute=0, second=0, microsecond=0)
    q = sum(1 for i in range(96)
            if working_at(a, base + timedelta(minutes=15 * i))
            and working_at(b, base + timedelta(minutes=15 * i)))
    return q * 15 / 60
