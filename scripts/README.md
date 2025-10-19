# Development Scripts

This directory contains scripts for maintaining code quality in the RAG chatbot project.

## Available Scripts

### Format Scripts

**Windows:** `format.bat`
**Linux/Mac:** `format.sh`

Automatically formats all Python code using:
- **black**: Enforces consistent code style (88 char line length)
- **isort**: Organizes imports in a standardized way

**Usage:**
```bash
# Windows
scripts\format.bat

# Linux/Mac
chmod +x scripts/format.sh
./scripts/format.sh
```

### Lint Scripts

**Windows:** `lint.bat`
**Linux/Mac:** `lint.sh`

Runs static analysis tools to check code quality:
- **flake8**: Checks PEP 8 style violations and common errors
- **mypy**: Performs type checking

**Usage:**
```bash
# Windows
scripts\lint.bat

# Linux/Mac
chmod +x scripts/lint.sh
./scripts/lint.sh
```

### Quality Check Scripts

**Windows:** `quality-check.bat`
**Linux/Mac:** `quality-check.sh`

Comprehensive quality check that runs:
1. Black formatting check (without modifying files)
2. Import sorting check
3. Flake8 linting
4. MyPy type checking
5. Pytest test suite with coverage

Returns exit code 0 if all checks pass, 1 if any fail.

**Usage:**
```bash
# Windows
scripts\quality-check.bat

# Linux/Mac
chmod +x scripts/quality-check.sh
./scripts/quality-check.sh
```

## Configuration Files

- **pyproject.toml**: Tool configurations for black, isort, mypy, and pytest
- **.flake8**: Flake8 linter settings

## Recommended Workflow

### Before Committing Code

1. Format your code:
   ```bash
   scripts\format.bat  # or ./scripts/format.sh
   ```

2. Run quality checks:
   ```bash
   scripts\quality-check.bat  # or ./scripts/quality-check.sh
   ```

3. Fix any issues reported

4. Commit your changes

### Continuous Development

Run the linter frequently during development:
```bash
scripts\lint.bat  # or ./scripts/lint.sh
```

This provides quick feedback on code style and potential issues without running the full test suite.

## Tool Details

### Black
- **Line length**: 88 characters
- **Target version**: Python 3.13
- **Excludes**: `.venv`, `chroma_db`, build directories

### isort
- **Profile**: Black-compatible
- **Line length**: 88 characters
- **Multi-line output**: Mode 3 (vertical hanging indent)

### Flake8
- **Max line length**: 88 characters
- **Ignored rules**: E203, W503, E501 (for black compatibility)
- **Per-file ignores**: F401 in `__init__.py` files

### MyPy
- **Python version**: 3.13
- **Mode**: Relaxed (allows untyped definitions for rapid development)
- **Ignores**: Missing imports
- **Excludes**: `chroma_db/`, `.venv/`, `tests/`

### Pytest
- **Test paths**: `backend/tests`
- **Coverage**: HTML and terminal reports
- **Naming**: `test_*.py` files with `test_*` functions

## Troubleshooting

### Scripts won't execute on Linux/Mac
Make scripts executable:
```bash
chmod +x scripts/*.sh
```

### Virtual environment not found
Make sure you've run `uv sync --extra dev` first to install all development dependencies.

### Tests failing
Ensure your `.env` file is configured with a valid `ANTHROPIC_API_KEY`.

### Type checking errors
MyPy is configured with relaxed settings. If you see errors, you can:
- Add type hints to fix the issues
- Add `# type: ignore` comments for specific lines
- Adjust settings in `pyproject.toml` under `[tool.mypy]`
