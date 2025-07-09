import asyncio
import json
import os
from typing import Dict, Any, List
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
from mcp.types import Tool, TextContent
import anthropic

# Initialize MCP server
server = Server("content-planner")

# Initialize Anthropic client
anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Content planning templates
CONTENT_STRUCTURES = {
    "educational": {
        "components": ["hook", "problem_statement", "key_points", "example", "takeaway", "cta"],
        "flow": "Curiosity → Education → Application"
    },
    "entertainment": {
        "components": ["hook", "setup", "twist", "payoff", "cta"],
        "flow": "Attention → Surprise → Satisfaction"
    },
    "motivational": {
        "components": ["hook", "relatability", "challenge", "solution", "empowerment", "cta"],
        "flow": "Connection → Inspiration → Action"
    },
    "tutorial": {
        "components": ["hook", "overview", "steps", "result", "cta"],
        "flow": "Promise → Process → Outcome"
    }
}

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available planning tools"""
    return [
        Tool(
            name="create_content_plan",
            description="Create detailed content structure based on research",
            inputSchema={
                "type": "object",
                "properties": {
                    "research": {
                        "type": "object",
                        "description": "Research data from research server",
                        "properties": {
                            "analysis": {"type": "object"},
                            "input_type": {"type": "string"}
                        }
                    },
                    "content_type": {
                        "type": "string",
                        "description": "Type of content structure",
                        "enum": ["educational", "entertainment", "motivational", "tutorial"],
                        "default": "educational"
                    },
                    "duration": {
                        "type": "integer",
                        "description": "Target duration in seconds",
                        "default": 45
                    }
                },
                "required": ["research"]
            }
        ),
        Tool(
            name="generate_visual_suggestions",
            description="Generate visual suggestions for each content section",
            inputSchema={
                "type": "object",
                "properties": {
                    "content_plan": {
                        "type": "object",
                        "description": "Content plan to visualize"
                    }
                },
                "required": ["content_plan"]
            }
        ),
        Tool(
            name="optimize_for_platform",
            description="Optimize content plan for specific platform",
            inputSchema={
                "type": "object",
                "properties": {
                    "content_plan": {
                        "type": "object",
                        "description": "Content plan to optimize"
                    },
                    "platform": {
                        "type": "string",
                        "description": "Target platform",
                        "enum": ["instagram", "tiktok", "youtube_shorts"],
                        "default": "instagram"
                    }
                },
                "required": ["content_plan"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list:
    """Handle tool execution"""
    
    if name == "create_content_plan":
        content_type = arguments.get("content_type", "educational")
        duration = arguments.get("duration", 45)
        result = await create_content_plan(arguments["research"], content_type, duration)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "generate_visual_suggestions":
        result = await generate_visual_suggestions(arguments["content_plan"])
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "optimize_for_platform":
        platform = arguments.get("platform", "instagram")
        result = await optimize_for_platform(arguments["content_plan"], platform)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    else:
        raise ValueError(f"Unknown tool: {name}")

async def create_content_plan(research: Dict[str, Any], content_type: str, duration: int) -> Dict[str, Any]:
    """Create detailed content structure based on research"""
    
    structure = CONTENT_STRUCTURES.get(content_type, CONTENT_STRUCTURES["educational"])
    analysis = research.get("analysis", {})
    
    prompt = f"""
    Create a detailed content plan for a {duration}-second {content_type} reel.
    
    Research insights:
    - Key facts: {json.dumps(analysis.get('facts', []))}
    - Trends: {json.dumps(analysis.get('trends', []))}
    - Suggested angle: {analysis.get('suggested_angle', '')}
    
    Content structure: {structure['components']}
    Flow: {structure['flow']}
    
    For each component, provide:
    1. Content text/idea
    2. Duration in seconds
    3. Emotional tone
    4. Key message
    
    Ensure the hook is irresistible and the CTA is specific.
    Format as JSON with these exact keys: hook, main_points, cta, visual_suggestions, pacing
    """
    
    message = anthropic_client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=1000,
        temperature=0.7,
        messages=[{"role": "user", "content": prompt}]
    )
    
    try:
        response_text = message.content[0].text
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            plan = json.loads(json_match.group())
        else:
            plan = {"error": "Could not parse response"}
    except:
        plan = {"raw_response": response_text}
    
    # Add metadata
    plan.update({
        "content_type": content_type,
        "target_duration": duration,
        "structure_used": structure,
        "research_input_type": research.get("input_type", "unknown")
    })
    
    return plan

async def generate_visual_suggestions(content_plan: Dict[str, Any]) -> Dict[str, Any]:
    """Generate visual suggestions for each content section"""
    
    prompt = f"""
    Generate specific visual suggestions for this reel content plan:
    
    {json.dumps(content_plan, indent=2)}
    
    For each section/point, suggest:
    1. Visual type (text overlay, b-roll, animation, transition)
    2. Specific imagery or footage needed
    3. Text formatting (font style, animation)
    4. Color scheme/mood
    5. Any special effects or filters
    
    Consider platform best practices for short-form video.
    Make visuals support the message without overwhelming.
    
    Format as JSON with sections matching the content plan structure.
    """
    
    message = anthropic_client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1000,
        temperature=0.8,
        messages=[{"role": "user", "content": prompt}]
    )
    
    try:
        response_text = message.content[0].text
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            visuals = json.loads(json_match.group())
        else:
            visuals = {"error": "Could not parse response"}
    except:
        visuals = {"raw_response": response_text}
    
    return {
        "content_plan": content_plan,
        "visual_suggestions": visuals,
        "estimated_scene_count": len(content_plan.get("main_points", [])) + 3  # hook, cta, transitions
    }

async def optimize_for_platform(content_plan: Dict[str, Any], platform: str) -> Dict[str, Any]:
    """Optimize content plan for specific platform"""
    
    platform_specs = {
        "instagram": {
            "aspect_ratio": "9:16",
            "max_duration": 60,
            "best_practices": [
                "Strong visual hook in first 1 second",
                "Captions always on",
                "Sound-off optimization",
                "Square or vertical format",
                "Use of trending audio"
            ]
        },
        "tiktok": {
            "aspect_ratio": "9:16",
            "max_duration": 60,
            "best_practices": [
                "Native feel, less polished",
                "Trending sounds crucial",
                "Quick cuts and transitions",
                "Comment-bait endings",
                "Duet/stitch friendly"
            ]
        },
        "youtube_shorts": {
            "aspect_ratio": "9:16",
            "max_duration": 60,
            "best_practices": [
                "YouTube-style thumbnails",
                "Clear value proposition",
                "Subscribe reminders",
                "End screen elements",
                "Playlist friendly"
            ]
        }
    }
    
    specs = platform_specs.get(platform, platform_specs["instagram"])
    
    optimizations = {
        "platform": platform,
        "specifications": specs,
        "content_adjustments": [],
        "technical_requirements": {
            "aspect_ratio": specs["aspect_ratio"],
            "max_duration": specs["max_duration"],
            "resolution": "1080x1920",
            "fps": 30
        }
    }
    
    # Platform-specific adjustments
    if platform == "tiktok":
        optimizations["content_adjustments"].append("Add trending sound suggestion")
        optimizations["content_adjustments"].append("Make hook more casual/relatable")
    elif platform == "youtube_shorts":
        optimizations["content_adjustments"].append("Add subscribe reminder in CTA")
        optimizations["content_adjustments"].append("Include searchable keywords")
    
    # Check duration compliance
    if content_plan.get("target_duration", 60) > specs["max_duration"]:
        optimizations["content_adjustments"].append(f"Reduce duration to {specs['max_duration']}s")
    
    return {
        "original_plan": content_plan,
        "platform_optimizations": optimizations,
        "best_practices_checklist": specs["best_practices"]
    }

async def main():
    """Run the MCP server"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="content-planner",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())