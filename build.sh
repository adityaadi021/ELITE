#!/usr/bin/env bash
# Build script for Render deployment

echo "🚀 Starting build process..."

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo "✅ Build completed successfully!" 