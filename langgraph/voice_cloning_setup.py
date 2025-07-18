# voice_cloning_setup.py
import os
import shutil
import librosa
import soundfile as sf
from typing import Dict, Any, List
from langchain_core.tools import tool

class VoiceCloningSetup:
    def __init__(self):
        self.voice_samples_dir = "langgraph/voice_samples"
        self.supported_formats = ['.wav', '.mp3', '.m4a', '.flac', '.ogg']
        self._ensure_directory()
    
    def _ensure_directory(self):
        """Ensure voice samples directory exists."""
        os.makedirs(self.voice_samples_dir, exist_ok=True)
        
        # Create a README file with instructions
        readme_path = os.path.join(self.voice_samples_dir, "README.md")
        if not os.path.exists(readme_path):
            readme_content = """# Voice Samples for Cloning

## How to Add Your Voice

1. **Record a clear audio sample:**
   - Duration: 10-30 seconds (optimal: 15-20 seconds)
   - Quality: Clear speech, minimal background noise
   - Content: Natural speech, varied tones
   - Format: WAV preferred (MP3, M4A also supported)

2. **Save your file:**
   - Name format: `your_name.wav`
   - Place in this folder: `langgraph/voice_samples/`
   - Example: `john_doe.wav`, `sarah.wav`

3. **Use in voice generation:**
   - Use filename (without extension) as `voice_name`
   - Example: For `john_doe.wav`, use `voice_name="john_doe"`

## Recording Tips

- **Environment:** Quiet room, close to microphone
- **Speech:** Natural pace, clear pronunciation
- **Content:** Read a paragraph or speak naturally
- **Quality:** 22kHz+ sample rate, 16-bit+ depth

## Supported Formats
- WAV (recommended)
- MP3
- M4A
- FLAC
- OGG

## Example Voice Sample Text
"Hello, this is my voice sample for cloning. I'm speaking clearly and naturally to create the best possible voice model. The weather is nice today, and I'm excited to see how this technology works with my unique voice characteristics."
"""
            with open(readme_path, 'w') as f:
                f.write(readme_content)
    
    def process_voice_sample(self, 
                           input_path: str, 
                           voice_name: str,
                           normalize: bool = True,
                           target_sr: int = 22050) -> Dict[str, Any]:
        """Process and optimize a voice sample for cloning."""
        
        if not os.path.exists(input_path):
            return {
                "success": False,
                "error": f"Input file not found: {input_path}",
                "output_path": None
            }
        
        try:
            # Load audio file
            audio, sr = librosa.load(input_path, sr=target_sr)
            
            # Check duration (should be 5-60 seconds)
            duration = len(audio) / sr
            if duration < 5:
                return {
                    "success": False,
                    "error": f"Audio too short ({duration:.1f}s). Minimum 5 seconds required.",
                    "output_path": None
                }
            
            if duration > 60:
                # Trim to first 60 seconds
                audio = audio[:60 * sr]
                duration = 60
            
            # Normalize audio if requested
            if normalize:
                # Remove DC offset
                audio = audio - audio.mean()
                # Normalize to 0.8 max amplitude (leave some headroom)
                max_amp = abs(audio).max()
                if max_amp > 0:
                    audio = audio * (0.8 / max_amp)
            
            # Generate output path
            output_filename = f"{voice_name}.wav"
            output_path = os.path.join(self.voice_samples_dir, output_filename)
            
            # Save processed audio
            sf.write(output_path, audio, target_sr)
            
            # Get file size
            file_size = os.path.getsize(output_path)
            
            return {
                "success": True,
                "output_path": output_path,
                "voice_name": voice_name,
                "duration": f"{duration:.1f}s",
                "sample_rate": target_sr,
                "file_size": f"{file_size / 1024:.1f}KB",
                "normalized": normalize
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Processing failed: {str(e)}",
                "output_path": None
            }
    
    def analyze_voice_sample(self, file_path: str) -> Dict[str, Any]:
        """Analyze a voice sample for quality assessment."""
        
        if not os.path.exists(file_path):
            return {"error": "File not found"}
        
        try:
            audio, sr = librosa.load(file_path, sr=None)
            duration = len(audio) / sr
            
            # Basic audio analysis
            rms_energy = librosa.feature.rms(y=audio)[0].mean()
            spectral_centroid = librosa.feature.spectral_centroid(y=audio, sr=sr)[0].mean()
            zero_crossing_rate = librosa.feature.zero_crossing_rate(audio)[0].mean()
            
            # Quality assessment
            quality_score = 0
            quality_notes = []
            
            # Duration check
            if 10 <= duration <= 30:
                quality_score += 30
                quality_notes.append("✅ Good duration")
            elif 5 <= duration <= 60:
                quality_score += 20
                quality_notes.append("⚠️ Acceptable duration")
            else:
                quality_notes.append("❌ Poor duration (too short/long)")
            
            # Energy check (not too quiet, not clipping)
            if 0.01 <= rms_energy <= 0.3:
                quality_score += 25
                quality_notes.append("✅ Good volume level")
            else:
                quality_notes.append("⚠️ Volume may be too low/high")
            
            # Sample rate check
            if sr >= 22050:
                quality_score += 25
                quality_notes.append("✅ Good sample rate")
            else:
                quality_notes.append("⚠️ Low sample rate")
            
            # Spectral content check
            if 1000 <= spectral_centroid <= 3000:
                quality_score += 20
                quality_notes.append("✅ Good spectral content")
            else:
                quality_notes.append("⚠️ Unusual spectral content")
            
            return {
                "duration": f"{duration:.1f}s",
                "sample_rate": sr,
                "rms_energy": f"{rms_energy:.4f}",
                "spectral_centroid": f"{spectral_centroid:.0f}Hz",
                "zero_crossing_rate": f"{zero_crossing_rate:.4f}",
                "quality_score": quality_score,
                "quality_notes": quality_notes,
                "recommendation": "Excellent" if quality_score >= 80 else 
                               "Good" if quality_score >= 60 else 
                               "Fair" if quality_score >= 40 else "Poor"
            }
            
        except Exception as e:
            return {"error": f"Analysis failed: {str(e)}"}

@tool
async def setup_voice_sample(
    input_file_path: str,
    voice_name: str,
    normalize: bool = True
) -> str:
    """Set up a voice sample for cloning by processing and optimizing the audio.
    
    Args:
        input_file_path: Path to your audio file
        voice_name: Name for your voice (used in generation)
        normalize: Whether to normalize audio levels
    
    Returns:
        Processing result and setup status
    """
    try:
        setup = VoiceCloningSetup()
        
        # Validate voice name
        if not voice_name.replace("_", "").replace("-", "").isalnum():
            return """
❌ **INVALID VOICE NAME**

Voice name should contain only letters, numbers, underscores, and hyphens.

**Examples:**
- ✅ `john_doe`
- ✅ `sarah-voice`  
- ✅ `voice1`
- ❌ `john doe` (space)
- ❌ `voice@home` (special chars)
"""
        
        # Process the voice sample
        result = setup.process_voice_sample(
            input_path=input_file_path,
            voice_name=voice_name,
            normalize=normalize
        )
        
        if result["success"]:
            # Analyze the processed sample
            analysis = setup.analyze_voice_sample(result["output_path"])
            
            return f"""
✅ **VOICE SAMPLE SETUP SUCCESSFUL**

**📄 Voice Name:** {result['voice_name']}
**📁 Saved To:** {result['output_path']}
**⏱️ Duration:** {result['duration']}
**🔊 Sample Rate:** {result['sample_rate']}Hz
**📦 File Size:** {result['file_size']}
**🔧 Normalized:** {'Yes' if result['normalized'] else 'No'}

**📊 QUALITY ANALYSIS:**
**Score:** {analysis.get('quality_score', 0)}/100 ({analysis.get('recommendation', 'Unknown')})

**Quality Notes:**
{chr(10).join(analysis.get('quality_notes', ['Analysis unavailable']))}

**🎯 USAGE:**
Now you can use `voice_name="{voice_name}"` in the generate_voiceover function!

**💡 TIPS FOR BETTER RESULTS:**
- Speak clearly and naturally
- Use varied tones and emotions
- Ensure good audio quality
- 15-20 seconds is optimal length
"""
        else:
            return f"""
❌ **VOICE SAMPLE SETUP FAILED**

**Error:** {result['error']}

**💡 TROUBLESHOOTING:**
1. Check file path: {input_file_path}
2. Ensure supported format: WAV, MP3, M4A, FLAC, OGG
3. Verify file is not corrupted
4. Check audio duration (5-60 seconds recommended)

**📝 RECORDING TIPS:**
- Use quiet environment
- Speak 10-30 seconds
- Clear, natural speech
- Good microphone quality
"""
            
    except Exception as e:
        return f"❌ Error setting up voice sample: {str(e)}"

@tool
async def analyze_voice_quality(file_path: str) -> str:
    """Analyze the quality of a voice sample before setting it up.
    
    Args:
        file_path: Path to the audio file to analyze
    
    Returns:
        Detailed quality analysis and recommendations
    """
    try:
        setup = VoiceCloningSetup()
        analysis = setup.analyze_voice_sample(file_path)
        
        if "error" in analysis:
            return f"""
❌ **ANALYSIS FAILED**

**Error:** {analysis['error']}

**💡 CHECK:**
- File exists: {file_path}
- Supported format: WAV, MP3, M4A, FLAC, OGG
- File not corrupted
"""
        
        return f"""
📊 **VOICE SAMPLE QUALITY ANALYSIS**

**📄 File:** {os.path.basename(file_path)}

**📈 TECHNICAL SPECS:**
- Duration: {analysis['duration']}
- Sample Rate: {analysis['sample_rate']}Hz
- RMS Energy: {analysis['rms_energy']}
- Spectral Centroid: {analysis['spectral_centroid']}
- Zero Crossing Rate: {analysis['zero_crossing_rate']}

**🎯 QUALITY ASSESSMENT:**
- **Score:** {analysis['quality_score']}/100
- **Rating:** {analysis['recommendation']}

**📝 QUALITY NOTES:**
{chr(10).join(analysis['quality_notes'])}

**💡 RECOMMENDATIONS:**
{
'🎉 Excellent quality! Perfect for voice cloning.' if analysis['quality_score'] >= 80 else
'👍 Good quality. Should work well for voice cloning.' if analysis['quality_score'] >= 60 else  
'⚠️ Fair quality. Consider improving recording conditions.' if analysis['quality_score'] >= 40 else
'❌ Poor quality. Please record a new sample with better conditions.'
}

**📋 NEXT STEPS:**
{
'Ready to use! Run setup_voice_sample to process this file.' if analysis['quality_score'] >= 60 else
'Consider re-recording in a quieter environment with better equipment.'
}
"""
        
    except Exception as e:
        return f"❌ Error analyzing voice quality: {str(e)}"

# Voice cloning setup tools
voice_cloning_tools = [setup_voice_sample, analyze_voice_quality]