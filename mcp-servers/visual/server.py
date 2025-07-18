import asyncio
import json
import os
from typing import Dict, Any, List
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
from mcp.types import Tool, TextContent
from PIL import Image, ImageDraw, ImageFont
import io
import base64

# Initialize MCP server
server = Server("visual-generator")

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available visual generation tools"""
    return [
        Tool(
            name="generate_visuals",
            description="Generate placeholder visuals for script sections",
            inputSchema={
                "type": "object",
                "properties": {
                    "script": {
                        "type": "object",
                        "description": "Script with visual cues"
                    },
                    "visual_plan": {
                        "type": "object",
                        "description": "Visual suggestions from planner"
                    }
                },
                "required": ["script"]
            }
        ),
        Tool(
            name="create_thumbnail",
            description="Create thumbnail for the reel",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Title for thumbnail"
                    },
                    "style": {
                        "type": "string",
                        "description": "Thumbnail style",
                        "enum": ["bold", "minimal", "colorful"],
                        "default": "bold"
                    }
                },
                "required": ["title"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list:
    """Handle tool execution"""
    
    if name == "generate_visuals":
        visual_plan = arguments.get("visual_plan", {})
        result = await generate_visuals(arguments["script"], visual_plan)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "create_thumbnail":
        style = arguments.get("style", "bold")
        result = await create_thumbnail(arguments["title"], style)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    else:
        raise ValueError(f"Unknown tool: {name}")

async def generate_visuals(script: Dict[str, Any], visual_plan: Dict[str, Any]) -> Dict[str, Any]:
    """Generate placeholder visuals for script sections"""
    
    # Extract visual cues from script
    visual_cues = script.get("visual_cues", [])
    
    # In production, this would call Google Cloud Imagen or other services
    # For now, return placeholder information
    visuals = []
    
    for i, cue in enumerate(visual_cues):
        visual = {
            "index": i,
            "cue": cue,
            "type": "placeholder",
            "description": f"Placeholder for: {cue}",
            "duration": 3.0,  # seconds
            "transition": "fade",
            "status": "pending_generation"
        }
        visuals.append(visual)
    
    # Add default visuals if none specified
    if not visuals:
        visuals = [
            {
                "index": 0,
                "type": "title_card",
                "description": "Opening title card",
                "duration": 3.0,
                "transition": "fade_in"
            },
            {
                "index": 1,
                "type": "content",
                "description": "Main content visuals",
                "duration": 40.0,
                "transition": "cut"
            },
            {
                "index": 2,
                "type": "cta_card",
                "description": "Call-to-action card",
                "duration": 5.0,
                "transition": "fade_out"
            }
        ]
    
    return {
        "visuals": visuals,
        "total_visual_duration": sum(v["duration"] for v in visuals),
        "visual_count": len(visuals),
        "generation_status": "placeholder",
        "notes": "This is a placeholder. In production, would use Google Cloud Imagen/Veo"
    }

async def create_thumbnail(title: str, style: str = "bold") -> Dict[str, Any]:
    """Create a simple placeholder thumbnail"""
    
    # Create a simple image with PIL
    width, height = 1080, 1920  # 9:16 aspect ratio
    
    # Style configurations
    styles = {
        "bold": {"bg_color": (255, 0, 0), "text_color": (255, 255, 255)},
        "minimal": {"bg_color": (240, 240, 240), "text_color": (50, 50, 50)},
        "colorful": {"bg_color": (100, 200, 255), "text_color": (255, 255, 0)}
    }
    
    style_config = styles.get(style, styles["bold"])
    
    # Create image
    img = Image.new('RGB', (width, height), color=style_config["bg_color"])
    draw = ImageDraw.Draw(img)
    
    # Add text (using default font for simplicity)
    # In production, would use custom fonts
    text_bbox = draw.textbbox((0, 0), title)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    
    draw.text((x, y), title, fill=style_config["text_color"])
    
    # Convert to base64 for transport
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    return {
        "thumbnail": {
            "title": title,
            "style": style,
            "dimensions": f"{width}x{height}",
            "format": "png",
            "base64_preview": img_base64[:100] + "...",  # Truncated for response
            "status": "generated"
        },
        "alternatives": [
            {"style": s, "available": True} for s in styles.keys() if s != style
        ]
    }

async def main():
    """Run the MCP server"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="visual-generator",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())