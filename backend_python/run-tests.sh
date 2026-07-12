#!/bin/bash
set -e

echo "🧪 Running all tests before deployment..."

echo "📍 Testing Python backend..."
cd backend_python

# Use standard Python packaging (setuptools)
python -m venv venv
source venv/bin/activate
pip install -e .
pip install -r requirements.txt
pip install pytest pytest-asyncio email-validator  # Install pytest in venv
python -m pytest tests/ --verbose  # Use python -m pytest to be safe

deactivate
cd ..
echo "✅ Python backend tests passed!"