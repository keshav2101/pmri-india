"""
core/database.py — Async SQLAlchemy engine and session.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import get_settings

settings = get_settings()

# Supabase Transaction Pooler (port 6543) does not support prepared statements.
# Disabling them is required to avoid errors on write operations (INSERT/UPDATE).
_connect_args: dict = {}
if ":6543/" in settings.database_url or "pooler.supabase.com" in settings.database_url:
    _connect_args = {
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    }

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=5,
    max_overflow=2,
    connect_args=_connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
