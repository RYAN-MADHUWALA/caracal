#!/usr/bin/env python3
"""
Master validation script for test infrastructure.

This script runs all validation checks to ensure the test infrastructure
is properly configured and functional.
"""
import subprocess
import sys
from pathlib import Path


def run_validation_script(script_name: str) -> tuple[bool, str]:
    """Run a validation script and return success status."""
    script_path = Path(__file__).parent / script_name
    
    if not script_path.exists():
        return False, f"Script not found: {script_name}"
    
    try:
        result = subprocess.run(
            ["python3", str(script_path)],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=Path(__file__).parent.parent
        )
        
        output = result.stdout + result.stderr
        return result.returncode == 0, output
    
    except subprocess.TimeoutExpired:
        return False, "Validation timed out"
    except Exception as e:
        return False, f"Error running validation: {e}"


def main():
    """Run all validation scripts."""
    print("=" * 70)
    print("Test Infrastructure - Complete Validation Suite")
    print("=" * 70)
    print()
    
    validation_scripts = [
        ("Structure Validation", "validate_structure.py"),
        ("Execution Validation", "validate_execution.py"),
        ("Coverage Validation", "validate_coverage.py"),
        ("CI/CD Validation", "validate_cicd.py"),
    ]
    
    all_passed = True
    results = []
    
    for name, script in validation_scripts:
        print(f"\n{'=' * 70}")
        print(f"Running: {name}")
        print('=' * 70)
        
        success, output = run_validation_script(script)
        results.append((name, success))
        
        # Print the output from the validation script
        print(output)
        
        if not success:
            all_passed = False
    
    # Print summary
    print("\n" + "=" * 70)
    print("Validation Summary")
    print("=" * 70)
    
    for name, success in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"{name:.<50} {status}")
    
    print("=" * 70)
    
    if all_passed:
        print("\n✓ All validations passed! Test infrastructure is ready.")
        print("=" * 70)
        return 0
    else:
        print("\n✗ Some validations failed. Review the output above.")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
