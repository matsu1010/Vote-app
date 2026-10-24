from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
import json

from app.database import get_db
from app.models.user import User
from app.models.question import Question
from app.models.admin_recipient import AdminRecipient
from app.models.admin_action_log import AdminActionLog
from app.models.votoken import VotokenPackage
from app.schemas import VotokenPackageCreate, VotokenPackageResponse, VotokenPackageUpdate
from app.security import get_current_user, get_super_admin_user

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/votoken/packages")
def list_votoken_packages_admin(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_admin and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Only admins can view Votoken packages")

    packages = db.query(VotokenPackage).order_by(VotokenPackage.created_at.desc()).all()
    return packages


@router.post("/votoken/packages", response_model=VotokenPackageResponse)
def create_votoken_package_admin(
    payload: VotokenPackageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_admin and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Only admins can create Votoken packages")

    if payload.vote_count <= 0:
        raise HTTPException(status_code=400, detail="vote_count must be greater than zero")
    if payload.price_cents < 0:
        raise HTTPException(status_code=400, detail="price_cents must be zero or greater")

    package = VotokenPackage(
        name=payload.name,
        vote_count=payload.vote_count,
        price_cents=payload.price_cents,
        currency=payload.currency,
        enabled=payload.enabled,
        expires_in_days=payload.expires_in_days,
    )
    db.add(package)
    db.commit()
    db.refresh(package)
    return package


@router.put("/votoken/packages/{package_id}", response_model=VotokenPackageResponse)
def update_votoken_package_admin(
    package_id: UUID,
    payload: VotokenPackageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_admin and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Only admins can update Votoken packages")

    package = db.query(VotokenPackage).filter(VotokenPackage.id == package_id).first()
    if package is None:
        raise HTTPException(status_code=404, detail="Votoken package not found")

    if payload.name is not None:
        package.name = payload.name
    if payload.vote_count is not None:
        if payload.vote_count <= 0:
            raise HTTPException(status_code=400, detail="vote_count must be greater than zero")
        package.vote_count = payload.vote_count
    if payload.price_cents is not None:
        if payload.price_cents < 0:
            raise HTTPException(status_code=400, detail="price_cents must be zero or greater")
        package.price_cents = payload.price_cents
    if payload.currency is not None:
        package.currency = payload.currency
    if payload.enabled is not None:
        package.enabled = payload.enabled
    if payload.expires_in_days is not None:
        package.expires_in_days = payload.expires_in_days

    db.commit()
    db.refresh(package)
    return package


@router.post("/votoken/packages/{package_id}/toggle")
def toggle_votoken_package_admin(
    package_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_admin and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Only admins can toggle Votoken packages")

    package = db.query(VotokenPackage).filter(VotokenPackage.id == package_id).first()
    if package is None:
        raise HTTPException(status_code=404, detail="Votoken package not found")

    package.enabled = not package.enabled
    db.commit()
    db.refresh(package)
    return {"message": "Package toggled", "enabled": package.enabled, "package_id": str(package.id)}


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
