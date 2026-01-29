"""
Database connection configuration.
"""
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# Get database URL from environment variable
# Default to localhost for local testing outside docker (if port forwarded)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://brawl_user:brawl_password@postgres:5432/brawlgpt_db")

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=False)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
    pass


async def get_db():
    """Dependency to get a database session."""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    """Initialize the database by creating all tables."""
    async with engine.begin() as conn:
        # Create all tables defined in Base.metadata
        await conn.run_sync(Base.metadata.create_all)
