from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import QueuePool
from app.config import settings

# PostgreSQL engine with connection pooling
# pool_size: number of persistent connections kept alive
# max_overflow: extra connections allowed above pool_size under burst load
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,        # Test connections before use to detect stale connections
    pool_recycle=3600,         # Recycle connections every 1 hour
    echo=False                 # Set True in dev to log SQL queries
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency: provides a database session and ensures it is closed after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
