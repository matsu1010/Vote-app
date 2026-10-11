from sqlalchemy import Column, String, DateTime, Boolean, UUID, Text
from datetime import datetime
import uuid
from app.database import Base

class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="active")  # active, closed, archived
    
    # Session-wide settings
    require_email_verification = Column(Boolean, default=False)
    allow_anonymous = Column(Boolean, default=False)
    enable_data_retention = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
