@echo off
REM Run all quality checks (Windows version)

echo ================================
echo Running Code Quality Checks
echo ================================
echo.

REM Format check (without modifying files)
echo 1. Checking code formatting...
call conda activate ragchatbot && uv run black --check backend\ main.py
set BLACK_EXIT=%ERRORLEVEL%

echo.
echo 2. Checking import sorting...
call conda activate ragchatbot && uv run isort --check-only backend\ main.py
set ISORT_EXIT=%ERRORLEVEL%

echo.
echo 3. Running linter...
call conda activate ragchatbot && uv run flake8 backend\ main.py --max-line-length=88 --extend-ignore=E203,W503
set FLAKE8_EXIT=%ERRORLEVEL%

echo.
echo 4. Running type checker...
call conda activate ragchatbot && uv run mypy backend\ main.py
set MYPY_EXIT=%ERRORLEVEL%

echo.
echo 5. Running tests with coverage...
cd backend
call conda activate ragchatbot && uv run pytest
set PYTEST_EXIT=%ERRORLEVEL%
cd ..

echo.
echo ================================
echo Quality Check Summary
echo ================================
if %BLACK_EXIT%==0 (echo Black formatting: PASS) else (echo Black formatting: FAIL)
if %ISORT_EXIT%==0 (echo Import sorting: PASS) else (echo Import sorting: FAIL)
if %FLAKE8_EXIT%==0 (echo Flake8 linting: PASS) else (echo Flake8 linting: FAIL)
if %MYPY_EXIT%==0 (echo MyPy type check: PASS) else (echo MyPy type check: FAIL)
if %PYTEST_EXIT%==0 (echo Pytest tests: PASS) else (echo Pytest tests: FAIL)
echo ================================

REM Exit with error if any check failed
if not %BLACK_EXIT%==0 exit /b 1
if not %ISORT_EXIT%==0 exit /b 1
if not %FLAKE8_EXIT%==0 exit /b 1
if not %MYPY_EXIT%==0 exit /b 1
if not %PYTEST_EXIT%==0 exit /b 1

echo.
echo All quality checks passed!
