from fastapi import APIRouter, Header, HTTPException
from typing import Optional
from app.db import storage
from app.schemas.project import ProjectDetailResponse, Participant

router = APIRouter()

@router.get("/{project_id}", response_model=ProjectDetailResponse)
def get_project(project_id: str, x_user_id: Optional[str] = Header(None)):
    proj = storage.projects_db.get(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    req_u = storage.users_db[proj["requester_id"]]
    work_u = storage.users_db[proj["worker_id"]]

    my_role = "worker" if x_user_id == proj["worker_id"] else "requester"

    return ProjectDetailResponse(
        project_id=proj["id"],
        title=proj["title"],
        scope=proj.get("scope"),
        status=proj["status"],
        agreed_credits=proj["agreed_credits"],
        deadline=proj.get("deadline"),
        participants=[
            Participant(user_id=req_u["id"], name=req_u["name"], timezone=req_u["timezone"], country=req_u["country"], role="requester"),
            Participant(user_id=work_u["id"], name=work_u["name"], timezone=work_u["timezone"], country=work_u["country"], role="worker")
        ],
        my_role=my_role
    )