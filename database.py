# Database configuration and async SQLAlchemy session utilities.
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

load_dotenv('.env_10c6229a-2c2d-44bf-a722-7f4465657ae8', override=True)

DEFAULT_DATABASE_URL = 'mysql+aiomysql://myuser:mypassword@localhost:3306/gen_226c439ab41f'
DATABASE_URL = os.getenv('DATABASE_URL', DEFAULT_DATABASE_URL)


def _to_async_url(url: str) -> str:
    """Convert a synchronous MySQL URL to its aiomysql counterpart."""
    if url.startswith('mysql://'):
        return 'mysql+aiomysql://' + url[len('mysql://'):]
    return url


engine = create_async_engine(
    _to_async_url(DATABASE_URL),
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=5,
    max_overflow=10,
)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class for all ORM models."""


@asynccontextmanager
async def get_session():
    """Provide a transactional-capable session for explicit handler use."""
    session = SessionLocal()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
