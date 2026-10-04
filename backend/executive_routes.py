from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional

from backend.database import get_db
from backend.models import User, Question, Vote, VoteAuditLog

router = APIRouter(prefix="/executive", tags=["executive"])


class ExportPermissionRequest(BaseModel):
    allow_export: bool = True


@router.get("/questions/pending")
def list_pending_questions(db: Session = Depends(get_db), current_user: User = Depends(lambda: None)):
    raise HTTPException(status_code=501, detail="Executive workflow is not yet implemented")


@router.post("/questions/{question_id}/approve")
def approve_question(question_id: str, db: Session = Depends(get_db), current_user: User = Depends(lambda: None)):
    raise HTTPException(status_code=501, detail="Question approval is not yet implemented")


@router.post("/questions/{question_id}/reject")
def reject_question(question_id: str, db: Session = Depends(get_db), current_user: User = Depends(lambda: None)):
    raise HTTPException(status_code=501, detail="Question rejection is not yet implemented")


@router.post("/questions/{question_id}/archive")
def archive_question(question_id: str, db: Session = Depends(get_db), current_user: User = Depends(lambda: None)):
    raise HTTPException(status_code=501, detail="Question archiving is not yet implemented")


@router.put("/questions/{question_id}/visibility")
def set_visibility(question_id: str, visibility: str, db: Session = Depends(get_db), current_user: User = Depends(lambda: None)):
    raise HTTPException(status_code=501, detail="Result visibility control is not yet implemented")


@router.get("/export")
def export_all_data(db: Session = Depends(get_db), current_user: User = Depends(lambda: None)):
    raise HTTPException(status_code=501, detail="Executive export is not yet implemented")
