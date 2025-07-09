#!/usr/bin/env python3
"""
Monitor for new videos ready for social media publishing
"""

import os
import asyncio
import json
import time
from datetime import datetime
from dotenv import load_dotenv

# Import tools from agents
from ..agents.notion_agent import list_tasks_tracker_projects
from ..agents.arcade_agent import monitor_final_draft_folder, publish_video_to_social_media

# Load environment variables
load_dotenv()

# Configuration - Set default folder ID
FINAL_DRAFT_FOLDER_ID = os.getenv("FINAL_DRAFT_FOLDER_ID", "")

async def check_for_new_videos():
    """Check for newly uploaded videos ready for social media publishing"""
    print("🔍 Checking for videos ready to publish...")
    
    try:
        # Get all projects with "Review" deploy status
        projects_data = await list_tasks_tracker_projects("Review")
        if "No projects found" in projects_data:
            print("📋 No projects with 'Review' status found")
            return
        
        # Check videos in final_draft folder
        videos_data = await monitor_final_draft_folder(FINAL_DRAFT_FOLDER_ID)
        if "No videos found" in videos_data:
            print("📋 No videos found in final_draft folder")
            return
        
        print("\n" + "-"*50)
        print("📋 PROJECTS READY FOR PUBLISHING:")
        print(projects_data)
        print("\n" + "-"*50)
        print("📹 VIDEOS READY FOR PUBLISHING:")
        print(videos_data)
        print("\n" + "-"*50)
        print("⚠️ MANUAL ACTION REQUIRED:")
        print("Use publish_video_to_social_media tool to publish videos to social media platforms")
    
    except Exception as e:
        print(f"❌ Error checking for new videos: {str(e)}")

def monitor_continuously():
    """Run continuous monitoring for new videos"""
    print("🚀 Starting Social Media Publishing Monitor")
    print(f"📂 Monitoring final_draft folder: {FINAL_DRAFT_FOLDER_ID}")
    print("⏱️ Checking every 10 minutes")
    print("Press Ctrl+C to stop\n")
    
    while True:
        try:
            asyncio.run(check_for_new_videos())
            time.sleep(600)  # Check every 10 minutes
        except KeyboardInterrupt:
            print("\n⏹️ Monitor stopped")
            break
        except Exception as e:
            print(f"❌ Error in monitor: {str(e)}")
            time.sleep(600)  # Continue even after error

if __name__ == "__main__":
    if not FINAL_DRAFT_FOLDER_ID:
        print("❌ FINAL_DRAFT_FOLDER_ID not set in .env file")
        print("Please set it and restart the script")
        exit(1)
    
    monitor_continuously()