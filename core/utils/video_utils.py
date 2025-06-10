import asyncio
import subprocess
import json
import os
from typing import Dict, Any, Optional, List
from pathlib import Path

class VideoProcessor:
    """Utility class for video processing operations"""
    
    @staticmethod
    async def get_video_info(video_path: str) -> Dict[str, Any]:
        """Get video information using ffprobe"""
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams",
            video_path
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                data = json.loads(stdout.decode())
                
                # Find video stream
                video_stream = next(
                    (s for s in data["streams"] if s["codec_type"] == "video"), 
                    None
                )
                
                if video_stream:
                    return {
                        "duration": float(data["format"]["duration"]),
                        "resolution": f"{video_stream['width']}x{video_stream['height']}",
                        "fps": eval(video_stream["r_frame_rate"]),
                        "codec": video_stream["codec_name"],
                        "file_size_mb": round(int(data["format"]["size"]) / (1024*1024), 2)
                    }
            
            return {"error": "Could not parse video info"}
            
        except Exception as e:
            return {"error": f"Failed to get video info: {str(e)}"}
    
    @staticmethod
    async def concatenate_videos(video_files: List[str], output_path: str) -> bool:
        """Concatenate multiple video files"""
        try:
            # Create file list for ffmpeg
            list_file = output_path.replace(".mp4", "_list.txt")
            
            with open(list_file, "w") as f:
                for video_file in video_files:
                    f.write(f"file '{video_file}'\n")
            
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", list_file,
                "-c", "copy",
                output_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            
            # Clean up
            os.remove(list_file)
            
            return process.returncode == 0
            
        except Exception as e:
            print(f"Video concatenation failed: {e}")
            return False
    
    @staticmethod
    async def add_audio_to_video(video_path: str, audio_path: str, output_path: str, 
                               audio_volume: float = 1.0) -> bool:
        """Add audio track to video"""
        try:
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-i", audio_path,
                "-c:v", "copy",
                "-c:a", "aac",
                "-filter:a", f"volume={audio_volume}",
                "-shortest",
                output_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            return process.returncode == 0
            
        except Exception as e:
            print(f"Audio addition failed: {e}")
            return False

    @staticmethod
    async def optimize_for_platform(input_video: str, platform: str, output_path: str) -> bool:
        """Optimize video for specific platform"""
        platform_specs = {
            "instagram": {
                "resolution": "1080x1920",
                "bitrate": "4000k",
                "fps": 30,
                "max_duration": 60
            },
            "tiktok": {
                "resolution": "1080x1920", 
                "bitrate": "3500k",
                "fps": 30,
                "max_duration": 60
            },
            "youtube_shorts": {
                "resolution": "1080x1920",
                "bitrate": "5000k", 
                "fps": 30,
                "max_duration": 60
            }
        }
        
        spec = platform_specs.get(platform, platform_specs["instagram"])
        
        try:
            cmd = [
                "ffmpeg", "-y",
                "-i", input_video,
                "-vf", f"scale={spec['resolution']}:force_original_aspect_ratio=decrease,pad={spec['resolution']}:(ow-iw)/2:(oh-ih)/2",
                "-c:v", "libx264",
                "-b:v", spec["bitrate"],
                "-r", str(spec["fps"]),
                "-t", str(spec["max_duration"]),
                "-movflags", "+faststart",
                output_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            return process.returncode == 0
            
        except Exception as e:
            print(f"Platform optimization failed: {e}")
            return False