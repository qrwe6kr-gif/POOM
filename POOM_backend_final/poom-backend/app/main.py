from fastapi import FastAPI

from .db import init_db
from .routers import collabs, demo, users

API_PREFIX = "/api/v1"   # 팀 확정 계약 v2 — docs/api_spec_v2.md

app = FastAPI(title="POOM Backend", version="0.2.0",
              description="POOM + AI Relay — 해커톤 백엔드 (API 계약 v2)")
init_db()
app.include_router(users.router, prefix=API_PREFIX, tags=["users"])
app.include_router(collabs.router, prefix=API_PREFIX, tags=["projects"])
app.include_router(demo.router, prefix=API_PREFIX, tags=["demo"])


@app.get("/health")
def health():
    """인프라 헬스체크 — 계약 밖의 루트 경로에 둔다(로드밸런서·배포 플랫폼용)."""
    return {"ok": True}
