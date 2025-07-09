#!/usr/bin/env python3
"""
Test script to verify image generation functionality in orchestrator
"""

import asyncio
import os
import sys
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from image_generation_agent import ImageGenerationAgent

async def test_image_generation_availability():
    """Test if image generation services are available"""
    print("🔍 Testing Image Generation Service Availability")
    print("=" * 50)
    
    agent = ImageGenerationAgent()
    
    print(f"Together AI Available: {agent.together_available}")
    print(f"Together API Key Set: {'Yes' if agent.together_api_key else 'No'}")
    print(f"Together Client Ready: {'Yes' if agent.together_client else 'No'}")
    
    if agent.together_available and agent.together_client:
        print("✅ Together AI is ready for image generation!")
        return True
    else:
        print("❌ Together AI not ready. Check API key and installation.")
        return False

async def test_single_image_generation():
    """Test generating a single image"""
    print("\n🎨 Testing Single Image Generation")
    print("=" * 50)
    
    agent = ImageGenerationAgent()
    
    test_prompt = "A modern rocket ship launching into space with AI circuits, futuristic style"
    
    try:
        result = await agent.generate_image_together(
            prompt=test_prompt,
            width=1024,
            height=576
        )
        
        if result['status'] == 'success':
            print("✅ Image generation successful!")
            print(f"Model: {result.get('model', 'N/A')}")
            print(f"File: {result.get('file_path', 'N/A')}")
            return True
        else:
            print(f"❌ Generation failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

if __name__ == "__main__":
    async def main():
        print("🚀 Rocket Reels AI - Orchestrator Image Generation Test")
        print("=====================================================\n")
        
        # Test availability
        available = await test_image_generation_availability()
        
        # Test generation if available
        generation_success = False
        if available:
            generation_success = await test_single_image_generation()
        
        print("\n📊 Test Summary")
        print("=" * 20)
        print(f"Service Available: {'✅' if available else '❌'}")
        print(f"Generation Test: {'✅' if generation_success else '❌'}")
        
        if available and generation_success:
            print("\n🎉 Image generation is working correctly!")
        else:
            print("\n⚠️ Image generation needs attention.")
            if not available:
                print("  - Check Together AI API key in .env file")
                print("  - Ensure 'together' package is installed")
    
    asyncio.run(main())