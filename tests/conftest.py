"""Pytest configuration and fixtures."""
import os
import sys
from typing import Generator
from unittest.mock import MagicMock, Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from app.config import Settings, get_settings
from app.infrastructure.database.models import Base
from app.infrastructure.database.session import DatabaseSession
from app.main import create_app


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Create test settings."""
    return Settings(
        app_env="development",
        postgres_user="testuser",
        postgres_password="testpass",
        postgres_db="test_db",
        postgres_host="localhost",
        postgres_port=5433,  # Test database port
        redis_host="localhost",
        redis_port=6380,  # Test redis port
        telegram_bot_token="test_token",
        google_api_key="test_key",
    )


@pytest.fixture(scope="session")
def test_engine(test_settings):
    """Create test database engine."""
    # Use PostgreSQL for tests with test database
    import psycopg
    from sqlalchemy.pool import NullPool
    
    test_db_name = f"test_{test_settings.postgres_db}"
    
    # Create test database if it doesn't exist
    conn_params = {
        "host": test_settings.postgres_host,
        "port": test_settings.postgres_port,
        "user": test_settings.postgres_user,
        "password": test_settings.postgres_password,
        "dbname": "postgres"
    }
    
    with psycopg.connect(**conn_params) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            # Check if database exists
            cur.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (test_db_name,)
            )
            if not cur.fetchone():
                # Create database
                cur.execute(f'CREATE DATABASE "{test_db_name}"')
    
    # Create engine for test database
    test_db_url = (
        f"postgresql+psycopg://{test_settings.postgres_user}:{test_settings.postgres_password}"
        f"@{test_settings.postgres_host}:{test_settings.postgres_port}/{test_db_name}"
    )
    
    engine = create_engine(test_db_url, poolclass=NullPool)
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Clean up
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    
    # Drop test database
    with psycopg.connect(**conn_params) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            # Terminate connections to test database
            cur.execute(
                """
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = %s
                AND pid <> pg_backend_pid()
                """,
                (test_db_name,)
            )
            # Drop database
            cur.execute(f'DROP DATABASE IF EXISTS "{test_db_name}"')


@pytest.fixture
def test_session(test_engine) -> Generator[Session, None, None]:
    """Create test database session with cleanup."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    
    # Clean all tables before each test
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    
    yield session
    
    # Rollback any uncommitted changes and close
    session.rollback()
    session.close()


@pytest.fixture
def mock_db_session(test_settings, test_session):
    """Create mock database session manager."""
    from contextlib import contextmanager
    
    db_session = Mock(spec=DatabaseSession)
    
    @contextmanager
    def mock_get_session():
        yield test_session
    
    db_session.get_session = mock_get_session
    return db_session


@pytest.fixture
def mock_redis_publisher():
    """Create mock Redis publisher."""
    publisher = Mock()
    publisher.publish = Mock()
    publisher.check_health = Mock(return_value=True)
    return publisher


@pytest.fixture
def mock_telegram_client():
    """Create mock Telegram client."""
    client = Mock()
    client.send_message = Mock(return_value={"ok": True})
    client.check_health = Mock(return_value=True)
    return client


@pytest.fixture
def mock_google_ai_client():
    """Create mock Google AI client."""
    client = Mock()
    client.generate_text = Mock(return_value="Generated text")
    client.check_health = Mock(return_value=True)
    return client


@pytest.fixture
def client(test_settings, monkeypatch) -> TestClient:
    """Create test client."""
    # Override get_settings to return test settings
    monkeypatch.setattr("app.config.get_settings", lambda: test_settings)

    # Create app
    app = create_app()

    # Create test client
    return TestClient(app)
