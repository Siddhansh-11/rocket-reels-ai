import asyncio
import json
import os
from typing import Dict, Any, Optional
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
from mcp.types import Tool, TextContent
import yt_dlp
import aiofiles
from pathlib import Path

# Initialize MCP server
server = Server("input-processor")

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available tools for input processing"""
    return [
        Tool(
            name="process_youtube",
            description="Extract transcript and metadata from YouTube video",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "YouTube video URL"
                    }
                },
                "required": ["url"]
            }
        ),
        Tool(
            name="process_file",
            description="Process uploaded documents, PDFs, or media files",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to process"
                    },
                    "file_type": {
                        "type": "string",
                        "description": "Type of file (pdf, docx, txt, image)",
                        "enum": ["pdf", "docx", "txt", "image", "auto"]
                    }
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="process_prompt",
            description="Structure user prompt for pipeline processing",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "User's creative prompt or topic"
                    },
                    "style": {
                        "type": "string",
                        "description": "Content style preference",
                        "enum": ["educational", "entertaining", "motivational", "tutorial"],
                        "default": "educational"
                    }
                },
                "required": ["prompt"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list:
    """Handle tool execution"""
    
    if name == "process_youtube":
        result = await process_youtube(arguments["url"])
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "process_file":
        file_type = arguments.get("file_type", "auto")
        result = await process_file(arguments["file_path"], file_type)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "process_prompt":
        style = arguments.get("style", "educational")
        result = await process_prompt(arguments["prompt"], style)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    else:
        raise ValueError(f"Unknown tool: {name}")

async def process_youtube(url: str) -> Dict[str, Any]:
    """Extract transcript and metadata from YouTube video"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['en'],
        'skip_download': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Extract transcript
            transcript = ""
            if 'subtitles' in info and 'en' in info['subtitles']:
                # Process subtitles to extract text
                transcript = "Transcript extraction would be implemented here"
            elif 'automatic_captions' in info and 'en' in info['automatic_captions']:
                transcript = "Auto-generated transcript would be extracted here"
            
            return {
                "type": "youtube",
                "title": info.get('title', ''),
                "description": info.get('description', ''),
                "duration": info.get('duration', 0),
                "channel": info.get('channel', ''),
                "view_count": info.get('view_count', 0),
                "upload_date": info.get('upload_date', ''),
                "transcript": transcript,
                "thumbnail": info.get('thumbnail', ''),
                "tags": info.get('tags', []),
                "url": url
            }
    except Exception as e:
        return {
            "type": "youtube",
            "error": str(e),
            "url": url
        }

async def process_file(file_path: str, file_type: str) -> Dict[str, Any]:
    """Process various file types and extract content"""
    path = Path(file_path)
    
    if not path.exists():
        return {
            "type": "file",
            "error": f"File not found: {file_path}",
            "file_path": file_path
        }
    
    # Auto-detect file type if needed
    if file_type == "auto":
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            file_type = "pdf"
        elif suffix in [".docx", ".doc"]:
            file_type = "docx"
        elif suffix == ".txt":
            file_type = "txt"
        elif suffix in [".jpg", ".jpeg", ".png", ".gif"]:
            file_type = "image"
    
    try:
        if file_type == "pdf":
            # PDF processing would use pypdf2
            content = "PDF content extraction would be implemented here"
        elif file_type == "docx":
            # DOCX processing would use python-docx
            content = "DOCX content extraction would be implemented here"
        elif file_type == "txt":
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
        elif file_type == "image":
            # Image processing would extract metadata and prepare for visual analysis
            content = "Image metadata extraction would be implemented here"
        else:
            content = f"Unsupported file type: {file_type}"
        
        return {
            "type": "file",
            "file_type": file_type,
            "file_path": file_path,
            "file_name": path.name,
            "content": content,
            "size_bytes": path.stat().st_size,
            "modified_time": path.stat().st_mtime
        }
    
    except Exception as e:
        return {
            "type": "file",
            "error": str(e),
            "file_path": file_path,
            "file_type": file_type
        }

async def process_prompt(prompt: str, style: str = "educational") -> Dict[str, Any]:
    """Structure user prompt for pipeline processing"""
    # Extract potential topic and instructions
    lines = prompt.strip().split('\n')
    
    # Simple heuristic to identify topic vs instructions
    if len(lines) > 1:
        topic = lines[0]
        instructions = '\n'.join(lines[1:])
    else:
        topic = prompt
        instructions = f"Create {style} content about this topic"
    
    # Analyze prompt for content hints
    content_hints = []
    if any(word in prompt.lower() for word in ['tips', 'tricks', 'hacks']):
        content_hints.append('listicle')
    if any(word in prompt.lower() for word in ['how to', 'tutorial', 'guide']):
        content_hints.append('tutorial')
    if any(word in prompt.lower() for word in ['story', 'experience', 'journey']):
        content_hints.append('narrative')
    
    return {
        "type": "prompt",
        "topic": topic,
        "full_prompt": prompt,
        "instructions": instructions,
        "style": style,
        "content_hints": content_hints,
        "word_count": len(prompt.split()),
        "estimated_focus": "single" if len(prompt.split()) < 20 else "detailed"
    }

async def main():
    """Run the MCP server"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="input-processor",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())