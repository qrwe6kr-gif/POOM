from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import FRONTEND_ORIGIN
from .db import init_db
from .routers import collabs, demo, users

API_PREFIX = "/api/v1"   # 팀 확정 계약 v2 — docs/api_spec_v2.md

DEV_ORIGIN = "http://localhost:3000"          # Next.js 개발 서버
ALLOWED_ORIGINS = [DEV_ORIGIN]
if FRONTEND_ORIGIN and FRONTEND_ORIGIN != DEV_ORIGIN:
    ALLOWED_ORIGINS.append(FRONTEND_ORIGIN)   # 배포된 프론트 도메인

app = FastAPI(title="POOM Backend", version="0.2.0",
              description="POOM + AI Relay — 해커톤 백엔드 (API 계약 v2)")

# 인증이 쿠키가 아니라 X-User-Id 헤더 방식이므로 allow_credentials는 켜지 않는다.
# (켜면 브라우저가 자격 증명 요청으로 취급해 오리진 와일드카드·프리플라이트 규칙이 더 빡빡해진다)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],          # 커스텀 헤더 X-User-Id가 preflight를 통과해야 한다
    allow_credentials=False,
)

init_db()
app.include_router(users.router, prefix=API_PREFIX, tags=["users"])
app.include_router(collabs.router, prefix=API_PREFIX, tags=["projects"])
app.include_router(demo.router, prefix=API_PREFIX, tags=["demo"])


@app.get("/health")
def health():
    """인프라 헬스체크 — 계약 밖의 루트 경로에 둔다(로드밸런서·배포 플랫폼용)."""
    return {"ok": True}
