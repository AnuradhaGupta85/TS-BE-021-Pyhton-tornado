# SQLAlchemy ORM models for expense tracker data.
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import Boolean, Column, Date, DateTime, Enum as SqlEnum, ForeignKey, Numeric, String, Table, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class TransactionType(str, Enum):
    """Supported financial transaction directions."""

    INCOME = 'Income'
    EXPENSE = 'Expense'


class User(Base):
    """An authenticated application user."""

    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False, server_default='')
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    transactions: Mapped[list[Transaction]] = relationship(back_populates='user', cascade='all, delete-orphan')
    categories: Mapped[list[Category]] = relationship(back_populates='owner', cascade='all, delete-orphan')
    password_reset_tokens: Mapped[list[PasswordResetToken]] = relationship(back_populates='user', cascade='all, delete-orphan')
    revoked_tokens: Mapped[list[RevokedToken]] = relationship(back_populates='user', cascade='all, delete-orphan')

    def __repr__(self) -> str:
        return f'<User id={self.id} email={self.email!r}>'


class Category(Base):
    """A shared predefined category or a user-owned custom category."""

    __tablename__ = 'categories'
    __table_args__ = (UniqueConstraint('name', 'owner_id', name='uq_category_name_owner'),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    is_predefined: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    owner: Mapped[User | None] = relationship(back_populates='categories')
    transactions: Mapped[list[Transaction]] = relationship(back_populates='category')

    def __repr__(self) -> str:
        return f'<Category id={self.id} name={self.name!r}>'


transaction_tags = Table(
    'transaction_tags',
    Base.metadata,
    Column('transaction_id', ForeignKey('transactions.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True),
)


class Tag(Base):
    """A user-owned label for flexible transaction filtering."""

    __tablename__ = 'tags'
    __table_args__ = (UniqueConstraint('name', 'owner_id', name='uq_tag_name_owner'),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    transactions: Mapped[list[Transaction]] = relationship(secondary=transaction_tags, back_populates='tags')


class Transaction(Base):
    """A user-owned income or expense entry."""

    __tablename__ = 'transactions'

    id: Mapped[int] = mapped_column(primary_key=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    type: Mapped[TransactionType] = mapped_column(SqlEnum(TransactionType), nullable=False, index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey('categories.id', ondelete='RESTRICT'), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped[User] = relationship(back_populates='transactions')
    category: Mapped[Category] = relationship(back_populates='transactions')
    tags: Mapped[list[Tag]] = relationship(secondary=transaction_tags, back_populates='transactions')
    attachments: Mapped[list[TransactionAttachment]] = relationship(back_populates='transaction', cascade='all, delete-orphan')

    def __repr__(self) -> str:
        return f'<Transaction id={self.id} type={self.type.value} amount={self.amount}>'


class TransactionAttachment(Base):
    __tablename__ = 'transaction_attachments'

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey('transactions.id', ondelete='CASCADE'), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    transaction: Mapped[Transaction] = relationship(back_populates='attachments')


class PasswordResetToken(Base):
    __tablename__ = 'password_reset_tokens'

    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    user: Mapped[User] = relationship(back_populates='password_reset_tokens')


class RevokedToken(Base):
    __tablename__ = 'revoked_tokens'

    id: Mapped[int] = mapped_column(primary_key=True)
    jti: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    user: Mapped[User] = relationship(back_populates='revoked_tokens')
