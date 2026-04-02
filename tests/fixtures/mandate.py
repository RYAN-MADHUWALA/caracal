"""Mandate test fixtures."""
import pytest
from datetime import datetime, timedelta
from typing import Dict, Any
import uuid


@pytest.fixture
def valid_mandate_data() -> Dict[str, Any]:
    """Provide valid mandate data for testing."""
    return {
        "authority_id": str(uuid.uuid4()),
        "principal_id": "user-123",
        "scope": "read:secrets",
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(hours=24),
    }


@pytest.fixture
def mandate_with_constraints() -> Dict[str, Any]:
    """Provide mandate data with constraints."""
    return {
        "authority_id": str(uuid.uuid4()),
        "principal_id": "user-456",
        "scope": "write:secrets",
        "constraints": {
            "max_uses": 10,
            "allowed_ips": ["192.168.1.0/24"],
            "time_window": {"start": "09:00", "end": "17:00"},
        },
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=7),
    }


@pytest.fixture
def expired_mandate_data() -> Dict[str, Any]:
    """Provide expired mandate data for testing."""
    return {
        "authority_id": str(uuid.uuid4()),
        "principal_id": "user-789",
        "scope": "read:secrets",
        "created_at": datetime.utcnow() - timedelta(days=30),
        "expires_at": datetime.utcnow() - timedelta(days=1),
    }


@pytest.fixture
def revoked_mandate_data() -> Dict[str, Any]:
    """Provide revoked mandate data for testing."""
    return {
        "authority_id": str(uuid.uuid4()),
        "principal_id": "user-999",
        "scope": "admin:all",
        "status": "revoked",
        "revoked_at": datetime.utcnow() - timedelta(hours=2),
        "revoked_by": "admin-user",
        "revocation_reason": "Security policy violation",
        "created_at": datetime.utcnow() - timedelta(days=5),
        "expires_at": datetime.utcnow() + timedelta(days=25),
    }


@pytest.fixture
def multiple_mandates() -> list[Dict[str, Any]]:
    """Provide multiple mandate records for testing."""
    base_time = datetime.utcnow()
    return [
        {
            "authority_id": str(uuid.uuid4()),
            "principal_id": f"user-{i}",
            "scope": ["read:secrets", "write:secrets", "admin:all"][i % 3],
            "created_at": base_time - timedelta(days=i),
            "expires_at": base_time + timedelta(days=30 - i),
        }
        for i in range(10)
    ]
