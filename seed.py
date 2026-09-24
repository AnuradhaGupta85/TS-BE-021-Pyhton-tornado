# Database schema setup and predefined category seeding utility.
import asyncio

from dotenv import load_dotenv
from sqlalchemy import inspect, select, text

from database import Base, SessionLocal, engine
from models import Category

load_dotenv('.env_10c6229a-2c2d-44bf-a722-7f4465657ae8', override=True)

PREDEFINED_CATEGORIES = ['Food', 'Transport', 'Housing', 'Utilities', 'Salary']


async def seed() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        columns = await conn.run_sync(lambda sync_conn: {column['name'] for column in inspect(sync_conn).get_columns('users')})
        if 'name' not in columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN name VARCHAR(100) NOT NULL DEFAULT ''"))
    async with SessionLocal() as db:
        existing = set((await db.execute(select(Category.name).where(Category.is_predefined.is_(True)))).scalars().all())
        for name in PREDEFINED_CATEGORIES:
            if name not in existing:
                db.add(Category(name=name, is_predefined=True, owner_id=None))
        await db.commit()


if __name__ == '__main__':
    asyncio.run(seed())
