# Initialize database tables on app startup
from backend.database import engine, Base
from backend.models import User, Question, Vote, VoteAuditLog

# Create all tables if they don't exist
Base.metadata.create_all(bind=engine)
