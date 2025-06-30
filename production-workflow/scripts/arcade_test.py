"""
Simple test for Arcade Agent using local video file
Tests the Twitter posting functionality without Google Drive
"""

import asyncio
import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Import arcade agent functionality
from agents.arcade_agent import SocialMediaClient

# Set up constants
ASSETS_FOLDER = os.path.join(parent_dir, "assets")
VIDEO_FILE = os.path.join(ASSETS_FOLDER, "rocket_reel_20250625_122424.mp4")

async def test_twitter_posting():
    """Test Twitter posting with local video file"""
    print("\n🚀 ARCADE AGENT TWITTER TEST")
    print("=" * 50)
    
    # Check if video file exists
    if not os.path.exists(VIDEO_FILE):
        print(f"❌ Error: Video file not found at {VIDEO_FILE}")
        print("Please check the assets folder and file name")
        return False
    
    print(f"✅ Found video file: {os.path.basename(VIDEO_FILE)}")
    print(f"📊 Size: {os.path.getsize(VIDEO_FILE) / (1024 * 1024):.2f} MB")
    
    # Initialize social media client
    print("\n📱 Initializing social media client...")
    client = SocialMediaClient()
    
    # Check Twitter credentials
    if not client.has_twitter:
        print("❌ Error: Twitter credentials missing or incomplete")
        print("Please check your .env file for Twitter API keys")
        return False
    
    print("✅ Twitter credentials found")
    print(f"🔑 Available platforms: {', '.join(client.available_platforms)}")
    
    # Prepare test caption
    test_caption = f"🚀 Testing Rocket Reels AI social media automation! #AITest #TechVideo {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    print(f"\n📝 Test caption: {test_caption}")
    
    # Attempt to publish to Twitter
    print("\n🐦 Attempting to publish to Twitter...")
    try:
        result = await client.publish_to_twitter(VIDEO_FILE, test_caption)
        
        if result.get("success"):
            print("\n✅ SUCCESS! Video published to Twitter")
            print(f"🔗 Post URL: {result.get('post_url')}")
            print(f"📝 Message: {result.get('message')}")
            return True
        else:
            print(f"\n❌ Publishing failed: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error during publishing: {str(e)}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Arcade Agent Twitter publishing")
    success = asyncio.run(test_twitter_posting())
    
    if success:
        print("\n🎉 TEST PASSED: Arcade Agent is working correctly!")
    else:
        print("\n⚠️ TEST FAILED: Arcade Agent needs troubleshooting")