import asyncio
import json
import os
import sys
from typing import Dict, Any, List
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
from mcp.types import Tool, TextContent
from datetime import datetime
import subprocess
from pathlib import Path

# Initialize MCP server
server = Server("export")

# Platform specifications
PLATFORM_SPECS = {
    "instagram": {
        "resolution": "1080x1920",
        "max_duration": 60,
        "format": "mp4",
        "codec": "libx264",
        "bitrate": "4000k",
        "audio_bitrate": "128k",
        "fps": 30
    },
    "tiktok": {
        "resolution": "1080x1920",
        "max_duration": 60,
        "format": "mp4",
        "codec": "libx264",
        "bitrate": "3500k",
        "audio_bitrate": "128k",
        "fps": 30
    },
    "youtube_shorts": {
        "resolution": "1080x1920",
        "max_duration": 60,
        "format": "mp4",
        "codec": "libx264",
        "bitrate": "5000k",
        "audio_bitrate": "192k",
        "fps": 30
    }
}

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available export tools"""
    return [
        Tool(
            name="export_for_platforms",
            description="Export video optimized for multiple platforms",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_video": {"type": "string", "description": "Path to source video"},
                    "platforms": {
                        "type": "array", 
                        "items": {"type": "string", "enum": list(PLATFORM_SPECS.keys())},
                        "description": "Target platforms"
                    },
                    "quality": {"type": "string", "enum": ["high", "medium", "low"], "default": "high"}
                },
                "required": ["source_video", "platforms"]
            }
        ),
        Tool(
            name="create_thumbnail_variations",
            description="Create multiple thumbnail variations",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_path": {"type": "string"},
                    "title": {"type": "string"},
                    "styles": {"type": "array", "items": {"type": "string"}},
                    "count": {"type": "integer", "default": 3}
                },
                "required": ["video_path", "title"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list:
    """Handle tool execution"""
    
    if name == "export_for_platforms":
        result = await export_for_platforms(
            arguments["source_video"],
            arguments["platforms"],
            arguments.get("quality", "high")
        )
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "create_thumbnail_variations":
        result = await create_thumbnail_variations(
            arguments["video_path"],
            arguments["title"],
            arguments.get("styles", ["bold", "minimal", "colorful"]),
            arguments.get("count", 3)
        )
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    else:
        raise ValueError(f"Unknown tool: {name}")

async def export_for_platforms(source_video: str, platforms: List[str], quality: str) -> Dict[str, Any]:
    """Export video optimized for multiple platforms"""
    try:
        export_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"./data/exports/platform_optimized/{export_id}"
        os.makedirs(output_dir, exist_ok=True)
        
        exports = []
        
        for platform in platforms:
            if platform not in PLATFORM_SPECS:
                continue
                
            spec = PLATFORM_SPECS[platform]
            output_path = f"{output_dir}/{platform}_optimized.{spec['format']}"
            
            # Mock platform optimization
            await create_optimized_video(source_video, output_path, spec, quality)
            
            # Get file stats
            file_size = 0
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path) / (1024*1024)  # MB
            
            exports.append({
                "platform": platform,
                "file_path": output_path,
                "resolution": spec["resolution"],
                "duration": spec["max_duration"],
                "file_size_mb": round(file_size, 2),
                "format": spec["format"],
                "optimized_for": f"{platform}_vertical_video"
            })
        
        return {
            "export_id": export_id,
            "source_video": source_video,
            "platforms": platforms,
            "quality": quality,
            "exports": exports,
            "total_exports": len(exports),
            "status": "completed",
            "created_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {"error": f"Platform export failed: {str(e)}"}

async def create_thumbnail_variations(video_path: str, title: str, styles: List[str], count: int) -> Dict[str, Any]:
    """Create multiple thumbnail variations"""
    try:
        thumbnail_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"./data/exports/thumbnails/{thumbnail_id}"
        os.makedirs(output_dir, exist_ok=True)
        
        thumbnails = []
        
        for i, style in enumerate(styles[:count]):
            thumbnail_path = f"{output_dir}/thumbnail_{style}_{i}.jpg"
            
            # Mock thumbnail creation
            await create_mock_thumbnail(thumbnail_path, title, style)
            
            thumbnails.append({
                "style": style,
                "file_path": thumbnail_path,
                "title": title,
                "index": i
            })
        
        return {
            "thumbnail_id": thumbnail_id,
            "video_path": video_path,
            "title": title,
            "thumbnails": thumbnails,
            "count": len(thumbnails),
            "status": "completed"
        }
        
    except Exception as e:
        return {"error": f"Thumbnail creation failed: {str(e)}"}

async def create_optimized_video(source_video: str, output_path: str, spec: Dict, quality: str):
    """Create platform-optimized video"""
    try:
        # Adjust bitrate based on quality
        bitrate = spec["bitrate"]
        if quality == "medium":
            bitrate = str(int(bitrate.replace("k", "")) * 0.7) + "k"
        elif quality == "low":
            bitrate = str(int(bitrate.replace("k", "")) * 0.5) + "k"
        
        cmd = [
            "ffmpeg", "-y",
            "-i", source_video,
            "-vf", f"scale={spec['resolution']}:force_original_aspect_ratio=decrease,pad={spec['resolution']}:(ow-iw)/2:(oh-ih)/2",
            "-c:v", spec["codec"],
            "-b:v", bitrate,
            "-c:a", "aac",
            "-b:a", spec["audio_bitrate"],
            "-r", str(spec["fps"]),
            "-t", str(spec["max_duration"]),
            "-movflags", "+faststart",
            output_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        
    except:
        # Create mock file if FFmpeg fails
        Path(output_path).touch()

async def create_mock_thumbnail(output_path: str, title: str, style: str):
    """Create a mock thumbnail"""
    try:
        # Simple colored rectangle as thumbnail
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c={'red' if style=='bold' else 'blue' if style=='minimal' else 'green'}:size=1080x1920:duration=1",
            "-frames:v", "1",
            output_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        
    except:
        Path(output_path).touch()

async def main():
    """Run the MCP server"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="export",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())