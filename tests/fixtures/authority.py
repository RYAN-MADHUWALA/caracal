"""Authority test fixtures."""
import pytest
from datetime import datetime, timedelta
from typing import Dict, Any


@pytest.fixture
def valid_authority_data() -> Dict[str, Any]:
    """Provide valid authority data for testing."""
    return {
        "name": "test-authority",
        "scope": "read:secrets",
        "description": "Test authority for unit tests",
        "created_at": datetime.utcnow(),
    }


@pytest.fixture
def authority_with_metadata() -> Dict[str, Any]:
    """Provide authority data with metadata."""
    return {
        "name": "metadata-authority",
        "scope": "write:secrets",
        "description": "Authority with metadata",
        "metadata": {
            "owner": "test-user",
            "environment": "test",
            "tags": ["test", "fixture"],
        },
        "created_at": datetime.utcnow(),
    }


@pytest.fixture
def expired_authority_data() -> Dict[str, Any]:
    """Provide expired authority data for testing."""
    return {
        "name": "expired-authority",
        "scope": "read:secrets",
        "description": "Expired authority for testing",
        "created_at": datetime.utcnow() - timedelta(days=365),
        "expires_at": datetime.utcnow() - timedelta(days=1),
    }


@pytest.fixture
def multiple_authorities() -> list[Dict[str, Any]]:
    """Provide multiple authority records for testing."""
    return [
        {
            "name": f"authority-{i}",
            "scope": "read:secrets" if i % 2 == 0 else "write:secrets",
            "description": f"Test authority {i}",
            "created_at": datetime.utcnow(),
        }
        for i in range(5)
    ]
