"""
Copyright (C) 2026 Garudex Labs.  All Rights Reserved.
Caracal, a product of Garudex Labs

Import verification tests for native implementations.

These tests verify that:
1. Native implementations can be imported from caracal.core modules
2. No ASE imports exist in the codebase
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


class TestNoASEImports:
    """Test that no ASE imports exist in the codebase."""
    
    def get_python_files(self, directory: Path) -> list:
        """Recursively get all Python files in a directory."""
        python_files = []
        for root, dirs, files in os.walk(directory):
            # Skip virtual environments and cache directories
            dirs[:] = [d for d in dirs if d not in ['.venv', '__pycache__', '.pytest_cache', 'node_modules', '.git']]
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)
        
        return python_files
    
    def test_no_ase_imports_in_caracal(self):
        """Test that no Python files in Caracal contain ASE imports."""
        caracal_dir = Path(__file__).parent.parent.parent / "caracal"
        
        if not caracal_dir.exists():
            pytest.skip("Caracal directory not found")
        
        python_files = self.get_python_files(caracal_dir)
        
        files_with_ase_imports = []
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Check for ASE imports
                    if 'from ase.' in content or 'import ase' in content:
                        # Exclude comments
                        lines = content.split('\n')
                        for line_num, line in enumerate(lines, 1):
                            stripped = line.strip()
                            # Skip comments
                            if stripped.startswith('#'):
                                continue
                            
                            if 'from ase.' in line or 'import ase' in line:
                                files_with_ase_imports.append({
                                    'file': str(file_path.relative_to(caracal_dir.parent)),
                                    'line': line_num,
                                    'content': line.strip()
                                })
            except Exception as e:
                # Skip files that can't be read
                continue
        
        # Assert no ASE imports found
        if files_with_ase_imports:
            error_msg = "Found ASE imports in the following files:\n"
            for item in files_with_ase_imports:
                error_msg += f"  {item['file']}:{item['line']} - {item['content']}\n"
            pytest.fail(error_msg)
    
    def test_no_ase_imports_in_tests(self):
        """Test that no test files contain ASE imports."""
        tests_dir = Path(__file__).parent.parent
        
        if not tests_dir.exists():
            pytest.skip("Tests directory not found")
        
        python_files = self.get_python_files(tests_dir)
        
        files_with_ase_imports = []
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Check for ASE imports
                    if 'from ase.' in content or 'import ase' in content:
                        # Exclude comments
                        lines = content.split('\n')
                        for line_num, line in enumerate(lines, 1):
                            stripped = line.strip()
                            # Skip comments
                            if stripped.startswith('#'):
                                continue
                            
                            if 'from ase.' in line or 'import ase' in line:
                                files_with_ase_imports.append({
                                    'file': str(file_path.relative_to(tests_dir.parent)),
                                    'line': line_num,
                                    'content': line.strip()
                                })
            except Exception as e:
                # Skip files that can't be read
                continue
        
        # Assert no ASE imports found
        if files_with_ase_imports:
            error_msg = "Found ASE imports in test files:\n"
            for item in files_with_ase_imports:
                error_msg += f"  {item['file']}:{item['line']} - {item['content']}\n"
            pytest.fail(error_msg)
    
    def test_no_ase_directory(self):
        """Test that the ase/ directory does not exist in the workspace."""
        workspace_root = Path(__file__).parent.parent.parent.parent
        ase_dir = workspace_root / "ase"
        
        assert not ase_dir.exists(), f"ASE directory still exists at {ase_dir}"
    
    def test_no_ase_in_pyproject_toml(self):
        """Test that pyproject.toml files do not reference ase-protocol."""
        workspace_root = Path(__file__).parent.parent.parent.parent
        
        # Check Caracal/pyproject.toml
        caracal_pyproject = workspace_root / "Caracal" / "pyproject.toml"
        if caracal_pyproject.exists():
            with open(caracal_pyproject, 'r') as f:
                content = f.read()
                assert 'ase-protocol' not in content, \
                    f"Found 'ase-protocol' in {caracal_pyproject}"
        
        # Check caracalEnterprise pyproject.toml files
        enterprise_api_pyproject = workspace_root / "caracalEnterprise" / "services" / "enterprise-api" / "pyproject.toml"
        if enterprise_api_pyproject.exists():
            with open(enterprise_api_pyproject, 'r') as f:
                content = f.read()
                assert 'ase-protocol' not in content, \
                    f"Found 'ase-protocol' in {enterprise_api_pyproject}"
