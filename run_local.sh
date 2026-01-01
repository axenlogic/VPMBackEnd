#!/bin/bash

# Local Development Server Startup Script
cd /Users/qatesting/Documents/VPMBackEnd

# Check if venv exists and is accessible
if [ ! -f "venv/bin/activate" ]; then
    echo "❌ Virtual environment not found!"
    echo "Run ./fix_venv.sh to recreate it"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if activation was successful
if [ "$VIRTUAL_ENV" = "" ]; then
    echo "❌ Failed to activate virtual environment!"
    echo "Try running: ./fix_venv.sh"
    exit 1
fi

echo "✅ Virtual environment activated"
echo "🚀 Starting server on http://localhost:8000"
echo "📚 API docs available at http://localhost:8000/docs"
echo ""

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

