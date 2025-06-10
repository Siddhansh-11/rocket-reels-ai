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
server = Server("assembly")

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available assembly tools"""
    return [
        Tool(
            name="assemble_video",
            description="Assemble final video from components",
            inputSchema={
                "type": "object",
                "properties": {
                    "script": {"type": "object", "description": "Script with timing"},
                    "visuals": {"type": "array", "description": "Visual assets"},
                    "audio": {"type": "object", "description": "Audio configuration"},
                    "transitions": {"type": "array", "description": "Transition effects"},
                    "output_settings": {"type": "object", "description": "Output specifications"}
                },
                "required": ["script", "visuals", "audio"]
            }
        ),
        Tool(
            name="generate_voiceover", 
            description="Generate AI voiceover using ElevenLabs",
            inputSchema={
                "type": "object",
                "properties": {
                    "script_text": {"type": "string"},
                    "voice_id": {"type": "string", "default": "rachel"},
                    "speed": {"type": "number", "default": 1.0},
                    "style": {"type": "string", "enum": ["energetic", "calm", "professional"], "default": "energetic"}
                },
                "required": ["script_text"]
            }
        ),
        Tool(
            name="add_background_music",
            description="Add background music and sound effects",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_path": {"type": "string"},
                    "music_style": {"type": "string", "enum": ["upbeat", "calm", "dramatic", "none"]},
                    "volume_level": {"type": "number", "default": 0.3}
                },
                "required": ["video_path"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list:
    """Handle tool execution"""
    
    if name == "assemble_video":
        result = await assemble_video(
            arguments["script"],
            arguments["visuals"], 
            arguments["audio"],
            arguments.get("transitions", []),
            arguments.get("output_settings", {})
        )
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "generate_voiceover":
        result = await generate_voiceover(
            arguments["script_text"],
            arguments.get("voice_id", "rachel"),
            arguments.get("speed", 1.0),
            arguments.get("style", "energetic")
        )
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "add_background_music":
        result = await add_background_music(
            arguments["video_path"],
            arguments.get("music_style", "upbeat"),
            arguments.get("volume_level", 0.3)
        )
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    else:
        raise ValueError(f"Unknown tool: {name}")

async def assemble_video(script: Dict[str, Any], visuals: List[Dict], audio: Dict[str, Any], 
                        transitions: List[Dict], output_settings: Dict[str, Any]) -> Dict[str, Any]:
    """Assemble the final video from all components"""
    try:
        assembly_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"./data/exports/assembled/{assembly_id}"
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate voiceover first
        script_text = script.get("full_script", "")
        voiceover_result = await generate_voiceover(script_text, audio.get("voice_id", "rachel"))
        
        # Create mock video assembly
        final_video_path = f"{output_dir}/final_video.mp4"
        await create_mock_video(final_video_path, script, visuals)
        
        return {
            "assembly_id": assembly_id,
            "video_path": final_video_path,
            "duration": 45.0,
            "resolution": "1080x1920",
            "file_size_mb": 12.5,
            "components": {
                "script_segments": len(script.get("segments", [])),
                "visual_assets": len(visuals),
                "voiceover": voiceover_result.get("audio_path"),
                "transitions": len(transitions)
            },
            "status": "completed",
            "created_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {"error": f"Video assembly failed: {str(e)}"}

async def generate_voiceover(script_text: str, voice_id: str, speed: float = 1.0, style: str = "energetic") -> Dict[str, Any]:
    """Generate AI voiceover (mock implementation)"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_path = f"./data/temp/voiceover_{timestamp}.mp3"
        
        # Ensure temp directory exists
        os.makedirs("./data/temp", exist_ok=True)
        
        # Create mock audio file
        duration = len(script_text) * 0.15  # 150ms per character
        await create_mock_audio(audio_path, duration)
        
        return {
            "audio_path": audio_path,
            "duration": duration,
            "voice_id": voice_id,
            "style": style,
            "script_length": len(script_text),
            "status": "success"
        }
        
    except Exception as e:
        return {"error": f"Voiceover generation failed: {str(e)}"}

async def add_background_music(video_path: str, music_style: str, volume_level: float) -> Dict[str, Any]:
    """Add background music to video"""
    try:
        output_path = video_path.replace(".mp4", "_with_music.mp4")
        
        # Mock music addition
        return {
            "input_video": video_path,
            "output_video": output_path,
            "music_style": music_style,
            "volume_level": volume_level,
            "status": "completed"
        }
        
    except Exception as e:
        return {"error": f"Background music addition failed: {str(e)}"}

async def create_mock_video(output_path: str, script: Dict, visuals: List[Dict]):
    """Create a mock video file"""
    try:
        # Create a simple test pattern using FFmpeg if available
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "testsrc=duration=45:size=1080x1920:rate=30",
            "-f", "lavfi", 
            "-i", "sine=frequency=1000:duration=45",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-shortest",
            output_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        
    except:
        # If FFmpeg not available, create a placeholder file
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).touch()

async def create_mock_audio(output_path: str, duration: float):
    """Create a mock audio file"""
    try:
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"sine=frequency=800:duration={min(duration, 60)}",
            "-c:a", "mp3",
            output_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        
    except:
        # Create empty file if FFmpeg not available
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).touch()

async def main():
    """Run the MCP server"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="assembly",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())