from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.question import Question
from app.schemas import QuestionCreate, QuestionResponse

router = APIRouter(prefix="/api/questions", tags=["questions"])


@router.post("", response_model=QuestionResponse)
def create_question(question: QuestionCreate, db: Session = Depends(get_db)):
    new_question = Question(
        title=question.title,
        description=question.description,
        require_email_verification=question.require_email_verification,
        allow_anonymous=question.allow_anonymous,
        enable_data_retention=question.enable_data_retention,
    )
    db.add(new_question)
    db.commit()
    db.refresh(new_question)
    return new_question
