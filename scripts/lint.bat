@echo off
REM Run linting checks (Windows version)

echo Running flake8 linter...
call conda activate ragchatbot && uv run flake8 backend\ main.py --max-line-length=88 --extend-ignore=E203,W503

echo.
echo Running mypy type checker...
call conda activate ragchatbot && uv run mypy backend\ main.py

echo.
echo Linting complete!
