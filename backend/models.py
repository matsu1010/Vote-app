from pydantic import BaseModel, Field
from typing import Optional


class UserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=255)
    email_hash: str = Field(..., min_length=3, max_length=255)
    password_hash: str = Field(..., min_length=6, max_length=255)
    role: Optional[str] = "user"


class QuestionCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=500)
    description: Optional[str] = None


class VoteCreate(BaseModel):
    question_id: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1, max_length=255)


class QuestionStatusUpdate(BaseModel):
    status: str


class ResultsVisibilityUpdate(BaseModel):
    visibility: str = Field(..., pattern="^(private|admin_and_executive|public)$")
