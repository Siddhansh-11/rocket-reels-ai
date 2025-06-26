# voice_workflow_integration.py
import json
from typing import Dict, Any
from langchain_core.tools import tool

# Import voice-related tools
from voice_generation_agent import voice_tools
from gdrive_voice_storage import gdrive_voice_tools  
from voice_cloning_setup import voice_cloning_tools

@tool
async def complete_voice_workflow(
    script_text: str,
    voice_name: str = "default",
    emotion: str = "neutral",
    script_title: str = "",
    upload_to_gdrive: bool = True,
    exaggeration: float = 0.5,
    cfg_weight: float = 0.5
) -> str:
    """Complete end-to-end voice generation workflow: generate voice + upload to Google Drive.
    
    Args:
        script_text: The script text to convert to speech
        voice_name: Voice to use ("default" or custom voice name)
        emotion: Emotion style (neutral, dramatic, excited, calm, expressive)
        script_title: Title for the script (used in file naming)
        upload_to_gdrive: Whether to upload to Google Drive
        exaggeration: Voice exaggeration level (0.0-1.0)
        cfg_weight: CFG weight for speed control (0.0-1.0)
    
    Returns:
        Complete workflow result
    """
    try:
        from voice_generation_agent import generate_voiceover
        from gdrive_voice_storage import upload_voice_to_gdrive
        
        workflow_steps = []
        
        # Step 1: Generate voiceover
        workflow_steps.append("🎙️ Generating voiceover...")
        
        voice_result = await generate_voiceover(
            script_text=script_text,
            voice_name=voice_name,
            emotion=emotion,
            exaggeration=exaggeration,
            cfg_weight=cfg_weight
        )
        
        # Parse the voice generation result to extract file path
        if "VOICEOVER GENERATED SUCCESSFULLY" in voice_result:
            # Extract file path from the result (this is a simplified approach)
            lines = voice_result.split('\n')
            file_path = None
            for line in lines:
                if "Local Path:" in line:
                    file_path = line.split("Local Path:")[1].strip()
                    break
            
            if not file_path:
                return f"""
❌ **WORKFLOW FAILED AT VOICE GENERATION**

Could not extract file path from voice generation result.

**Voice Generation Output:**
{voice_result}
"""
            
            workflow_steps.append("✅ Voice generation completed")
            
            # Step 2: Upload to Google Drive (if requested)
            gdrive_result = ""
            if upload_to_gdrive:
                workflow_steps.append("☁️ Uploading to Google Drive...")
                
                gdrive_result = await upload_voice_to_gdrive(
                    file_path=file_path,
                    voice_name=voice_name,
                    script_title=script_title,
                    emotion=emotion,
                    duration="",  # Duration will be extracted from file
                    additional_metadata={
                        "exaggeration": exaggeration,
                        "cfg_weight": cfg_weight,
                        "workflow": "complete_voice_workflow"
                    }
                )
                
                if "VOICE UPLOADED TO GOOGLE DRIVE" in gdrive_result:
                    workflow_steps.append("✅ Google Drive upload completed")
                else:
                    workflow_steps.append("⚠️ Google Drive upload failed")
            
            # Combine results
            return f"""
🎬 **COMPLETE VOICE WORKFLOW FINISHED**

**📋 Workflow Steps:**
{chr(10).join([f"  {step}" for step in workflow_steps])}

**🎙️ VOICE GENERATION RESULT:**
{voice_result}

{"**☁️ GOOGLE DRIVE UPLOAD RESULT:**" + chr(10) + gdrive_result if upload_to_gdrive else "**📁 Local Storage Only** (Google Drive upload skipped)"}

**🎯 WORKFLOW SUMMARY:**
- Script processed: ✅
- Voice generated: ✅
- Google Drive upload: {'✅' if upload_to_gdrive and 'UPLOADED' in gdrive_result else '⚠️ Skipped' if not upload_to_gdrive else '❌ Failed'}

**📝 NEXT STEPS:**
{'Your voice file is ready for use in video production!' if 'UPLOADED' in gdrive_result else 'Your voice file is saved locally and ready to use!'}
"""
        else:
            return f"""
❌ **WORKFLOW FAILED AT VOICE GENERATION**

**Voice Generation Error:**
{voice_result}

**💡 Troubleshooting:**
1. Check if script text is valid
2. Verify voice name exists (use list_available_voices)
3. Ensure Chatterbox TTS is properly installed
4. Check system resources (GPU/CPU availability)
"""
            
    except Exception as e:
        return f"❌ Complete voice workflow failed: {str(e)}"

@tool
async def voice_workflow_status() -> str:
    """Check the status of voice generation system and requirements.
    
    Returns:
        System status and setup requirements
    """
    try:
        status_checks = []
        
        # Check 1: Chatterbox TTS installation
        try:
            import chatterbox.tts
            status_checks.append("✅ Chatterbox TTS: Installed")
        except ImportError:
            status_checks.append("❌ Chatterbox TTS: Not installed")
        
        # Check 2: Required audio libraries
        try:
            import torchaudio
            status_checks.append("✅ TorchAudio: Available")
        except ImportError:
            status_checks.append("❌ TorchAudio: Missing")
        
        try:
            import librosa
            status_checks.append("✅ Librosa: Available")
        except ImportError:
            status_checks.append("❌ Librosa: Missing")
        
        try:
            import soundfile
            status_checks.append("✅ SoundFile: Available")
        except ImportError:
            status_checks.append("❌ SoundFile: Missing")
        
        # Check 3: CUDA availability
        try:
            import torch
            if torch.cuda.is_available():
                status_checks.append(f"✅ CUDA: Available (GPU: {torch.cuda.get_device_name(0)})")
            else:
                status_checks.append("⚠️ CUDA: Not available (will use CPU)")
        except ImportError:
            status_checks.append("❌ PyTorch: Missing")
        
        # Check 4: Google Drive setup
        import os
        if os.path.exists('langgraph/credentials.json'):
            status_checks.append("✅ Google Drive: Credentials found")
        else:
            status_checks.append("⚠️ Google Drive: Credentials missing")
        
        # Check 5: Voice samples directory
        if os.path.exists('langgraph/voice_samples'):
            samples = [f for f in os.listdir('langgraph/voice_samples') 
                      if f.endswith(('.wav', '.mp3', '.m4a'))]
            if samples:
                status_checks.append(f"✅ Voice Samples: {len(samples)} found")
            else:
                status_checks.append("⚠️ Voice Samples: Directory empty")
        else:
            status_checks.append("❌ Voice Samples: Directory missing")
        
        # Check 6: Generated voices directory
        if os.path.exists('langgraph/generated_voices'):
            voices = [f for f in os.listdir('langgraph/generated_voices') 
                     if f.endswith('.wav')]
            status_checks.append(f"✅ Generated Voices: Directory ready ({len(voices)} files)")
        else:
            status_checks.append("⚠️ Generated Voices: Directory missing")
        
        # Overall status
        failed_checks = [check for check in status_checks if check.startswith('❌')]
        warning_checks = [check for check in status_checks if check.startswith('⚠️')]
        
        if not failed_checks:
            overall_status = "🎉 **SYSTEM READY** - All core components available!"
        elif len(failed_checks) <= 2:
            overall_status = "⚠️ **PARTIAL SETUP** - Some components need installation"
        else:
            overall_status = "❌ **SETUP REQUIRED** - Multiple components missing"
        
        return f"""
🔍 **VOICE WORKFLOW SYSTEM STATUS**

{overall_status}

**📋 COMPONENT STATUS:**
{chr(10).join(status_checks)}

**🚀 QUICK SETUP GUIDE:**

**1. Install Chatterbox TTS:**
```bash
pip install chatterbox-tts
```

**2. Install Audio Dependencies:**
```bash
pip install librosa soundfile
```

**3. Google Drive Setup:**
- Download OAuth credentials from Google Cloud Console
- Save as `langgraph/credentials.json`
- Enable Google Drive API

**4. Add Your Voice:**
- Record 10-30 second clear audio sample
- Save as `langgraph/voice_samples/your_name.wav`
- Use `setup_voice_sample` tool to process

**📊 SYSTEM RECOMMENDATIONS:**
{
'🎯 System is ready for voice generation!' if not failed_checks else
'🔧 Install missing components for full functionality' if len(failed_checks) <= 2 else
'⚙️ Complete setup required before using voice features'
}
"""
        
    except Exception as e:
        return f"❌ Error checking voice workflow status: {str(e)}"

@tool 
async def voice_generation_help() -> str:
    """Get comprehensive help for voice generation and cloning workflow.
    
    Returns:
        Complete guide for using the voice generation system
    """
    return """
🎙️ **VOICE GENERATION & CLONING GUIDE**

## 🚀 QUICK START

**1. Generate Voice with Default Voice:**
```python
generate_voiceover(
    script_text="Your script here",
    emotion="neutral"
)
```

**2. Generate Voice with Your Voice:**
```python
# First setup your voice sample
setup_voice_sample(
    input_file_path="/path/to/your/voice.wav",
    voice_name="my_voice"
)

# Then generate with your voice
generate_voiceover(
    script_text="Your script here",
    voice_name="my_voice",
    emotion="dramatic"
)
```

**3. Complete Workflow (Generate + Upload):**
```python
complete_voice_workflow(
    script_text="Your script here",
    voice_name="my_voice",
    script_title="AMD GPU Review",
    emotion="excited",
    upload_to_gdrive=True
)
```

## 📋 AVAILABLE TOOLS

**Voice Generation:**
- `generate_voiceover()` - Convert text to speech
- `list_available_voices()` - Show available voice samples

**Voice Cloning Setup:**
- `setup_voice_sample()` - Process your voice for cloning
- `analyze_voice_quality()` - Check audio quality before setup

**Google Drive Integration:**
- `upload_voice_to_gdrive()` - Upload voice files to Drive
- `list_gdrive_voice_files()` - List uploaded voice files

**Workflow:**
- `complete_voice_workflow()` - End-to-end generation + upload
- `voice_workflow_status()` - Check system status

## 🎭 EMOTION STYLES

- **neutral** - Natural, conversational
- **dramatic** - Expressive, theatrical  
- **excited** - Energetic, enthusiastic
- **calm** - Gentle, soothing
- **expressive** - Varied tones, dynamic

## ⚙️ ADVANCED PARAMETERS

**exaggeration** (0.0-1.0):
- Lower = subtle, natural
- Higher = more expressive, dramatic

**cfg_weight** (0.0-1.0):
- Lower = faster speech
- Higher = slower, more deliberate

## 📁 FOLDER STRUCTURE

```
langgraph/
├── voice_samples/          # Your voice recordings
│   ├── my_voice.wav       # Your processed voice sample
│   └── README.md          # Recording instructions
├── generated_voices/      # Generated audio files
│   └── voice_*.wav        # Generated voiceovers
├── credentials.json       # Google Drive OAuth
└── token.json            # Google Drive token
```

## 🎤 RECORDING YOUR VOICE

**Best Practices:**
- **Duration:** 10-30 seconds (15-20 optimal)
- **Content:** Natural speech, varied tones
- **Environment:** Quiet room, good microphone
- **Quality:** 22kHz+, 16-bit+, minimal noise

**Example Recording Script:**
"Hello, this is my voice sample for cloning. I'm speaking clearly and naturally to create the best possible voice model. The weather is nice today, and I'm excited to see how this technology works with my unique voice characteristics."

## 🔧 TROUBLESHOOTING

**Common Issues:**
1. **"Model not found"** → Run: `pip install chatterbox-tts`
2. **"CUDA error"** → System will fallback to CPU automatically
3. **"Voice sample not found"** → Check file exists in `voice_samples/`
4. **"Google Drive auth failed"** → Setup credentials.json
5. **"Poor voice quality"** → Use `analyze_voice_quality()` tool

**Performance Tips:**
- Use CUDA GPU for faster generation
- Keep script text under 5000 characters
- Use WAV format for voice samples
- Record in quiet environment

## 📞 SUPPORT

Use `voice_workflow_status()` to check system setup and get specific error diagnostics.

🎉 **Ready to create amazing voiceovers!**
"""

# Complete voice workflow tools
voice_workflow_tools = [
    complete_voice_workflow, 
    voice_workflow_status, 
    voice_generation_help
] + voice_tools + gdrive_voice_tools + voice_cloning_tools