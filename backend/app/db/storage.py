from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Dict, List, Any, Optional

# 가상 현재 시각 (기본 실시간)
virtual_clock: Dict[str, Optional[datetime]] = {}

def get_current_time(user_id: Optional[str] = None) -> datetime:
    if user_id and user_id in virtual_clock and virtual_clock[user_id]:
        return virtual_clock[user_id]
    return datetime.now(timezone.utc)

# 1. 사용자 테이블 (v2 명세)
users_db: Dict[str, Dict[str, Any]] = {
    "kr_user_01": {
        "id": "kr_user_01",
        "name": "민준",
        "email": "minjun@poom.dev",
        "country": "KR",
        "timezone": "Asia/Seoul",
        "preferred_language": "ko",
        "work_start": 9,
        "work_end": 18,
        "sleep_start": 23,
        "sleep_end": 7,
        "last_active_at": datetime(2026, 8, 19, 14, 0, tzinfo=timezone.utc)
    },
    "us_user_01": {
        "id": "us_user_01",
        "name": "Alex",
        "email": "alex@poom.dev",
        "country": "US",
        "timezone": "America/Los_Angeles",
        "preferred_language": "en",
        "work_start": 9,
        "work_end": 18,
        "sleep_start": 23,
        "sleep_end": 7,
        "last_active_at": datetime(2026, 8, 19, 14, 15, tzinfo=timezone.utc)
    }
}

# 2. 프로젝트 테이블
projects_db: Dict[str, Dict[str, Any]] = {
    "proj_landing_01": {
        "id": "proj_landing_01",
        "requester_id": "kr_user_01",
        "worker_id": "us_user_01",
        "title": "랜딩페이지 UI 제작",
        "scope": "모바일 메인 화면 시안 제작 및 디자인 가이드",
        "agreed_credits": 60,
        "status": "IN_PROGRESS",
        "deadline": "2026-08-21T18:00:00+00:00",
        "requester_completed": False,
        "worker_completed": False
    }
}

# 3. 메시지 테이블 (팀 플로우 대본 5건)
messages_db: List[Dict[str, Any]] = [
    {"id": 1, "project_id": "proj_landing_01", "sender_id": "us_user_01", "content": "메인 화면 시안을 만들어 주세요.", "sent_at": "2026-08-19T14:00:00+00:00", "read_at": None},
    {"id": 2, "project_id": "proj_landing_01", "sender_id": "us_user_01", "content": "모바일 화면을 먼저 제작해 주세요.", "sent_at": "2026-08-19T14:02:00+00:00", "read_at": None},
    {"id": 3, "project_id": "proj_landing_01", "sender_id": "us_user_01", "content": "메인 컬러는 파란색(#2563eb)으로 결정했습니다.", "sent_at": "2026-08-19T14:05:00+00:00", "read_at": None},
    {"id": 4, "project_id": "proj_landing_01", "sender_id": "us_user_01", "content": "버튼은 라운드형과 사각형 중 어떤 것이 좋을까요?", "sent_at": "2026-08-19T14:10:00+00:00", "read_at": None},
    {"id": 5, "project_id": "proj_landing_01", "sender_id": "us_user_01", "content": "내일 오전까지 초안을 부탁드립니다.", "sent_at": "2026-08-19T14:15:00+00:00", "read_at": None}
]

# 4. 다이제스트 테이블
digests_db: List[Dict[str, Any]] = []

def reset_seed():
    global messages_db, digests_db, virtual_clock
    virtual_clock.clear()
    digests_db.clear()
    messages_db = [
        {"id": 1, "project_id": "proj_landing_01", "sender_id": "us_user_01", "content": "메인 화면 시안을 만들어 주세요.", "sent_at": "2026-08-19T14:00:00+00:00", "read_at": None},
        {"id": 2, "project_id": "proj_landing_01", "sender_id": "us_user_01", "content": "모바일 화면을 먼저 제작해 주세요.", "sent_at": "2026-08-19T14:02:00+00:00", "read_at": None},
        {"id": 3, "project_id": "proj_landing_01", "sender_id": "us_user_01", "content": "메인 컬러는 파란색(#2563eb)으로 결정했습니다.", "sent_at": "2026-08-19T14:05:00+00:00", "read_at": None},
        {"id": 4, "project_id": "proj_landing_01", "sender_id": "us_user_01", "content": "버튼은 라운드형과 사각형 중 어떤 것이 좋을까요?", "sent_at": "2026-08-19T14:10:00+00:00", "read_at": None},
        {"id": 5, "project_id": "proj_landing_01", "sender_id": "us_user_01", "content": "내일 오전까지 초안을 부탁드립니다.", "sent_at": "2026-08-19T14:15:00+00:00", "read_at": None}
    ]