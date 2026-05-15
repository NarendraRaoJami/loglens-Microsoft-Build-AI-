#!/bin/bash
set -e

echo "🔍 LogLens — AI Log & Email Intelligence"
echo "========================================="

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt --break-system-packages -q

# Check API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "⚠️  WARNING: ANTHROPIC_API_KEY not set. Please export it before running."
  echo "   export ANTHROPIC_API_KEY=your-key-here"
  exit 1
fi

echo "✅ Ready! Starting server on http://localhost:8000"
cd backend && uvicorn main:main --host 0.0.0.0 --port 8000 --reload
