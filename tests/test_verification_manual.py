#!/usr/bin/env python3
"""Manual verification test for native implementations."""

import sys
from decimal import Decimal
from datetime import datetime

# Import native implementations
from caracal.core.metering import MeteringEvent
from caracal.core.identity import AgentIdentity, VerificationStatus
from caracal.core.audit import AuditReference

def test_metering_event():
    """Test MeteringEvent instantiation and serialization."""
    print("Testing MeteringEvent...")
    
    # Test instantiation
    event = MeteringEvent(
        agent_id="agent-123",
        resource_type="mcp.tool.search",
        quantity=Decimal("1.5")
    )
    assert event.agent_id == "agent-123"
    print("  ✓ MeteringEvent instantiation")
    
    # Test serialization
    data = event.to_dict()
    restored = MeteringEvent.from_dict(data)
    assert restored.agent_id == event.agent_id
    assert restored.quantity == event.quantity
    print("  ✓ MeteringEvent serialization")

def test_agent_identity():
    """Test AgentIdentity instantiation and serialization."""
    print("Testing AgentIdentity...")
    
    # Test instantiation
    identity = AgentIdentity(
        agent_id="agent-123",
        name="Test Agent",
        owner="owner@example.com",
        created_at=datetime.utcnow().isoformat() + "Z",
        metadata={}
    )
    assert identity.agent_id == "agent-123"
    print("  ✓ AgentIdentity instantiation")
    
    # Test serialization
    data = identity.to_dict()
    restored = AgentIdentity.from_dict(data)
    assert restored.agent_id == identity.agent_id
    assert restored.name == identity.name
    print("  ✓ AgentIdentity serialization")

def test_audit_reference():
    """Test AuditReference instantiation and serialization."""
    print("Testing AuditReference...")
    
    # Test instantiation
    ref = AuditReference(audit_id="audit-123")
    assert ref.audit_id == "audit-123"
    print("  ✓ AuditReference instantiation")
    
    # Test serialization
    data = ref.to_dict()
    restored = AuditReference.from_dict(data)
    assert restored.audit_id == ref.audit_id
    print("  ✓ AuditReference serialization")

if __name__ == "__main__":
    try:
        test_metering_event()
        test_agent_identity()
        test_audit_reference()
        print("\n✅ All verification tests passed!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
