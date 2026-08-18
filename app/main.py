from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import room, messages, demo, relay, action

app = FastAPI(
    title="POOM Backend API",
    description="AI 기반 비동기 글로벌 메이커 협업 플랫폼 API",
    version="1.0.0"
)

# 프론트엔드 연동을 위한 CORS 전체 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(room.router, prefix="/api", tags=["Room"])
app.include_router(messages.router, prefix="/api", tags=["Messages"])
app.include_router(demo.router, prefix="/api", tags=["Demo"])
app.include_router(relay.router, prefix="/api", tags=["Relay Digest"])
app.include_router(action.router, prefix="/api", tags=["Action"])

@app.get("/")
def root():
    return {"status": "ok", "message": "POOM Backend Server is Running!"}