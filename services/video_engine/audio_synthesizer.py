
import asyncio
import aiohttp
import os
from typing import Dict, Any, List, Optional
import tempfile
import json
from datetime import datetime

class AudioSynthesizer:
    """ElevenLabs voice synthesis integration"""
    
    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.voice_id = os.getenv("ELEVENLABS_VOICE_ID", "rachel")
        self.base_url = "https://api.elevenlabs.io/v1"
        
    async def synthesize_script(self, script: str, voice_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Synthesize entire script with timing markers"""
        try:
            # Parse script into segments
            segments = self._parse_script_segments(script)
            
            # Synthesize each segment
            audio_segments = []
            total_duration = 0
            
            for i, segment in enumerate(segments):
                audio_data = await self._synthesize_segment(segment["text"], voice_config)
                
                segment_file = f"./data/exports/audio/segment_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
                os.makedirs(os.path.dirname(segment_file), exist_ok=True)
                
                with open(segment_file, 'wb') as f:
                    f.write(audio_data)
                
                # Get duration (would use audio analysis library in production)
                duration = await self._get_audio_duration(segment_file)
                
                audio_segments.append({
                    "text": segment["text"],
                    "file_path": segment_file,
                    "duration": duration,
                    "start_time": total_duration,
                    "emphasis_words": segment.get("emphasis_words", []),
                    "pause_after": segment.get("pause_after", 0)
                })
                
                total_duration += duration + segment.get("pause_after", 0)
            
            # Combine segments into final audio
            final_audio_path = await self._combine_audio_segments(audio_segments)
            
            return {
                "final_audio_path": final_audio_path,
                "segments": audio_segments,
                "total_duration": total_duration,
                "voice_used": voice_config.get("voice_id", self.voice_id),
                "synthesis_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"error": f"Audio synthesis failed: {str(e)}"}
    
    async def _synthesize_segment(self, text: str, voice_config: Dict[str, Any] = None) -> bytes:
        """Synthesize individual text segment"""
        
        url = f"{self.base_url}/text-to-speech/{self.voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        
        # Voice settings for different emotions/styles
        voice_settings = {
            "stability": voice_config.get("stability", 0.75),
            "similarity_boost": voice_config.get("similarity_boost", 0.75),
            "style": voice_config.get("style", 0.0),
            "use_speaker_boost": voice_config.get("use_speaker_boost", True)
        }
        
        data = {
            "text": text,
            "model_id": voice_config.get("model_id", "eleven_multilingual_v2"),
            "voice_settings": voice_settings
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    error_text = await response.text()
                    raise Exception(f"ElevenLabs API error: {response.status} - {error_text}")
    
    def _parse_script_segments(self, script: str) -> List[Dict[str, Any]]:
        """Parse script into segments with timing and emphasis"""
        segments = []
        
        # Split by sentences or natural pauses
        sentences = script.split('. ')
        
        for sentence in sentences:
            if not sentence.strip():
                continue
                
            # Detect emphasis words (ALL CAPS or **bold**)
            emphasis_words = self._extract_emphasis_words(sentence)
            
            # Detect pause markers
            pause_after = 0.5 if sentence.endswith('...') else 0.2
            
            # Clean text for synthesis
            clean_text = self._clean_text_for_synthesis(sentence)
            
            segments.append({
                "text": clean_text,
                "emphasis_words": emphasis_words,
                "pause_after": pause_after
            })
        
        return segments
    
    def _extract_emphasis_words(self, text: str) -> List[str]:
        """Extract words that should be emphasized"""
        import re
        
        # Find ALL CAPS words
        caps_words = re.findall(r'\b[A-Z]{2,}\b', text)
        
        # Find **bold** words
        bold_words = re.findall(r'\*\*(.*?)\*\*', text)
        
        return caps_words + bold_words
    
    def _clean_text_for_synthesis(self, text: str) -> str:
        """Clean text for better synthesis"""
        import re
        
        # Remove markdown formatting
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        
        # Replace [PAUSE] with actual pause
        text = re.sub(r'\[PAUSE\]', '...', text)
        
        # Remove visual cues
        text = re.sub(r'\[VISUAL:.*?\]', '', text)
        
        return text.strip()
    
    async def _get_audio_duration(self, audio_file: str) -> float:
        """Get audio file duration (placeholder - would use librosa or ffprobe)"""
        # In production, use: librosa.get_duration(filename=audio_file)
        # For now, estimate based on text length (average 150 words per minute)
        return 3.0  # Placeholder duration
    
    async def _combine_audio_segments(self, segments: List[Dict[str, Any]]) -> str:
        """Combine audio segments with appropriate pauses"""
        
        output_path = f"./data/exports/audio/final_audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        
        # Use FFmpeg to concatenate audio files with pauses
        input_files = []
        filter_complex = []
        
        for i, segment in enumerate(segments):
            input_files.extend(["-i", segment["file_path"]])
            
            if segment["pause_after"] > 0:
                # Add silence
                silence_duration = segment["pause_after"]
                filter_complex.append(f"[{i}]apad=pad_dur={silence_duration}[padded{i}]")
            else:
                filter_complex.append(f"[{i}]acopy[padded{i}]")
        
        # Concatenate all segments
        concat_inputs = "".join(f"[padded{i}]" for i in range(len(segments)))
        filter_complex.append(f"{concat_inputs}concat=n={len(segments)}:v=0:a=1[out]")
        
        ffmpeg_cmd = [
            "ffmpeg", "-y"
        ] + input_files + [
            "-filter_complex", ";".join(filter_complex),
            "-map", "[out]",
            output_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        await process.communicate()
        
        if process.returncode != 0:
            raise Exception("Failed to combine audio segments")
        
        return output_path

# Voice configuration presets
VOICE_PRESETS = {
    "energetic": {
        "stability": 0.60,
        "similarity_boost": 0.85,
        "style": 0.20,
        "use_speaker_boost": True
    },
    "calm": {
        "stability": 0.85,
        "similarity_boost": 0.75,
        "style": 0.05,
        "use_speaker_boost": False
    },
    "professional": {
        "stability": 0.75,
        "similarity_boost": 0.80,
        "style": 0.10,
        "use_speaker_boost": True
    },
    "conversational": {
        "stability": 0.70,
        "similarity_boost": 0.75,
        "style": 0.15,
        "use_speaker_boost": True
    }
}