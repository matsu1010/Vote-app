from sqlalchemy import Column, String, Text, DateTime, Boolean, UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base

class Question(Base):
    __tablename__ = "questions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="open")  # open, closed
    
    # Session Settings (toggleable)
    require_email_verification = Column(Boolean, default=False)
    allow_anonymous = Column(Boolean, default=False)
    enable_data_retention = Column(Boolean, default=True)
    
    # Close options
    close_type = Column(String(50))  # manual, scheduled, vote_threshold
    scheduled_close_time = Column(DateTime, nullable=True)
    vote_threshold = Column(String(255), nullable=True)  # JSON string with threshold config
    
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    votes = relationship("Vote", back_populates="question", cascade="all, delete-orphan")
