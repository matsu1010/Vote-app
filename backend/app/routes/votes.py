from fastapi import APIRouter, Depends, HTTPException, Request
from uuid import UUID
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.question import Question
from app.models.vote import Vote
from app.models.votoken import AnonymousWallet
from app.security import decode_token
from app.schemas import VoteCreate, VoteResponse

router = APIRouter(prefix="/api/votes", tags=["votes"])


def _get_auth_payload(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        return None
    token = auth_header.split(" ", 1)[1].strip()
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return payload


@router.post("/{question_id}", response_model=VoteResponse)
def submit_vote(
    question_id: UUID,
    vote: VoteCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    if question.status == "closed":
        raise HTTPException(status_code=400, detail="Question is closed")

    payload = _get_auth_payload(request)
    if payload is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    if payload.get("scope") == "voter":
        wallet_id = UUID(str(payload.get("sub")))
        wallet = db.query(AnonymousWallet).filter(AnonymousWallet.id == wallet_id).first()
        if wallet is None:
            raise HTTPException(status_code=401, detail="Wallet not found")
        if not wallet.is_active:
            raise HTTPException(status_code=403, detail="Wallet is disabled")
        if wallet.expires_at is not None and wallet.expires_at < datetime.utcnow():
            raise HTTPException(status_code=403, detail="Wallet has expired")
        if wallet.remaining_votokens <= 0:
            raise HTTPException(status_code=403, detail="No Votokens remaining in this wallet")

        existing_vote = db.query(Vote).filter(
            Vote.voter_id == wallet_id,
            Vote.question_id == question_id,
        ).first()

        if existing_vote:
            existing_vote.answer = vote.answer
            existing_vote.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing_vote)
            return existing_vote

        wallet.remaining_votokens -= 1
        new_vote = Vote(
            voter_id=wallet_id,
            question_id=question_id,
            answer=vote.answer,
        )
        db.add(new_vote)
        db.add(wallet)
        db.commit()
        db.refresh(new_vote)
        return new_vote

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

    current_user = db.query(User).filter(User.id == user_id).first()
    if current_user is None:
        raise HTTPException(status_code=401, detail="User not found")

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
