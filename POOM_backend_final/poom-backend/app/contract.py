"""내부 표현 ↔ 팀 확정 API 계약 v2(docs/api_spec_v2.md)의 경계 변환.

엔진·finalize()의 내부 키는 그대로 두고, 라우터가 **응답을 만드는 순간에만**
v2 네이밍으로 바꾼다. 이 파일이 그 유일한 경계다.
내부 스키마를 건드리지 않으므로 환각 게이트(engines/digest.py의 finalize)는 영향받지 않는다.

주의 — DB 모델이 스키마 v2로 전환된 뒤로 **프로젝트 상태(MATCHED/IN_PROGRESS/…)와
거래 종류(SIGNUP_BONUS/HOLD/…)는 저장 값이 곧 계약 값**이라 변환이 필요 없다.
여기 남은 것은 실제로 표현이 다른 것들뿐이다: 상태 엔진의 소문자 state, 조회자 언어 라벨,
12시간제 시각, 다이제스트 payload 키.
"""
from typing import Optional

from .engines.digest import FIELDS

# Timezone Status 엔진의 state → v2 status
USER_STATUS = {
    "working": "WORKING",
    "sleeping": "SLEEPING",
    "soon": "STARTING_SOON",
    "away": "AWAY",
}

# status_label — **조회자**의 preferred_language 기준(대상자 언어가 아니다)
STATUS_LABEL = {
    "ko": {"WORKING": "업무 가능", "SLEEPING": "비근무",
           "STARTING_SOON": "근무 시작 예정", "AWAY": "자리 비움"},
    "en": {"WORKING": "Available", "SLEEPING": "Off hours",
           "STARTING_SOON": "Starting soon", "AWAY": "Away"},
}

# 다이제스트 payload 키: 내부(engines.digest.FIELDS) → v2
DIGEST_KEYS = {
    "relay_summary": "summary",
    "decisions": "decisions",
    "open_items": "pending",
    "key_questions": "key_questions",
    "action_items": "action_items",
    "tone_note": "tone_cushioned_message",
}


def user_status(state: str) -> str:
    return USER_STATUS.get(state, state.upper())


def status_label(status: str, viewer_lang: str) -> str:
    table = STATUS_LABEL.get(viewer_lang) or STATUS_LABEL["en"]
    return table.get(status, status)


def local_time_12h(hhmm: str) -> str:
    """엔진의 24시간제 "03:45" → 명세 표기 "03:45 AM"."""
    h, m = (int(x) for x in hhmm.split(":"))
    return f"{(h % 12) or 12:02d}:{m:02d} {'AM' if h < 12 else 'PM'}"


def digest_payload(payload: Optional[dict]) -> Optional[dict]:
    """저장된 내부 payload를 v2 필드명으로 바꿔 내보낸다. 값·항목 구조는 손대지 않는다."""
    if not payload:
        return None
    out = {DIGEST_KEYS[k]: payload.get(k, []) for k in FIELDS[:5]}
    out[DIGEST_KEYS["tone_note"]] = payload.get("tone_note", "")
    return out
