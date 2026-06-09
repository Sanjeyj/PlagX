"""Database engine and session management. Supports SQLite and PostgreSQL."""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    """Dependency that provides a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create all tables."""
    from sqlalchemy import text
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # Safe migration for pdf_status column
        if engine.dialect.name == "sqlite":
            result = await conn.execute(text("PRAGMA table_info(reports)"))
            columns = [row[1] for row in result.fetchall()]
            if "pdf_status" not in columns:
                await conn.execute(text("ALTER TABLE reports ADD COLUMN pdf_status VARCHAR(20) DEFAULT 'pending'"))
        else:
            try:
                await conn.execute(text("ALTER TABLE reports ADD COLUMN pdf_status VARCHAR(20) DEFAULT 'pending'"))
            except Exception:
                # Column might already exist or table might not exist (e.g. in test env)
                pass
