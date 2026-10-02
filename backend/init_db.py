from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(255), unique=True, nullable=False)
    email_hash = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="user")  # user, admin, executive
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    votes = relationship("Vote", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("VoteAuditLog", back_populates="user", cascade="all, delete-orphan")
    created_questions = relationship("Question", back_populates="created_by_user", foreign_keys="Question.created_by")
    approved_questions = relationship("Question", back_populates="approved_by_user", foreign_keys="Question.approved_by")


class Question(Base):
    __tablename__ = "questions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(500), nullable=False)
    description = Column(String(2000), nullable=True)
    status = Column(String(20), default="pending_approval")  # pending_approval, open, archived, rejected
    results_visibility = Column(String(20), default="private")  # private, admin_and_executive, public
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    approved_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    votes = relationship("Vote", back_populates="question", cascade="all, delete-orphan")
    created_by_user = relationship("User", back_populates="created_questions", foreign_keys=[created_by])
    approved_by_user = relationship("User", back_populates="approved_questions", foreign_keys=[approved_by])


class Vote(Base):
    __tablename__ = "votes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(String(36), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    answer = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="votes")
    question = relationship("Question", back_populates="votes")
    audit_logs = relationship("VoteAuditLog", back_populates="vote", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_user_id", "user_id"),
        Index("idx_question_id", "question_id"),
        Index("idx_created_at", "created_at"),
        Index("idx_votes_user_created", "user_id", "created_at"),
        Index("idx_votes_question_created", "question_id", "created_at"),
    )


class VoteAuditLog(Base):
    __tablename__ = "vote_audit_log"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    vote_id = Column(String(36), ForeignKey("votes.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    action = Column(String(50), nullable=False)
    old_value = Column(String(255), nullable=True)
    new_value = Column(String(255), nullable=True)
    reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    vote = relationship("Vote", back_populates="audit_logs")
    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("idx_user_id", "user_id"),
        Index("idx_vote_id", "vote_id"),
        Index("idx_created_at", "created_at"),
        Index("idx_audit_user_created", "user_id", "created_at"),
    )
