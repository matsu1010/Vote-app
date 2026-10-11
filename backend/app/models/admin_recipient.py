from sqlalchemy import Column, String, DateTime, UUID, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base

class AdminRecipient(Base):
    __tablename__ = "admin_recipients"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id"), nullable=False)
    admin_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    question = relationship("Question", back_populates="admin_recipients")
    admin = relationship("User", back_populates="result_access")
    
    __table_args__ = (
        # Unique constraint: each admin can only be listed once per question
        __import__('sqlalchemy').UniqueConstraint('question_id', 'admin_id', name='uq_question_admin'),
    )
