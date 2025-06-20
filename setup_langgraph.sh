#!/bin/bash

echo "🚀 Setting up LangGraph environment for Rocket Reels AI"
echo "======================================================="

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows
    source .venv/Scripts/activate
else
    # Linux/Mac
    source .venv/bin/activate
fi

# Upgrade pip
echo "Upgrading pip..."
python -m pip install --upgrade pip

# Install requirements
echo "Installing requirements..."
pip install -r requirements.txt

# Install orchestrator as a package
echo "Installing orchestrator module..."
pip install -e ./orchestrator

# Test import
echo "Testing LangGraph import..."
python test_graph_import.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "To run LangGraph dev server:"
echo "  langgraph dev --config langgraph_minimal.json"
echo ""
echo "Or with the full config:"
echo "  langgraph dev"