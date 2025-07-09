#!/usr/bin/env python3
"""
Production Workflow Runner
Simple script to execute the production workflow with proper graph structure.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from core.production_workflow import run_production_workflow

async def main():
    """Main runner function"""
    
    print("🚀 Production Workflow Runner")
    print("=" * 50)
    
    # Get topic from command line or use default
    if len(sys.argv) > 1:
        topic = " ".join(sys.argv[1:])
    else:
        topic = input("Enter topic for content creation (or press Enter for 'latest AI breakthrough'): ").strip()
        if not topic:
            topic = "latest AI breakthrough"
    
    print(f"🎯 Topic: {topic}")
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    try:
        # Run the workflow
        result = await run_production_workflow(topic)
        
        print("\n" + "=" * 50)
        print("📊 WORKFLOW SUMMARY")
        print("=" * 50)
        
        print(f"✅ Status: {result.current_step}")
        print(f"📝 Article ID: {result.article_id}")
        print(f"📜 Script ID: {result.script_id}")
        print(f"🎨 Images Generated: {len(result.images_generated)}")
        print(f"🎙️ Voice Files: {len(result.voice_files)}")
        print(f"⚠️ Errors: {len(result.errors)}")
        
        if result.errors:
            print("\n❌ ERRORS ENCOUNTERED:")
            for i, error in enumerate(result.errors, 1):
                print(f"  {i}. {error}")
        
        print("\n🎬 Production assets ready for video creation!")
        
    except Exception as e:
        print(f"❌ FATAL ERROR: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)