# LangGraph Workflow Testing Guide

This guide explains how to test the Rocket Reels AI orchestration workflow using the new `langgraph.json` configuration.

## Prerequisites

1. Ensure all required API keys are set in your `.env` file:
   - `ANTHROPIC_API_KEY`
   - `LANGCHAIN_API_KEY` (for LangGraph Studio monitoring)
   - `SUPABASE_URL` and `SUPABASE_ANON_KEY`

2. Start all services using Docker Compose:
   ```bash
   docker-compose up -d
   ```

## Configuration Overview

The `langgraph.json` file configures:

- **Workflow Graph**: Defines nodes, edges, and state transitions
- **MCP Servers**: Connection details for each microservice
- **Test Inputs**: Pre-configured test scenarios
- **Monitoring**: Metrics and alerts configuration
- **Human Review**: Settings for approval process

## Testing Methods

### 1. Automated Test Suite

Run the comprehensive test suite:

```bash
python test_langgraph_workflow.py
```

This tests:
- MCP server connectivity
- Workflow initialization
- State persistence
- Error handling
- Simple workflow execution

### 2. Manual Testing with Test Script

Use the original test script with different modes:

```bash
# Test with prompt input
python test_workflow.py

# Test with YouTube URL
python test_workflow.py youtube

# Quick test with auto-approval
python test_workflow.py quick
```

### 3. API Testing

Start the orchestrator and test via API:

```bash
# In one terminal
cd orchestrator
python main.py

# In another terminal - test the API
curl -X POST http://localhost:8001/workflow/test
```

### 4. LangGraph Studio Testing

1. Open [LangGraph Studio](https://smith.langchain.com/projects)
2. Find your project: "rocket-reels-ai"
3. Monitor workflow execution in real-time
4. View token usage and costs

## Workflow Phases

The workflow consists of these phases, each with human review:

1. **Input Processing** → Extracts content from YouTube/files/prompts
2. **Research** → Finds trends and additional information
3. **Planning** → Creates content structure and visual suggestions
4. **Script Writing** → Generates optimized reel script
5. **Visual Generation** → Creates placeholders for visuals/thumbnails

## Human Review Interface

Access at: http://localhost:8000

Features:
- Real-time preview of each phase output
- Approve/Revise/Reject options
- Cost tracking per phase
- Feedback system for revisions

## Debugging Tips

### Check MCP Server Logs
```bash
# View logs for a specific service
docker-compose logs -f input
docker-compose logs -f research
docker-compose logs -f planner
docker-compose logs -f script
docker-compose logs -f visual
```

### Check Orchestrator Logs
```bash
docker-compose logs -f orchestrator
```

### Common Issues

1. **MCP servers not reachable**
   - Ensure Docker containers are running: `docker-compose ps`
   - Check port conflicts: 8081-8085 must be available

2. **Workflow fails at specific phase**
   - Check the specific MCP server logs
   - Verify API keys are correctly set
   - Check cost limits in configuration

3. **Human review not working**
   - Ensure port 8000 is accessible
   - Check orchestrator logs for WebSocket errors

## Environment Variables

Key variables that affect testing:

- `AUTO_APPROVE_REVIEWS=true` - Skip human review (for testing)
- `COST_LIMIT_PER_REEL=0.50` - Maximum cost per workflow
- `LANGCHAIN_TRACING_V2=true` - Enable LangGraph Studio monitoring

## Performance Benchmarks

Expected durations per phase:
- Input Processing: < 30 seconds
- Research: < 60 seconds  
- Planning: < 45 seconds
- Script Writing: < 45 seconds
- Visual Generation: < 120 seconds

Total workflow: < 5 minutes

## Next Steps

1. **Production Deployment**
   - Switch to SQLite/PostgreSQL checkpointer
   - Implement proper authentication
   - Set up monitoring alerts

2. **Integration Testing**
   - Test with real YouTube videos
   - Test file uploads
   - Test concurrent workflows

3. **Optimization**
   - Implement caching for research
   - Optimize MCP server response times
   - Add retry logic for failures