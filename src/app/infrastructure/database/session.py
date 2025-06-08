"""SQLAlchemy session management for synchronous operations."""
import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from app.config import Settings
from app.infrastructure.database.models import Base

logger = logging.getLogger(__name__)


class DatabaseSession:
    """Manages SQLAlchemy sessions for ORM operations."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._engine = None
        self._session_factory = None

    def initialize(self) -> None:
        """Initialize the SQLAlchemy engine and session factory."""
        if self._engine is not None:
            return

        logger.info("Initializing SQLAlchemy engine")

        # Create engine with connection pooling
        self._engine = create_engine(
            self.settings.postgres_url,
            poolclass=QueuePool,
            pool_size=self.settings.postgres_pool_size,
            max_overflow=self.settings.postgres_max_overflow,
            pool_pre_ping=True,  # Enable connection health checks
            echo=self.settings.debug,  # Log SQL statements in debug mode
        )

        # Create session factory
        self._session_factory = sessionmaker(
            bind=self._engine, autocommit=False, autoflush=False, expire_on_commit=False
        )

        logger.info("SQLAlchemy engine initialized successfully")

    def create_tables(self) -> None:
        """Create all database tables."""
        if self._engine is None:
            raise RuntimeError("Database engine not initialized")

        logger.info("Creating database tables")
        Base.metadata.create_all(bind=self._engine)
        logger.info("Database tables created successfully")

    def drop_tables(self) -> None:
        """Drop all database tables."""
        if self._engine is None:
            raise RuntimeError("Database engine not initialized")

        logger.warning("Dropping all database tables")
        Base.metadata.drop_all(bind=self._engine)
        logger.info("Database tables dropped")

    def close(self) -> None:
        """Close the database engine."""
        if self._engine is not None:
            logger.info("Closing database engine")
            self._engine.dispose()
            self._engine = None
            self._session_factory = None

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session."""
        if self._session_factory is None:
            raise RuntimeError("Session factory not initialized")

        session = self._session_factory()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def check_health(self) -> bool:
        """Check if database connection is healthy."""
        try:
            with self.get_session() as session:
                session.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
