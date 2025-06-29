#!/usr/bin/env python3
"""
Monitor Google Drive final_draft folders and update Notion when videos are uploaded.
This script can be run manually or scheduled to check for new video uploads.
"""

import asyncio
import sys
import os
from typing import List, Dict

# Add the parent directory to the path so we can import our agents
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from agents.asset_gathering_agent import asset_gathering_tools
from agents.notion_agent import notion_tools

async def check_all_projects() -> List[Dict]:
    """Check all Notion projects for video uploads in their final_draft folders."""
    try:
        # Get list of all Notion projects with "Assets Ready" status
        list_tool = notion_tools[3]  # list_notion_projects
        projects_result = await list_tool.ainvoke("Assets Ready")
        
        print("📋 Checking all projects with 'Assets Ready' status...")
        print(projects_result)
        
        # Parse projects from result (this would need more sophisticated parsing in production)
        # For now, we'll return the raw result
        return [{"result": projects_result}]
        
    except Exception as e:
        print(f"❌ Error checking projects: {e}")
        return []

async def monitor_project_folder(folder_path: str) -> bool:
    """Monitor a specific project folder for video uploads."""
    try:
        print(f"🔍 Monitoring: {folder_path}")
        
        # Check final_draft folder for videos
        monitor_tool = asset_gathering_tools[2]  # monitor_final_draft_folder
        monitor_result = await monitor_tool.ainvoke(folder_path)
        
        print(monitor_result)
        
        # Check if video was detected
        if "VIDEO DETECTED" in monitor_result:
            print(f"🎬 Video found in {folder_path}!")
            
            # Extract video filename from result
            video_filename = "final_video.mp4"  # Default name
            if "Name:" in monitor_result:
                lines = monitor_result.split('\n')
                for line in lines:
                    if "Name:" in line:
                        video_filename = line.split("Name:")[1].strip()
                        break
            
            # Update Notion status
            update_tool = notion_tools[1]  # update_notion_video_status
            update_result = await update_tool.ainvoke({
                'folder_path': folder_path,
                'video_filename': video_filename
            })
            
            print("📋 Notion update result:")
            print(update_result)
            
            return True
        else:
            print(f"⏳ No video detected yet in {folder_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error monitoring {folder_path}: {e}")
        return False

async def manual_trigger_update(folder_path: str, video_filename: str = ""):
    """Manually trigger Notion update for a specific project."""
    try:
        print(f"🔄 Manually triggering update for: {folder_path}")
        
        update_tool = notion_tools[1]  # update_notion_video_status
        result = await update_tool.ainvoke({
            'folder_path': folder_path,
            'video_filename': video_filename or "final_video.mp4"
        })
        
        print("📋 Manual update result:")
        print(result)
        
    except Exception as e:
        print(f"❌ Manual update error: {e}")

async def get_project_summary(folder_path: str):
    """Get detailed summary of a project folder."""
    try:
        summary_tool = asset_gathering_tools[3]  # get_project_summary
        result = await summary_tool.ainvoke(folder_path)
        
        print(f"📊 Project Summary for {folder_path}:")
        print(result)
        
    except Exception as e:
        print(f"❌ Summary error: {e}")

async def main():
    """Main monitoring function."""
    print("🚀 Final Draft Monitor - Rocket Reels AI")
    print("=" * 50)
    
    if len(sys.argv) < 2:
        print("""
Usage:
    python monitor_final_draft.py <command> [options]

Commands:
    check-all                    - Check all projects for video uploads
    monitor <folder_path>        - Monitor specific project folder
    update <folder_path> [video] - Manually trigger Notion update
    summary <folder_path>        - Get project folder summary

Examples:
    python monitor_final_draft.py check-all
    python monitor_final_draft.py monitor "RocketReelsAI/AI_Breakthrough_20241228_1430"
    python monitor_final_draft.py update "RocketReelsAI/AI_Breakthrough_20241228_1430" "final_edit_v2.mp4"
    python monitor_final_draft.py summary "RocketReelsAI/AI_Breakthrough_20241228_1430"
""")
        return
    
    command = sys.argv[1].lower()
    
    if command == "check-all":
        await check_all_projects()
        
    elif command == "monitor" and len(sys.argv) >= 3:
        folder_path = sys.argv[2]
        video_detected = await monitor_project_folder(folder_path)
        if video_detected:
            print("✅ Video detected and Notion updated!")
        else:
            print("⏳ No new videos found")
            
    elif command == "update" and len(sys.argv) >= 3:
        folder_path = sys.argv[2]
        video_filename = sys.argv[3] if len(sys.argv) >= 4 else ""
        await manual_trigger_update(folder_path, video_filename)
        
    elif command == "summary" and len(sys.argv) >= 3:
        folder_path = sys.argv[2]
        await get_project_summary(folder_path)
        
    else:
        print("❌ Invalid command or missing arguments")
        print("Use 'python monitor_final_draft.py' for help")

if __name__ == "__main__":
    asyncio.run(main())