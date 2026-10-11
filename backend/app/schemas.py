from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

# User Schemas
class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(UserBase):
    id: UUID
    is_admin: bool
    is_super_admin: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# Question Schemas
class QuestionBase(BaseModel):
    title: str
    description: Optional[str] = None
    require_email_verification: bool = False
    allow_anonymous: bool = False
    enable_data_retention: bool = True

class QuestionCreate(QuestionBase):
    pass

class QuestionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    require_email_verification: Optional[bool] = None
    allow_anonymous: Optional[bool] = None
    enable_data_retention: Optional[bool] = None

class QuestionResponse(QuestionBase):
    id: UUID
    status: str
    created_at: datetime
    closed_at: Optional[datetime]
    
    class Config:
        from_attributes = True

# Vote Schemas
class VoteCreate(BaseModel):
    answer: str

class VoteUpdate(BaseModel):
    answer: str

class VoteResponse(BaseModel):
    id: UUID
    user_id: UUID
    question_id: UUID
    answer: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# Results Schema
class VoteCount(BaseModel):
    answer: str
    count: int
    percentage: float

class QuestionResults(BaseModel):
    question_id: UUID
    title: str
    total_votes: int
    results: list[VoteCount]
