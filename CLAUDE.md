# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Rocket Reels AI is an AI-powered video reel generation system that transforms trending tech news into 30-60 second educational videos. It uses Model Context Protocol (MCP) servers for modular functionality and LangGraph for workflow orchestration with human review checkpoints.

## Development Commands

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# For production workflow
cd production-workflow && pip install -r requirements.txt

# For MCP server
cd mcp-servers/orchestrator && pip install -r requirements.txt

# Configure environment
cp config/.env.template config/.env
# Edit config/.env with required API keys
```

### Running the Application
```bash
# Test basic workflow
python test_workflow.py
python test_workflow.py youtube  # Test with YouTube input
python test_workflow.py quick    # Quick test run

# Run production workflow
cd production-workflow
python scripts/run_workflow.py "your topic here"

# Test workflow structure
python scripts/test_workflow.py

# Test specific components
python scripts/test_workflow.py --component search
python scripts/test_workflow.py --component notion

# Monitor projects
python scripts/monitor_final_draft.py check-all
python scripts/monitor_final_draft.py monitor "ProjectName"
```

### MCP Server Operations
```bash
# Start MCP server for Claude Desktop integration
./scripts/start-mcp-server.sh

# Start MCP server manually
cd mcp-servers/orchestrator
python server.py

# Start WebSocket server for real-time updates
cd mcp-servers/orchestrator
python websocket_server.py

# Test MCP server
cd mcp-servers/orchestrator
python -c "import server; print('MCP server imports successfully')"
```

### Docker Operations
```bash
cd production-workflow
docker-compose up -d              # Start all services
docker-compose ps                 # Check service status
docker-compose logs -f [service]  # View logs
docker-compose restart [service]  # Restart specific service
```

### Testing
```bash
# Run pytest tests (when available)
pytest

# Test individual agents
python orchestrator/test_chat_agent.py
python orchestrator/test_image_generation.py
```

## Architecture

### Workflow Pipeline
The system follows a multi-phase workflow with human review checkpoints:

```
Search → Crawl → Store Article → Generate Script → Store Script
                                                       ↓
   Image Generation ← Prompt Generation ← Voice Generation (parallel)
           ↓                                    ↓
           └──── Asset Gathering ←──────────────┘
                       ↓
               Notion Integration
                       ↓
                   Finalize
```

### Key Components

1. **MCP Servers** (`/mcp-servers/`): Modular services for each pipeline phase
   - `input/`: Process YouTube transcripts and files
   - `research/`: Web search and trend analysis  
   - `planner/`: Content structure and visual suggestions
   - `script/`: Reel-optimized copywriting
   - `visual/`: Visual generation and scene planning

2. **Orchestrator** (`/orchestrator/`): Core workflow management
   - `langraph_workflow.py`: Main workflow definition
   - `human_review.py`: Human review interface (http://localhost:8000)
   - `workflow_state.py`: State management
   - `mcp_client.py`: MCP server communication

3. **Production Workflow** (`/production-workflow/`): Complete implementation
   - `agents/`: Individual agent implementations for each phase
   - `core/`: Core workflow logic and orchestration
   - `storage/`: Google Drive integration for asset organization
   - `scripts/`: Utility scripts for testing and monitoring

### External Service Integration

The project integrates with multiple services:
- **AI Models**: Anthropic (Claude), OpenAI, Mistral, Together AI
- **Voice**: ElevenLabs for voiceover generation
- **Search**: Tavily API for web research
- **Storage**: Google Drive for asset organization
- **Database**: Supabase for data persistence
- **Project Management**: Notion for team collaboration
- **Monitoring**: LangGraph Studio for workflow visualization

### State Management

The workflow uses a shared state structure (`WorkflowState`) that includes:
- Topic and search results
- Generated scripts and assets
- Human review feedback
- Cost tracking for API usage
- Project metadata and links

Each agent operates on this state and passes it forward with modifications.

### Human Review System

Human review is implemented at key checkpoints:
- Review interface runs on http://localhost:8000
- Supports feedback on scripts, images, and overall quality
- Feedback is incorporated into subsequent phases

### Asset Organization

The system automatically:
- Creates Google Drive folders for each project
- Organizes images, scripts, and voice files
- Generates project tracking entries in Notion
- Maintains cost tracking across all API calls

## Claude Desktop Integration

The project includes an MCP (Model Context Protocol) server that integrates with Claude Desktop, allowing you to trigger workflows directly from Claude conversations.

### Setup Claude Desktop Integration

1. **Install Dependencies**:
```bash
pip install -r mcp-servers/orchestrator/requirements.txt
```

2. **Configure Claude Desktop**:
Copy the configuration to your Claude Desktop config:
```bash
cp claude-desktop-config.json ~/.config/claude-desktop/config.json
```

3. **Update Configuration**:
Edit the config file with your actual project path and API keys:
```json
{
  "mcpServers": {
    "rocket-reels": {
      "command": "python",
      "args": ["/absolute/path/to/rocket-reels-ai/mcp-servers/orchestrator/server.py"],
      "env": {
        "ANTHROPIC_API_KEY": "your-key",
        "TAVILY_API_KEY": "your-key",
        ...
      }
    }
  }
}
```

4. **Restart Claude Desktop** and the MCP tools will be available.

### Usage in Claude Desktop

Once configured, you can use these commands in Claude Desktop:

- **"Generate a viral reel about AI breakthrough"** - Triggers full content pipeline
- **"Create scripts from this article: [URL]"** - Converts article to social media scripts  
- **"Search trending tech stories"** - Find latest trending topics
- **"Check status of workflow abc-123"** - Get workflow progress
- **"Show all active workflows"** - List running workflows

### Available MCP Tools

- `trigger_content_workflow`: Start complete content generation
- `get_workflow_status`: Check workflow progress  
- `search_trending_topics`: Find trending content ideas
- `generate_viral_scripts`: Create scripts from article URLs
- `list_active_workflows`: Show all active workflows
- `cancel_workflow`: Stop a running workflow

### Real-time Progress Updates

The MCP server includes a WebSocket server for real-time progress tracking:

```bash
# Start WebSocket server (runs on ws://localhost:8765)
cd mcp-servers/orchestrator
python websocket_server.py
```

Connect to:
- `ws://localhost:8765/all` - All workflow updates
- `ws://localhost:8765/workflow/{id}` - Specific workflow updates

## Environment Configuration

Required API keys in `config/.env`:
- `ANTHROPIC_API_KEY`: Claude AI
- `TAVILY_API_KEY`: Web search
- `OPENAI_API_KEY`: GPT models
- `MISTRAL_API_KEY`: Mistral models
- `SUPABASE_URL` & `SUPABASE_ANON_KEY`: Database
- `NOTION_API_KEY` & `NOTION_DATABASE_ID`: Project tracking
- `LANGCHAIN_API_KEY`: LangGraph Studio monitoring

Optional:
- `ELEVENLABS_API_KEY`: Voice generation
- `PEXELS_API_KEY`: Stock images
- `ARCADE_API_KEY`: Content distribution