from sqlalchemy import Column, String, DateTime, UUID, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base

class AdminActionLog(Base):
    __tablename__ = "admin_action_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admin_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    action_type = Column(String(50), nullable=False)  # create_question, close_question, promote_admin, etc.
    action_details = Column(Text, nullable=True)  # JSON string with details
    target_resource_id = Column(UUID(as_uuid=True), nullable=True)  # ID of affected resource
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    admin_user = relationship("User", back_populates="admin_actions")
