#!/bin/bash
# Rocket Reels AI - Quick Start Script

echo "🚀 Rocket Reels AI - Starting Services"
echo "======================================"

# Check if .env exists
if [ ! -f "config/.env" ]; then
    echo "⚠️  No .env file found. Copying template..."
    cp config/.env.template config/.env
    echo "📝 Please edit config/.env with your API keys before continuing."
    echo "   Required keys:"
    echo "   - ANTHROPIC_API_KEY"
    echo "   - ELEVENLABS_API_KEY"
    echo "   - SUPABASE_URL and SUPABASE_KEY"
    echo "   - LANGCHAIN_API_KEY (for LangGraph Studio)"
    exit 1
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker Desktop first."
    exit 1
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Build and start services
echo "🔨 Building Docker images..."
docker-compose build

echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🏥 Checking service health..."
docker-compose ps

echo ""
echo "✅ Rocket Reels AI is running!"
echo ""
echo "🌐 Access points:"
echo "   - Human Review Interface: http://localhost:8000"
echo "   - API Endpoints: http://localhost:8001"
echo "   - LangGraph Studio: https://smith.langchain.com/projects"
echo ""
echo "📝 To test the workflow:"
echo "   python test_workflow.py"
echo ""
echo "🛑 To stop services:"
echo "   docker-compose down"
echo ""