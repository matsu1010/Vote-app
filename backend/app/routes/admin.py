from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from app.database import get_db
from app.models.user import User
from app.models.question import Question
from app.models.admin_action_log import AdminActionLog
from app.security import get_current_user, get_super_admin_user
import json

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.post("/users/{user_id}/make-admin")
def make_user_admin(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_super_admin_user)
):
    """Promote user to admin (super admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_admin = True
    
    # Log action
    log = AdminActionLog(
        admin_id=current_user.id,
        action_type="promote_admin",
        action_details=json.dumps({"user_id": str(user_id)}),
        target_resource_id=user_id
    )
    db.add(log)
    db.commit()
    db.refresh(user)
    
    return {"message": "User promoted to admin", "user": user}

@router.post("/questions/{question_id}/close")
def close_question(
    question_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Close a question (admin only)"""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    # Check if user is admin
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can close questions"
        )
    
    question.status = "closed"
    
    # Log action
    log = AdminActionLog(
        admin_id=current_user.id,
        action_type="close_question",
        action_details=json.dumps({"question_id": str(question_id)}),
        target_resource_id=question_id
    )
    db.add(log)
    db.commit()
    db.refresh(question)
    
    return {"message": "Question closed", "question": question}

@router.get("/logs")
def get_admin_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Get admin action logs"""
    logs = db.query(AdminActionLog).order_by(AdminActionLog.created_at.desc()).limit(100).all()
    return logs

def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Verify current user is an admin"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user
