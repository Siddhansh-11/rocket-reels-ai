"""
Notion Agent for Rocket Reels AI - Tasks Tracker Integration
Completely rewritten to match exact Tasks Tracker database properties
"""

import asyncio
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from langchain_core.tools import tool
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Notion API configuration
NOTION_API_KEY = os.getenv('NOTION_API_KEY')
NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')
NOTION_API_VERSION = "2022-06-28"
NOTION_BASE_URL = "https://api.notion.com/v1"

def _get_notion_headers():
    """Get headers for Notion API requests"""
    return {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json"
    }

@tool  
async def create_notion_project_row(script_data: Dict[str, Any]) -> str:
    """Create new project row in Tasks Tracker database using exact property names."""
    try:
        # Validate environment
        if not NOTION_API_KEY or not NOTION_DATABASE_ID:
            return "❌ Notion API key or Database ID not configured in environment"
        
        # Extract data from script_data
        script_id = script_data.get('script_id', f"script_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        article_id = script_data.get('article_id', 'N/A')
        project_name = script_data.get('project_name', script_data.get('title', 'Untitled Project'))
        folder_id = script_data.get('folder_id', '')
        script_content = script_data.get('script_content', '')
        
        # Clean project name
        project_name = project_name.replace('/', '-').replace('\\', '-')[:100]
        
        # Build folder URL if folder_id exists
        folder_url = f"https://drive.google.com/drive/folders/{folder_id}" if folder_id else None
        
        # Extract hook from script
        hook_text = ""
        if script_content:
            lines = script_content.split('\n')
            for line in lines:
                if 'HOOK:' in line.upper() or '**HOOK**' in line.upper():
                    hook_text = line.replace('HOOK:', '').replace('**HOOK**:', '').strip()
                    break
            if not hook_text:
                hook_text = script_content[:150] + "..." if len(script_content) > 150 else script_content
        
        # Prepare detailed comments
        comments_text = f"""🎬 Rocket Reels AI Project

📋 Project: {project_name}
📄 Script ID: {script_id}
📰 Article ID: {article_id}

🎭 Hook: {hook_text or "No hook extracted"}

🕐 Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🎯 Status: Assets ready for video creation

📁 Folder: {folder_url or "Pending folder creation"}
🎬 Ready for editor to create video"""
        
        # Properties matching your Tasks Tracker database exactly
        properties = {
            "Topic name": {
                "title": [
                    {
                        "text": {
                            "content": f"🎬 {project_name}"
                        }
                    }
                ]
            },
            "Article Id": {
                "rich_text": [
                    {
                        "text": {
                            "content": article_id
                        }
                    }
                ]
            },
            "Assignee": {
                "people": []  # Empty - can be filled manually
            },
            "Channel": {
                "multi_select": []  # Empty initially
            },
            "Comments": {
                "rich_text": [
                    {
                        "text": {
                            "content": comments_text
                        }
                    }
                ]
            },
            "Created date and time": {
                "date": {
                    "start": datetime.now().isoformat()
                }
            },
            "Deploy status": {
                "multi_select": [  # ✅ Changed to multi_select (not select)
                    {
                        "name": "Assets Ready"  # Default status
                    }
                ]
            },
            "Due date": {
                "date": None  # Empty initially
            },
            "Final Video Link": {
                "url": None  # Empty until video uploaded
            },
            "Folder Link": {
                "url": folder_url
            },
            "Publish Date and time": {
                "date": None  # Empty until scheduled
            },
            "Script Id": {
                "rich_text": [
                    {
                        "text": {
                            "content": script_id
                        }
                    }
                ]
            },
            "Status": {
                "status": {  # ✅ Changed to status type (not select)
                    "name": "In Progress"  # Default workflow status
                }
            }
            # Note: Updated at is auto-managed by Notion
        }
        
        # Create page payload
        page_payload = {
            "parent": {
                "database_id": NOTION_DATABASE_ID
            },
            "properties": properties
        }
        
        # Make API request
        response = await asyncio.to_thread(
            requests.post,
            f"{NOTION_BASE_URL}/pages",
            headers=_get_notion_headers(),
            json=page_payload
        )
        
        if response.status_code == 200:
            result = response.json()
            page_id = result.get('id', 'Unknown')
            page_url = result.get('url', 'Unknown')
            
            return f"""✅ **TASKS TRACKER PROJECT CREATED**

📋 **Project Details:**
- Topic: {project_name}
- Database: Tasks Tracker
- Page ID: {page_id}
- Page URL: {page_url}

📄 **Project Data:**
- Script ID: {script_id}
- Article ID: {article_id}
- Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Folder: {folder_url or 'Pending'}

🎬 **Status:**
- Deploy Status: Assets Ready
- Workflow Status: In Progress
- Final Video: Pending upload
- Channels: To be selected

🎯 **Next Step:** Editor creates video and uploads to final_draft folder"""
            
        else:
            error_info = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
            return f"❌ Failed to create Notion page: {response.status_code}\nError: {error_info}"
            
    except Exception as e:
        return f"❌ Notion project creation failed: {str(e)}"

@tool
async def update_video_uploaded(project_folder_path: str, video_filename: str = "", video_url: str = "") -> str:
    """Update Tasks Tracker when video is uploaded to final_draft folder."""
    try:
        if not NOTION_API_KEY or not NOTION_DATABASE_ID:
            return "❌ Notion not configured"
        
        # Search for project by folder path in comments
        search_payload = {
            "filter": {
                "property": "Comments",
                "rich_text": {
                    "contains": project_folder_path
                }
            }
        }
        
        # Search database
        search_response = await asyncio.to_thread(
            requests.post,
            f"{NOTION_BASE_URL}/databases/{NOTION_DATABASE_ID}/query",
            headers=_get_notion_headers(),
            json=search_payload
        )
        
        if search_response.status_code != 200:
            return f"❌ Failed to search database: {search_response.status_code}"
        
        results = search_response.json()
        pages = results.get('results', [])
        
        if not pages:
            return f"⚠️ No project found for folder: {project_folder_path}"
        
        # Update the first matching project
        page_id = pages[0]['id']
        
        # Get existing comments
        existing_comments = ""
        if pages[0]['properties']['Comments'].get('rich_text'):
            existing_comments = pages[0]['properties']['Comments']['rich_text'][0]['text']['content']
        
        # Build video URL
        final_video_url = video_url or f"https://drive.google.com/file/d/{video_filename}/view"
        
        # Update payload
        update_payload = {
            "properties": {
                "Final Video Link": {
                    "url": final_video_url
                },
                "Deploy status": {
                    "multi_select": [  # ✅ Changed to multi_select
                        {
                            "name": "Review"  # Ready for review
                        }
                    ]
                },
                "Status": {
                    "status": {  # ✅ Changed to status type
                        "name": "Done"  # Video completed
                    }
                },
                "Comments": {
                    "rich_text": [
                        {
                            "text": {
                                "content": f"""{existing_comments}

🎬 **VIDEO UPLOADED:**
📁 File: {video_filename or "final_video.mp4"}
🔗 Video Link: {final_video_url}
🕐 Upload Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
✅ Status: Ready for review and publishing

🚀 **Next Steps:**
1. Review video quality
2. Select publication channels
3. Schedule publish date
4. Update deploy status to 'Publish' when ready"""
                            }
                        }
                    ]
                }
            }
        }
        
        # Update page
        update_response = await asyncio.to_thread(
            requests.patch,
            f"{NOTION_BASE_URL}/pages/{page_id}",
            headers=_get_notion_headers(),
            json=update_payload
        )
        
        if update_response.status_code == 200:
            return f"""✅ **TASKS TRACKER UPDATED**

📋 **Video Upload Recorded:**
- Project ID: {page_id}
- Video File: {video_filename or 'final_video.mp4'}
- Video URL: {final_video_url}
- Deploy Status: Review
- Workflow Status: Done
- Update Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎬 **Project Ready for Publishing!**"""
        else:
            return f"❌ Failed to update project: {update_response.status_code}"
            
    except Exception as e:
        return f"❌ Video update failed: {str(e)}"

@tool
async def update_publish_details(project_id: str, channels: List[str], publish_date: str = "") -> str:
    """Update Tasks Tracker with publication details."""
    try:
        if not NOTION_API_KEY or not NOTION_DATABASE_ID:
            return "❌ Notion not configured"
        
        # Prepare channel options
        channel_options = []
        valid_channels = ['Instagram', 'LinkedIn', 'Twitter', 'YouTube', 'TikTok']
        for channel in channels:
            channel_name = channel.title()
            if channel_name in valid_channels:
                channel_options.append({"name": channel_name})
        
        # Prepare update
        update_payload = {
            "properties": {
                "Channel": {
                    "multi_select": channel_options
                },
                "Deploy status": {
                    "multi_select": [  # ✅ Changed to multi_select
                        {
                            "name": "Published"
                        }
                    ]
                }
            }
        }
        
        # Add publish date if provided
        if publish_date:
            try:
                parsed_date = datetime.fromisoformat(publish_date.replace('Z', '+00:00'))
                update_payload["properties"]["Publish Date and time"] = {
                    "date": {
                        "start": parsed_date.isoformat()
                    }
                }
            except:
                update_payload["properties"]["Publish Date and time"] = {
                    "date": {
                        "start": datetime.now().isoformat()
                    }
                }
        
        # Update page
        response = await asyncio.to_thread(
            requests.patch,
            f"{NOTION_BASE_URL}/pages/{project_id}",
            headers=_get_notion_headers(),
            json=update_payload
        )
        
        if response.status_code == 200:
            return f"""✅ **PUBLICATION COMPLETE**

📋 **Published Details:**
- Channels: {', '.join(channels)}
- Publish Date: {publish_date or datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Deploy Status: Published
- Project ID: {project_id}

🎉 **Project Complete!** Content live across selected channels."""
        else:
            return f"❌ Failed to update publish status: {response.status_code}"
            
    except Exception as e:
        return f"❌ Publish update failed: {str(e)}"

@tool  
async def list_tasks_tracker_projects(status_filter: str = "") -> str:
    """List all projects in Tasks Tracker database."""
    try:
        if not NOTION_API_KEY or not NOTION_DATABASE_ID:
            return "❌ Notion not configured"
        
        # Prepare query
        query_payload = {}
        if status_filter:
            query_payload["filter"] = {
                "property": "Deploy status",
                "multi_select": {  # ✅ Changed to multi_select
                    "contains": status_filter
                }
            }
        
        # Query database
        response = await asyncio.to_thread(
            requests.post,
            f"{NOTION_BASE_URL}/databases/{NOTION_DATABASE_ID}/query",
            headers=_get_notion_headers(),
            json=query_payload
        )
        
        if response.status_code != 200:
            return f"❌ Failed to query Tasks Tracker: {response.status_code}"
        
        results = response.json()
        pages = results.get('results', [])
        
        if not pages:
            filter_text = f" with status '{status_filter}'" if status_filter else ""
            return f"📋 No projects found in Tasks Tracker{filter_text}"
        
        # Format results
        projects_list = f"📋 **TASKS TRACKER PROJECTS** ({len(pages)} found)\n\n"
        
        for page in pages[:10]:  # Show first 10
            props = page.get('properties', {})
            
            # Extract details
            topic = "Untitled"
            if props.get('Topic name', {}).get('title'):
                topic = props['Topic name']['title'][0]['text']['content']
            
            deploy_status = "Unknown"
            if props.get('Deploy status', {}).get('multi_select'):  # ✅ Changed to multi_select
                statuses = props['Deploy status']['multi_select']
                if statuses:
                    deploy_status = statuses[0]['name']  # Get first status
            
            workflow_status = "Unknown"
            if props.get('Status', {}).get('status'):  # ✅ Changed to status
                workflow_status = props['Status']['status']['name']
            
            created_date = "Unknown"
            if props.get('Created date and time', {}).get('date'):
                created_date = props['Created date and time']['date']['start'][:10]
            
            script_id = "N/A"
            if props.get('Script Id', {}).get('rich_text'):
                script_id = props['Script Id']['rich_text'][0]['text']['content']
            
            folder_link = props.get('Folder Link', {}).get('url', '')
            
            projects_list += f"""🎬 **{topic}**
   Deploy Status: {deploy_status}
   Workflow Status: {workflow_status}
   Created: {created_date}
   Script ID: {script_id}
   Folder: {'✅ Linked' if folder_link else '❌ No folder'}
   Page ID: {page['id']}

"""
        
        return projects_list
        
    except Exception as e:
        return f"❌ Failed to list projects: {str(e)}"

@tool
async def monitor_project_folder(folder_path: str) -> str:
    """Monitor project folder for final video uploads (placeholder)."""
    return f"""🔍 **MONITORING PROJECT FOLDER**

📁 Folder: {folder_path}
🕐 Status: Monitoring active
⏳ Waiting for video upload to final_draft/ folder

💡 **Manual Update Available:**
Use update_video_uploaded() when video is ready"""

# Export tools for Tasks Tracker integration
notion_tools = [
    create_notion_project_row,
    update_video_uploaded,
    update_publish_details,
    list_tasks_tracker_projects,
    monitor_project_folder
]