"""Database connection management using psycopg3 (synchronous only)."""
import logging
from contextlib import contextmanager
from typing import Generator

import psycopg
from psycopg_pool import ConnectionPool

from app.config import Settings

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Manages synchronous database connections using psycopg3."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._pool: ConnectionPool | None = None

    def initialize(self) -> None:
        """Initialize the connection pool."""
        if self._pool is not None:
            return

        logger.info("Initializing database connection pool")

        # Create connection pool with psycopg3
        self._pool = ConnectionPool(
            conninfo=self.settings.postgres_url,
            min_size=1,
            max_size=self.settings.postgres_pool_size,
            timeout=30.0,
            max_idle=600.0,
            max_lifetime=3600.0,
        )

        # Test the connection
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()
                if result[0] != 1:
                    raise RuntimeError("Database connection test failed")

        logger.info("Database connection pool initialized successfully")

    def close(self) -> None:
        """Close the connection pool."""
        if self._pool is not None:
            logger.info("Closing database connection pool")
            self._pool.close()
            self._pool = None

    @contextmanager
    def get_connection(self) -> Generator[psycopg.Connection, None, None]:
        """Get a database connection from the pool."""
        if self._pool is None:
            raise RuntimeError("Database connection pool not initialized")

        with self._pool.connection() as conn:
            yield conn

    def execute_query(self, query: str, params: dict | None = None) -> list:
        """Execute a query and return results."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchall()

    def execute_command(self, command: str, params: dict | None = None) -> None:
        """Execute a command (INSERT, UPDATE, DELETE)."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(command, params)
                conn.commit()

    def check_health(self) -> bool:
        """Check if database connection is healthy."""
        try:
            result = self.execute_query("SELECT 1")
            return result[0][0] == 1
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
