from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.question import Question
from app.models.vote import Vote
from app.security import get_current_user, get_current_voter
from app.schemas import VoteCreate, VoteResponse

router = APIRouter(prefix="/api/votes", tags=["votes"])


@router.post("/{question_id}", response_model=VoteResponse)
def submit_vote(
    question_id: UUID,
    vote: VoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_voter: dict = Depends(get_current_voter),
):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    if question.status == "closed":
        raise HTTPException(status_code=400, detail="Question is closed")

    # Only allow current_user OR voter token; current_user is always present for authenticated users,
    # while current_voter route is used for public voting sessions.
    voter_id = None
    if current_user is not None and str(current_user.id) != "":
        voter_id = None

    if current_voter is not None:
        voter_id = UUID(str(current_voter.get("sub")))

    if voter_id is not None:
        existing_vote = db.query(Vote).filter(
            Vote.voter_id == voter_id,
            Vote.question_id == question_id,
        ).first()

        if existing_vote:
            existing_vote.answer = vote.answer
            existing_vote.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing_vote)
            return existing_vote

        new_vote = Vote(
            voter_id=voter_id,
            question_id=question_id,
            answer=vote.answer,
        )
        db.add(new_vote)
        db.commit()
        db.refresh(new_vote)
        return new_vote

    existing_vote = db.query(Vote).filter(
        Vote.user_id == current_user.id,
        Vote.question_id == question_id,
    ).first()

    if existing_vote:
        existing_vote.answer = vote.answer
        existing_vote.updated_at = datetime.utcnow()
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
