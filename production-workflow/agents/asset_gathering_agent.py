import asyncio
import json
import os
import re
import tempfile
from typing import Dict, Any, List, Optional
from datetime import datetime
from langchain_core.tools import tool
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import pickle
import time

# Google Drive API configuration
SCOPES = ['https://www.googleapis.com/auth/drive.file']
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'langgraph', 'credentials.json')
TOKEN_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'langgraph', 'token.json')

def _sanitize_folder_name(name: str) -> str:
    """Sanitize folder name for Google Drive compatibility."""
    # Remove/replace problematic characters including apostrophes
    sanitized = re.sub(r'[<>:"/\\|?*\']', '_', name)
    sanitized = re.sub(r'\s+', '_', sanitized)
    return sanitized[:100]

def _get_drive_service():
    """Initialize and return Google Drive service."""
    try:
        print("DEBUG: Initializing Google Drive service...")
        creds = None
        if os.path.exists(TOKEN_FILE):
            print(f"DEBUG: Loading token from {TOKEN_FILE}")
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        else:
            print(f"DEBUG: Token file {TOKEN_FILE} not found")
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("DEBUG: Refreshing expired token")
                creds.refresh(Request())
            else:
                if not os.path.exists(CREDENTIALS_FILE):
                    raise FileNotFoundError(f"Credentials file {CREDENTIALS_FILE} not found")
                print(f"DEBUG: Running OAuth flow with credentials from {CREDENTIALS_FILE}")
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(TOKEN_FILE, 'w') as token:
                print(f"DEBUG: Saving new token to {TOKEN_FILE}")
                token.write(creds.to_json())
        service = build('drive', 'v3', credentials=creds)
        print("DEBUG: Google Drive service initialized successfully")
        return service
    except Exception as e:
        error_msg = f"Google Drive service initialization failed: {str(e)}"
        print(f"ERROR: {error_msg}")
        raise Exception(error_msg)

def _find_folder_by_name(service, folder_name: str, parent_id: str = None) -> Optional[str]:
    """Find folder by name, optionally within a parent folder."""
    try:
        # Escape single quotes in folder name for Google Drive API query
        escaped_folder_name = folder_name.replace("'", "\\'")
        query = f"name='{escaped_folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        
        results = service.files().list(q=query, fields="files(id, name)").execute()
        folders = results.get('files', [])
        
        return folders[0]['id'] if folders else None
    except Exception as e:
        print(f"Error finding folder {folder_name}: {str(e)}")
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
        print(f"Error creating folder {folder_name}: {str(e)}")
        return None

@tool
async def create_project_folder_structure(script_data: Dict[str, Any]) -> str:
    """Create organized project folder structure in Google Drive.
    
    Args:
        script_data: Dictionary containing script and project information
    """
    try:
        service = _get_drive_service()
        
        script_title = script_data.get('title', script_data.get('script_content', 'Untitled')[:50])
        script_id = script_data.get('script_id', 'unknown')
        article_id = script_data.get('article_id', 'unknown')
        
        project_name = _sanitize_folder_name(f"{script_title}_{datetime.now().strftime('%Y%m%d_%H%M')}")
        
        main_folder_id = _find_folder_by_name(service, "RocketReelsAI")
        if not main_folder_id:
            return "RocketReelsAI main folder not found in Google Drive. Please create it first."
        
        project_folder_id = _create_folder(service, project_name, main_folder_id)
        if not project_folder_id:
            return f"Failed to create project folder: {project_name}"
        
        subfolders = {
            'generated_images': 'Generated images and visual assets',
            'voiceover': 'Generated voice files and audio assets', 
            'scripts': 'Script files and text content',
            'final_draft': 'Final video files (for editor upload)',
            'resources': 'Additional resources and references',
            'broll': 'B-roll assets downloaded from Pexels'
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
                return f"Failed to create subfolder: {folder_name}"
        
        project_folder_info = service.files().get(fileId=project_folder_id, fields='webViewLink').execute()
        folder_url = project_folder_info.get('webViewLink', '#')
        
        metadata_content = json.dumps({
            'script_id': script_id,
            'article_id': article_id,
            'project_name': project_name,
            'created_at': datetime.now().isoformat(),
            'created_by': 'RocketReelsAI',
            'folder_structure': list(subfolders.keys()),
            'metadata': script_data.get('metadata', {})
        }, indent=2)
        
        import tempfile
        temp_file_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                temp_file.write(metadata_content)
                temp_file_path = temp_file.name
            
            from googleapiclient.http import MediaFileUpload
            metadata_file = {
                'name': 'project_metadata.json',
                'parents': [project_folder_id],
                'mimeType': 'application/json'
            }
            media = MediaFileUpload(temp_file_path, mimetype='application/json')
            service.files().create(body=metadata_file, media_body=media).execute()
            
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except OSError:
                    pass
        
        folder_path = f"RocketReelsAI/{project_name}"
        
        return f"""PROJECT FOLDER STRUCTURE CREATED

Project Details:
- Project Name: {project_name}
- Main Folder ID: {project_folder_id}
- Folder URL: {folder_url}
- Folder Path: {folder_path}

Subfolders Created:
{chr(10).join([f"  - {name}/ - {info['description']}" for name, info in created_folders.items()])}

Metadata:
- Script ID: {script_id}
- Article ID: {article_id}
- Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Next Steps:
1. Move generated assets to appropriate subfolders
2. Editor uploads final video to final_draft/ folder
3. Notion workspace will be updated with project details"""
        
    except Exception as e:
        return f"Folder creation error: {str(e)}"

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
        
        path_parts = project_folder_path.split('/')
        if len(path_parts) < 2:
            return "Invalid folder path format. Expected: RocketReelsAI/ProjectName"
        
        main_folder_name = path_parts[0]
        project_folder_name = path_parts[1]
        
        main_folder_id = _find_folder_by_name(service, main_folder_name)
        if not main_folder_id:
            return f"Main folder '{main_folder_name}' not found"
        
        project_folder_id = _find_folder_by_name(service, project_folder_name, main_folder_id)
        if not project_folder_id:
            return f"Project folder '{project_folder_name}' not found"
        
        subfolders = {
            'generated_images': _find_folder_by_name(service, 'generated_images', project_folder_id),
            'voiceover': _find_folder_by_name(service, 'voiceover', project_folder_id),
            'scripts': _find_folder_by_name(service, 'scripts', project_folder_id),
            'broll': _find_folder_by_name(service, 'broll', project_folder_id)
        }
        
        missing_folders = [name for name, folder_id in subfolders.items() if not folder_id]
        if missing_folders:
            return f"Missing subfolders: {', '.join(missing_folders)}"
        
        organized_assets = {}
        
        # Move images
        if 'images' in assets_data and assets_data['images']:
            images_moved = []
            for image in assets_data['images']:
                try:
                    # Parse JSON string if necessary
                    image_path = image
                    if isinstance(image, str) and image.startswith('{'):
                        image_data = json.loads(image)
                        image_path = image_data.get('file_path', '')
                    
                    if os.path.exists(image_path):
                        image_filename = os.path.basename(image_path)
                        image_file_metadata = {
                            'name': image_filename,
                            'parents': [subfolders['generated_images']]
                        }
                        from googleapiclient.http import MediaFileUpload
                        media = MediaFileUpload(image_path, mimetype='image/jpeg')
                        image_file = service.files().create(body=image_file_metadata, media_body=media).execute()
                        images_moved.append(image_file.get('id'))
                        print(f"Uploaded image: {image_filename}")
                        media = None
                        time.sleep(0.5)
                    else:
                        print(f"Image file not found: {image_path}")
                except Exception as e:
                    print(f"Failed to upload image {image_path}: {str(e)}")
    
            organized_assets['images'] = images_moved
        
        # Move voice files
        if 'voice_files' in assets_data and assets_data['voice_files']:
            voice_moved = []
            for voice_item in assets_data['voice_files']:
                try:
                    voice_path = None
                    
                    # Extract file path from voice generation result
                    if isinstance(voice_item, str):
                        # Check if it's a direct file path
                        if os.path.exists(voice_item):
                            voice_path = voice_item
                        else:
                            # Parse from voice generation result text
                            for line in voice_item.split('\n'):
                                if "Local Path:" in line:
                                    voice_path = line.split("Local Path:")[1].strip()
                                    # Remove markdown formatting
                                    voice_path = voice_path.lstrip('*').strip()
                                    break
                                elif "file_path" in line.lower() and ":" in line:
                                    voice_path = line.split(":")[-1].strip()
                                    # Remove markdown formatting
                                    voice_path = voice_path.lstrip('*').strip()
                                    break
                    
                    if voice_path and os.path.exists(voice_path):
                        voice_filename = os.path.basename(voice_path)
                        voice_file_metadata = {
                            'name': voice_filename,
                            'parents': [subfolders['voiceover']]
                        }
                        from googleapiclient.http import MediaFileUpload
                        # Detect proper mimetype based on file extension
                        if voice_path.lower().endswith('.wav'):
                            mimetype = 'audio/wav'
                        elif voice_path.lower().endswith('.mp3'):
                            mimetype = 'audio/mp3'
                        elif voice_path.lower().endswith('.m4a'):
                            mimetype = 'audio/m4a'
                        else:
                            mimetype = 'audio/wav'  # Default
                        
                        media = MediaFileUpload(voice_path, mimetype=mimetype)
                        voice_file = service.files().create(body=voice_file_metadata, media_body=media).execute()
                        voice_moved.append(voice_file.get('id'))
                        print(f"Uploaded voice file: {voice_filename}")
                        media = None
                        time.sleep(0.5)
                    else:
                        print(f"Voice file not found: {voice_path}")
                except Exception as e:
                    print(f"Failed to upload voice file {voice_item}: {str(e)}")
            
            organized_assets['voice_files'] = voice_moved
        
        # Create script file
        if 'script_content' in assets_data:
            script_content = assets_data['script_content']
            script_filename = f"script_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
            
            import tempfile
            temp_file_path = None
            try:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
                    temp_file.write(script_content)
                    temp_file_path = temp_file.name
                
                from googleapiclient.http import MediaFileUpload
                script_file_metadata = {
                    'name': script_filename,
                    'parents': [subfolders['scripts']]
                }
                media = MediaFileUpload(temp_file_path, mimetype='text/plain')
                script_file = service.files().create(body=script_file_metadata, media_body=media).execute()
                organized_assets['script_file'] = script_file.get('id')
                print(f"Uploaded script: {script_filename}")
                media = None
                time.sleep(0.5)
            finally:
                if temp_file_path and os.path.exists(temp_file_path):
                    try:
                        os.unlink(temp_file_path)
                    except OSError as e:
                        print(f"Note: Could not delete temp file {temp_file_path}: {e}")
        
        # Upload CSV files from local assets directory
        assets_dir = os.path.join(os.path.dirname(__file__), '..', 'assets')
        if os.path.exists(assets_dir):
            csv_files = [f for f in os.listdir(assets_dir) if f.endswith('.csv')]
            csv_uploaded = []
            for csv_file in csv_files:
                try:
                    csv_path = os.path.join(assets_dir, csv_file)
                    if os.path.exists(csv_path):
                        from googleapiclient.http import MediaFileUpload
                        # Visual production table goes to main project folder, others to scripts
                        if 'visual_production_table' in csv_file:
                            parent_folder = project_folder_id  # Main project folder
                        else:
                            parent_folder = subfolders['scripts']  # Scripts subfolder
                        
                        csv_file_metadata = {
                            'name': csv_file,
                            'parents': [parent_folder]
                        }
                        media = MediaFileUpload(csv_path, mimetype='text/csv')
                        uploaded_file = service.files().create(body=csv_file_metadata, media_body=media).execute()
                        csv_uploaded.append(uploaded_file.get('id'))
                        print(f"Uploaded CSV: {csv_file} to {'project folder' if 'visual_production_table' in csv_file else 'scripts folder'}")
                        media = None
                        time.sleep(0.5)
                        
                        # Delete the local CSV file after successful upload
                        try:
                            os.unlink(csv_path)
                            print(f"Deleted local CSV file: {csv_file}")
                        except OSError as e:
                            print(f"Note: Could not delete CSV file {csv_file}: {e}")
                    else:
                        print(f"CSV file not found: {csv_path}")
                except Exception as e:
                    print(f"Failed to upload CSV file {csv_file}: {str(e)}")
            
            organized_assets['csv_files'] = csv_uploaded

        # Upload b-roll assets if available
        print(f"DEBUG: Checking for B-roll assets in assets_data keys: {list(assets_data.keys())}")
        if 'broll_assets' in assets_data and assets_data['broll_assets']:
            broll_data = assets_data['broll_assets']
            broll_uploaded = []
            print(f"DEBUG: Found B-roll data, type: {type(broll_data)}")
            if isinstance(broll_data, dict):
                print(f"DEBUG: B-roll data keys: {list(broll_data.keys())}")
            
            # Handle downloaded files if they exist
            if isinstance(broll_data, dict) and 'downloaded_files' in broll_data:
                print(f"DEBUG: Found {len(broll_data['downloaded_files'])} downloaded B-roll files")
                for broll_file in broll_data['downloaded_files']:
                    try:
                        file_path = broll_file.get('path')
                        if file_path and os.path.exists(file_path):
                            filename = os.path.basename(file_path)
                            file_metadata = {
                                'name': filename,
                                'parents': [subfolders['broll']]
                            }
                            
                            # Determine mimetype
                            if broll_file.get('type') == 'video' or filename.endswith('.mp4'):
                                mimetype = 'video/mp4'
                            else:
                                mimetype = 'image/jpeg'
                            
                            from googleapiclient.http import MediaFileUpload
                            media = MediaFileUpload(file_path, mimetype=mimetype)
                            uploaded_file = service.files().create(body=file_metadata, media_body=media).execute()
                            broll_uploaded.append(uploaded_file.get('id'))
                            print(f"Uploaded b-roll: {filename}")
                            media = None
                            time.sleep(0.5)
                        else:
                            print(f"B-roll file not found: {file_path}")
                    except Exception as e:
                        print(f"Failed to upload b-roll file: {str(e)}")
                
                organized_assets['broll'] = broll_uploaded
                print(f"DEBUG: Uploaded {len(broll_uploaded)} B-roll files to Google Drive")
            else:
                print("DEBUG: No 'downloaded_files' found in B-roll data")
            
            # Also save b-roll metadata
            if isinstance(broll_data, dict) and ('images' in broll_data or 'videos' in broll_data):
                broll_metadata = {
                    'generated_at': datetime.now().isoformat(),
                    'total_assets': {
                        'images': len(broll_data.get('images', [])),
                        'videos': len(broll_data.get('videos', []))
                    },
                    'assets': {
                        'images': broll_data.get('images', []),
                        'videos': broll_data.get('videos', [])
                    },
                    'source': 'Pexels API'
                }
                
                metadata_filename = f"broll_metadata_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
                temp_file_path = None
                try:
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                        json.dump(broll_metadata, temp_file, indent=2)
                        temp_file_path = temp_file.name
                    
                    metadata_file = {
                        'name': metadata_filename,
                        'parents': [subfolders['broll']],
                        'mimeType': 'application/json'
                    }
                    from googleapiclient.http import MediaFileUpload
                    media = MediaFileUpload(temp_file_path, mimetype='application/json')
                    service.files().create(body=metadata_file, media_body=media).execute()
                    print(f"Uploaded b-roll metadata: {metadata_filename}")
                    media = None
                finally:
                    if temp_file_path and os.path.exists(temp_file_path):
                        try:
                            os.unlink(temp_file_path)
                        except OSError:
                            pass
        else:
            print("DEBUG: No B-roll assets found in assets_data")
        
        return f"""ASSETS ORGANIZED

Project: {project_folder_path}

Assets Organized:
- Images: {len(organized_assets.get('images', []))} files -> generated_images/
- Voice Files: {len(organized_assets.get('voice_files', []))} files -> voiceover/
- Script: {'Created' if 'script_file' in organized_assets else 'Failed'} -> scripts/
- CSV Files: {len(organized_assets.get('csv_files', []))} files -> scripts/
- B-roll: {len(organized_assets.get('broll', []))} files -> broll/

Folder Structure Ready:
- generated_images/
- voiceover/
- scripts/
- broll/
- final_draft/ (awaiting editor upload)
- resources/

Status: Ready for editor to upload final video to final_draft/ folder"""
        
    except Exception as e:
        return f"Asset organization error: {str(e)}"

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
        
        path_parts = project_folder_path.split('/')
        if len(path_parts) < 2:
            return "Invalid folder path format"
        
        main_folder_name = path_parts[0]
        project_folder_name = path_parts[1]
        
        main_folder_id = _find_folder_by_name(service, main_folder_name)
        project_folder_id = _find_folder_by_name(service, project_folder_name, main_folder_id)
        final_draft_folder_id = _find_folder_by_name(service, 'final_draft', project_folder_id)
        
        if not final_draft_folder_id:
            return f"final_draft folder not found in {project_folder_path}"
        
        video_query = f"'{final_draft_folder_id}' in parents and trashed=false and (mimeType contains 'video/' or name contains '.mp4' or name contains '.mov' or name contains '.avi')"
        results = service.files().list(q=video_query, fields="files(id, name, createdTime, size)").execute()
        video_files = results.get('files', [])
        
        if video_files:
            latest_video = max(video_files, key=lambda x: x['createdTime'])
            
            return f"""VIDEO DETECTED IN FINAL DRAFT!

Project: {project_folder_path}
Folder: final_draft/

Latest Video:
- Name: {latest_video['name']}
- ID: {latest_video['id']}
- Created: {latest_video['createdTime']}
- Size: {latest_video.get('size', 'Unknown')} bytes

Total Videos: {len(video_files)} files found

Action Required: Update Notion workspace with video ready status"""
        else:
            return f"""MONITORING FINAL DRAFT FOLDER

Project: {project_folder_path}
Folder: final_draft/

Status: No video files detected yet
Last Check: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Waiting for editor to upload final video..."""
        
    except Exception as e:
        return f"Monitoring error: {str(e)}"

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
        
        path_parts = project_folder_path.split('/')
        main_folder_id = _find_folder_by_name(service, path_parts[0])
        project_folder_id = _find_folder_by_name(service, path_parts[1], main_folder_id)
        
        if not project_folder_id:
            return f"Project folder not found: {project_folder_path}"
        
        subfolders = ['generated_images', 'voiceover', 'scripts', 'broll', 'final_draft', 'resources']
        folder_summary = {}
        
        for subfolder_name in subfolders:
            subfolder_id = _find_folder_by_name(service, subfolder_name, project_folder_id)
            if subfolder_id:
                files_query = f"'{subfolder_id}' in parents and trashed=false"
                results = service.files().list(q=files_query, fields="files(id, name, mimeType)").execute()
                files = results.get('files', [])
                
                folder_summary[subfolder_name] = {
                    'file_count': len(files),
                    'files': [{'name': f['name'], 'type': f['mimeType']} for f in files[:5]]
                }
        
        metadata_query = f"'{project_folder_id}' in parents and name='project_metadata.json' and trashed=false"
        metadata_results = service.files().list(q=metadata_query, fields="files(id)").execute()
        has_metadata = len(metadata_results.get('files', [])) > 0
        
        summary = f"""PROJECT SUMMARY: {project_folder_path}

Folder Structure:
"""
        
        for folder_name, info in folder_summary.items():
            file_count = info['file_count']
            status = "Populated" if file_count > 0 else "Empty"
            summary += f"  {status} {folder_name}/ - {file_count} files\n"
            
            if info['files']:
                for file in info['files'][:3]:
                    summary += f"    - {file['name']}\n"
                if file_count > 3:
                    summary += f"    ... and {file_count - 3} more\n"
        
        summary += f"""
Metadata: {'Available' if has_metadata else 'Missing'}
Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Project Status:"""
        
        has_images = folder_summary.get('generated_images', {}).get('file_count', 0) > 0
        has_voice = folder_summary.get('voiceover', {}).get('file_count', 0) > 0
        has_script = folder_summary.get('scripts', {}).get('file_count', 0) > 0
        has_final_video = folder_summary.get('final_draft', {}).get('file_count', 0) > 0
        
        if has_final_video:
            summary += "\nREADY FOR PUBLISHING - Final video uploaded!"
        elif has_images and has_voice and has_script:
            summary += "\nREADY FOR EDITING - All assets available"
        elif has_images or has_voice or has_script:
            summary += "\nIN PROGRESS - Some assets available"
        else:
            summary += "\nINITIALIZED - Awaiting assets"
        
        return summary
        
    except Exception as e:
        return f"Summary error: {str(e)}"

asset_gathering_tools = [
    create_project_folder_structure,
    organize_generated_assets,
    monitor_final_draft_folder,
    get_project_summary
]