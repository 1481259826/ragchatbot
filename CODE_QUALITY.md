# Code Quality Setup

This document describes the code quality tools and processes implemented in this project.

## Overview

The project now includes a comprehensive code quality toolchain to ensure consistent code style, catch potential bugs, and maintain high standards across the codebase.

## Tools Installed

### 1. Black (Code Formatter)
- **Purpose**: Automatically formats Python code to a consistent style
- **Version**: >=24.0.0
- **Configuration**: Line length 88, Python 3.13 target
- **When to use**: Before every commit

### 2. isort (Import Sorter)
- **Purpose**: Organizes and sorts Python imports consistently
- **Version**: >=5.13.0
- **Configuration**: Black-compatible profile
- **When to use**: Automatically with Black

### 3. Flake8 (Linter)
- **Purpose**: Checks code for PEP 8 violations and common errors
- **Version**: >=7.0.0
- **Configuration**: 88 char line length, ignores E203, W503, E501
- **When to use**: During development and before commits

### 4. MyPy (Type Checker)
- **Purpose**: Static type checking for Python
- **Version**: >=1.8.0
- **Configuration**: Relaxed mode for rapid development
- **When to use**: Before major commits or releases

### 5. Pytest + Coverage
- **Purpose**: Run tests with coverage reporting
- **Versions**: pytest>=8.0.0, pytest-cov>=4.1.0
- **Configuration**: HTML and terminal coverage reports
- **When to use**: Before every commit

## Quick Start

### Installation

```bash
# Install all development dependencies
conda activate ragchatbot
uv sync --extra dev
```

### Daily Usage

```bash
# Format your code (Windows)
scripts\format.bat

# Format your code (Linux/Mac)
./scripts/format.sh

# Run all quality checks (Windows)
scripts\quality-check.bat

# Run all quality checks (Linux/Mac)
./scripts/quality-check.sh
```

## Development Workflow

### 1. During Development
```bash
# Quick format check
uv run black --check backend/ main.py

# Quick lint
uv run flake8 backend/ main.py
```

### 2. Before Committing
```bash
# Step 1: Format code
scripts\format.bat  # or ./scripts/format.sh

# Step 2: Run all quality checks
scripts\quality-check.bat  # or ./scripts/quality-check.sh

# Step 3: Review any issues and fix them

# Step 4: Commit
git add .
git commit -m "your message"
```

### 3. Pre-Commit Hook (Optional)
To automatically run quality checks before every commit, you can add a git pre-commit hook:

```bash
# Create .git/hooks/pre-commit file with:
#!/bin/bash
./scripts/quality-check.sh
```

## Configuration Files

### pyproject.toml
Contains configuration for:
- Black formatter settings
- isort import sorting settings
- MyPy type checking settings
- Pytest test configuration

### .flake8
Contains flake8-specific settings:
- Line length limits
- Ignored error codes
- Excluded directories
- Per-file ignores

## Quality Standards

### Code Formatting
- Maximum line length: 88 characters
- Consistent indentation: 4 spaces
- Import organization: Standard library → Third-party → Local
- String quotes: Automatically normalized by Black

### Linting Rules
- PEP 8 compliance (with Black-compatible exceptions)
- No unused imports or variables
- Proper docstring formatting
- Logical error detection

### Type Checking
- Gradual typing approach
- Warning on untyped returns
- Ignores missing imports from third-party libraries
- Excludes test directories

### Test Coverage
- Minimum coverage: Not enforced (informational)
- HTML coverage report: `htmlcov/index.html`
- Terminal coverage summary after each test run

## CI/CD Integration (Future)

The quality check script is designed to be CI/CD friendly:
- Returns exit code 0 on success, 1 on failure
- Outputs clear pass/fail status for each check
- Can be integrated with GitHub Actions, GitLab CI, etc.

Example GitHub Actions workflow:
```yaml
- name: Run quality checks
  run: |
    uv sync --extra dev
    ./scripts/quality-check.sh
```

## Troubleshooting

### Black and Flake8 Conflicts
The configuration is already set up to avoid conflicts:
- E203 (whitespace before ':') - ignored for Black
- W503 (line break before binary operator) - ignored for Black
- E501 (line too long) - ignored, Black handles this

### Import Errors in MyPy
If MyPy complains about missing imports:
1. Check if the package has type stubs
2. Add `# type: ignore` comment if necessary
3. Add to `[tool.mypy]` exclude list if persistent

### Slow Quality Checks
If quality checks are too slow:
1. Run individual tools instead of full suite
2. Use `--check` flags to skip file modifications
3. Run tests in parallel: `pytest -n auto`

## Benefits

1. **Consistency**: All code follows the same style guidelines
2. **Quality**: Automated detection of potential bugs and issues
3. **Efficiency**: Less time spent on code review for style issues
4. **Confidence**: Comprehensive test coverage with automated reporting
5. **Maintainability**: Easier onboarding for new developers

## Current Status

✅ All tools installed and configured
✅ Entire codebase formatted with Black
✅ All imports sorted with isort
✅ Scripts created for Windows and Linux/Mac
✅ Documentation updated
✅ Ready for use in development workflow

## Next Steps

1. Add pre-commit hooks for automatic quality checks
2. Set up CI/CD pipeline with quality gates
3. Configure IDE plugins for real-time feedback
4. Consider adding additional tools (bandit for security, etc.)
5. Gradually increase type coverage with MyPy

## Resources

- [Black Documentation](https://black.readthedocs.io/)
- [isort Documentation](https://pycqa.github.io/isort/)
- [Flake8 Documentation](https://flake8.pycqa.org/)
- [MyPy Documentation](https://mypy.readthedocs.io/)
- [Pytest Documentation](https://docs.pytest.org/)
