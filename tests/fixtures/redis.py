"""Redis test fixtures."""
import pytest
from typing import Dict, Any


@pytest.fixture
def redis_config() -> Dict[str, Any]:
    """Provide Redis configuration for testing."""
    return {
        "host": "localhost",
        "port": 6379,
        "db": 0,
        "password": None,
        "decode_responses": True,
        "socket_timeout": 5,
        "socket_connect_timeout": 5,
    }


@pytest.fixture
def redis_url() -> str:
    """Provide Redis URL for testing."""
    return "redis://localhost:6379/0"


@pytest.fixture
def cached_mandate_data() -> Dict[str, Any]:
    """Provide cached mandate data for testing."""
    return {
        "mandate_id": "mandate-123",
        "authority_id": "auth-456",
        "principal_id": "user-789",
        "scope": "read:secrets",
        "ttl": 3600,
        "cached_at": "2024-01-01T12:00:00Z",
    }


@pytest.fixture
def cache_keys() -> list[str]:
    """Provide test cache keys."""
    return [
        "mandate:user-123",
        "authority:auth-456",
        "delegation:del-789",
        "session:sess-abc",
        "rate_limit:user-123",
    ]


@pytest.fixture
def redis_cluster_config() -> Dict[str, Any]:
    """Provide Redis cluster configuration for testing."""
    return {
        "startup_nodes": [
            {"host": "localhost", "port": 7000},
            {"host": "localhost", "port": 7001},
            {"host": "localhost", "port": 7002},
        ],
        "decode_responses": True,
        "skip_full_coverage_check": True,
    }
