"""
db/postgres.py
──────────────
Async SQLAlchemy engine + session factory for PostgreSQL.
Uses asyncpg driver for high-performance async queries.
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.db.models.work_item import Base

# Create the async engine (connection pool built-in)
engine = create_async_engine(
    settings.database_url,
    echo=False,          # set True to log every SQL statement
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # test connections before using (resilience)
)

# Session factory – use this to create DB sessions
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def create_tables():
    """Create all tables. Called at startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """
    FastAPI dependency – yields a DB session per request.
    Automatically commits on success, rolls back on error.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
