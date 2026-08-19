"""AI Relay 트리거 — 지연 평가(lazy) 방식.

크론이 없다. 수신자가 접속(다이제스트 조회)하는 순간 조건을 검사해 생성한다.
"""
from datetime import datetime
from ..config import RELAY_THRESHOLD_HOURS
from ..timeutil import aware


def uncovered_messages(messages, last_covered_id):
    if last_covered_id is None:
        return list(messages)
    return [m for m in messages if m.id > last_covered_id]


def should_generate(viewer_id: str, messages, last_covered_id, now_utc: datetime,
                    threshold_hours: int = RELAY_THRESHOLD_HOURS):
    """자동 발동 조건: (미커버 메시지 존재) AND (마지막 발화자 ≠ 나) AND (경과 ≥ 임계).

    반환: (발동 여부, 미커버 메시지 목록)
    """
    if not messages:
        return False, []
    unc = uncovered_messages(messages, last_covered_id)
    if not unc:
        return False, []
    last = messages[-1]
    if last.sender_id == viewer_id:
        return False, unc
    elapsed_h = (now_utc - aware(last.sent_at)).total_seconds() / 3600
    return elapsed_h >= threshold_hours, unc
