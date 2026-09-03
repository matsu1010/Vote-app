from sqlalchemy import Column, String, DateTime, UUID, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base

class Vote(Base):
    __tablename__ = "votes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    answer = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # One vote per user per question
    __table_args__ = (UniqueConstraint('user_id', 'question_id', name='uq_user_question_vote'),)
    
    # Relationships
    user = relationship("User", back_populates="votes")
    question = relationship("Question", back_populates="votes")
    audit_logs = relationship("AuditLog", back_populates="vote")
