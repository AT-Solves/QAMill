"""
Database initialization and session management
SQLAlchemy setup with proper configuration
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from config.settings import settings
from models.database import Base

# Create engine based on configuration
if settings.database.url.startswith("sqlite://"):
    # SQLite uses StaticPool for testing
    engine = create_engine(
        settings.database.url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=settings.database.echo,
    )
else:
    # PostgreSQL/MySQL with connection pooling
    engine = create_engine(
        settings.database.url,
        pool_size=settings.database.pool_size,
        max_overflow=settings.database.max_overflow,
        echo=settings.database.echo,
    )

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Create all tables
Base.metadata.create_all(bind=engine)
