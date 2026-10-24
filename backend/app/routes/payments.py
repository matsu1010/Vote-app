from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.models.user import User
from app.models.vote import Vote
from app.models.question import Question
from app.models.votoken import AnonymousWallet
from app.security import get_current_user

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


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout_session(
    payload: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.votoken import VotokenPackage

    package = db.query(VotokenPackage).filter(VotokenPackage.id == payload.package_id).first()
    if package is None:
        raise HTTPException(status_code=404, detail="Package not found")

    session_id = f"demo-checkout-{payload.package_id}"
    return CheckoutResponse(
        session_id=session_id,
        checkout_url=f"https://example.com/checkout/{session_id}",
        status="demo",
        package_id=package.id,
        amount_cents=package.price_cents,
    )


@router.post("/webhook")
def payment_webhook():
    return {"status": "received", "mode": "demo"}
