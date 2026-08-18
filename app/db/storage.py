from datetime import datetime

# 방 및 워크플로우 상태
room_state = {
    "room_id": "room_landing_01",
    "project_title": "랜딩페이지 UI 제작",
    "workflow": {
        "current_step": 2,
        "progress_percent": 50
    },
    "participants": [
        {
            "user_id": 1,
            "name": "Alex",
            "role": "Project Lead",
            "location": "San Francisco - 07:15",
            "status": "working",
            "badge": "근무 중"
        },
        {
            "user_id": 2,
            "name": "아기 사자",
            "role": "Collaborator",
            "location": "Seoul - 23:15",
            "status": "online",
            "badge": "온라인"
        }
    ],
    "timezone_gap_text": "두 도시의 시차는 16시간입니다."
}

# 초기 Alex의 5개 누적 메시지
initial_messages = [
    {"message_id": "m1", "sender_name": "Alex", "sender_role": "Project Lead", "time": "23:00", "content": "메인 화면 시안을 만들어 주세요.", "is_unread": True},
    {"message_id": "m2", "sender_name": "Alex", "sender_role": "Project Lead", "time": "23:02", "content": "모바일 화면을 먼저 제작해 주세요.", "is_unread": True},
    {"message_id": "m3", "sender_name": "Alex", "sender_role": "Project Lead", "time": "23:05", "content": "메인 컬러는 파란색(#2563eb)으로 결정했습니다.", "is_unread": True},
    {"message_id": "m4", "sender_name": "Alex", "sender_role": "Project Lead", "time": "23:10", "content": "버튼은 라운드형과 사각형 중 어떤 것이 좋을까요?", "is_unread": True},
    {"message_id": "m5", "sender_name": "Alex", "sender_role": "Project Lead", "time": "23:15", "content": "내일 오전까지 초안을 부탁드립니다.", "is_unread": True}
]

messages_db = list(initial_messages)
absence_banner_state = {"show": True, "text": "3시간 동안 답장이 없어 새 메시지 5개가 쌓였습니다."}
latest_digest_cache = None