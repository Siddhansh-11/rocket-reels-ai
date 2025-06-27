#!/usr/bin/env python3
"""Test script for voice generation with custom voice."""

import os
import sys
import asyncio

# Add langgraph to path
sys.path.append('langgraph')

async def test_voice_generation():
    """Test voice generation with your custom voice."""
    try:
        from voice_generation_agent import generate_voiceover
        
        # Test script
        test_script = "What if I told you… India just built an UNHACKABLE internet? This is a test of the voice cloning system."
        
        print("🎙️ Testing voice generation with your custom voice...")
        print(f"📝 Script: {test_script}")
        print(f"👤 Voice: my_voice")
        
        # Generate voiceover with your custom voice
        result = await generate_voiceover(
            script_text=test_script,
            voice_name="my_voice",  # Your custom voice
            emotion="neutral",
            exaggeration=0.5,
            cfg_weight=0.5
        )
        
        print("\n" + "="*50)
        print("RESULT:")
        print("="*50)
        print(result)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n🔧 Try installing missing dependencies:")
        print("pip install torch torchaudio")

if __name__ == "__main__":
    asyncio.run(test_voice_generation())