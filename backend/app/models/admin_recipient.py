from sqlalchemy import Column, String, DateTime, UUID, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class AdminRecipient(Base):
    __tablename__ = "admin_recipients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    admin_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    delivery_mode = Column(String(50), default="summary", nullable=False)
    destination_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    question = relationship("Question", back_populates="admin_recipients")
    admin = relationship("User", back_populates="result_access")

    __table_args__ = (
        UniqueConstraint("question_id", "admin_id", name="uq_question_admin_recipient"),
    )
