from backend.database import engine, Base
from backend.models import User, Question, Vote, VoteAuditLog

Base.metadata.create_all(bind=engine)
