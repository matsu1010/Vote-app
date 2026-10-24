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


@router.get("/admin/report")
def get_admin_report(
    question_ids: list[UUID] = Query(...),
    wallet_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_admin and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Only admins can access the full report")

    public_summary = {}
    full_counts = {}
    wallet_records = {}
    wallet_to_chain = defaultdict(list)

    for question_id in question_ids:
        question = db.query(Question).filter(Question.id == question_id).first()
        if question is None:
            continue

        vote_rows = db.query(Vote).filter(Vote.question_id == question_id).all()
        answer_counts = defaultdict(int)
        for vote in vote_rows:
            answer_counts[vote.answer] += 1

        total_votes = sum(answer_counts.values())
        public_summary[str(question_id)] = {
            "question_title": question.title,
            "public_percentage": {
                answer: round((count / total_votes * 100) if total_votes > 0 else 0, 2)
                for answer, count in sorted(answer_counts.items())
            },
            "public_status": question.public_results_enabled,
        }

        full_counts[str(question_id)] = {
            "question_title": question.title,
            "total_votes": total_votes,
            "answers": {answer: count for answer, count in sorted(answer_counts.items())},
        }

        for vote in vote_rows:
            wallet_key = str(vote.voter_id or vote.user_id)
            if wallet_key == "None":
                continue

            wallet_alias = None
            if vote.voter_id is not None:
                wallet = db.query(AnonymousWallet).filter(AnonymousWallet.id == vote.voter_id).first()
                if wallet is not None:
                    wallet_alias = wallet.alias

            wallet_records.setdefault(wallet_key, {
                "wallet_id": wallet_key,
                "wallet_alias": wallet_alias,
                "votes": [],
            })
            wallet_records[wallet_key]["votes"].append({
                "question_id": str(question_id),
                "question_title": question.title,
                "answer": vote.answer,
                "created_at": vote.created_at.isoformat(),
            })
            wallet_to_chain[wallet_key].append(vote.answer)

    chain_counts = defaultdict(int)
    chain_wallets = defaultdict(list)
    for wallet_key, answers in wallet_to_chain.items():
        chain = tuple(answers)
        chain_counts[chain] += 1
        chain_wallets[chain].append(wallet_records.get(wallet_key, {}).get("wallet_alias") or wallet_key)

    chains = [
        {
            "chain": list(chain_key),
            "wallet_count": count,
            "wallet_aliases": sorted(wallets),
        }
        for chain_key, count in sorted(chain_counts.items(), key=lambda item: (-item[1], item[0]))
        for wallets in [chain_wallets[chain_key]]
    ]

    other_chain_count = 0
    if chains:
        top_chain_wallet_count = max(item["wallet_count"] for item in chains)
        other_chain_count = sum(item["wallet_count"] for item in chains if item["wallet_count"] < top_chain_wallet_count)
    if not chains:
        other_chain_count = 0

    wallet_filter = None
    if wallet_id is not None:
        wallet_filter = wallet_records.get(str(wallet_id))

    return {
        "report_id": f"report-{len(question_ids)}-{len(wallet_records)}",
        "generated_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "question_ids": [str(question_id) for question_id in question_ids],
        "public_summary": public_summary,
        "full_counts": full_counts,
        "wallets": sorted(wallet_records.values(), key=lambda item: item["wallet_id"]),
        "chains": chains,
        "other_chain_count": other_chain_count,
        "wallet_lookup": wallet_filter,
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
