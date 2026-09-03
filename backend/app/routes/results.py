from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import UUID
from app.database import get_db
from app.models.question import Question
from app.models.vote import Vote
from app.schemas import QuestionResults, VoteCount

router = APIRouter(prefix="/api/results", tags=["results"])

@router.get("/{question_id}", response_model=QuestionResults)
def get_question_results(question_id: UUID, db: Session = Depends(get_db)):
    """Get voting results for a question"""
    # Check question exists
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    # Count votes by answer
    vote_counts = db.query(
        Vote.answer,
        func.count(Vote.id).label("count")
    ).filter(Vote.question_id == question_id).group_by(Vote.answer).all()
    
    total_votes = sum(count for _, count in vote_counts)
    
    # Calculate percentages
    results = []
    for answer, count in vote_counts:
        percentage = (count / total_votes * 100) if total_votes > 0 else 0
        results.append(VoteCount(
            answer=answer,
            count=count,
            percentage=round(percentage, 2)
        ))
    
    return QuestionResults(
        question_id=question_id,
        title=question.title,
        total_votes=total_votes,
        results=results
    )

@router.get("")
def get_all_results(db: Session = Depends(get_db)):
    """Get results for all questions"""
    questions = db.query(Question).all()
    results = []
    
    for question in questions:
        vote_counts = db.query(
            Vote.answer,
            func.count(Vote.id).label("count")
        ).filter(Vote.question_id == question.id).group_by(Vote.answer).all()
        
        total_votes = sum(count for _, count in vote_counts)
        
        vote_results = []
        for answer, count in vote_counts:
            percentage = (count / total_votes * 100) if total_votes > 0 else 0
            vote_results.append(VoteCount(
                answer=answer,
                count=count,
                percentage=round(percentage, 2)
            ))
        
        results.append(QuestionResults(
            question_id=question.id,
            title=question.title,
            total_votes=total_votes,
            results=vote_results
        ))
    
    return results
