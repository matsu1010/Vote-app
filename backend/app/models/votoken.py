from sqlalchemy import Column, String, Integer, Boolean, DateTime, UUID, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class VotokenPackage(Base):
    __tablename__ = "votoken_packages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    vote_count = Column(Integer, nullable=False, default=1)
    price_cents = Column(Integer, nullable=False, default=0)
    currency = Column(String(8), nullable=False, default="USD")
    enabled = Column(Boolean, nullable=False, default=True)
    expires_in_days = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    purchases = relationship("PackagePurchase", back_populates="package", cascade="all, delete-orphan")


class AnonymousWallet(Base):
    __tablename__ = "anonymous_wallets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alias = Column(String(64), unique=True, nullable=False, index=True)
    remaining_votokens = Column(Integer, nullable=False, default=0)
    total_purchased = Column(Integer, nullable=False, default=0)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    purchases = relationship("PackagePurchase", back_populates="wallet", cascade="all, delete-orphan")


class PackagePurchase(Base):
    __tablename__ = "package_purchases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey("anonymous_wallets.id", ondelete="CASCADE"), nullable=False, index=True)
    package_id = Column(UUID(as_uuid=True), ForeignKey("votoken_packages.id", ondelete="SET NULL"), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="paid")
    amount_cents = Column(Integer, nullable=False, default=0)
    currency = Column(String(8), nullable=False, default="USD")
    purchased_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    wallet = relationship("AnonymousWallet", back_populates="purchases")
    package = relationship("VotokenPackage", back_populates="purchases")
