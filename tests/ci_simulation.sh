#!/bin/bash
# Simulate exact CI workflow steps

set -e  # Exit on any error

echo "=========================================="
echo "CI Workflow Simulation"
echo "=========================================="

# Step 1: Run unit tests (like CI does)
echo ""
echo "Step 1: Running unit tests with coverage..."
python -m pytest -m unit \
    --cov=caracal \
    --cov-report=xml \
    --cov-report=term \
    --junitxml=junit-unit.xml

echo "✓ Unit tests passed"

# Step 2: Check coverage threshold
echo ""
echo "Step 2: Checking coverage threshold..."
python -m coverage report --fail-under=10

echo "✓ Coverage threshold met"

# Step 3: Generate HTML report
echo ""
echo "Step 3: Generating HTML coverage report..."
python -m coverage html

echo "✓ HTML report generated"

echo ""
echo "=========================================="
echo "✓ ALL CI STEPS PASSED!"
echo "=========================================="
