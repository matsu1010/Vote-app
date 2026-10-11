from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from app.database import get_db
from app.models.user import User
from app.models.question import Question
from app.schemas import QuestionCreate, QuestionUpdate, QuestionResponse
from app.security import get_current_user, get_admin_user

router = APIRouter(prefix="/api/questions", tags=["questions"])

@router.post("", response_model=QuestionResponse)
def create_question(
    question_data: QuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Create a new question (admin only)"""
    new_question = Question(
        title=question_data.title,
        description=question_data.description,
        require_email_verification=question_data.require_email_verification,
        allow_anonymous=question_data.allow_anonymous,
        enable_data_retention=question_data.enable_data_retention
    )
    db.add(new_question)
    db.commit()
    db.refresh(new_question)
    return new_question

@router.get("", response_model=list[QuestionResponse])
def list_questions(db: Session = Depends(get_db)):
    """List all open questions"""
    questions = db.query(Question).filter(Question.status == "open").all()
    return questions

@router.get("/{question_id}", response_model=QuestionResponse)
def get_question(question_id: UUID, db: Session = Depends(get_db)):
    """Get a specific question"""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    return question

@router.put("/{question_id}", response_model=QuestionResponse)
def update_question(
    question_id: UUID,
    question_data: QuestionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Update a question (admin only)"""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    # Update fields
    if question_data.title:
        question.title = question_data.title
    if question_data.description:
        question.description = question_data.description
    if question_data.status:
        question.status = question_data.status
    
    db.commit()
    db.refresh(question)
    return question

@router.delete("/{question_id}")
def delete_question(
    question_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Delete a question (admin only)"""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    db.delete(question)
    db.commit()
    return {"message": "Question deleted"}
