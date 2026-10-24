import json
import re
import uuid
from datetime import datetime, timedelta

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from uuid import UUID

from app.config import settings
from app.database import get_db
from app.models.votoken import AnonymousWallet, PackagePurchase, VotokenPackage

router = APIRouter(prefix="/api/payments", tags=["payments"])


class CheckoutRequest(BaseModel):
    package_id: UUID
    wallet_alias: str | None = None


class CheckoutResponse(BaseModel):
    session_id: str
    checkout_url: str
    status: str
    package_id: UUID
    amount_cents: int


def _clean_wallet_alias(alias: str | None) -> str:
    base = (alias or "wallet").strip()
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", base.lower()).strip("-")
    if not cleaned:
        cleaned = "wallet"
    return f"{cleaned}-{uuid.uuid4().hex[:8]}"


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout_session(
    payload: CheckoutRequest,
    db: Session = Depends(get_db),
):
    package = db.query(VotokenPackage).filter(VotokenPackage.id == payload.package_id).first()
    if package is None:
        raise HTTPException(status_code=404, detail="Package not found")
    if not package.enabled:
        raise HTTPException(status_code=400, detail="Package is disabled")

    alias_value = payload.wallet_alias or "wallet"
    alias = _clean_wallet_alias(alias_value)

    if not settings.stripe_secret_key:
        return CheckoutResponse(
            session_id=f"demo-checkout-{uuid.uuid4().hex[:12]}",
            checkout_url=f"{settings.frontend_url}/checkout/demo?package_id={package.id}",
            status="demo",
            package_id=package.id,
            amount_cents=package.price_cents,
        )

    stripe.api_key = settings.stripe_secret_key
    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": (package.currency or "USD").lower(),
                "unit_amount": int(package.price_cents),
                "product_data": {
                    "name": package.name,
                },
            },
            "quantity": 1,
        }],
        success_url=f"{settings.frontend_url}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.frontend_url}/checkout/cancel?session_id={{CHECKOUT_SESSION_ID}}",
        metadata={
            "package_id": str(package.id),
            "wallet_alias": alias,
        },
    )

    return CheckoutResponse(
        session_id=session.id,
        checkout_url=session.url,
        status="created",
        package_id=package.id,
        amount_cents=package.price_cents,
    )


@router.post("/webhook")
async def payment_webhook(request: Request, db: Session = Depends(get_db)):
    if not settings.stripe_secret_key:
        return JSONResponse({"status": "demo-received", "mode": "demo"})

    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")
    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing Stripe signature")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.stripe_webhook_secret,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] != "checkout.session.completed":
        return JSONResponse({"status": "ignored", "event_type": event["type"]})

    session = event["data"]["object"]
    metadata = session.get("metadata") or {}
    package_id = metadata.get("package_id")
    wallet_alias = metadata.get("wallet_alias")

    if not package_id:
        raise HTTPException(status_code=400, detail="Missing package_id in checkout metadata")

    package = db.query(VotokenPackage).filter(VotokenPackage.id == package_id).first()
    if package is None:
        raise HTTPException(status_code=404, detail="Package not found during webhook processing")

    final_alias = wallet_alias or f"wallet-{uuid.uuid4().hex[:8]}"
    if db.query(AnonymousWallet).filter(AnonymousWallet.alias == final_alias).first():
        final_alias = f"{final_alias}-{uuid.uuid4().hex[:8]}"

    expires_at = None
    if package.expires_in_days is not None:
        expires_at = datetime.utcnow() + timedelta(days=package.expires_in_days)

    wallet = AnonymousWallet(
        alias=final_alias,
        remaining_votokens=package.vote_count,
        total_purchased=package.vote_count,
        expires_at=expires_at,
        is_active=True,
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

    return JSONResponse({
        "status": "paid",
        "wallet_id": str(wallet.id),
        "wallet_alias": wallet.alias,
        "package_id": str(package.id),
        "votes_granted": package.vote_count,
    })
