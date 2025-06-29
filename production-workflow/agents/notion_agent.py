import asyncio
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from langchain_core.tools import tool
import requests
import time
from dotenv import load_dotenv  # ← ADD THIS MISSING IMPORT

# Notion API configuration
load_dotenv()  # ← ADD THIS LINE TO LOAD .env VARIABLES
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
    """Create new project tracking row in Notion database with enhanced schema."""
    try:
        # Extract required fields
        script_id = script_data.get('script_id', '')
        article_id = script_data.get('article_id', '')
        project_name = script_data.get('project_name', script_data.get('title', 'Untitled'))
        folder_path = script_data.get('folder_path', '')
        article_title = script_data.get('article_title', script_data.get('title', ''))
        script_content = script_data.get('script_content', '')
        
        if not script_id:
            return "❌ Script ID is required for Notion project creation"
        
        # Extract hook from script content
        script_hook = ""
        if script_content:
            lines = script_content.split('\n')
            for line in lines:
                if 'HOOK:' in line.upper() or line.strip().startswith('**HOOK'):
                    script_hook = line.replace('HOOK:', '').replace('**HOOK**:', '').strip()
                    break
            if not script_hook and script_content:
                script_hook = script_content[:100] + "..." if len(script_content) > 100 else script_content
        
        # Extract visual suggestions
        visual_suggestions = script_data.get('visual_suggestions', [])
        if not visual_suggestions and script_content:
            visual_suggestions = [
                "Professional background presentation",
                "Technology-focused graphics", 
                "Modern UI/UX elements"
            ]
        
        # Initialize Notion client
        notion_token = os.getenv('NOTION_API_KEY')
        database_id = os.getenv('NOTION_DATABASE_ID')
        
        if not notion_token or not database_id:
            return "❌ Notion API key or database ID not found in environment variables"
        
        # Sanitize project name
        project_name = project_name.replace('/', '-').replace('\\', '-')[:100]
        
        # Create folder URL (assuming RocketReelsAI structure)
        folder_url = f"https://drive.google.com/drive/folders/{script_data.get('folder_id', '')}" if script_data.get('folder_id') else ""
        
        # Prepare description with all video project details
        description_content = f"""🎬 Video Project Details:

📋 Project: {project_name}
📄 Script ID: {script_id or "N/A"}
📰 Article ID: {article_id or "N/A"}

🎭 Script Hook:
{(script_hook[:300] + "...") if len(script_hook) > 300 else script_hook or "No hook"}

🎨 Visual Suggestions:
{chr(10).join([f"• {suggestion}" for suggestion in visual_suggestions[:3]]) if visual_suggestions else "• None"}

🕐 Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🎯 Status: Assets ready for editing"""

        # Enhanced Notion page properties for new schema
        notion_properties = {
            "Topic name": {  # Main project identifier
                "title": [
                    {
                        "text": {
                            "content": f"{project_name}"
                        }
                    }
                ]
            },
            "Final video link": {  # URL field - empty initially
                "url": None
            },
            "Folder link": {  # Google Drive folder URL
                "url": folder_url if folder_url else None
            },
            "Created Date and time": {  # Date & time when project created
                "date": {
                    "start": datetime.now().isoformat()
                }
            },
            "Publish Date and time": {  # Date & time when published - empty initially
                "date": None
            },
            "Channel": {  # Multi-select for publication channels
                "multi_select": []  # Empty initially, filled when published
            },
            "Deploy Status": {  # Select field for editor workflow
                "select": {
                    "name": "Review"  # Default status when assets are ready
                }
            },
            "Comments": {  # Rich text for editor/team comments
                "rich_text": [
                    {
                        "text": {
                            "content": description_content
                        }
                    }
                ]
            }
        }
        
        # Create page payload
        page_data = {
            "parent": {
                "database_id": database_id
            },
            "properties": notion_properties
        }
        
        # Make API request to create page
        response = await asyncio.to_thread(
            requests.post,
            f"{NOTION_BASE_URL}/pages",
            headers=_get_notion_headers(),
            json=page_data
        )
        
        if response.status_code == 200:
            page_info = response.json()
            page_id = page_info.get('id', 'Unknown')
            page_url = page_info.get('url', '#')
            
            return f"""✅ **NOTION PROJECT CREATED**

📋 **Project Details:**
- Topic: {project_name}
- Status: Review (Assets Ready)
- Notion Page ID: {page_id}
- Page URL: {page_url}

📁 **Linked Data:**
- Script ID: {script_id}
- Article ID: {article_id}
- Folder Link: {folder_url or 'Pending'}
- Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎬 **Workflow Status:**
- ✅ Assets Ready
- 📝 Deploy Status: Review
- 🎥 Final Video: Pending upload
- 📅 Publish Date: To be scheduled
- 📢 Channels: To be selected

🎯 **Next Step:** Editor reviews assets and uploads final video"""
            
        else:
            error_detail = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
            return f"❌ Failed to create Notion page: {response.status_code} - {error_detail}"
            
    except Exception as e:
        return f"❌ Notion integration error: {str(e)}"

@tool
async def update_notion_video_status(folder_path: str, video_filename: str = "", video_url: str = "") -> str:
    """Update Notion project when final video is uploaded."""
    try:
        if not NOTION_API_KEY or not NOTION_DATABASE_ID:
            return "❌ Notion API key or Database ID not configured"
        
        # Search for project by folder link
        query_payload = {
            "filter": {
                "property": "Comments", 
                "rich_text": {
                    "contains": folder_path
                }
            }
        }
        
        # Query database for matching project
        search_response = await asyncio.to_thread(
            requests.post,
            f"{NOTION_BASE_URL}/databases/{NOTION_DATABASE_ID}/query",
            headers=_get_notion_headers(),
            json=query_payload
        )
        
        if search_response.status_code != 200:
            return f"❌ Failed to search Notion database: {search_response.status_code}"
        
        search_results = search_response.json()
        pages = search_results.get('results', [])
        
        if not pages:
            return f"⚠️ No matching project found for folder path: {folder_path}"
        
        # Update the first matching page
        page_id = pages[0]['id']
        
        # Prepare update payload for enhanced schema
        update_payload = {
            "properties": {
                "Final video link": {
                    "url": video_url if video_url else f"https://drive.google.com/file/d/{video_filename}/view"
                },
                "Deploy Status": {
                    "select": {
                        "name": "Publish"  # Ready for publishing
                    }
                },
                "Comments": {
                    "rich_text": [
                        {
                            "text": {
                                "content": f"""{pages[0]['properties']['Comments']['rich_text'][0]['text']['content'] if pages[0]['properties']['Comments'].get('rich_text') else ''}

🎬 VIDEO UPLOADED:
📁 File: {video_filename or "final_video.mp4"}
🔗 Video Link: {video_url or 'Drive file uploaded'}
🕐 Upload Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
✅ Status: Ready for publishing

🎯 Next: Select channels and schedule publish date"""
                            }
                        }
                    ]
                }
            }
        }
        
        # Update the page
        update_response = await asyncio.to_thread(
            requests.patch,
            f"{NOTION_BASE_URL}/pages/{page_id}",
            headers=_get_notion_headers(),
            json=update_payload
        )
        
        if update_response.status_code == 200:
            return f"""✅ **NOTION STATUS UPDATED**

📋 **Project Updated:**
- Page ID: {page_id}
- Deploy Status: Publish (Ready)
- Final Video: {video_filename or 'final_video.mp4'}
- Video Link: {video_url or 'Available in Drive'}
- Upload Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🚀 **Next Steps:**
1. Select publication channels (Instagram/LinkedIn/Twitter)
2. Schedule publish date and time
3. Update deploy status to 'Published' when live"""
        else:
            error_detail = update_response.json() if update_response.headers.get('content-type', '').startswith('application/json') else update_response.text
            return f"❌ Failed to update Notion page: {update_response.status_code} - {error_detail}"
            
    except Exception as e:
        return f"❌ Notion update error: {str(e)}"

@tool
async def update_publish_status(project_id: str, channels: List[str], publish_date: str = "") -> str:
    """Update Notion project with publication details."""
    try:
        if not NOTION_API_KEY or not NOTION_DATABASE_ID:
            return "❌ Notion API key or Database ID not configured"
        
        # Prepare channel multi-select options
        channel_options = []
        for channel in channels:
            if channel.lower() in ['instagram', 'linkedin', 'twitter']:
                channel_options.append({"name": channel.title()})
        
        # Prepare update payload
        update_payload = {
            "properties": {
                "Channel": {
                    "multi_select": channel_options
                },
                "Deploy Status": {
                    "select": {
                        "name": "Published"
                    }
                }
            }
        }
        
        # Add publish date if provided
        if publish_date:
            try:
                # Parse and format date
                from datetime import datetime
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
        
        # Update the page
        update_response = await asyncio.to_thread(
            requests.patch,
            f"{NOTION_BASE_URL}/pages/{project_id}",
            headers=_get_notion_headers(),
            json=update_payload
        )
        
        if update_response.status_code == 200:
            return f"""✅ **PUBLISHED STATUS UPDATED**

📋 **Publication Details:**
- Channels: {', '.join(channels)}
- Publish Date: {publish_date or datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Deploy Status: Published
- Project ID: {project_id}

🎉 **Project Complete!** Content successfully published across selected channels."""
        else:
            return f"❌ Failed to update publish status: {update_response.status_code}"
            
    except Exception as e:
        return f"❌ Publish status update error: {str(e)}"

@tool
async def monitor_gdrive_folder(folder_path: str) -> str:
    """Monitor Google Drive folder for changes (placeholder function)."""
    return f"🔍 Monitoring {folder_path} - Feature coming soon"

@tool  
async def list_notion_projects(status_filter: str = "") -> str:
    """List all projects in Notion database with optional status filter."""
    try:
        if not NOTION_API_KEY or not NOTION_DATABASE_ID:
            return "❌ Notion API key or Database ID not configured"
        
        # Prepare query payload
        query_payload = {}
        if status_filter:
            query_payload["filter"] = {
                "property": "Deploy Status",
                "select": {
                    "equals": status_filter
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
            return f"❌ Failed to query Notion database: {response.status_code}"
        
        results = response.json()
        pages = results.get('results', [])
        
        if not pages:
            return f"📋 No projects found" + (f" with status '{status_filter}'" if status_filter else "")
        
        # Format results
        projects_list = f"📋 **NOTION PROJECTS** ({len(pages)} found)\n\n"
        
        for page in pages[:10]:  # Show first 10 projects
            props = page.get('properties', {})
            
            # Extract project details
            topic_name = "Untitled"
            if props.get('Topic name', {}).get('title'):
                topic_name = props['Topic name']['title'][0]['text']['content']
            
            deploy_status = "Unknown"
            if props.get('Deploy Status', {}).get('select'):
                deploy_status = props['Deploy Status']['select']['name']
            
            created_date = "Unknown"
            if props.get('Created Date and time', {}).get('date'):
                created_date = props['Created Date and time']['date']['start'][:10]
            
            folder_link = props.get('Folder link', {}).get('url', '')
            
            projects_list += f"""🎬 **{topic_name}**
   Status: {deploy_status}
   Target Date: {created_date}
   Folder: {folder_link.split('/')[-1] if folder_link else 'Not set'}
   Page ID: {page['id']}

"""
        
        return projects_list
        
    except Exception as e:
        return f"❌ Failed to list projects: {str(e)}"

# Fixed tools list - remove undefined functions
notion_tools = [
    create_notion_project_row,
    update_notion_video_status,
    monitor_gdrive_folder,
    list_notion_projects,
    update_publish_status
]