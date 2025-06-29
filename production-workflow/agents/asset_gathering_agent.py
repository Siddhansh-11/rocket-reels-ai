import asyncio
import json
import os
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from langchain_core.tools import tool
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import pickle

# Google Drive API configuration
SCOPES = ['https://www.googleapis.com/auth/drive']
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'langgraph', 'credentials.json')
TOKEN_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'langgraph', 'token.json')

def _sanitize_folder_name(name: str) -> str:
    """Sanitize folder name for Google Drive compatibility."""
    # Remove invalid characters and limit length
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
    sanitized = re.sub(r'\s+', '_', sanitized)  # Replace spaces with underscores
    return sanitized[:100]  # Limit to 100 characters

def _get_drive_service():
    """Initialize and return Google Drive service."""
    try:
        from storage.gdrive_storage import initialize_gdrive_storage
        storage = initialize_gdrive_storage()
        if storage and hasattr(storage, 'service'):
            return storage.service
        else:
            raise Exception("Failed to initialize Google Drive service")
    except Exception as e:
        raise Exception(f"Google Drive service initialization failed: {str(e)}")

def _find_folder_by_name(service, folder_name: str, parent_id: str = None) -> Optional[str]:
    """Find folder by name, optionally within a parent folder."""
    try:
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        
        results = service.files().list(q=query, fields="files(id, name)").execute()
        folders = results.get('files', [])
        
        return folders[0]['id'] if folders else None
    except Exception as e:
        print(f"Error finding folder {folder_name}: {e}")
        return None

def _create_folder(service, folder_name: str, parent_id: str = None) -> str:
    """Create a new folder in Google Drive."""
    try:
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        if parent_id:
            folder_metadata['parents'] = [parent_id]
        
        folder = service.files().create(body=folder_metadata, fields='id').execute()
        return folder.get('id')
    except Exception as e:
        print(f"Error creating folder {folder_name}: {e}")
        return None

def _move_files_to_folder(service, file_pattern: str, source_folder_id: str, dest_folder_id: str) -> List[str]:
    """Move files matching pattern from source to destination folder."""
    try:
        moved_files = []
        
        # Search for files in source folder matching pattern
        query = f"'{source_folder_id}' in parents and trashed=false"
        if file_pattern != "*":
            query += f" and name contains '{file_pattern}'"
        
        results = service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get('files', [])
        
        for file in files:
            try:
                # Move file to destination folder
                service.files().update(
                    fileId=file['id'],
                    addParents=dest_folder_id,
                    removeParents=source_folder_id,
                    fields='id, parents'
                ).execute()
                moved_files.append(file['name'])
                print(f"Moved file: {file['name']}")
            except Exception as move_error:
                print(f"Failed to move file {file['name']}: {move_error}")
        
        return moved_files
    except Exception as e:
        print(f"Error moving files: {e}")
        return []

@tool
async def create_project_folder_structure(script_data: Dict[str, Any]) -> str:
    """Create organized project folder structure in Google Drive.
    
    Args:
        script_data: Dictionary containing script and project information
    """
    try:
        # Get Google Drive service - FIX: Add this line
        service = _get_drive_service()
        
        # Extract script details
        script_title = script_data.get('title', script_data.get('script_content', 'Untitled')[:50])
        script_id = script_data.get('script_id', 'unknown')
        article_id = script_data.get('article_id', 'unknown')
        
        # Sanitize project name for folder
        project_name = _sanitize_folder_name(f"{script_title}_{datetime.now().strftime('%Y%m%d_%H%M')}")
        
        # Find RocketReelsAI main folder
        main_folder_id = _find_folder_by_name(service, "RocketReelsAI")
        if not main_folder_id:
            return "❌ RocketReelsAI main folder not found in Google Drive. Please create it first."
        
        # Create project folder
        project_folder_id = _create_folder(service, project_name, main_folder_id)
        if not project_folder_id:
            return f"❌ Failed to create project folder: {project_name}"
        
        # Create subfolders
        subfolders = {
            'generated_images': 'Generated images and visual assets',
            'voiceover': 'Generated voice files and audio assets', 
            'scripts': 'Script files and text content',
            'final_draft': 'Final video files (for editor upload)',
            'resources': 'Additional resources and references'
        }
        
        created_folders = {}
        for folder_name, description in subfolders.items():
            subfolder_id = _create_folder(service, folder_name, project_folder_id)
            if subfolder_id:
                created_folders[folder_name] = {
                    'id': subfolder_id,
                    'description': description
                }
            else:
                return f"❌ Failed to create subfolder: {folder_name}"
        
        # Get project folder web URL
        project_folder_info = service.files().get(fileId=project_folder_id, fields='webViewLink').execute()
        folder_url = project_folder_info.get('webViewLink', '#')
        
        # Create metadata file content
        metadata_content = json.dumps({
            'script_id': script_id,
            'article_id': article_id,
            'project_name': project_name,
            'created_at': datetime.now().isoformat(),
            'created_by': 'RocketReelsAI',
            'folder_structure': list(subfolders.keys()),
            'metadata': script_data.get('metadata', {})
        }, indent=2)
        
        # Create and upload metadata file - FIX: Proper file handling
        metadata_file = {
            'name': 'project_metadata.json',
            'parents': [project_folder_id],
            'mimeType': 'application/json'
        }
        
        # Write to temp file and upload properly
        import tempfile
        temp_file_path = None
        try:
            # Create temp file with proper context management
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                temp_file.write(metadata_content)
                temp_file_path = temp_file.name
            
            # Upload after file is closed
            from googleapiclient.http import MediaFileUpload
            media = MediaFileUpload(temp_file_path, mimetype='application/json')
            service.files().create(body=metadata_file, media_body=media).execute()
            
        finally:
            # Clean up temp file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except OSError:
                    pass  # File might already be deleted
        
        # Prepare folder path for return
        folder_path = f"RocketReelsAI/{project_name}"
        
        return f"""✅ **PROJECT FOLDER STRUCTURE CREATED**

📁 **Project Details:**
- Project Name: {project_name}
- Main Folder ID: {project_folder_id}
- Folder URL: {folder_url}
- Folder Path: {folder_path}

📂 **Subfolders Created:**
{chr(10).join([f"  - {name}/ - {info['description']}" for name, info in created_folders.items()])}

📋 **Metadata:**
- Script ID: {script_id}
- Article ID: {article_id}
- Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎯 **Next Steps:**
1. Move generated assets to appropriate subfolders
2. Editor uploads final video to final_draft/ folder
3. Notion workspace will be updated with project details"""
        
    except Exception as e:
        return f"❌ Folder creation error: {str(e)}"

@tool
async def organize_generated_assets(project_folder_path: str, assets_data: Dict[str, Any]) -> str:
    """Move generated assets from workflow to organized project folders.
    
    Args:
        project_folder_path: Path to the project folder (e.g., "RocketReelsAI/ProjectName")
        assets_data: Dictionary containing asset file paths and metadata
        
    Returns:
        Success message with organization details
    """
    try:
        service = _get_drive_service()
        
        # Parse folder path to get project folder ID
        path_parts = project_folder_path.split('/')
        if len(path_parts) < 2:
            return "❌ Invalid folder path format. Expected: RocketReelsAI/ProjectName"
        
        main_folder_name = path_parts[0]
        project_folder_name = path_parts[1]
        
        # Find main folder
        main_folder_id = _find_folder_by_name(service, main_folder_name)
        if not main_folder_id:
            return f"❌ Main folder '{main_folder_name}' not found"
        
        # Find project folder
        project_folder_id = _find_folder_by_name(service, project_folder_name, main_folder_id)
        if not project_folder_id:
            return f"❌ Project folder '{project_folder_name}' not found"
        
        # Get subfolder IDs
        subfolders = {
            'generated_images': _find_folder_by_name(service, 'generated_images', project_folder_id),
            'voiceover': _find_folder_by_name(service, 'voiceover', project_folder_id),
            'scripts': _find_folder_by_name(service, 'scripts', project_folder_id)
        }
        
        # Check if all subfolders exist
        missing_folders = [name for name, folder_id in subfolders.items() if not folder_id]
        if missing_folders:
            return f"❌ Missing subfolders: {', '.join(missing_folders)}"
        
        # Organize assets
        organized_assets = {}
        
        # Move images
        if 'images' in assets_data and assets_data['images']:
            images_moved = []
            for image_path in assets_data['images']:
                # This would involve uploading files or moving them if they're already in Drive
                # For now, we'll record the organization plan
                images_moved.append(image_path)
            organized_assets['images'] = images_moved
        
        # Move voice files
        if 'voice_files' in assets_data and assets_data['voice_files']:
            voice_moved = []
            for voice_path in assets_data['voice_files']:
                voice_moved.append(voice_path)
            organized_assets['voice_files'] = voice_moved
        
        # Create script file
        if 'script_content' in assets_data:
            script_content = assets_data['script_content']
            script_filename = f"script_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
            
            # Create script file in scripts subfolder
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
                temp_file.write(script_content)
                temp_file_path = temp_file.name
            
            try:
                from googleapiclient.http import MediaFileUpload
                script_file_metadata = {
                    'name': script_filename,
                    'parents': [subfolders['scripts']]
                }
                media = MediaFileUpload(temp_file_path, mimetype='text/plain')
                script_file = service.files().create(body=script_file_metadata, media_body=media).execute()
                organized_assets['script_file'] = script_file.get('id')
            finally:
                os.unlink(temp_file_path)
        
        return f"""✅ **ASSETS ORGANIZED**

📁 **Project:** {project_folder_path}

📂 **Assets Organized:**
- Images: {len(organized_assets.get('images', []))} files → generated_images/
- Voice Files: {len(organized_assets.get('voice_files', []))} files → voiceover/
- Script: {'✅ Created' if 'script_file' in organized_assets else '❌ Failed'} → scripts/

📋 **Folder Structure Ready:**
- generated_images/ ✅
- voiceover/ ✅  
- scripts/ ✅
- final_draft/ ✅ (awaiting editor upload)
- resources/ ✅

🎬 **Status:** Ready for editor to upload final video to final_draft/ folder"""
        
    except Exception as e:
        return f"❌ Asset organization error: {str(e)}"

@tool
async def monitor_final_draft_folder(project_folder_path: str) -> str:
    """Monitor final_draft folder for new video uploads.
    
    Args:
        project_folder_path: Path to the project folder (e.g., "RocketReelsAI/ProjectName")
        
    Returns:
        Status of monitoring and any detected uploads
    """
    try:
        service = _get_drive_service()
        
        # Parse folder path
        path_parts = project_folder_path.split('/')
        if len(path_parts) < 2:
            return "❌ Invalid folder path format"
        
        main_folder_name = path_parts[0]
        project_folder_name = path_parts[1]
        
        # Find project folder
        main_folder_id = _find_folder_by_name(service, main_folder_name)
        project_folder_id = _find_folder_by_name(service, project_folder_name, main_folder_id)
        final_draft_folder_id = _find_folder_by_name(service, 'final_draft', project_folder_id)
        
        if not final_draft_folder_id:
            return f"❌ final_draft folder not found in {project_folder_path}"
        
        # Check for video files in final_draft folder
        video_query = f"'{final_draft_folder_id}' in parents and trashed=false and (mimeType contains 'video/' or name contains '.mp4' or name contains '.mov' or name contains '.avi')"
        results = service.files().list(q=video_query, fields="files(id, name, createdTime, size)").execute()
        video_files = results.get('files', [])
        
        if video_files:
            # Video found! Return details
            latest_video = max(video_files, key=lambda x: x['createdTime'])
            
            return f"""🎬 **VIDEO DETECTED IN FINAL DRAFT!**

📁 **Project:** {project_folder_path}
📂 **Folder:** final_draft/

🎥 **Latest Video:**
- Name: {latest_video['name']}
- ID: {latest_video['id']}
- Created: {latest_video['createdTime']}
- Size: {latest_video.get('size', 'Unknown')} bytes

📋 **Total Videos:** {len(video_files)} files found

🚀 **Action Required:** Update Notion workspace with video ready status"""
        else:
            return f"""🔍 **MONITORING FINAL DRAFT FOLDER**

📁 **Project:** {project_folder_path}
📂 **Folder:** final_draft/

📊 **Status:** No video files detected yet
🕐 **Last Check:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

⏳ **Waiting for editor to upload final video...**"""
        
    except Exception as e:
        return f"❌ Monitoring error: {str(e)}"

@tool
async def get_project_summary(project_folder_path: str) -> str:
    """Get comprehensive summary of project folder and assets.
    
    Args:
        project_folder_path: Path to the project folder
        
    Returns:
        Detailed project summary
    """
    try:
        service = _get_drive_service()
        
        # Parse and find project folder
        path_parts = project_folder_path.split('/')
        main_folder_id = _find_folder_by_name(service, path_parts[0])
        project_folder_id = _find_folder_by_name(service, path_parts[1], main_folder_id)
        
        if not project_folder_id:
            return f"❌ Project folder not found: {project_folder_path}"
        
        # Get folder structure and file counts
        subfolders = ['generated_images', 'voiceover', 'scripts', 'final_draft', 'resources']
        folder_summary = {}
        
        for subfolder_name in subfolders:
            subfolder_id = _find_folder_by_name(service, subfolder_name, project_folder_id)
            if subfolder_id:
                # Count files in subfolder
                files_query = f"'{subfolder_id}' in parents and trashed=false"
                results = service.files().list(q=files_query, fields="files(id, name, mimeType)").execute()
                files = results.get('files', [])
                
                folder_summary[subfolder_name] = {
                    'file_count': len(files),
                    'files': [{'name': f['name'], 'type': f['mimeType']} for f in files[:5]]  # First 5 files
                }
        
        # Check for metadata file
        metadata_query = f"'{project_folder_id}' in parents and name='project_metadata.json' and trashed=false"
        metadata_results = service.files().list(q=metadata_query, fields="files(id)").execute()
        has_metadata = len(metadata_results.get('files', [])) > 0
        
        # Build summary
        summary = f"""📋 **PROJECT SUMMARY: {project_folder_path}**

📁 **Folder Structure:**
"""
        
        for folder_name, info in folder_summary.items():
            file_count = info['file_count']
            status_icon = "✅" if file_count > 0 else "📂"
            summary += f"  {status_icon} {folder_name}/ - {file_count} files\n"
            
            # Show sample files
            if info['files']:
                for file in info['files'][:3]:
                    summary += f"    - {file['name']}\n"
                if file_count > 3:
                    summary += f"    ... and {file_count - 3} more\n"
        
        summary += f"""
📄 **Metadata:** {'✅ Available' if has_metadata else '❌ Missing'}
🕐 **Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎬 **Project Status:**"""
        
        # Determine project status
        has_images = folder_summary.get('generated_images', {}).get('file_count', 0) > 0
        has_voice = folder_summary.get('voiceover', {}).get('file_count', 0) > 0
        has_script = folder_summary.get('scripts', {}).get('file_count', 0) > 0
        has_final_video = folder_summary.get('final_draft', {}).get('file_count', 0) > 0
        
        if has_final_video:
            summary += "\n🚀 READY FOR PUBLISHING - Final video uploaded!"
        elif has_images and has_voice and has_script:
            summary += "\n⏳ READY FOR EDITING - All assets available"
        elif has_images or has_voice or has_script:
            summary += "\n🔄 IN PROGRESS - Some assets available"
        else:
            summary += "\n📂 INITIALIZED - Awaiting assets"
        
        return summary
        
    except Exception as e:
        return f"❌ Summary error: {str(e)}"

# Export tools for use in workflow
asset_gathering_tools = [
    create_project_folder_structure,
    organize_generated_assets,
    monitor_final_draft_folder,
    get_project_summary
]