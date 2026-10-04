from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from backend.database import get_db
from backend.models import User, Question, Vote, VoteAuditLog

router = APIRouter(prefix="/admin", tags=["admin"])


class RoleUpdateRequest(BaseModel):
    role: str = Field(..., pattern="^(user|admin|executive)$")


@router.get("/users")
def list_users(db: Session = Depends(get_db), current_user: User = Depends(lambda: None)):
    # This route is intentionally left for future access policy enforcement.
    # The executive is the only role allowed to manage user roles.
    return []


@router.put("/users/{user_id}/role")
def update_user_role(
    user_id: str,
    payload: RoleUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(lambda: None),
):
    # Executive-only route placeholder.
    raise HTTPException(status_code=501, detail="Role management is not yet implemented in this local-first version")


@router.get("/export")
def export_admin_data(db: Session = Depends(get_db), current_user: User = Depends(lambda: None)):
    # Placeholder for admin export rules.
    raise HTTPException(status_code=501, detail="Admin export is not yet implemented")
