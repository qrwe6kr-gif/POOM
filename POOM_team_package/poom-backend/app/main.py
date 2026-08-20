from typing import Any, Dict, List, Optional
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="POOM Backend",
    version="0.1.0",
    description="POOM + AI Relay — 해커톤 백엔드 스타터"
)

# 1. CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. 헬스 체크
@app.get("/health")
def health():
    return {"ok": True}

# 3. 방 정보 조회
@app.get("/api/room")
async def get_room():
    return {
        "status": "success",
        "room_id": "room-1",
        "title": "랜딩페이지 UI 제작",
        "participants": [
            {"id": "alex", "name": "Alex", "role": "Project Lead", "status": "off_work", "timezone": "San Francisco"},
            {"id": "user", "name": "아기 사자", "role": "Maker", "status": "online", "timezone": "Seoul"}
        ]
    }

# 4. 메시지 목록 조회
@app.get("/api/messages")
async def get_messages():
    return {
        "status": "success",
        "messages": [
            {"sender": "Alex", "role": "Project Lead", "time": "어제 13:00 PDT", "text": "안녕하세요. 이번 랜딩페이지는 처음 방문한 사용자가 POOM이 어떤 문제를 해결하는지 바로 이해하는 것이 가장 중요합니다. 메인 화면에서 핵심 가치와 주요 CTA가 자연스럽게 이어지도록 1차 시안을 부탁드려요."},
            {"sender": "Alex", "role": "Project Lead", "time": "어제 13:18 PDT", "text": "우선 모바일 화면부터 작업해 주시면 좋겠습니다. 390px 기준으로 헤드라인, 서비스 요약, CTA 순서가 명확하게 보이도록 정보 위계를 잡아 주시고, 실제 사용 시 버튼을 누르기 불편하지 않은지도 함께 봐주세요."},
            {"sender": "Alex", "role": "Project Lead", "time": "어제 13:42 PDT", "text": "메인 컬러는 파란색(#2563eb)으로 정리했습니다. 화면 전체를 파란색으로 채우기보다는 버튼과 꼭 강조해야 하는 정보에만 사용하고, 배경과 카드는 차분하게 구성해 주시면 좋겠습니다."},
            {"sender": "Alex", "role": "Project Lead", "time": "어제 14:20 PDT", "text": "버튼 형태는 아직 최종 결정하지 못했습니다. 라운드형과 각진 형태 중 POOM의 신뢰감 있고 부드러운 인상에 더 잘 맞는 방향을 디자이너 관점에서 제안해 주시면 시안 검토에 도움이 될 것 같아요."},
            {"sender": "Alex", "role": "Project Lead", "time": "어제 15:10 PDT", "text": "내일 오전에 팀 내부 리뷰를 진행할 예정입니다. 가능하다면 모바일 1차 시안과 함께 주요 레이아웃을 그렇게 구성한 이유를 짧게 정리해서 보내 주세요. 검토 후 피드백을 한 번에 전달드리겠습니다."}
        ]
    }

# 5. AI 다이제스트 생성
@app.post("/api/relay-digest")
async def create_relay_digest(request: Request):
    return {
        "status": "success",
        "digest": {
            "summary": "Alex가 아기 사자의 수면 시간 동안 랜딩페이지 메인 화면의 구체적인 제작 조건을 전달했습니다.",
            "decisions": "모바일 390px 화면을 우선 설계하고, 메인 컬러는 파란색(#2563eb)으로 적용하기로 했습니다.",
            "pending": "CTA 버튼 형태와 카드 대비 수준에 대한 최종 디자인 판단이 필요합니다.",
            "key_questions": "브랜드 인상과 접근성을 고려할 때 CTA 버튼을 라운드형과 사각형 중 어떤 형태로 제작할까요?",
            "action_items": [
                {"id": 1, "text": "모바일 메인 화면 1차 시안 제작", "completed": False},
                {"id": 2, "text": "디자인 의도와 함께 내일 오전까지 전달", "completed": False}
            ],
            "suggested_reply": "전달해 주신 요구사항을 확인했습니다. 모바일 390px 화면을 우선 설계하고 접근성 대비도 함께 점검하겠습니다. CTA는 전체 인상과 자연스럽게 연결되는 라운드형으로 먼저 제안드리겠습니다."
        }
    }

# 6. 액션 수락 및 메시지 전송 (모든 URL 패턴 대응)
@app.api_route("/api/action/accept", methods=["GET", "POST", "PUT", "PATCH"])
@app.api_route("/api/accept", methods=["GET", "POST", "PUT", "PATCH"])
@app.api_route("/api/accept/{path:path}", methods=["GET", "POST", "PUT", "PATCH"])
@app.api_route("/api/collabs/{path:path}", methods=["GET", "POST", "PUT", "PATCH"])
@app.api_route("/api/demo/{path:path}", methods=["GET", "POST", "PUT", "PATCH"])
async def handle_accept_action(request: Request):
    return {"status": "success", "message": "Action accepted and reply sent"}