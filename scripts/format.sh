#!/bin/bash

# Format Python code with black and isort

echo "Running black formatter..."
uv run black backend/ main.py

echo ""
echo "Running isort import sorter..."
uv run isort backend/ main.py

echo ""
echo "Code formatting complete!"
