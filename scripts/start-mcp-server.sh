#!/bin/bash

# Rocket Reels AI MCP Server Startup Script

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Rocket Reels AI MCP Server${NC}"

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo -e "${RED}❌ Python is not installed or not in PATH${NC}"
    exit 1
fi

# Check if required dependencies are installed
echo -e "${YELLOW}📦 Checking dependencies...${NC}"

# Try to import required modules
python -c "
import sys
import os
sys.path.append('$PROJECT_ROOT')
sys.path.append('$PROJECT_ROOT/production-workflow')

try:
    import mcp.server
    import asyncio
    import langgraph
    print('✅ Core dependencies found')
except ImportError as e:
    print(f'❌ Missing dependency: {e}')
    sys.exit(1)
" || {
    echo -e "${RED}❌ Missing dependencies. Please run:${NC}"
    echo "  cd $PROJECT_ROOT"
    echo "  pip install -r requirements.txt"
    echo "  pip install -r production-workflow/requirements.txt"
    echo "  pip install -r mcp-servers/orchestrator/requirements.txt"
    exit 1
}

# Check for environment variables
echo -e "${YELLOW}🔑 Checking environment variables...${NC}"

# Load .env if it exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo -e "${GREEN}📄 Loading .env file${NC}"
    export $(cat "$PROJECT_ROOT/.env" | grep -v '^#' | xargs)
fi

# Check for required API keys
missing_keys=()

if [ -z "$ANTHROPIC_API_KEY" ]; then
    missing_keys+=("ANTHROPIC_API_KEY")
fi

if [ -z "$TAVILY_API_KEY" ]; then
    missing_keys+=("TAVILY_API_KEY")
fi

if [ -z "$SUPABASE_URL" ]; then
    missing_keys+=("SUPABASE_URL")
fi

if [ -z "$SUPABASE_ANON_KEY" ]; then
    missing_keys+=("SUPABASE_ANON_KEY")
fi

if [ ${#missing_keys[@]} -gt 0 ]; then
    echo -e "${RED}❌ Missing required environment variables:${NC}"
    for key in "${missing_keys[@]}"; do
        echo "  - $key"
    done
    echo -e "${YELLOW}💡 Create a .env file in the project root with these variables${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Environment variables found${NC}"

# Set Python path
export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/production-workflow:$PYTHONPATH"

# Change to MCP server directory
cd "$PROJECT_ROOT/mcp-servers/orchestrator"

echo -e "${GREEN}🎬 Starting MCP Server...${NC}"
echo -e "${YELLOW}📍 Server path: $PROJECT_ROOT/mcp-servers/orchestrator/server.py${NC}"
echo -e "${YELLOW}🔗 Add this path to your Claude Desktop MCP configuration${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

# Start the server
python server.py