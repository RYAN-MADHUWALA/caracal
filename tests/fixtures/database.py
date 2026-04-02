"""Database test fixtures."""
import pytest
from typing import Generator, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool


@pytest.fixture
def in_memory_db_engine():
    """Provide an in-memory SQLite database engine for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return engine


@pytest.fixture
def db_session(in_memory_db_engine) -> Generator[Session, None, None]:
    """Provide a database session for testing."""
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=in_memory_db_engine,
    )
    
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def db_connection(in_memory_db_engine):
    """Provide a database connection for testing."""
    connection = in_memory_db_engine.connect()
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture
def test_database_url() -> str:
    """Provide a test database URL."""
    return "postgresql://test:test@localhost:5432/caracal_test"


@pytest.fixture
def migration_versions() -> list[str]:
    """Provide test migration version identifiers."""
    return [
        "001_initial_schema",
        "002_add_authority_metadata",
        "003_add_delegation_constraints",
        "004_add_audit_log",
        "005_add_merkle_tree",
    ]
