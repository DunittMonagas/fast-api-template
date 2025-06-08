"""Unit of Work implementation for transaction management."""
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.application.repositories import UnitOfWork
from app.infrastructure.database.session import DatabaseSession

logger = logging.getLogger(__name__)


class SQLAlchemyUnitOfWork(UnitOfWork):
    """SQLAlchemy implementation of Unit of Work pattern."""

    def __init__(self, db_session: DatabaseSession):
        self.db_session = db_session
        self._session: Optional[Session] = None

    def __enter__(self):
        """Begin transaction."""
        if self._session is not None:
            raise RuntimeError("Unit of work already active")

        self._session = self.db_session._session_factory()
        logger.debug("Transaction started")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End transaction (commit or rollback)."""
        if self._session is None:
            return

        try:
            if exc_type is None:
                # No exception, commit
                self.commit()
            else:
                # Exception occurred, rollback
                self.rollback()
        finally:
            self._session.close()
            self._session = None
            logger.debug("Transaction ended")

    def commit(self):
        """Commit the current transaction."""
        if self._session is None:
            raise RuntimeError("No active transaction")

        try:
            self._session.commit()
            logger.debug("Transaction committed")
        except Exception:
            self._session.rollback()
            logger.error("Transaction commit failed, rolled back")
            raise

    def rollback(self):
        """Rollback the current transaction."""
        if self._session is None:
            raise RuntimeError("No active transaction")

        self._session.rollback()
        logger.debug("Transaction rolled back")
