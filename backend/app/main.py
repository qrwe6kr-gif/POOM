from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import users, projects, messages, digest, demo

app = FastAPI(
    title="POOM API v2",
    description="AI 기반 비동기 글로벌 메이커 협업 플랫폼 API v2",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 인프라 헬스체크
@app.get("/health", tags=["Infra"])
def health():
    return {"ok": True}

# v2 API 라우터 등록
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["Projects"])
app.include_router(messages.router, prefix="/api/v1/projects", tags=["Messages"])
app.include_router(digest.router, prefix="/api/v1/projects", tags=["AI Relay Digest"])
app.include_router(demo.router, prefix="/api/v1/demo", tags=["Demo"])