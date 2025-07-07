import asyncio
import json
import os
import sys
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
from mcp.types import Tool, TextContent

# Import unified workflow interface
from core.workflow_interface import (
    workflow_manager, 
    WorkflowConfig, 
    WorkflowType, 
    trigger_workflow,
    search_trending_topics as search_trending,
    generate_scripts_from_url
)

# Initialize MCP server
server = Server("rocket-reels-orchestrator")

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available orchestration tools"""
    return [
        Tool(
            name="trigger_content_workflow",
            description="Start a complete content generation workflow from topic to final assets",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The topic or article URL to create content about"
                    },
                    "workflow_type": {
                        "type": "string",
                        "description": "Type of workflow to run",
                        "enum": ["full_pipeline", "quick_generate", "search_and_script", "article_to_script"],
                        "default": "full_pipeline"
                    },
                    "platforms": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["youtube", "tiktok", "instagram", "all"]},
                        "description": "Target platforms for content generation",
                        "default": ["all"]
                    },
                    "style": {
                        "type": "string",
                        "description": "Content style preference",
                        "enum": ["educational", "entertaining", "viral", "professional"],
                        "default": "educational"
                    }
                },
                "required": ["topic"]
            }
        ),
        Tool(
            name="get_workflow_status",
            description="Get the current status and progress of a running workflow",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {
                        "type": "string",
                        "description": "ID of the workflow to check status for"
                    }
                },
                "required": ["workflow_id"]
            }
        ),
        Tool(
            name="search_trending_topics",
            description="Search for trending tech news and content ideas",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for trending topics"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results to return",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 10
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="generate_viral_scripts",
            description="Generate viral social media scripts from an article URL",
            inputSchema={
                "type": "object",
                "properties": {
                    "article_url": {
                        "type": "string",
                        "description": "URL of the article to generate scripts from"
                    },
                    "platforms": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["youtube", "tiktok", "instagram", "all"]},
                        "description": "Target platforms for script generation",
                        "default": ["all"]
                    },
                    "tone": {
                        "type": "string",
                        "description": "Tone for the scripts",
                        "enum": ["casual", "professional", "humorous", "urgent"],
                        "default": "casual"
                    }
                },
                "required": ["article_url"]
            }
        ),
        Tool(
            name="list_active_workflows",
            description="List all currently active workflows and their status",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": false
            }
        ),
        Tool(
            name="cancel_workflow",
            description="Cancel a running workflow",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {
                        "type": "string",
                        "description": "ID of the workflow to cancel"
                    }
                },
                "required": ["workflow_id"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list:
    """Handle tool execution"""
    
    try:
        if name == "trigger_content_workflow":
            result = await trigger_content_workflow(
                topic=arguments["topic"],
                workflow_type=arguments.get("workflow_type", "full_pipeline"),
                platforms=arguments.get("platforms", ["all"]),
                style=arguments.get("style", "educational")
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "get_workflow_status":
            result = await get_workflow_status(arguments["workflow_id"])
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "search_trending_topics":
            result = await search_trending_topics(
                query=arguments["query"],
                limit=arguments.get("limit", 5)
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "generate_viral_scripts":
            result = await generate_viral_scripts(
                article_url=arguments["article_url"],
                platforms=arguments.get("platforms", ["all"]),
                tone=arguments.get("tone", "casual")
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "list_active_workflows":
            result = await list_active_workflows()
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "cancel_workflow":
            result = await cancel_workflow(arguments["workflow_id"])
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    except Exception as e:
        error_result = {
            "error": str(e),
            "tool": name,
            "arguments": arguments,
            "timestamp": datetime.now().isoformat()
        }
        return [TextContent(type="text", text=json.dumps(error_result, indent=2))]

async def trigger_content_workflow(
    topic: str, 
    workflow_type: str = "full_pipeline",
    platforms: List[str] = ["all"],
    style: str = "educational"
) -> Dict[str, Any]:
    """Trigger a content generation workflow using the unified interface"""
    
    try:
        # Create workflow configuration
        config = WorkflowConfig(
            topic=topic,
            workflow_type=WorkflowType(workflow_type),
            platforms=platforms,
            style=style
        )
        
        # Create and start workflow
        workflow_id = await workflow_manager.create_workflow(config)
        
        # Execute workflow in background
        asyncio.create_task(workflow_manager.execute_workflow(workflow_id))
        
        return {
            "success": True,
            "workflow_id": workflow_id,
            "status": "starting",
            "topic": topic,
            "workflow_type": workflow_type,
            "platforms": platforms,
            "style": style,
            "message": "Workflow started successfully. Use get_workflow_status to check progress."
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "topic": topic,
            "workflow_type": workflow_type
        }


async def get_workflow_status(workflow_id: str) -> Dict[str, Any]:
    """Get the status of a specific workflow"""
    
    status = workflow_manager.get_workflow_status(workflow_id)
    
    if status is None:
        return {
            "error": f"Workflow {workflow_id} not found",
            "workflow_id": workflow_id
        }
    
    return status

async def search_trending_topics(query: str, limit: int = 5) -> Dict[str, Any]:
    """Search for trending topics using the unified interface"""
    
    try:
        return await search_trending(query, limit)
    except Exception as e:
        return {
            "query": query,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

async def generate_viral_scripts(article_url: str, platforms: List[str], tone: str) -> Dict[str, Any]:
    """Generate viral scripts from article URL using the unified interface"""
    
    try:
        return await generate_scripts_from_url(article_url, platforms, tone)
    except Exception as e:
        return {
            "article_url": article_url,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

async def list_active_workflows() -> Dict[str, Any]:
    """List all active workflows using the unified interface"""
    
    workflows_data = workflow_manager.list_workflows()
    workflows_data["timestamp"] = datetime.now().isoformat()
    
    return workflows_data

async def cancel_workflow(workflow_id: str) -> Dict[str, Any]:
    """Cancel a running workflow using the unified interface"""
    
    success = await workflow_manager.cancel_workflow(workflow_id)
    
    if not success:
        # Get status to determine why cancellation failed
        status = workflow_manager.get_workflow_status(workflow_id)
        if status is None:
            return {
                "error": f"Workflow {workflow_id} not found",
                "workflow_id": workflow_id
            }
        else:
            return {
                "error": f"Cannot cancel workflow {workflow_id} with status: {status['status']}",
                "workflow_id": workflow_id,
                "current_status": status["status"]
            }
    
    return {
        "success": True,
        "workflow_id": workflow_id,
        "status": "cancelled",
        "cancelled_at": datetime.now().isoformat()
    }

async def main():
    """Run the MCP server"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="rocket-reels-orchestrator",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())