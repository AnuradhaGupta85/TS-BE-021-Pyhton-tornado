# Pydantic request and response validation schemas.
from datetime import date as Date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from models import TransactionType


class RegisterSchema(BaseModel):
    email: EmailStr
    name: str = Field(default='', max_length=100)
    password: str = Field(min_length=8, max_length=128)


class ProfileUpdateSchema(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None


class ChangePasswordSchema(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class ForgotPasswordSchema(BaseModel):
    email: EmailStr


class ResetPasswordSchema(BaseModel):
    token: str = Field(min_length=1, max_length=512)
    new_password: str = Field(min_length=8, max_length=128)


class LoginSchema(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class CategoryCreateSchema(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class TransactionCreateSchema(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    type: TransactionType
    category_id: int = Field(gt=0)
    date: Date
    description: str | None = Field(default=None, max_length=5000)
    tag_ids: list[int] = Field(default_factory=list)


class TransactionUpdateSchema(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    type: TransactionType | None = None
    category_id: int | None = Field(default=None, gt=0)
    date: Date | None = None
    description: str | None = Field(default=None, max_length=5000)
    tag_ids: list[int] | None = None


class TagCreateSchema(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    name: str
    created_at: datetime


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    is_predefined: bool
    owner_id: int | None


class TransactionResponse(BaseModel):
    id: int
    amount: Decimal
    type: TransactionType
    category_id: int
    category_name: str
    date: Date
    description: str | None
    user_id: int
    tags: list[dict] = Field(default_factory=list)
    attachments: list[dict] = Field(default_factory=list)


class SummarySchema(BaseModel):
    total_income: Decimal
    total_expenses: Decimal
    balance: Decimal
    expenses_by_category: list[dict]
