import requests
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import UUID

from app.database import get_db
from app.models.question import Question
from app.models.vote import Vote
from app.models.admin_recipient import AdminRecipient
from app.models.user import User
from app.models.votoken import AnonymousWallet
from app.schemas import QuestionResults, VoteCount, VoteChoiceDetail, PublicQuestionResults, PublicVoteCount
from app.security import get_current_user

router = APIRouter(prefix="/api/results", tags=["results"])


def build_question_summary(question_id: UUID, db: Session):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    if not question.public_results_enabled:
        raise HTTPException(status_code=403, detail="Public results are disabled for this question")

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


@router.get("/{question_id}", response_model=PublicQuestionResults)
def get_question_results(question_id: UUID, db: Session = Depends(get_db)):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    if not question.public_results_enabled:
        raise HTTPException(status_code=403, detail="Public results are disabled for this question")

    vote_counts = db.query(
        Vote.answer,
        func.count(Vote.id).label("count")
    ).filter(Vote.question_id == question_id).group_by(Vote.answer).all()

    total_votes = sum(count for _, count in vote_counts)
    results = []

    for answer, count in vote_counts:
        percentage = (count / total_votes * 100) if total_votes > 0 else 0
        results.append(PublicVoteCount(
            answer=answer,
            percentage=round(percentage, 2)
        ))

    return PublicQuestionResults(
        question_id=question_id,
        title=question.title,
        results=results
    )


@router.get("/{question_id}/details", response_model=list[VoteChoiceDetail])
def get_question_vote_details(
    question_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    if not current_user.is_admin and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Only admins can access individual vote details")

    rows = db.query(Vote).filter(Vote.question_id == question_id).order_by(Vote.created_at.asc()).all()
    details = []

    for row in rows:
        wallet_alias = None
        if row.voter_id is not None:
            wallet = db.query(AnonymousWallet).filter(AnonymousWallet.id == row.voter_id).first()
            if wallet is not None:
                wallet_alias = wallet.alias

        details.append(VoteChoiceDetail(
            vote_id=row.id,
            question_id=row.question_id,
            answer=row.answer,
            wallet_id=row.voter_id,
            wallet_alias=wallet_alias,
            user_id=row.user_id,
            created_at=row.created_at,
        ))

    return details


@router.get("/admin/chains")
def get_admin_vote_chains(
    question_ids: list[UUID] = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_admin and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Only admins can access vote-chain data")

    ordered_question_ids = sorted(question_ids, key=lambda qid: str(qid))
    per_question_counts = {}
    wallet_to_chain = defaultdict(list)
    wallet_aliases = {}

    for question_id in ordered_question_ids:
        question = db.query(Question).filter(Question.id == question_id).first()
        if question is None:
            continue

        vote_rows = db.query(Vote).filter(Vote.question_id == question_id).all()
        by_answer = defaultdict(int)
        for vote in vote_rows:
            by_answer[vote.answer] += 1
        per_question_counts[str(question_id)] = dict(sorted(by_answer.items()))

        for vote in vote_rows:
            wallet_id = vote.voter_id or vote.user_id
            if wallet_id is None:
                continue
            wallet_to_chain[str(wallet_id)].append(vote.answer)
            if str(wallet_id) not in wallet_aliases:
                wallet = db.query(AnonymousWallet).filter(AnonymousWallet.id == wallet_id).first()
                wallet_aliases[str(wallet_id)] = wallet.alias if wallet else str(wallet_id)

    chain_counts = defaultdict(int)
    chain_wallets = defaultdict(list)
    for wallet_id, answers in wallet_to_chain.items():
        chain_key = tuple(answers)
        chain_counts[chain_key] += 1
        chain_wallets[chain_key].append(wallet_aliases.get(wallet_id, wallet_id))

    chains = [
        {
            "chain": list(chain_key),
            "wallet_count": count,
            "wallet_aliases": sorted(wallets),
        }
        for chain_key, count in sorted(chain_counts.items(), key=lambda item: (-item[1], item[0]))
        for wallets in [chain_wallets[chain_key]]
    ]

    return {
        "question_ids": [str(qid) for qid in ordered_question_ids],
        "per_question_counts": per_question_counts,
        "chains": chains,
        "other_chain_count": 0,
    }


@router.get("/question/{question_id}/recipients")
def get_question_result_recipients(
    question_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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
