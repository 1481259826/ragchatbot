@echo off
REM Format Python code with black and isort (Windows version)

echo Running black formatter...
call conda activate ragchatbot && uv run black backend\ main.py

echo.
echo Running isort import sorter...
call conda activate ragchatbot && uv run isort backend\ main.py

echo.
echo Code formatting complete!
