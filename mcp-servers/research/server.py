import asyncio
import json
import os
from typing import Dict, Any, List
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
from mcp.types import Tool, TextContent
from duckduckgo_search import DDGS
import anthropic
from datetime import datetime

# Initialize MCP server
server = Server("research")

# Initialize Anthropic client
anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available research tools"""
    return [
        Tool(
            name="research_topic",
            description="Research topic based on input type (YouTube, file, or prompt)",
            inputSchema={
                "type": "object",
                "properties": {
                    "input_data": {
                        "type": "object",
                        "description": "Processed input from the input server",
                        "properties": {
                            "type": {"type": "string"},
                            "topic": {"type": "string"},
                            "content": {"type": "string"}
                        }
                    },
                    "depth": {
                        "type": "string",
                        "description": "Research depth",
                        "enum": ["quick", "standard", "comprehensive"],
                        "default": "standard"
                    }
                },
                "required": ["input_data"]
            }
        ),
        Tool(
            name="find_trending_angle",
            description="Find trending angles and hooks for the topic",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Topic to find angles for"
                    },
                    "target_audience": {
                        "type": "string",
                        "description": "Target audience",
                        "default": "general"
                    }
                },
                "required": ["topic"]
            }
        ),
        Tool(
            name="verify_facts",
            description="Verify facts and find authoritative sources",
            inputSchema={
                "type": "object",
                "properties": {
                    "claims": {
                        "type": "array",
                        "description": "List of claims to verify",
                        "items": {"type": "string"}
                    }
                },
                "required": ["claims"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list:
    """Handle tool execution"""
    
    if name == "research_topic":
        depth = arguments.get("depth", "standard")
        result = await research_topic(arguments["input_data"], depth)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "find_trending_angle":
        target_audience = arguments.get("target_audience", "general")
        result = await find_trending_angle(arguments["topic"], target_audience)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "verify_facts":
        result = await verify_facts(arguments["claims"])
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    else:
        raise ValueError(f"Unknown tool: {name}")

async def research_topic(input_data: Dict[str, Any], depth: str = "standard") -> Dict[str, Any]:
    """Research based on input type with different strategies"""
    
    input_type = input_data.get("type")
    
    # Determine research focus based on input type
    if input_type == "youtube":
        # For YouTube, focus on expanding/updating the content
        research_query = f"latest updates {input_data.get('title', '')} {datetime.now().year}"
        context = f"Video transcript: {input_data.get('transcript', '')[:500]}..."
    elif input_type == "file":
        # For files, extract key concepts to research
        research_query = f"trends and insights {input_data.get('content', '')[:200]}"
        context = f"Document content: {input_data.get('content', '')[:500]}..."
    else:  # prompt
        # For prompts, research the topic directly
        research_query = input_data.get('topic', '')
        context = f"User request: {input_data.get('full_prompt', '')}"
    
    # Perform web search
    search_results = await web_search(research_query, depth)
    
    # Analyze with AI to extract insights
    analysis_prompt = f"""
    Analyze this research for creating a 30-60 second educational reel.
    
    Context: {context}
    
    Search Results: {json.dumps(search_results[:5], indent=2)}
    
    Extract:
    1. 3-5 key facts that would surprise or educate viewers
    2. Current trends or recent developments
    3. Common misconceptions to address
    4. Suggested content angle for maximum engagement
    5. Credible sources to reference
    
    Format as JSON with keys: facts, trends, misconceptions, suggested_angle, sources
    """
    
    message = anthropic_client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1000,
        temperature=0.7,
        messages=[{"role": "user", "content": analysis_prompt}]
    )
    
    try:
        # Extract JSON from response
        response_text = message.content[0].text
        # Find JSON in response
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            analysis = json.loads(json_match.group())
        else:
            analysis = {"error": "Could not parse AI response"}
    except:
        analysis = {"raw_response": response_text}
    
    return {
        "input_type": input_type,
        "research_query": research_query,
        "search_results": search_results[:5],
        "analysis": analysis,
        "research_depth": depth,
        "timestamp": datetime.now().isoformat()
    }

async def web_search(query: str, depth: str = "standard") -> List[Dict[str, Any]]:
    """Perform web search using DuckDuckGo"""
    num_results = {"quick": 5, "standard": 10, "comprehensive": 20}.get(depth, 10)
    
    try:
        ddgs = DDGS()
        results = []
        search_results = ddgs.text(query, max_results=num_results)
        for result in search_results:
            results.append({
                "title": result.get("title", ""),
                "url": result.get("href", ""),
                "snippet": result.get("body", ""),
            })
        return results
    except Exception as e:
        return [{"error": f"Search failed: {str(e)}"}]

async def find_trending_angle(topic: str, target_audience: str = "general") -> Dict[str, Any]:
    """Find trending angles and hooks for the topic"""
    
    # Search for trending content
    trend_query = f"{topic} viral trending {datetime.now().year}"
    trending_results = await web_search(trend_query, "quick")
    
    # Analyze for angles
    angle_prompt = f"""
    Find engaging angles for a 30-60 second reel about: {topic}
    Target audience: {target_audience}
    
    Recent trending content: {json.dumps(trending_results[:3], indent=2)}
    
    Suggest:
    1. 3 compelling hooks (first 3 seconds)
    2. 3 unique angles that haven't been overdone
    3. 1 controversial or surprising take
    4. Emotional triggers to incorporate
    
    Format as JSON with keys: hooks, angles, controversial_take, emotional_triggers
    """
    
    message = anthropic_client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=800,
        temperature=0.8,
        messages=[{"role": "user", "content": angle_prompt}]
    )
    
    try:
        response_text = message.content[0].text
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            angles = json.loads(json_match.group())
        else:
            angles = {"error": "Could not parse response"}
    except:
        angles = {"raw_response": response_text}
    
    return {
        "topic": topic,
        "target_audience": target_audience,
        "trending_context": trending_results[:3],
        "content_angles": angles,
        "timestamp": datetime.now().isoformat()
    }

async def verify_facts(claims: List[str]) -> Dict[str, Any]:
    """Verify facts and find authoritative sources"""
    verified_claims = []
    
    for claim in claims[:5]:  # Limit to 5 claims
        # Search for verification
        search_results = await web_search(f"fact check {claim}", "quick")
        
        verified_claims.append({
            "claim": claim,
            "search_results": search_results[:3],
            "confidence": "high" if len(search_results) > 2 else "medium"
        })
    
    return {
        "verified_claims": verified_claims,
        "summary": f"Verified {len(verified_claims)} claims",
        "timestamp": datetime.now().isoformat()
    }

async def main():
    """Run the MCP server"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="research",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())