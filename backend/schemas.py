from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime

from backend.database import Base, SessionLocal, engine, get_db
from backend.models import User, Question, Vote, VoteAuditLog
from backend.schemas import (
    UserCreate,
    QuestionCreate,
    VoteCreate,
    QuestionStatusUpdate,
    ResultsVisibilityUpdate,
)

app = FastAPI(title="Vote App Local Backend")


@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)


def get_current_user(user_id: str = Header(..., alias="X-User-Id"), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def require_roles(user: User, allowed_roles: list[str]):
    if user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail=f"Role {user.role} is not allowed for this action")


def get_question_or_404(db: Session, question_id: str):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question


@app.get("/")
def root():
    return {
        "message": "Vote App local backend is running",
        "mode": "local-first",
        "database": "SQLite local file",
    }


@app.get("/health")
def health_check():
    return {"status": "ok", "mode": "local-first"}


@app.post("/users")
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    existing_username = db.query(User).filter(User.username == payload.username).first()
    if existing_username:
        raise HTTPException(status_code=409, detail="Username already exists")

    existing_email = db.query(User).filter(User.email_hash == payload.email_hash).first()
    if existing_email:
        raise HTTPException(status_code=409, detail="Email already exists")

    user = User(
        username=payload.username,
        email_hash=payload.email_hash,
        password_hash=payload.password_hash,
        role=payload.role or "user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "created_at": user.created_at,
    }


@app.get("/questions")
def list_questions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == "executive":
        questions = db.query(Question).order_by(Question.created_at.desc()).all()
        return [serialize_question(q) for q in questions]

    if current_user.role == "admin":
        questions = (
            db.query(Question)
            .filter(Question.status == "archived")
            .filter(Question.results_visibility.in_(["admin_and_executive", "public"]))
            .order_by(Question.closed_at.desc())
            .all()
        )
        return [serialize_question(q) for q in questions]

    questions = (
        db.query(Question)
        .filter(Question.status == "open")
        .order_by(Question.created_at.desc())
        .all()
    )
    return [serialize_question(q) for q in questions]


@app.post("/questions")
def create_question(
    payload: QuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_roles(current_user, ["executive"])

    question = Question(
        title=payload.title,
        description=payload.description,
        status="pending_approval",
        created_by=current_user.id,
        results_visibility="private",
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return {
        "id": question.id,
        "title": question.title,
        "status": question.status,
        "created_by": question.created_by,
    }


@app.post("/questions/{question_id}/approve")
def approve_question(
    question_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_roles(current_user, ["executive"])
    question = get_question_or_404(db, question_id)

    if question.status not in ["pending_approval", "rejected"]:
        raise HTTPException(status_code=409, detail="Only pending or rejected questions can be approved")

    question.status = "open"
    question.approved_by = current_user.id
    question.approved_at = datetime.utcnow()
    question.updated_at = datetime.utcnow()

    db.add(question)
    db.commit()
    db.refresh(question)
    return {"id": question.id, "status": question.status, "approved_by": question.approved_by}


@app.post("/questions/{question_id}/reject")
def reject_question(
    question_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_roles(current_user, ["executive"])
    question = get_question_or_404(db, question_id)

    question.status = "rejected"
    question.updated_at = datetime.utcnow()
    db.add(question)
    db.commit()
    return {"id": question.id, "status": question.status, "rejected_by": current_user.id}


@app.post("/questions/{question_id}/close")
def close_question(
    question_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_roles(current_user, ["executive"])
    question = get_question_or_404(db, question_id)

    if question.status != "open":
        raise HTTPException(status_code=409, detail="Only open questions can be archived")

    question.status = "archived"
    question.closed_at = datetime.utcnow()
    question.updated_at = datetime.utcnow()
    db.add(question)
    db.commit()
    db.refresh(question)
    return {"id": question.id, "status": question.status, "closed_at": question.closed_at}


@app.post("/questions/{question_id}/results-visibility")
def set_results_visibility(
    question_id: str,
    payload: ResultsVisibilityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_roles(current_user, ["executive"])
    question = get_question_or_404(db, question_id)

    question.results_visibility = payload.visibility
    question.updated_at = datetime.utcnow()
    db.add(question)
    db.commit()
    db.refresh(question)
    return {"id": question.id, "results_visibility": question.results_visibility}


@app.post("/votes")
def cast_vote(
    payload: VoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    question = get_question_or_404(db, payload.question_id)

    if question.status != "open":
        raise HTTPException(status_code=409, detail="Voting is not open for this question")

    if current_user.role not in ["user", "admin", "executive"]:
        raise HTTPException(status_code=403, detail="User role does not allow voting")

    existing_vote = (
        db.query(Vote)
        .filter(Vote.user_id == current_user.id)
        .filter(Vote.question_id == question.id)
        .first()
    )
    if existing_vote:
        raise HTTPException(status_code=409, detail="This user has already voted on this question")

    vote = Vote(user_id=current_user.id, question_id=question.id, answer=payload.answer)
    db.add(vote)

    audit_log = VoteAuditLog(
        vote_id=vote.id,
        user_id=current_user.id,
        action="created",
        old_value=None,
        new_value=payload.answer,
        reason="Initial vote",
    )
    db.add(audit_log)
    db.commit()
    db.refresh(vote)
    return {"id": vote.id, "question_id": vote.question_id, "answer": vote.answer}


@app.get("/questions/{question_id}/results")
def get_results(
    question_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    question = get_question_or_404(db, question_id)

    if current_user.role == "executive":
        pass
    elif current_user.role == "admin":
        if question.status != "archived" or question.results_visibility not in ["admin_and_executive", "public"]:
            raise HTTPException(status_code=403, detail="Admin does not have permission to view results for this question")
    elif question.results_visibility != "public":
        raise HTTPException(status_code=403, detail="This question's results are not public")

    result_rows = (
        db.query(Vote.answer.label("answer"), func.count(Vote.id).label("count"))
        .filter(Vote.question_id == question_id)
        .group_by(Vote.answer)
        .all()
    )

    total_votes = sum(row.count for row in result_rows)
    results = []
    for row in result_rows:
        results.append(
            {
                "answer": row.answer,
                "count": row.count,
                "percentage": round((row.count / total_votes) * 100, 2) if total_votes else 0,
            }
        )

    return {
        "question_id": question.id,
        "title": question.title,
        "status": question.status,
        "results_visibility": question.results_visibility,
        "results": results,
    }


def serialize_question(question: Question):
    return {
        "id": question.id,
        "title": question.title,
        "description": question.description,
        "status": question.status,
        "results_visibility": question.results_visibility,
        "created_by": question.created_by,
        "approved_by": question.approved_by,
        "created_at": question.created_at,
        "approved_at": question.approved_at,
        "closed_at": question.closed_at,
        "expires_at": question.expires_at,
    }


@app.get("/export")
def export_data(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_roles(current_user, ["executive"])

    users = db.query(User).all()
    questions = db.query(Question).all()
    votes = db.query(Vote).all()
    audit = db.query(VoteAuditLog).all()

    return {
        "users": [
            {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "created_at": user.created_at,
            }
            for user in users
        ],
        "questions": [serialize_question(question) for question in questions],
        "votes": [
            {
                "id": vote.id,
                "user_id": vote.user_id,
                "question_id": vote.question_id,
                "answer": vote.answer,
                "created_at": vote.created_at,
            }
            for vote in votes
        ],
        "audit_logs": [
            {
                "id": log.id,
                "vote_id": log.vote_id,
                "user_id": log.user_id,
                "action": log.action,
                "old_value": log.old_value,
                "new_value": log.new_value,
                "reason": log.reason,
                "created_at": log.created_at,
            }
            for log in audit
        ],
    }


# Local-first app note: the data is stored in SQLite and can be copied or exported by an admin/executive.
