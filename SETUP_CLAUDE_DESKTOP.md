# Claude Desktop MCP Integration Setup

This guide will help you connect the Rocket Reels AI workflow orchestration to Claude Desktop using the Model Context Protocol (MCP).

## Prerequisites

1. **Claude Desktop App**: Download and install from [Claude Desktop](https://claude.ai/download)
2. **Python Environment**: Python 3.8+ with all project dependencies installed
3. **API Keys**: All required API keys configured in your environment

## Installation Steps

### 1. Install Dependencies

```bash
# Install main project dependencies
cd rocket-reels-ai
pip install -r requirements.txt
pip install -r production-workflow/requirements.txt

# Install MCP server dependencies
cd mcp-servers/orchestrator
pip install -r requirements.txt
```

### 2. Configure API Keys

Create a `.env` file in the project root or ensure these environment variables are set:

```bash
# Required API Keys
ANTHROPIC_API_KEY=your-anthropic-api-key
TAVILY_API_KEY=your-tavily-api-key
OPENAI_API_KEY=your-openai-api-key
SUPABASE_URL=your-supabase-url
SUPABASE_ANON_KEY=your-supabase-anon-key

# Optional but recommended
MISTRAL_API_KEY=your-mistral-api-key
NOTION_API_KEY=your-notion-api-key
NOTION_DATABASE_ID=your-notion-database-id
LANGCHAIN_API_KEY=your-langchain-api-key
ELEVENLABS_API_KEY=your-elevenlabs-api-key
```

### 3. Test the MCP Server

Before configuring Claude Desktop, test that the MCP server works:

```bash
cd mcp-servers/orchestrator
python server.py
```

The server should start without errors. Press Ctrl+C to stop.

### 4. Configure Claude Desktop

#### Option A: Using the Configuration File (Recommended)

1. Copy the example configuration:
```bash
cp claude-desktop-config.json ~/.config/claude-desktop/config.json
```

2. Edit the configuration file:
```bash
nano ~/.config/claude-desktop/config.json
```

3. Update the absolute path to your project:
```json
{
  "mcpServers": {
    "rocket-reels": {
      "command": "python",
      "args": ["/full/path/to/your/rocket-reels-ai/mcp-servers/orchestrator/server.py"],
      "env": {
        "ANTHROPIC_API_KEY": "your-actual-api-key",
        "TAVILY_API_KEY": "your-actual-api-key",
        ...
      }
    }
  }
}
```

#### Option B: Manual Configuration

1. Open Claude Desktop settings (gear icon)
2. Navigate to "Advanced" → "MCP Servers"
3. Add a new server with these settings:
   - **Name**: `rocket-reels`
   - **Command**: `python`
   - **Arguments**: `["/full/path/to/rocket-reels-ai/mcp-servers/orchestrator/server.py"]`
   - **Environment Variables**: Add all your API keys

### 5. Restart Claude Desktop

Close and reopen Claude Desktop for the MCP server configuration to take effect.

### 6. Verify Integration

In a new Claude Desktop conversation, try these commands:

```
Check if rocket-reels MCP tools are available
```

You should see available tools like:
- `trigger_content_workflow`
- `get_workflow_status`
- `search_trending_topics`
- `generate_viral_scripts`
- `list_active_workflows`
- `cancel_workflow`

## Usage Examples

### Generate Content from a Topic

```
Generate a viral reel about "latest AI breakthrough in healthcare"
```

### Create Scripts from an Article

```
Create TikTok and Instagram scripts from this article: https://example.com/ai-news
```

### Search for Trending Topics

```
Find trending tech stories about cryptocurrency
```

### Check Workflow Status

```
Check the status of workflow abc-123-def
```

### Monitor Active Workflows

```
Show me all active content generation workflows
```

## Troubleshooting

### MCP Server Not Found

**Error**: `Server "rocket-reels" not found`

**Solutions**:
1. Check that the path in the config is absolute and correct
2. Verify Python can run the server script
3. Ensure all dependencies are installed
4. Restart Claude Desktop

### Import Errors

**Error**: `ModuleNotFoundError` when starting the server

**Solutions**:
1. Install missing dependencies: `pip install -r requirements.txt`
2. Check Python path includes the project directory
3. Verify the virtual environment is activated

### API Key Issues

**Error**: Authentication errors or "API key not found"

**Solutions**:
1. Verify API keys are correctly set in the environment variables
2. Check that keys have proper permissions
3. Ensure keys are not expired

### Server Startup Issues

**Error**: Server fails to start or crashes immediately

**Solutions**:
1. Test the server manually: `python mcp-servers/orchestrator/server.py`
2. Check the logs in Claude Desktop for error messages
3. Verify all import paths are correct

## Configuration Files Location

### macOS
```
~/.config/claude-desktop/config.json
```

### Windows
```
%APPDATA%/Claude/config.json
```

### Linux
```
~/.config/claude-desktop/config.json
```

## Advanced Configuration

### Custom Workflow Settings

You can modify the workflow behavior by editing `core/workflow_interface.py`:

- Adjust default timeouts
- Change cost limits
- Modify platform defaults
- Add custom workflow types

### Adding Progress Callbacks

To get real-time updates on workflow progress, you can add custom callbacks:

```python
from core.workflow_interface import workflow_manager

async def progress_callback(workflow, phase, current, total):
    print(f"Workflow {workflow.id}: {phase.name} ({current}/{total})")

# Add to a specific workflow
workflow.progress_callbacks.append(progress_callback)
```

### Environment-Specific Configurations

For different environments (development, staging, production), create separate config files:

```bash
# Development
~/.config/claude-desktop/config-dev.json

# Production
~/.config/claude-desktop/config-prod.json
```

## Security Considerations

1. **API Key Storage**: Never commit API keys to version control
2. **File Permissions**: Ensure config files have proper permissions (600)
3. **Network Access**: The MCP server runs locally and doesn't expose network ports
4. **Logging**: Sensitive information is not logged by default

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review the logs in Claude Desktop
3. Test the MCP server manually
4. Verify all dependencies and API keys are correct

## Next Steps

Once integrated, you can:

1. Create custom workflows for specific content types
2. Set up automated content generation schedules
3. Integrate with other tools and services
4. Build custom MCP tools for specific use cases