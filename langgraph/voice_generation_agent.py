# voice_generation_agent.py
import os
import json
import asyncio
import hashlib
import torchaudio as ta
from typing import Dict, List, Any, Optional
from langchain_core.tools import tool
from datetime import datetime
import subprocess
import sys

class VoiceGenerationAgent:
    def __init__(self):
        self.model = None
        self.sample_rate = 22050
        self.voice_samples_dir = "langgraph/voice_samples"
        self.generated_voices_dir = "langgraph/generated_voices"
        self._ensure_directories()
        
    def _ensure_directories(self):
        """Create necessary directories if they don't exist."""
        os.makedirs(self.voice_samples_dir, exist_ok=True)
        os.makedirs(self.generated_voices_dir, exist_ok=True)
        
    def _install_chatterbox(self):
        """Install Chatterbox TTS if not already installed."""
        try:
            import chatterbox.tts
            return True
        except ImportError:
            print("📦 Installing Chatterbox TTS...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "chatterbox-tts"])
                print("✅ Chatterbox TTS installed successfully!")
                return True
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to install Chatterbox TTS: {e}")
                return False
    
    def _load_model(self):
        """Load the Chatterbox TTS model."""
        if self.model is not None:
            return True
            
        try:
            if not self._install_chatterbox():
                return False
                
            from chatterbox.tts import ChatterboxTTS
            print("🤖 Loading Chatterbox TTS model...")
            self.model = ChatterboxTTS.from_pretrained(device="cuda" if self._has_cuda() else "cpu")
            self.sample_rate = self.model.sr
            print("✅ Model loaded successfully!")
            return True
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            return False
    
    def _has_cuda(self):
        """Check if CUDA is available."""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
    
    def _generate_filename(self, text: str, voice_name: str = "default") -> str:
        """Generate a unique filename for the audio."""
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"voice_{voice_name}_{timestamp}_{text_hash}.wav"
    
    def _get_voice_sample_path(self, voice_name: str) -> Optional[str]:
        """Get the path to a voice sample file."""
        if voice_name == "default":
            return None
            
        voice_files = [
            f"{self.voice_samples_dir}/{voice_name}.wav",
            f"{self.voice_samples_dir}/{voice_name}.mp3",
            f"{self.voice_samples_dir}/{voice_name}.m4a"
        ]
        
        for path in voice_files:
            if os.path.exists(path):
                return path
        return None
    
    def generate_voice(self, 
                      text: str, 
                      voice_name: str = "default",
                      exaggeration: float = 0.5,
                      cfg_weight: float = 0.5,
                      emotion: str = "neutral") -> Dict[str, Any]:
        """Generate voice from text using Chatterbox TTS."""
        
        if not self._load_model():
            return {
                "success": False,
                "error": "Failed to load Chatterbox TTS model",
                "file_path": None
            }
        
        try:
            # Adjust parameters based on emotion
            if emotion.lower() in ["dramatic", "excited", "expressive"]:
                exaggeration = max(0.7, exaggeration)
                cfg_weight = min(0.3, cfg_weight)
            elif emotion.lower() in ["calm", "gentle", "soft"]:
                exaggeration = min(0.3, exaggeration)
                cfg_weight = max(0.7, cfg_weight)
            
            # Get voice sample path if using custom voice
            audio_prompt_path = self._get_voice_sample_path(voice_name)
            
            # Generate audio
            print(f"🎙️ Generating voice for: {text[:50]}...")
            if audio_prompt_path:
                print(f"👤 Using voice sample: {audio_prompt_path}")
                wav = self.model.generate(
                    text, 
                    audio_prompt_path=audio_prompt_path,
                    exaggeration=exaggeration,
                    cfg_weight=cfg_weight
                )
            else:
                wav = self.model.generate(
                    text,
                    exaggeration=exaggeration,
                    cfg_weight=cfg_weight
                )
            
            # Save the generated audio
            filename = self._generate_filename(text, voice_name)
            file_path = os.path.join(self.generated_voices_dir, filename)
            
            ta.save(file_path, wav, self.sample_rate)
            
            # Get file info
            file_size = os.path.getsize(file_path)
            duration = wav.shape[-1] / self.sample_rate
            
            return {
                "success": True,
                "file_path": file_path,
                "filename": filename,
                "duration": f"{duration:.2f}s",
                "file_size": f"{file_size / 1024:.1f}KB",
                "voice_name": voice_name,
                "emotion": emotion,
                "text_length": len(text),
                "parameters": {
                    "exaggeration": exaggeration,
                    "cfg_weight": cfg_weight
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Voice generation failed: {str(e)}",
                "file_path": None
            }
    
    def list_voice_samples(self) -> List[str]:
        """List available voice samples."""
        if not os.path.exists(self.voice_samples_dir):
            return []
        
        voice_files = []
        for file in os.listdir(self.voice_samples_dir):
            if file.endswith(('.wav', '.mp3', '.m4a')):
                voice_name = os.path.splitext(file)[0]
                voice_files.append(voice_name)
        
        return voice_files

@tool
async def generate_voiceover(
    script_text: str,
    voice_name: str = "default",
    emotion: str = "neutral",
    exaggeration: float = 0.5,
    cfg_weight: float = 0.5
) -> str:
    """Generate voiceover audio from script text using Chatterbox TTS.
    
    Args:
        script_text: The text script to convert to speech
        voice_name: Name of voice sample to use ("default" for base model)
        emotion: Emotion style (neutral, dramatic, excited, calm, expressive)
        exaggeration: Exaggeration level (0.0-1.0, higher = more expressive)
        cfg_weight: CFG weight (0.0-1.0, lower = faster speech)
    
    Returns:
        JSON string with generation result and file path
    """
    try:
        agent = VoiceGenerationAgent()
        
        # Clean up script text (remove markdown formatting)
        clean_text = script_text.replace("**", "").replace("*", "")
        clean_text = clean_text.replace("HOOK:", "").replace("ACT 1:", "").replace("ACT 2:", "").replace("ACT 3:", "")
        clean_text = clean_text.replace("CONCLUSION/CTA:", "").replace("CTA:", "")
        clean_text = " ".join(clean_text.split())  # Remove extra whitespace
        
        if not clean_text.strip():
            return json.dumps({
                "success": False,
                "error": "No valid text found in script",
                "file_path": None
            })
        
        # Limit text length for reasonable generation time
        if len(clean_text) > 5000:
            clean_text = clean_text[:5000] + "..."
            
        result = agent.generate_voice(
            text=clean_text,
            voice_name=voice_name,
            exaggeration=exaggeration,
            cfg_weight=cfg_weight,
            emotion=emotion
        )
        
        if result["success"]:
            return f"""
🎙️ **VOICEOVER GENERATED SUCCESSFULLY**

**📄 Script Preview:** {clean_text[:100]}...
**🎵 Audio File:** {result['filename']}
**⏱️ Duration:** {result['duration']}
**📁 File Size:** {result['file_size']}
**👤 Voice:** {result['voice_name']}
**🎭 Emotion:** {result['emotion']}
**📊 Parameters:** Exaggeration: {result['parameters']['exaggeration']}, CFG: {result['parameters']['cfg_weight']}

**📍 Local Path:** {result['file_path']}

✅ **Voice generation complete!** Ready for Google Drive upload.
"""
        else:
            return f"""
❌ **VOICEOVER GENERATION FAILED**

**Error:** {result['error']}

**💡 Troubleshooting:**
- Check if Chatterbox TTS is properly installed
- Ensure CUDA is available for GPU acceleration
- Verify script text is not empty
- Try reducing text length if too long
"""
            
    except Exception as e:
        return f"❌ Error in voiceover generation: {str(e)}"

@tool
async def list_available_voices() -> str:
    """List all available voice samples for voice cloning.
    
    Returns:
        List of available voice sample names
    """
    try:
        agent = VoiceGenerationAgent()
        voices = agent.list_voice_samples()
        
        if not voices:
            return """
📢 **NO CUSTOM VOICES FOUND**

**Available Voices:**
- `default` (Built-in Chatterbox voice)

**💡 To add your voice:**
1. Record a clear audio sample (10-30 seconds)
2. Save as `your_name.wav` in `langgraph/voice_samples/`
3. Use `your_name` as voice_name parameter

**📋 Supported formats:** WAV, MP3, M4A
"""
        
        voices_list = "\n".join([f"- `{voice}`" for voice in ["default"] + voices])
        
        return f"""
🎭 **AVAILABLE VOICES**

**Voice Samples:**
{voices_list}

**💡 Usage:**
- Use voice name in generate_voiceover function
- `default` uses the base Chatterbox model
- Custom voices enable voice cloning

**📁 Voice samples location:** `langgraph/voice_samples/`
"""
        
    except Exception as e:
        return f"❌ Error listing voices: {str(e)}"

# Create voice agent tools list
voice_tools = [generate_voiceover, list_available_voices]