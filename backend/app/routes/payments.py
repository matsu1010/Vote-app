from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from uuid import UUID
import stripe
import hmac
import hashlib
from datetime import datetime

from app.database import get_db
from app.models.invite_code import InviteCode, InviteCodeBatch, Payment
from app.schemas import CheckoutSessionRequest, CheckoutSessionResponse
from app.config import settings
from app.security import get_admin_user

router = APIRouter(prefix="/api/payments", tags=["payments"])

stripe.api_key = settings.stripe_secret_key


@router.post("/create-checkout", response_model=CheckoutSessionResponse)
def create_checkout_session(
    body: CheckoutSessionRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_admin_user),
):
    batch = db.query(InviteCodeBatch).filter(InviteCodeBatch.id == body.batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    # Price is stored in cents on the batch
    price = batch.price_cents or 0
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {'name': f'Invite codes for batch {str(batch.id)}'},
                'unit_amount': price,
            },
            'quantity': body.quantity,
        }],
        mode='payment',
        success_url=body.success_url or 'https://example.com/success',
        cancel_url=body.cancel_url or 'https://example.com/cancel',
    )

    payment = Payment(
        batch_id=batch.id,
        stripe_session_id=session.id,
        amount_cents=price * body.quantity,
        status=session.status,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    return {"session_id": session.id, "checkout_url": session.url}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    secret = settings.stripe_webhook_secret

    if not secret:
        raise HTTPException(status_code=500, detail="Stripe webhook secret not configured")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, secret)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook signature verification failed: {str(e)}")

    # Handle checkout.session.completed
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        try:
            # Find Payment record by stripe_session_id
            payment = db.query(Payment).filter(Payment.stripe_session_id == session['id']).first()
            if payment:
                payment.status = 'completed'
                db.add(payment)

                # Mark as sold: allocate first `quantity` unsold codes in the batch
                batch = db.query(InviteCodeBatch).filter(InviteCodeBatch.id == payment.batch_id).first()
                if batch:
                    unsold = db.query(InviteCode).filter(InviteCode.batch_id == batch.id, InviteCode.sold == False).limit(session.get('metadata', {}).get('quantity', 1)).all()
                    count = 0
                    for code in unsold:
                        code.sold = True
                        code.sold_session_id = session['id']
                        code.sold_at = datetime.utcnow()
                        db.add(code)
                        count += 1
                    payment.amount_cents = int(session.get('amount_total', payment.amount_cents))
                    db.add(payment)

                db.commit()
        except Exception:
            db.rollback()
    return {"status": "ok"}
