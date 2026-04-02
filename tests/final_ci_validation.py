#!/usr/bin/env python
"""
Final CI validation - Comprehensive check before pushing to GitHub.
This script validates all fixes and ensures CI will pass.
"""
import subprocess
import sys
from pathlib import Path

def run_test(name, cmd, cwd=None):
    """Run a test command and return success status."""
    if cwd is None:
        cwd = Path(__file__).parent.parent
    
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            timeout=60
        )
        success = result.returncode == 0
        return success, result.returncode
    except Exception as e:
        return False, -1

def main():
    """Run all validation tests."""
    print("="*70)
    print("FINAL CI VALIDATION")
    print("="*70)
    print()
    
    tests = [
        ("Syntax: main_backup.py", 
         ["python", "-m", "py_compile", "caracal/cli/main_backup.py"]),
        
        ("Syntax: test_simple.py", 
         ["python", "-m", "py_compile", "tests/test_simple.py"]),
        
        ("Import: caracal package", 
         ["python", "-c", "import sys; sys.path.insert(0, '.'); import caracal"]),
        
        ("Import: pytest", 
         ["python", "-c", "import pytest"]),
        
        ("Import: coverage", 
         ["python", "-c", "import coverage"]),
        
        ("Test discovery", 
         ["python", "-m", "pytest", "--collect-only", "tests/test_simple.py", "-q"]),
        
        ("Run unit tests", 
         ["python", "-m", "pytest", "-m", "unit", "-v"]),
        
        ("Coverage measurement", 
         ["python", "-m", "pytest", "tests/test_simple.py", 
          "--cov=caracal", "--cov-report=term"]),
        
        ("Coverage threshold (10%)", 
         ["python", "-m", "coverage", "report", "--fail-under=10"]),
        
        ("Test structure validation", 
         ["python", "tests/validate_structure.py"]),
    ]
    
    results = []
    max_name_len = max(len(name) for name, _ in tests)
    
    for name, cmd in tests:
        success, exit_code = run_test(name, cmd)
        results.append((name, success, exit_code))
        
        status = "✓ PASS" if success else "✗ FAIL"
        padding = " " * (max_name_len - len(name))
        print(f"{name}{padding}  {status} (exit: {exit_code})")
    
    print()
    print("="*70)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    print(f"Results: {passed}/{total} tests passed")
    print()
    
    if passed == total:
        print("✓ ALL TESTS PASSED!")
        print()
        print("CI/CD Status: READY")
        print("Confidence: HIGH")
        print()
        print("You can safely push to GitHub. The CI pipeline should pass.")
        return 0
    else:
        print("✗ SOME TESTS FAILED!")
        print()
        print("CI/CD Status: NOT READY")
        print()
        print("Failed tests:")
        for name, success, exit_code in results:
            if not success:
                print(f"  - {name} (exit: {exit_code})")
        print()
        print("Please fix the issues before pushing to GitHub.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
