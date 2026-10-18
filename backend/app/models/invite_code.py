from sqlalchemy import Column, String, Text, DateTime, Boolean, UUID, ForeignKey, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class InviteCodeBatch(Base):
    __tablename__ = "invite_code_batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id", ondelete="SET NULL"), nullable=True)
    name = Column(Text, nullable=True)
    price_cents = Column(Integer, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    question = relationship("Question", back_populates="invite_code_batches")
    created_by_user = relationship("User", back_populates="created_code_batches")
    codes = relationship("InviteCode", back_populates="batch", cascade="all, delete-orphan")


class InviteCode(Base):
    __tablename__ = "invite_codes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("invite_code_batches.id", ondelete="CASCADE"), nullable=False)
    code_hash = Column(Text, nullable=False)
    fingerprint = Column(String(64), nullable=False, index=True)
    redeemed = Column(Boolean, default=False, nullable=False)
    redeemed_at = Column(DateTime, nullable=True)
    sold = Column(Boolean, default=False, nullable=False)
    sold_session_id = Column(Text, nullable=True)
    sold_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    batch = relationship("InviteCodeBatch", back_populates="codes")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("invite_code_batches.id", ondelete="SET NULL"), nullable=True)
    stripe_session_id = Column(Text, nullable=True)
    amount_cents = Column(Integer, nullable=True)
    status = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

