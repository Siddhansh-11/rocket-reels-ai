# test_voice_cloning.py
import os
import sys
import asyncio
from pathlib import Path

# Add the current directory to Python path
sys.path.append(str(Path(__file__).parent))

from voice_cloning_setup import VoiceCloningSetup, setup_voice_sample, analyze_voice_quality
from voice_generation_agent import VoiceGenerationAgent, generate_voiceover

async def test_voice_cloning_workflow():
    """Complete test of voice cloning workflow."""
    print("🧪 VOICE CLONING TEST SUITE")
    print("=" * 50)
    
    # Test data
    input_audio_path = "audio.wav"  # Use relative path
    voice_name = "my_voice_test"
    test_script = "Hello, this is a test of my voice cloning system. I'm speaking clearly to verify that the voice cloning is working correctly."
    
    # Step 1: Check if input file exists
    print("\n📁 STEP 1: Checking input audio file...")
    if not os.path.exists(input_audio_path):
        print(f"❌ Input audio file not found: {input_audio_path}")
        return False
    
    file_size = os.path.getsize(input_audio_path) / 1024  # KB
    print(f"✅ Input file found: {input_audio_path} ({file_size:.1f}KB)")
    
    # Step 2: Analyze voice quality
    print("\n📊 STEP 2: Analyzing voice quality...")
    try:
        quality_result = await analyze_voice_quality.ainvoke({"file_path": input_audio_path})
        print(quality_result)
        
        # Check if quality is acceptable
        if "Poor" in quality_result or "❌" in quality_result:
            print("\n⚠️ WARNING: Voice quality may be too low for good cloning")
            user_continue = input("\nContinue anyway? (y/n): ")
            if user_continue.lower() != 'y':
                return False
    except Exception as e:
        print(f"❌ Quality analysis failed: {e}")
        return False
    
    # Step 3: Setup voice sample
    print("\n🔧 STEP 3: Setting up voice sample...")
    try:
        setup_result = await setup_voice_sample.ainvoke({
            "input_file_path": input_audio_path,
            "voice_name": voice_name,
            "normalize": True
        })
        print(setup_result)
        
        if "❌" in setup_result:
            print("Setup failed, cannot continue")
            return False
            
    except Exception as e:
        print(f"❌ Voice setup failed: {e}")
        return False
    
    # Step 4: Generate voice with DEFAULT voice (baseline)
    print("\n🎙️ STEP 4: Testing DEFAULT voice generation...")
    try:
        default_result = await generate_voiceover.ainvoke({
            "script_text": test_script,
            "voice_name": "default",
            "emotion": "neutral",
            "exaggeration": 0.5,
            "cfg_weight": 0.5
        })
        print("DEFAULT VOICE RESULT:")
        print(default_result)
        
        # Extract default voice file path
        default_voice_path = None
        if "Local Path:" in default_result:
            for line in default_result.split('\n'):
                if "Local Path:" in line:
                    default_voice_path = line.split("Local Path:")[1].strip()
                    break
        
    except Exception as e:
        print(f"❌ Default voice generation failed: {e}")
        return False
    
    # Step 5: Generate voice with YOUR voice (cloned)
    print(f"\n🎭 STEP 5: Testing CLONED voice generation with '{voice_name}'...")
    try:
        cloned_result = await generate_voiceover.ainvoke({
            "script_text": test_script,
            "voice_name": voice_name,
            "emotion": "neutral",
            "exaggeration": 0.5,
            "cfg_weight": 0.5
        })
        print("CLONED VOICE RESULT:")
        print(cloned_result)
        
        # Extract cloned voice file path
        cloned_voice_path = None
        if "Local Path:" in cloned_result:
            for line in cloned_result.split('\n'):
                if "Local Path:" in line:
                    cloned_voice_path = line.split("Local Path:")[1].strip()
                    break
        
    except Exception as e:
        print(f"❌ Cloned voice generation failed: {e}")
        return False
    
    # Step 6: Compare file sizes and durations
    print("\n📊 STEP 6: Comparing generated voices...")
    
    files_to_compare = [
        ("Original Sample", input_audio_path),
        ("Default Voice", default_voice_path),
        ("Cloned Voice", cloned_voice_path)
    ]
    
    print("\nFILE COMPARISON:")
    for name, path in files_to_compare:
        if path and os.path.exists(path):
            size_kb = os.path.getsize(path) / 1024
            print(f"  {name}: {os.path.basename(path)} ({size_kb:.1f}KB)")
        else:
            print(f"  {name}: ❌ File not found")
    
    # Step 7: Test different emotions with cloned voice
    print(f"\n🎭 STEP 7: Testing different emotions with cloned voice...")
    emotions_to_test = ["dramatic", "excited", "calm"]
    
    for emotion in emotions_to_test:
        print(f"\n  Testing emotion: {emotion}")
        try:
            emotion_result = await generate_voiceover.ainvoke({
                "script_text": f"This is a {emotion} test of my voice clone.",
                "voice_name": voice_name,
                "emotion": emotion,
                "exaggeration": 0.7 if emotion in ["dramatic", "excited"] else 0.3,
                "cfg_weight": 0.3 if emotion in ["dramatic", "excited"] else 0.7
            })
            
            # Extract just the essential info
            if "VOICEOVER GENERATED SUCCESSFULLY" in emotion_result:
                lines = emotion_result.split('\n')
                for line in lines:
                    if "Audio File:" in line or "Duration:" in line or "Local Path:" in line:
                        print(f"    {line.strip()}")
            else:
                print(f"    ❌ Failed to generate {emotion} voice")
                
        except Exception as e:
            print(f"    ❌ Error with {emotion}: {e}")
    
    # Step 8: Manual comparison instructions
    print("\n🔍 STEP 8: Manual Comparison Instructions")
    print("=" * 50)
    print("To verify if voice cloning is working:")
    print("\n1. LISTEN TO YOUR ORIGINAL SAMPLE:")
    print(f"   File: {input_audio_path}")
    print("   Listen for: Your voice characteristics, tone, accent")
    
    print("\n2. LISTEN TO DEFAULT VOICE:")
    if default_voice_path:
        print(f"   File: {default_voice_path}")
    print("   This should sound like the base AI voice (not like you)")
    
    print("\n3. LISTEN TO CLONED VOICE:")
    if cloned_voice_path:
        print(f"   File: {cloned_voice_path}")
    print("   This should sound similar to your original voice")
    
    print("\n4. COMPARISON CHECKLIST:")
    print("   ✓ Does cloned voice sound more like you than default?")
    print("   ✓ Are speech patterns similar to your sample?")
    print("   ✓ Is the tone/pitch closer to your voice?")
    print("   ✓ Do you hear your accent/characteristics?")
    
    print("\n🎯 EXPECTED RESULTS:")
    print("   • Default voice: Generic AI voice")
    print("   • Cloned voice: Should resemble your voice characteristics")
    print("   • If they sound the same: Voice cloning may not be working")
    
    # Step 9: Troubleshooting suggestions
    print("\n🔧 TROUBLESHOOTING GUIDE:")
    print("=" * 30)
    print("If cloned voice doesn't sound like you:")
    print("\n1. CHECK VOICE SAMPLE QUALITY:")
    print("   • Re-record with better microphone")
    print("   • Ensure 15-30 seconds of clear speech")
    print("   • Record in quiet environment")
    print("   • Speak naturally with varied tones")
    
    print("\n2. TRY DIFFERENT PARAMETERS:")
    print("   • Increase exaggeration (0.7-0.9)")
    print("   • Adjust cfg_weight (0.2-0.8)")
    print("   • Test different emotions")
    
    print("\n3. CHECK CHATTERBOX VERSION:")
    print("   • Ensure latest version installed")
    print("   • Check CUDA availability for better processing")
    
    print("\n4. VERIFY FILE PATHS:")
    print("   • Ensure voice sample is in correct location")
    print("   • Check file permissions")
    
    return True

async def quick_voice_test():
    """Quick test to check if voice cloning is working at all."""
    print("🚀 QUICK VOICE CLONING TEST")
    print("=" * 30)
    
    # Check if voice sample exists
    voice_sample_path = "voice_samples/my_voice_test.wav"
    if not os.path.exists(voice_sample_path):
        print("❌ No processed voice sample found")
        print("Run the full test first: python test_voice_cloning.py")
        return
    
    print("✅ Found processed voice sample")
    
    # Quick generation test
    test_text = "Quick test to check if my voice clone works."
    
    print("\n🎙️ Generating with cloned voice...")
    try:
        result = await generate_voiceover.ainvoke({
            "script_text": test_text,
            "voice_name": "my_voice_test",
            "emotion": "neutral"
        })
        
        if "VOICEOVER GENERATED SUCCESSFULLY" in result:
            # Extract file path
            for line in result.split('\n'):
                if "Local Path:" in line:
                    file_path = line.split("Local Path:")[1].strip()
                    print(f"✅ Generated: {file_path}")
                    print("\n🎧 Listen to this file and compare with your original sample!")
                    break
        else:
            print("❌ Generation failed")
            print(result)
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("Voice Cloning Test Options:")
    print("1. Full test (setup + generation + comparison)")
    print("2. Quick test (generation only)")
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == "1":
        asyncio.run(test_voice_cloning_workflow())
    elif choice == "2":
        asyncio.run(quick_voice_test())
    else:
        print("Invalid choice. Running full test...")
        asyncio.run(test_voice_cloning_workflow())