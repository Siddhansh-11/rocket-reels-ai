# Rocket Reels Orchestrator MCP Server

This MCP server provides integration between Claude Desktop and the Rocket Reels AI content generation workflow.

## Features

- **Full Content Pipeline**: Complete workflow from topic to final video assets
- **Quick Generation**: Rapid search and script generation 
- **Viral Script Generation**: Transform articles into social media scripts
- **Workflow Management**: Track, monitor, and cancel running workflows
- **Real-time Status**: Get live updates on workflow progress

## Available Tools

### `trigger_content_workflow`
Start a complete content generation workflow.

**Parameters:**
- `topic` (required): Topic or article URL to create content about
- `workflow_type`: Type of workflow ("full_pipeline", "quick_generate", "search_and_script", "article_to_script")
- `platforms`: Target platforms (["youtube", "tiktok", "instagram", "all"])
- `style`: Content style ("educational", "entertaining", "viral", "professional")

### `get_workflow_status`
Get current status and progress of a running workflow.

**Parameters:**
- `workflow_id` (required): ID of the workflow to check

### `search_trending_topics`
Search for trending tech news and content ideas.

**Parameters:**
- `query` (required): Search query for trending topics
- `limit`: Number of results to return (1-10, default: 5)

### `generate_viral_scripts`
Generate viral social media scripts from an article URL.

**Parameters:**
- `article_url` (required): URL of article to generate scripts from
- `platforms`: Target platforms for script generation
- `tone`: Tone for scripts ("casual", "professional", "humorous", "urgent")

### `list_active_workflows`
List all currently active workflows and their status.

### `cancel_workflow`
Cancel a running workflow.

**Parameters:**
- `workflow_id` (required): ID of workflow to cancel

## Installation

1. Install dependencies:
```bash
cd mcp-servers/orchestrator
pip install -r requirements.txt
```

2. Install main project dependencies:
```bash
cd ../../
pip install -r requirements.txt
pip install -r production-workflow/requirements.txt
```

## Usage with Claude Desktop

Add to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "rocket-reels": {
      "command": "python",
      "args": ["/path/to/rocket-reels-ai/mcp-servers/orchestrator/server.py"],
      "env": {
        "ANTHROPIC_API_KEY": "your-key",
        "TAVILY_API_KEY": "your-key",
        "SUPABASE_URL": "your-url",
        "SUPABASE_ANON_KEY": "your-key"
      }
    }
  }
}
```

## Example Commands in Claude Desktop

- "Generate a viral reel about the latest AI news"
- "Create educational content about cryptocurrency trends"  
- "Turn this article into TikTok scripts: [URL]"
- "Search for trending tech stories this week"
- "Check status of workflow abc-123"

## Architecture

The server acts as a bridge between Claude Desktop and the Rocket Reels production workflow:

```
Claude Desktop → MCP Server → Production Workflow → LangGraph Agents
```

Each tool call triggers the appropriate workflow phase and returns real-time status updates.

## Development

To modify the server:

1. Edit `server.py` to add new tools or modify existing ones
2. Update the tool schemas in `handle_list_tools()`
3. Implement the actual tool logic in the corresponding async functions
4. Test using the MCP debugging tools

## Error Handling

The server includes comprehensive error handling and returns structured error responses with:
- Error message
- Tool name that failed
- Input arguments
- Timestamp

## Cost Tracking

All workflows include cost tracking for API usage across:
- Search APIs (Tavily)
- AI model calls (Anthropic, OpenAI, Mistral)
- Image generation
- Voice synthesis