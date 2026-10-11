from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
import json

from app.database import get_db
from app.models.user import User
from app.models.question import Question
from app.models.admin_recipient import AdminRecipient
from app.models.admin_action_log import AdminActionLog
from app.security import get_current_user, get_super_admin_user

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/questions/{question_id}/recipients")
def add_question_recipient(
    question_id: UUID,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_super_admin_user)
):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    admin_id = payload.get("admin_id")
    if not admin_id:
        raise HTTPException(status_code=400, detail="admin_id is required")

    admin = db.query(User).filter(User.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin user not found")

    if not admin.is_admin:
        raise HTTPException(status_code=403, detail="Selected user is not an admin")

    existing = db.query(AdminRecipient).filter(
        AdminRecipient.question_id == question_id,
        AdminRecipient.admin_id == admin_id
    ).first()

    if existing:
        return {"message": "Admin already assigned", "recipient": existing}

    recipient = AdminRecipient(
        question_id=question_id,
        admin_id=admin_id,
        delivery_mode=payload.get("delivery_mode", "summary"),
        destination_url=payload.get("destination_url")
    )
    db.add(recipient)

    log = AdminActionLog(
        admin_id=current_user.id,
        action_type="assign_result_recipient",
        action_details=json.dumps({
            "question_id": str(question_id),
            "admin_id": str(admin_id)
        }),
        target_resource_id=question_id
    )
    db.add(log)

    db.commit()
    db.refresh(recipient)

    return {"message": "Admin added as recipient", "recipient": recipient}


@router.get("/questions/{question_id}/recipients")
def list_question_recipients(
    question_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    if not current_user.is_admin and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Only admins can view recipients")

    recipients = db.query(AdminRecipient).filter(
        AdminRecipient.question_id == question_id
    ).all()

    return recipients


@router.delete("/questions/{question_id}/recipients/{admin_id}")
def remove_question_recipient(
    question_id: UUID,
    admin_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_super_admin_user)
):
    recipient = db.query(AdminRecipient).filter(
        AdminRecipient.question_id == question_id,
        AdminRecipient.admin_id == admin_id
    ).first()

    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")

    db.delete(recipient)

    log = AdminActionLog(
        admin_id=current_user.id,
        action_type="remove_result_recipient",
        action_details=json.dumps({
            "question_id": str(question_id),
            "admin_id": str(admin_id)
        }),
        target_resource_id=question_id
    )
    db.add(log)

    db.commit()
    return {"message": "Recipient removed"}


@router.post("/users/{user_id}/make-admin")
def make_user_admin(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_super_admin_user)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_admin = True

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
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can close questions")

    question.status = "closed"

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
