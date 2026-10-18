from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime, timedelta
import hashlib
import uuid

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.database import get_db
from app.models.invite_code import InviteCode, InviteCodeBatch
from app.models.user import User
from app.schemas import InviteCodeBatchCreate, RedeemCodeRequest, RedeemCodeResponse
from app.security import create_voter_token, get_admin_user
from app.config import settings

router = APIRouter(prefix="/api/codes", tags=["codes"])

# Use configured Argon2 parameters
ph = PasswordHasher(time_cost=settings.invite_code_argon2_time_cost,
                    memory_cost=settings.invite_code_argon2_memory_kb,
                    parallelism=settings.invite_code_argon2_parallelism)


def fingerprint_of(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()[:24]


@router.post("/batch", response_model=dict)
def create_code_batch(
    body: InviteCodeBatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    if body.count <= 0:
        raise HTTPException(status_code=400, detail="count must be greater than 0")

    batch = InviteCodeBatch(
        question_id=body.question_id,
        name=body.name,
        price_cents=body.price_cents,
        created_by=current_user.id,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    codes = []
    for _ in range(body.count):
        code = str(uuid.uuid4())
        code_hash = ph.hash(code)
        record = InviteCode(
            batch_id=batch.id,
            code_hash=code_hash,
            fingerprint=fingerprint_of(code),
            sold=(body.price_cents is not None and body.price_cents == 0),
            sold_session_id=("free" if (body.price_cents is not None and body.price_cents == 0) else None),
            sold_at=(datetime.utcnow() if (body.price_cents is not None and body.price_cents == 0) else None),
        )
        db.add(record)
        codes.append(code)

    db.commit()

    return {
        "batch_id": str(batch.id),
        "question_id": str(batch.question_id) if batch.question_id else None,
        "price_cents": batch.price_cents,
        "codes": codes,
    }


@router.post("/redeem", response_model=RedeemCodeResponse)
def redeem_code(
    payload: RedeemCodeRequest,
    db: Session = Depends(get_db),
):
    fp = fingerprint_of(payload.code)
    candidates = db.query(InviteCode).filter(InviteCode.fingerprint == fp, InviteCode.redeemed == False).all()
    if not candidates:
        raise HTTPException(status_code=404, detail="Invalid code")

    matched = None
    for candidate in candidates:
        try:
            ph.verify(candidate.code_hash, payload.code)
            matched = candidate
            break
        except VerifyMismatchError:
            continue

    if matched is None:
        raise HTTPException(status_code=404, detail="Invalid code")

    batch = db.query(InviteCodeBatch).filter(InviteCodeBatch.id == matched.batch_id).first()
    if batch is None:
        raise HTTPException(status_code=404, detail="Code batch not found")

    # If batch has a positive price and code not marked sold, require purchase
    if batch.price_cents is not None and batch.price_cents > 0 and not matched.sold:
        raise HTTPException(status_code=402, detail="Code not sold yet")

    # Mark redeemed
    matched.redeemed = True
    matched.redeemed_at = datetime.utcnow()
    db.add(matched)
    db.commit()

    # Issue ephemeral voter token
    voter_uuid = str(uuid.uuid4())
    expires = datetime.utcnow() + timedelta(hours=int(settings.voter_token_expire_hours))
    token = create_voter_token(voter_uuid, batch_id=str(batch.id), expires_delta=timedelta(hours=int(settings.voter_token_expire_hours)))

    return {
        "voter_token": token,
        "expires_at": expires,
    }


@router.post("/mark-sold")
def mark_codes_sold(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    codes = payload.get("codes") or []
    if not codes:
        raise HTTPException(status_code=400, detail="codes are required")

    marked = 0
    for raw_code in codes:
        normalized = str(raw_code).strip()
        fp = fingerprint_of(normalized)
        record = db.query(InviteCode).filter(InviteCode.fingerprint == fp).first()
        if not record:
            continue
        record.sold = True
        record.sold_session_id = payload.get("note") or "manual-sale"
        record.sold_at = datetime.utcnow()
        db.add(record)
        marked += 1

    db.commit()
    return {"message": "Codes marked as sold", "count": marked}
