from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID


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


class QuestionBase(BaseModel):
    title: str
    description: Optional[str] = None
    free_access: bool = False
    require_email_verification: bool = False
    allow_anonymous: bool = False
    enable_data_retention: bool = True


class QuestionCreate(QuestionBase):
    pass


class QuestionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    free_access: Optional[bool] = None
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


class VoteCreate(BaseModel):
    answer: str


class VoteUpdate(BaseModel):
    answer: str


class VoteResponse(BaseModel):
    id: UUID
    user_id: Optional[UUID] = None
    voter_id: Optional[UUID] = None
    question_id: UUID
    answer: str
    created_at: datetime

    class Config:
        from_attributes = True


class AdminRecipientCreate(BaseModel):
    admin_id: UUID
    delivery_mode: str = "summary"
    destination_url: Optional[str] = None


class AdminRecipientResponse(BaseModel):
    id: UUID
    question_id: UUID
    admin_id: UUID
    delivery_mode: str
    destination_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class VoteCount(BaseModel):
    answer: str
    count: int
    percentage: float


class QuestionResults(BaseModel):
    question_id: UUID
    title: str
    total_votes: int
    results: list[VoteCount]


class InviteCodeBatchCreate(BaseModel):
    question_id: Optional[UUID] = None
    count: int = 1
    price_cents: Optional[int] = None
    name: Optional[str] = None


class InviteCodeBatchResponse(BaseModel):
    id: UUID
    question_id: Optional[UUID]
    name: Optional[str]
    price_cents: Optional[int]
    created_by: Optional[UUID]
    created_at: datetime
    codes: List[str]

    class Config:
        from_attributes = True


class RedeemCodeRequest(BaseModel):
    code: str


class RedeemCodeResponse(BaseModel):
    voter_token: str
    expires_at: datetime


class ManualCodeSaleRequest(BaseModel):
    codes: List[str]
    note: Optional[str] = None


class CheckoutSessionRequest(BaseModel):
    batch_id: UUID
    quantity: int = 1
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class CheckoutSessionResponse(BaseModel):
    session_id: str
    checkout_url: str
