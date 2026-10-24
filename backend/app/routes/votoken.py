from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from uuid import UUID
import uuid

from app.database import get_db
from app.models.user import User
from app.models.votoken import AnonymousWallet, PackagePurchase, VotokenPackage
from app.schemas import (
    VotokenPackageCreate,
    VotokenPackageResponse,
    VotokenPurchaseRequest,
    VotokenPurchaseResponse,
)
from app.security import create_voter_token, get_admin_user

router = APIRouter(prefix="/api/votoken", tags=["votoken"])


@router.get("/packages", response_model=list[VotokenPackageResponse])
def list_votoken_packages(db: Session = Depends(get_db)):
    packages = (
        db.query(VotokenPackage)
        .filter(VotokenPackage.enabled.is_(True))
        .order_by(VotokenPackage.vote_count.asc())
        .all()
    )
    return packages


@router.post("/packages", response_model=VotokenPackageResponse)
def create_votoken_package(
    payload: VotokenPackageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    if payload.vote_count <= 0:
        raise HTTPException(status_code=400, detail="vote_count must be greater than zero")
    if payload.price_cents < 0:
        raise HTTPException(status_code=400, detail="price_cents must be zero or greater")

    package = VotokenPackage(
        name=payload.name,
        vote_count=payload.vote_count,
        price_cents=payload.price_cents,
        currency=payload.currency,
        enabled=payload.enabled,
        expires_in_days=payload.expires_in_days,
    )
    db.add(package)
    db.commit()
    db.refresh(package)
    return package


@router.post("/purchase", response_model=VotokenPurchaseResponse)
def purchase_votoken_package(
    payload: VotokenPurchaseRequest,
    db: Session = Depends(get_db),
):
    package = (
        db.query(VotokenPackage)
        .filter(VotokenPackage.id == payload.package_id, VotokenPackage.enabled.is_(True))
        .first()
    )
    if package is None:
        raise HTTPException(status_code=404, detail="Votoken package not found or disabled")

    expires_at = None
    if package.expires_in_days is not None:
        expires_at = datetime.utcnow() + timedelta(days=package.expires_in_days)

    wallet = AnonymousWallet(
        alias=f"wallet-{uuid.uuid4().hex[:10]}",
        remaining_votokens=package.vote_count,
        total_purchased=package.vote_count,
        expires_at=expires_at,
    )

    purchase = PackagePurchase(
        wallet=wallet,
        package=package,
        status="paid",
        amount_cents=package.price_cents,
        currency=package.currency,
        expires_at=expires_at,
    )

    db.add(wallet)
    db.add(purchase)
    db.commit()
    db.refresh(wallet)
    db.refresh(purchase)

    expires_delta = timedelta(days=package.expires_in_days) if package.expires_in_days is not None else None
    wallet_token = create_voter_token(str(wallet.id), expires_delta=expires_delta)

    return VotokenPurchaseResponse(
        wallet_id=wallet.id,
        alias=wallet.alias,
        package_id=package.id,
        package_name=package.name,
        vote_count=package.vote_count,
        remaining_votokens=wallet.remaining_votokens,
        expires_at=wallet.expires_at,
        token=wallet_token,
    )


@router.get("/wallets/{wallet_id}", response_model=dict)
def get_wallet_balance(wallet_id: UUID, db: Session = Depends(get_db)):
    wallet = db.query(AnonymousWallet).filter(AnonymousWallet.id == wallet_id).first()
    if wallet is None:
        raise HTTPException(status_code=404, detail="Wallet not found")

    return {
        "wallet_id": str(wallet.id),
        "alias": wallet.alias,
        "remaining_votokens": wallet.remaining_votokens,
        "total_purchased": wallet.total_purchased,
        "expires_at": wallet.expires_at,
        "is_active": wallet.is_active,
    }
