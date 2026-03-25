"""
Copyright (C) 2026 Garudex Labs.  All Rights Reserved.
Caracal, a product of Garudex Labs

Import verification tests for Caracal core modules.

These tests verify that native implementations can be imported
correctly from caracal.core modules.
"""

import os
import pytest
from pathlib import Path


class TestNativeImports:
    """Test that native implementations can be imported."""
    
    def test_import_metering_event(self):
        """Test that MeteringEvent can be imported from caracal.core.metering."""
        from caracal.core.metering import MeteringEvent
        
        # Verify it's a class
        assert isinstance(MeteringEvent, type)
        
        # Verify it has expected attributes
        assert hasattr(MeteringEvent, 'agent_id')
        assert hasattr(MeteringEvent, 'resource_type')
        assert hasattr(MeteringEvent, 'quantity')
        assert hasattr(MeteringEvent, 'timestamp')
        assert hasattr(MeteringEvent, 'metadata')
        assert hasattr(MeteringEvent, 'correlation_id')
        assert hasattr(MeteringEvent, 'parent_event_id')
        assert hasattr(MeteringEvent, 'tags')
        
        # Verify it has expected methods
        assert hasattr(MeteringEvent, 'to_dict')
        assert hasattr(MeteringEvent, 'from_dict')
        assert hasattr(MeteringEvent, 'matches_resource_pattern')
    
    def test_import_agent_identity(self):
        """Test that AgentIdentity can be imported from caracal.core.identity."""
        from caracal.core.identity import AgentIdentity
        
        # Verify it's a class
        assert isinstance(AgentIdentity, type)
        
        # Verify it has expected attributes
        assert hasattr(AgentIdentity, 'agent_id')
        assert hasattr(AgentIdentity, 'name')
        assert hasattr(AgentIdentity, 'owner')
        assert hasattr(AgentIdentity, 'created_at')
        assert hasattr(AgentIdentity, 'metadata')
        assert hasattr(AgentIdentity, 'public_key')
        assert hasattr(AgentIdentity, 'org_id')
        assert hasattr(AgentIdentity, 'role')
        assert hasattr(AgentIdentity, 'verification_status')
        assert hasattr(AgentIdentity, 'trust_level')
        assert hasattr(AgentIdentity, 'capabilities')
        assert hasattr(AgentIdentity, 'last_verified_at')
        
        # Verify it has expected methods
        assert hasattr(AgentIdentity, 'to_dict')
        assert hasattr(AgentIdentity, 'from_dict')
        assert hasattr(AgentIdentity, 'has_capability')
        assert hasattr(AgentIdentity, 'is_verified')
    
    def test_import_verification_status(self):
        """Test that VerificationStatus can be imported from caracal.core.identity."""
        from caracal.core.identity import VerificationStatus
        
        # Verify it's an enum
        from enum import Enum
        assert issubclass(VerificationStatus, Enum)
        
        # Verify it has expected values
        assert hasattr(VerificationStatus, 'UNVERIFIED')
        assert hasattr(VerificationStatus, 'VERIFIED')
        assert hasattr(VerificationStatus, 'TRUSTED')
    
    def test_import_audit_reference(self):
        """Test that AuditReference can be imported from caracal.core.audit."""
        from caracal.core.audit import AuditReference
        
        # Verify it's a class
        assert isinstance(AuditReference, type)
        
        # Verify it has expected attributes
        assert hasattr(AuditReference, 'audit_id')
        assert hasattr(AuditReference, 'location')
        assert hasattr(AuditReference, 'hash')
        assert hasattr(AuditReference, 'hash_algorithm')
        assert hasattr(AuditReference, 'previous_hash')
        assert hasattr(AuditReference, 'signature')
        assert hasattr(AuditReference, 'signer_id')
        assert hasattr(AuditReference, 'timestamp')
        assert hasattr(AuditReference, 'entry_count')
        
        # Verify it has expected methods
        assert hasattr(AuditReference, 'to_dict')
        assert hasattr(AuditReference, 'from_dict')
        assert hasattr(AuditReference, 'verify_hash')
        assert hasattr(AuditReference, 'verify_chain')
    
    def test_import_metering_collector(self):
        """Test that MeteringCollector can be imported from caracal.core.metering."""
        from caracal.core.metering import MeteringCollector
        
        # Verify it's a class
        assert isinstance(MeteringCollector, type)
        
        # Verify it has expected methods
        assert hasattr(MeteringCollector, 'collect_event')

