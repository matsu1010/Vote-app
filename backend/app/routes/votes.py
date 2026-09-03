from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from app.database import get_db
from app.models.user import User
from app.models.vote import Vote
from app.models.question import Question
from app.schemas import VoteCreate, VoteUpdate, VoteResponse
from app.security import get_current_user

router = APIRouter(prefix="/api/votes", tags=["votes"])

@router.post("/{question_id}", response_model=VoteResponse)
def submit_vote(
    question_id: UUID,
    vote_data: VoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit or update a vote for a question"""
    # Check question exists and is open
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    if question.status != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question is closed"
        )
    
    # Check if vote already exists
    existing_vote = db.query(Vote).filter(
        Vote.user_id == current_user.id,
        Vote.question_id == question_id
    ).first()
    
    if existing_vote:
        # Update existing vote
        existing_vote.answer = vote_data.answer
        db.commit()
        db.refresh(existing_vote)
        return existing_vote
    
    # Create new vote
    new_vote = Vote(
        user_id=current_user.id,
        question_id=question_id,
        answer=vote_data.answer
    )
    db.add(new_vote)
    db.commit()
    db.refresh(new_vote)
    return new_vote

@router.get("/{question_id}/my-vote", response_model=VoteResponse)
def get_my_vote(
    question_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's vote for a question"""
    vote = db.query(Vote).filter(
        Vote.user_id == current_user.id,
        Vote.question_id == question_id
    ).first()
    
    if not vote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No vote found for this question"
        )
    
    return vote

@router.delete("/{vote_id}")
def delete_vote(
    vote_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete own vote"""
    vote = db.query(Vote).filter(Vote.id == vote_id).first()
    
    if not vote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vote not found"
        )
    
    if vote.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete other user's vote"
        )
    
    db.delete(vote)
    db.commit()
    return {"message": "Vote deleted"}
