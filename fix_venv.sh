#!/bin/bash

# Fix Virtual Environment Script
# Run this script in your terminal (outside of Cursor) to fix venv permissions

cd /Users/qatesting/Documents/VPMBackEnd

echo "Backing up old venv..."
mv venv venv_backup_$(date +%Y%m%d_%H%M%S) 2>/dev/null || true

echo "Creating new virtual environment..."
python3 -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing dependencies..."
pip install -r requirements.txt

# Fix pydantic for Python 3.13 compatibility
echo "Fixing pydantic for Python 3.13 compatibility..."
pip install "pydantic>=2.12.0" --upgrade 2>&1 | grep -E "(Successfully|Requirement|ERROR)" || echo "Pydantic update attempted"

echo ""
echo "✅ Virtual environment recreated successfully!"
echo ""
echo "Now you can run the server with:"
echo "  source venv/bin/activate"
echo "  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "Or use the startup script:"
echo "  ./run_local.sh"

