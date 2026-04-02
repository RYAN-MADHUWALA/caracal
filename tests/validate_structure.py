#!/usr/bin/env python3
"""
Validate test directory structure.

This script validates that the test infrastructure follows the design specification.
"""
import os
import sys
from pathlib import Path
from typing import List, Tuple


def validate_directory_structure() -> Tuple[bool, List[str]]:
    """Validate that all required directories exist."""
    errors = []
    tests_dir = Path("tests")
    
    required_dirs = [
        "tests",
        "tests/unit",
        "tests/integration",
        "tests/e2e",
        "tests/security",
        "tests/sdk",
        "tests/fixtures",
        "tests/mocks",
        "tests/setup",
        # Unit test components
        "tests/unit/core",
        "tests/unit/cli",
        "tests/unit/db",
        "tests/unit/deployment",
        "tests/unit/mcp",
        "tests/unit/merkle",
        "tests/unit/monitoring",
        "tests/unit/provider",
        "tests/unit/redis",
        "tests/unit/runtime",
        "tests/unit/storage",
        "tests/unit/flow",
        "tests/unit/config",
        "tests/unit/enterprise",
        # Integration test components
        "tests/integration/core",
        "tests/integration/db",
        "tests/integration/deployment",
        "tests/integration/mcp",
        "tests/integration/merkle",
        "tests/integration/monitoring",
        "tests/integration/redis",
        "tests/integration/api",
        "tests/integration/enterprise",
        # E2E test components
        "tests/e2e/workflows",
        "tests/e2e/cli",
        "tests/e2e/flow",
        "tests/e2e/enterprise",
        # Security test components
        "tests/security/abuse",
        "tests/security/fuzzing",
        "tests/security/regression",
        # SDK placeholders
        "tests/sdk/python",
        "tests/sdk/typescript",
    ]
    
    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            errors.append(f"Missing directory: {dir_path}")
    
    return len(errors) == 0, errors


def validate_init_files() -> Tuple[bool, List[str]]:
    """Validate that __init__.py files exist in test directories."""
    errors = []
    
    required_init_files = [
        "tests/__init__.py",
        "tests/unit/__init__.py",
        "tests/integration/__init__.py",
        "tests/e2e/__init__.py",
        "tests/security/__init__.py",
        "tests/fixtures/__init__.py",
        "tests/mocks/__init__.py",
        "tests/setup/__init__.py",
    ]
    
    for init_file in required_init_files:
        if not Path(init_file).exists():
            errors.append(f"Missing __init__.py: {init_file}")
    
    return len(errors) == 0, errors


def validate_config_files() -> Tuple[bool, List[str]]:
    """Validate that configuration files exist."""
    errors = []
    
    required_files = [
        "tests/conftest.py",
        "pyproject.toml",
    ]
    
    for file_path in required_files:
        if not Path(file_path).exists():
            errors.append(f"Missing configuration file: {file_path}")
    
    return len(errors) == 0, errors


def validate_test_files() -> Tuple[bool, List[str]]:
    """Validate that test files follow naming conventions."""
    errors = []
    tests_dir = Path("tests")
    
    # Find all Python files in test directories
    test_dirs = ["unit", "integration", "e2e", "security"]
    
    for test_dir in test_dirs:
        dir_path = tests_dir / test_dir
        if not dir_path.exists():
            continue
        
        for py_file in dir_path.rglob("*.py"):
            # Skip __init__.py files
            if py_file.name == "__init__.py":
                continue
            
            # Check if file starts with test_
            if not py_file.name.startswith("test_"):
                errors.append(
                    f"Test file does not follow naming convention: {py_file}"
                )
    
    return len(errors) == 0, errors


def validate_sdk_readmes() -> Tuple[bool, List[str]]:
    """Validate that SDK README files exist."""
    errors = []
    
    required_readmes = [
        "tests/sdk/README.md",
        "tests/sdk/python/README.md",
        "tests/sdk/typescript/README.md",
    ]
    
    for readme in required_readmes:
        if not Path(readme).exists():
            errors.append(f"Missing SDK README: {readme}")
    
    return len(errors) == 0, errors


def validate_fixture_and_mock_files() -> Tuple[bool, List[str]]:
    """Validate that fixture and mock directories have content."""
    errors = []
    
    fixtures_dir = Path("tests/fixtures")
    mocks_dir = Path("tests/mocks")
    setup_dir = Path("tests/setup")
    
    # Check that directories have at least __init__.py
    for dir_path, name in [(fixtures_dir, "fixtures"), (mocks_dir, "mocks"), (setup_dir, "setup")]:
        if not dir_path.exists():
            errors.append(f"Missing {name} directory")
            continue
        
        py_files = list(dir_path.glob("*.py"))
        if len(py_files) == 0:
            errors.append(f"No Python files in {name} directory")
    
    return len(errors) == 0, errors


def main():
    """Run all validation checks."""
    print("=" * 70)
    print("Test Infrastructure Structure Validation")
    print("=" * 70)
    print()
    
    all_passed = True
    
    # Run all validation checks
    checks = [
        ("Directory Structure", validate_directory_structure),
        ("__init__.py Files", validate_init_files),
        ("Configuration Files", validate_config_files),
        ("Test File Naming", validate_test_files),
        ("SDK README Files", validate_sdk_readmes),
        ("Fixture and Mock Files", validate_fixture_and_mock_files),
    ]
    
    for check_name, check_func in checks:
        print(f"Checking: {check_name}")
        passed, errors = check_func()
        
        if passed:
            print(f"  ✓ PASSED")
        else:
            print(f"  ✗ FAILED")
            all_passed = False
            for error in errors:
                print(f"    - {error}")
        print()
    
    print("=" * 70)
    if all_passed:
        print("✓ All validation checks passed!")
        print("=" * 70)
        return 0
    else:
        print("✗ Some validation checks failed. See errors above.")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
