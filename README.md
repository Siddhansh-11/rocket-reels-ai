# AI Reel Factory with MCP Architecture

An AI-powered video reel generation system built with Model Context Protocol (MCP) servers. The system generates 30-60 second educational videos with human review at each phase and full workflow tracing in LangGraph Studio.

## 🏗️ Architecture

- **MCP Servers**: Modular services for each pipeline phase
- **Docker**: Containerized deployment
- **LangGraph**: Orchestration with human checkpoints
- **Human Review**: Web interface for approving each phase
- **External APIs**: Anthropic (AI), ElevenLabs (voice), Arcade (distribution)

## 🚀 Quick Start

### Prerequisites
- Docker Desktop
- Python 3.11+
- Required API Keys:
  - `ANTHROPIC_API_KEY` - For content generation
  - `ELEVENLABS_API_KEY` - For voice synthesis (optional)
  - `LANGCHAIN_API_KEY` - For LangGraph Studio monitoring
  - `ARCADE_API_KEY` - For social media distribution (optional)

### Setup

1. **Clone and configure**
   ```bash
   cd ai-reel-factory-mcp
   
   # Copy environment template
   cp config/.env.template config/.env
   
   # Edit .env with your API keys
   nano config/.env
   ```

2. **Start services**
   ```bash
   # Use the quick start script
   ./start.sh
   
   # Or manually with docker-compose
   docker-compose up -d
   ```

3. **Test the workflow**
   ```bash
   # Test with a prompt
   python test_workflow.py
   
   # Test with YouTube URL
   python test_workflow.py youtube
   
   # Quick test (auto-approve)
   python test_workflow.py quick
   ```

## 🎯 Usage Examples

### Generate from Prompt
```python
# Start workflow with prompt
curl -X POST http://localhost:8001/workflow/start \
  -H "Content-Type: application/json" \
  -d '{
    "input_type": "prompt",
    "input_data": {
      "prompt": "5 ChatGPT tips for developers",
      "style": "educational"
    }
  }'
```

### Generate from YouTube
```python
# Transform YouTube video into reel
curl -X POST http://localhost:8001/workflow/start \
  -H "Content-Type: application/json" \
  -d '{
    "input_type": "youtube",
    "input_data": {
      "url": "https://youtube.com/watch?v=..."
    }
  }'
```

## 📊 Monitoring & Review

### Human Review Interface
- **URL**: http://localhost:8000
- **Purpose**: Approve/revise each phase of generation
- **Features**: 
  - Real-time preview of content
  - Cost tracking
  - Feedback system
  - Revision requests

### LangGraph Studio
- **URL**: https://smith.langchain.com/projects
- **Features**:
  - Complete workflow visualization
  - Token usage tracking
  - Performance metrics
  - Error debugging

## 🔧 Architecture Details

### MCP Servers
1. **Input Processor** (Port 8081)
   - YouTube transcript extraction
   - File processing (PDF, DOCX, TXT)
   - Prompt structuring

2. **Research** (Port 8082)
   - Web search using DuckDuckGo
   - Trend analysis
   - Fact verification

3. **Content Planner** (Port 8083)
   - Structure creation
   - Visual suggestions
   - Platform optimization

4. **Script Writer** (Port 8084)
   - Reel-optimized copywriting
   - Hook generation
   - CTA optimization

5. **Visual Generator** (Port 8085)
   - Placeholder generation (ready for Imagen/Veo integration)
   - Thumbnail creation
   - Scene planning

### Workflow Phases
Each phase includes:
- Automated processing
- Quality validation
- Human review checkpoint
- Cost tracking
- Error recovery

## 🛠️ Development

### Adding New MCP Servers
1. Create server directory: `mcp-servers/your-server/`
2. Implement MCP protocol in `server.py`
3. Add Dockerfile
4. Update docker-compose.yml
5. Register in orchestrator

### Customizing Workflow
- Edit `orchestrator/langraph_workflow.py`
- Modify review interface in `orchestrator/human_review.py`
- Adjust cost limits in `.env`

## 📁 Project Structure

```
ai-reel-factory-mcp/
├── mcp-servers/
│   ├── input/           # Input processing
│   ├── research/        # Content research
│   ├── planner/         # Content planning
│   ├── script/          # Script writing
│   └── visual/          # Visual generation
├── orchestrator/
│   ├── langraph_workflow.py  # Main workflow
│   ├── human_review.py       # Review interface
│   ├── workflow_state.py     # State management
│   └── mcp_client.py         # MCP communication
├── config/
│   └── .env.template    # Environment template
├── outputs/             # Generated content
├── docker-compose.yml   # Service orchestration
├── start.sh            # Quick start script
└── test_workflow.py    # Test scripts
```

## 🚨 Troubleshooting

### Services not starting
```bash
# Check Docker status
docker-compose ps

# View logs
docker-compose logs -f [service-name]

# Restart specific service
docker-compose restart [service-name]
```

### API Key issues
- Ensure all required keys are in `.env`
- Check key formatting (no quotes needed)
- Verify API quotas and limits

### Human review not loading
- Check port 8000 is available
- Ensure orchestrator service is running
- Try accessing directly: http://localhost:8000

## 🔒 Security Notes

- Never commit `.env` file
- Use Docker secrets in production
- Implement rate limiting for APIs
- Add authentication to review interface

## 🚀 Next Steps

1. **Production Deployment**
   - Use Kubernetes for scaling
   - Add Redis for caching
   - Implement proper MCP server communication
   - Add Supabase for persistence

2. **Feature Additions**
   - Real video generation (Veo API)
   - Voice cloning options
   - A/B testing system
   - Analytics dashboard

3. **Integrations**
   - Connect Arcade for publishing
   - Add more visual generation services
   - Implement feedback loop from analytics