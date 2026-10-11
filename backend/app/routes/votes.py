from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.models.vote import Vote
from app.models.question import Question
from app.models.user import User
from app.schemas import VoteCreate, VoteResponse
from app.security import get_current_user

router = APIRouter(prefix="/api/votes", tags=["votes"])


@router.post("/{question_id}", response_model=VoteResponse)
def submit_vote(
    question_id: UUID,
    vote: VoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    if question.status == "closed":
        raise HTTPException(status_code=400, detail="Question is closed")

    existing_vote = db.query(Vote).filter(
        Vote.user_id == current_user.id,
        Vote.question_id == question_id
    ).first()

    if existing_vote:
        existing_vote.answer = vote.answer
        db.commit()
        db.refresh(existing_vote)
        return existing_vote

    new_vote = Vote(
        user_id=current_user.id,
        question_id=question_id,
        answer=vote.answer,
    )
    db.add(new_vote)
    db.commit()
    db.refresh(new_vote)
    return new_vote
