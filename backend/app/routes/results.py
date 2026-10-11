import requests
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import UUID

from app.database import get_db
from app.models.question import Question
from app.models.vote import Vote
from app.models.admin_recipient import AdminRecipient
from app.models.user import User
from app.schemas import QuestionResults, VoteCount
from app.security import get_current_user

router = APIRouter(prefix="/api/results", tags=["results"])


def build_question_summary(question_id: UUID, db: Session):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    vote_counts = db.query(
        Vote.answer,
        func.count(Vote.id).label("count")
    ).filter(Vote.question_id == question_id).group_by(Vote.answer).all()

    total_votes = sum(count for _, count in vote_counts)
    results = []

    for answer, count in vote_counts:
        percentage = (count / total_votes * 100) if total_votes > 0 else 0
        results.append({
            "answer": answer,
            "count": count,
            "percentage": round(percentage, 2)
        })

    return {
        "question_id": str(question_id),
        "title": question.title,
        "total_votes": total_votes,
        "results": results
    }


@router.get("/{question_id}", response_model=QuestionResults)
def get_question_results(question_id: UUID, db: Session = Depends(get_db)):
    """Get voting results for a question."""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    vote_counts = db.query(
        Vote.answer,
        func.count(Vote.id).label("count")
    ).filter(Vote.question_id == question_id).group_by(Vote.answer).all()

    total_votes = sum(count for _, count in vote_counts)

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


@router.get("/question/{question_id}/recipients")
def get_question_result_recipients(
    question_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Return the result recipient list for a question."""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    if not current_user.is_admin and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Only admins can access this endpoint")

    recipients = db.query(AdminRecipient).filter(
        AdminRecipient.question_id == question_id
    ).all()

    return recipients


@router.post("/question/{question_id}/forward")
def forward_question_results(
    question_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Forward only the aggregate summary to selected admins.
    This keeps customer vote data local and only sends the summary.
    """
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    if not current_user.is_admin and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Only admins can forward results")

    summary = build_question_summary(question_id, db)
    recipients = db.query(AdminRecipient).filter(
        AdminRecipient.question_id == question_id
    ).all()

    forwarded = []

    for recipient in recipients:
        if not recipient.destination_url:
            continue

        payload = {
            "question_id": str(question_id),
            "title": question.title,
            "summary": summary
        }

        try:
            response = requests.post(
                recipient.destination_url,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            forwarded.append({
                "admin_id": str(recipient.admin_id),
                "status": "sent"
            })
        except Exception:
            forwarded.append({
                "admin_id": str(recipient.admin_id),
                "status": "failed"
            })

    return {
        "message": "Result summary forwarded to selected admins",
        "summary": summary,
        "recipients": forwarded
    }
