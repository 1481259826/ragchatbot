#!/bin/bash

# Run all quality checks

echo "================================"
echo "Running Code Quality Checks"
echo "================================"
echo ""

# Format check (without modifying files)
echo "1. Checking code formatting..."
uv run black --check backend/ main.py
BLACK_EXIT=$?

echo ""
echo "2. Checking import sorting..."
uv run isort --check-only backend/ main.py
ISORT_EXIT=$?

echo ""
echo "3. Running linter..."
uv run flake8 backend/ main.py --max-line-length=88 --extend-ignore=E203,W503
FLAKE8_EXIT=$?

echo ""
echo "4. Running type checker..."
uv run mypy backend/ main.py
MYPY_EXIT=$?

echo ""
echo "5. Running tests with coverage..."
cd backend && uv run pytest
PYTEST_EXIT=$?
cd ..

echo ""
echo "================================"
echo "Quality Check Summary"
echo "================================"
echo "Black formatting: $([ $BLACK_EXIT -eq 0 ] && echo '✓ PASS' || echo '✗ FAIL')"
echo "Import sorting: $([ $ISORT_EXIT -eq 0 ] && echo '✓ PASS' || echo '✗ FAIL')"
echo "Flake8 linting: $([ $FLAKE8_EXIT -eq 0 ] && echo '✓ PASS' || echo '✗ FAIL')"
echo "MyPy type check: $([ $MYPY_EXIT -eq 0 ] && echo '✓ PASS' || echo '✗ FAIL')"
echo "Pytest tests: $([ $PYTEST_EXIT -eq 0 ] && echo '✓ PASS' || echo '✗ FAIL')"
echo "================================"

# Exit with error if any check failed
if [ $BLACK_EXIT -ne 0 ] || [ $ISORT_EXIT -ne 0 ] || [ $FLAKE8_EXIT -ne 0 ] || [ $MYPY_EXIT -ne 0 ] || [ $PYTEST_EXIT -ne 0 ]; then
    exit 1
fi

echo ""
echo "All quality checks passed! ✓"
