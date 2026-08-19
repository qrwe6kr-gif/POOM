from fastapi import FastAPI

from .db import init_db
from .routers import collabs, demo, users

app = FastAPI(title="POOM Backend", version="0.1.0",
              description="POOM + AI Relay — 해커톤 백엔드 스타터")
init_db()
app.include_router(users.router, tags=["users"])
app.include_router(collabs.router, tags=["collabs"])
app.include_router(demo.router, tags=["demo"])


@app.get("/health")
def health():
    return {"ok": True}
