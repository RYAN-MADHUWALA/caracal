#!/usr/bin/env python3
"""Quick test script for the refactored CLI."""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from caracal.cli.main import cli

if __name__ == '__main__':
    # Test basic help
    print("Testing: caracal --help")
    print("=" * 60)
    try:
        cli(['--help'])
    except SystemExit:
        pass
    
    print("\n\nTesting: caracal")
    print("=" * 60)
    try:
        cli([])
    except SystemExit:
        pass
    
    print("\n\nTesting: caracal workspace --help")
    print("=" * 60)
    try:
        cli(['workspace', '--help'])
    except SystemExit:
        pass
