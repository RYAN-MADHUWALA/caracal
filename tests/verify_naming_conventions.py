#!/usr/bin/env python3
"""
Verify test file naming conventions.

Requirements:
- All test files must start with test_
- All test files must use lowercase with underscores
- All test files must contain 1-2 words maximum (after test_)
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple


def is_valid_test_filename(filename: str) -> Tuple[bool, str]:
    """
    Check if a test filename follows naming conventions.
    
    Args:
        filename: The filename to check (without path)
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Must be a Python file
    if not filename.endswith('.py'):
        return True, ""  # Not a Python file, skip
    
    # Must start with test_
    if not filename.startswith('test_'):
        return False, f"Does not start with 'test_': {filename}"
    
    # Remove test_ prefix and .py suffix
    name_part = filename[5:-3]  # Remove 'test_' and '.py'
    
    # Check for lowercase with underscores only
    if not re.match(r'^[a-z_]+$', name_part):
        return False, f"Contains uppercase or invalid characters: {filename}"
    
    # Check word count (1-2 words maximum)
    # Words are separated by underscores
    words = [w for w in name_part.split('_') if w]  # Filter empty strings
    if len(words) > 2:
        return False, f"Contains more than 2 words ({len(words)} words): {filename}"
    
    return True, ""


def find_test_files(tests_dir: Path) -> List[Path]:
    """
    Find all Python test files in the tests directory.
    
    Args:
        tests_dir: Path to the tests directory
    
    Returns:
        List of test file paths
    """
    test_files = []
    for root, dirs, files in os.walk(tests_dir):
        # Skip __pycache__ and .hypothesis directories
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.hypothesis', '.pytest_cache']]
        
        for file in files:
            if file.endswith('.py') and file.startswith('test_'):
                test_files.append(Path(root) / file)
    
    return test_files


def verify_naming_conventions(tests_dir: Path) -> Tuple[List[str], List[str]]:
    """
    Verify all test files follow naming conventions.
    
    Args:
        tests_dir: Path to the tests directory
    
    Returns:
        Tuple of (valid_files, invalid_files_with_reasons)
    """
    test_files = find_test_files(tests_dir)
    valid_files = []
    invalid_files = []
    
    for test_file in test_files:
        filename = test_file.name
        is_valid, error_msg = is_valid_test_filename(filename)
        
        if is_valid:
            valid_files.append(str(test_file.relative_to(tests_dir)))
        else:
            invalid_files.append(f"{test_file.relative_to(tests_dir)}: {error_msg}")
    
    return valid_files, invalid_files


def main():
    """Main entry point."""
    # Find tests directory
    script_dir = Path(__file__).parent
    tests_dir = script_dir
    
    # Write to both stdout and a file
    output_file = tests_dir / "naming_conventions_report.txt"
    
    def write_output(msg):
        """Write to both stdout and file."""
        print(msg, flush=True)
        with open(output_file, 'a') as f:
            f.write(msg + '\n')
    
    # Clear the output file
    if output_file.exists():
        output_file.unlink()
    
    write_output("=" * 80)
    write_output("Test File Naming Convention Verification")
    write_output("=" * 80)
    write_output("")
    write_output("Requirements:")
    write_output("  - All test files must start with test_")
    write_output("  - All test files must use lowercase with underscores")
    write_output("  - All test files must contain 1-2 words maximum (after test_)")
    write_output("")
    write_output(f"Scanning directory: {tests_dir}")
    write_output("")
    
    valid_files, invalid_files = verify_naming_conventions(tests_dir)
    
    write_output(f"Total test files found: {len(valid_files) + len(invalid_files)}")
    write_output(f"Valid files: {len(valid_files)}")
    write_output(f"Invalid files: {len(invalid_files)}")
    write_output("")
    
    if invalid_files:
        write_output("=" * 80)
        write_output("INVALID FILES:")
        write_output("=" * 80)
        for invalid_file in sorted(invalid_files):
            write_output(f"  ❌ {invalid_file}")
        write_output("")
        write_output("=" * 80)
        write_output("RECOMMENDATIONS:")
        write_output("=" * 80)
        write_output("Files with more than 2 words should be renamed to use 1-2 words.")
        write_output("Examples:")
        write_output("  - test_authority_ledger.py -> test_authority.py (if in integration/core/)")
        write_output("  - test_mandate_delegation.py -> test_mandates.py (if in integration/core/)")
        write_output("  - test_circuit_breaker.py -> test_breaker.py")
        write_output("")
        return 1
    else:
        write_output("=" * 80)
        write_output("✅ All test files follow naming conventions!")
        write_output("=" * 80)
        return 0


if __name__ == '__main__':
    sys.exit(main())
