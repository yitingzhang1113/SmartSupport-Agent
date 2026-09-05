import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Set SQLAlchemy engine log level to WARNING
# This suppresses INFO-level SQL statements from being printed to the console.
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

# Create an asynchronous database engine->Connection Pool
engine = create_async_engine(
    settings.DATABASE_URL,
    # Disable SQL statement logging
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)

# Create an asynchronous session factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for all ORM models
Base = declarative_base()

# Database session dependency
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()

        except Exception:
            await session.rollback()
            raise

        finally:
            await session.close()