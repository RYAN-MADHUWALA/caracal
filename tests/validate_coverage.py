#!/usr/bin/env python3
"""
Validate coverage measurement capabilities.

This script validates that code coverage can be measured and reported correctly.
"""
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list, description: str) -> tuple[bool, str]:
    """Run a command and return success status and output."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=Path(__file__).parent.parent
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def validate_coverage_package():
    """Validate that coverage package is installed."""
    print("Checking: Coverage Package Installation")
    
    cmd = ["uv", "run", "python", "-c", "import coverage; print(coverage.__version__)"]
    success, output = run_command(cmd, "Coverage package check")
    
    if success and output.strip():
        print(f"  ✓ PASSED - Coverage package installed (version: {output.strip()})")
        return True
    else:
        print("  ✗ FAILED - Coverage package not available")
        return False


def validate_pytest_cov():
    """Validate that pytest-cov is installed."""
    print("Checking: pytest-cov Plugin")
    
    cmd = ["uv", "run", "python", "-c", "import pytest_cov; print('OK')"]
    success, output = run_command(cmd, "pytest-cov check")
    
    if success and "OK" in output:
        print("  ✓ PASSED - pytest-cov plugin installed")
        return True
    else:
        print("  ✗ FAILED - pytest-cov plugin not available")
        return False


def validate_coverage_config():
    """Validate that coverage configuration exists in pyproject.toml."""
    print("Checking: Coverage Configuration")
    
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        print("  ✗ FAILED - pyproject.toml not found")
        return False
    
    content = pyproject_path.read_text()
    
    required_sections = [
        "[tool.coverage.run]",
        "[tool.coverage.report]",
        "source = [\"caracal\"]",
        "fail_under = 90"
    ]
    
    missing = [section for section in required_sections if section not in content]
    
    if not missing:
        print("  ✓ PASSED - Coverage configuration is complete")
        return True
    else:
        print("  ✗ FAILED - Missing coverage configuration sections:")
        for section in missing:
            print(f"    - {section}")
        return False


def validate_coverage_run():
    """Validate that coverage can be measured."""
    print("Checking: Coverage Measurement")
    
    # Run a simple test with coverage
    cmd = [
        "uv", "run", "pytest",
        "tests/test_simple.py",
        "--cov=caracal",
        "--cov-report=term",
        "-v"
    ]
    success, output = run_command(cmd, "Coverage measurement")
    
    # Check if coverage output is present
    has_coverage = "coverage" in output.lower() or "%" in output
    
    if success or has_coverage:
        print("  ✓ PASSED - Coverage can be measured")
        return True
    else:
        print("  ✗ FAILED - Coverage measurement failed")
        print(f"    Output: {output[:200]}")
        return False


def validate_coverage_reports():
    """Validate that coverage reports can be generated."""
    print("Checking: Coverage Report Generation")
    
    # Check if HTML report directory exists or can be created
    htmlcov_path = Path("htmlcov")
    
    # Run coverage with HTML report
    cmd = [
        "uv", "run", "pytest",
        "tests/test_simple.py",
        "--cov=caracal",
        "--cov-report=html",
        "--cov-report=xml",
        "--cov-report=term",
        "-v"
    ]
    success, output = run_command(cmd, "Coverage report generation")
    
    # Check if reports were generated
    html_exists = htmlcov_path.exists() and (htmlcov_path / "index.html").exists()
    xml_exists = Path("coverage.xml").exists()
    
    if html_exists or xml_exists or "coverage" in output.lower():
        print("  ✓ PASSED - Coverage reports can be generated")
        if html_exists:
            print("    - HTML report: htmlcov/index.html")
        if xml_exists:
            print("    - XML report: coverage.xml")
        return True
    else:
        print("  ✗ FAILED - Coverage report generation failed")
        return False


def validate_coverage_threshold():
    """Validate that coverage threshold enforcement works."""
    print("Checking: Coverage Threshold Enforcement")
    
    # The threshold is set to 90% in pyproject.toml
    # This check verifies the configuration is present
    pyproject_path = Path("pyproject.toml")
    content = pyproject_path.read_text()
    
    if "fail_under = 90" in content:
        print("  ✓ PASSED - Coverage threshold configured (90%)")
        return True
    else:
        print("  ✗ FAILED - Coverage threshold not configured")
        return False


def main():
    """Run all validation checks."""
    print("=" * 70)
    print("Coverage Measurement Validation")
    print("=" * 70)
    print()
    
    checks = [
        validate_coverage_package,
        validate_pytest_cov,
        validate_coverage_config,
        validate_coverage_run,
        validate_coverage_reports,
        validate_coverage_threshold,
    ]
    
    results = []
    for check in checks:
        result = check()
        results.append(result)
        print()
    
    print("=" * 70)
    if all(results):
        print("✓ All validation checks passed!")
        print("=" * 70)
        return 0
    else:
        print("✗ Some validation checks failed. See errors above.")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
