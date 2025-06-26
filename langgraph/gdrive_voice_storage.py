# gdrive_voice_storage.py
import os
import json
from typing import Dict, Any, Optional
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from langchain_core.tools import tool

class GoogleDriveVoiceStorage:
    def __init__(self):
        self.SCOPES = ['https://www.googleapis.com/auth/drive']
        self.credentials_file = 'langgraph/credentials.json'
        self.token_file = 'langgraph/token.json'
        self.service = None
        self.voice_folder_id = None
        
    def authenticate(self) -> bool:
        """Authenticate with Google Drive API."""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    return False
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
        
        try:
            self.service = build('drive', 'v3', credentials=creds)
            return True
        except Exception as e:
            print(f"Authentication failed: {e}")
            return False
    
    def get_or_create_voice_folder(self) -> Optional[str]:
        """Get or create the 'Generated Voices' folder in Google Drive."""
        if not self.service:
            return None
        
        try:
            # Search for existing folder
            results = self.service.files().list(
                q="name='Generated Voices' and mimeType='application/vnd.google-apps.folder'",
                fields="files(id, name)"
            ).execute()
            
            items = results.get('files', [])
            
            if items:
                self.voice_folder_id = items[0]['id']
                return self.voice_folder_id
            
            # Create new folder
            folder_metadata = {
                'name': 'Generated Voices',
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            
            self.voice_folder_id = folder.get('id')
            return self.voice_folder_id
            
        except Exception as e:
            print(f"Error creating/finding folder: {e}")
            return None
    
    def upload_voice_file(self, 
                         file_path: str, 
                         filename: str = None,
                         metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Upload voice file to Google Drive."""
        
        if not os.path.exists(file_path):
            return {
                "success": False,
                "error": "File not found",
                "file_id": None,
                "file_url": None
            }
        
        if not self.authenticate():
            return {
                "success": False,
                "error": "Failed to authenticate with Google Drive",
                "file_id": None,
                "file_url": None
            }
        
        folder_id = self.get_or_create_voice_folder()
        if not folder_id:
            return {
                "success": False,
                "error": "Failed to create/find voice folder",
                "file_id": None,
                "file_url": None
            }
        
        try:
            # Prepare file metadata
            if not filename:
                filename = os.path.basename(file_path)
            
            file_metadata = {
                'name': filename,
                'parents': [folder_id]
            }
            
            # Add description with metadata
            if metadata:
                description_parts = []
                for key, value in metadata.items():
                    description_parts.append(f"{key}: {value}")
                file_metadata['description'] = "\n".join(description_parts)
            
            # Upload file
            media = MediaFileUpload(file_path, resumable=True)
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink, webContentLink'
            ).execute()
            
            file_id = file.get('id')
            
            # Make file publicly accessible for sharing
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }
            
            self.service.permissions().create(
                fileId=file_id,
                body=permission
            ).execute()
            
            # Get shareable link
            shareable_link = f"https://drive.google.com/file/d/{file_id}/view"
            download_link = f"https://drive.google.com/uc?export=download&id={file_id}"
            
            return {
                "success": True,
                "file_id": file_id,
                "file_url": shareable_link,
                "download_url": download_link,
                "filename": filename,
                "folder_id": folder_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Upload failed: {str(e)}",
                "file_id": None,
                "file_url": None
            }

@tool
async def upload_voice_to_gdrive(
    file_path: str,
    voice_name: str = "generated_voice",
    script_title: str = "",
    emotion: str = "neutral",
    duration: str = "",
    additional_metadata: Dict[str, Any] = None
) -> str:
    """Upload generated voice file to Google Drive in 'Generated Voices' folder.
    
    Args:
        file_path: Local path to the voice file
        voice_name: Name for the voice file
        script_title: Title of the script this voice was generated from
        emotion: Emotion used in generation
        duration: Duration of the audio
        additional_metadata: Any additional metadata to include
    
    Returns:
        Upload result with Google Drive links
    """
    try:
        storage = GoogleDriveVoiceStorage()
        
        # Prepare metadata
        metadata = {
            "Voice Name": voice_name,
            "Script Title": script_title,
            "Emotion": emotion,
            "Duration": duration,
            "Generated": "Chatterbox TTS",
            "Upload Date": json.dumps({"date": "today"}).replace('"', '')
        }
        
        if additional_metadata:
            metadata.update(additional_metadata)
        
        # Generate filename
        timestamp = json.dumps({"timestamp": "now"}).replace('"', '')
        filename = f"{voice_name}_{emotion}_{timestamp}.wav"
        
        result = storage.upload_voice_file(
            file_path=file_path,
            filename=filename,
            metadata=metadata
        )
        
        if result["success"]:
            return f"""
☁️ **VOICE UPLOADED TO GOOGLE DRIVE**

**📁 Folder:** Generated Voices
**📄 Filename:** {result['filename']}
**🆔 File ID:** {result['file_id']}

**🔗 Links:**
- **View:** {result['file_url']}
- **Download:** {result['download_url']}

**📊 Metadata:**
- Voice: {voice_name}
- Script: {script_title}
- Emotion: {emotion}
- Duration: {duration}

✅ **Upload successful!** Voice file is now accessible in Google Drive.
"""
        else:
            return f"""
❌ **GOOGLE DRIVE UPLOAD FAILED**

**Error:** {result['error']}

**💡 Troubleshooting:**
1. Check Google Drive credentials in `langgraph/credentials.json`
2. Ensure file exists at: {file_path}
3. Verify Google Drive API permissions
4. Check internet connection

**📝 Setup Guide:**
1. Go to Google Cloud Console
2. Enable Google Drive API
3. Create OAuth 2.0 credentials
4. Download as `credentials.json`
5. Place in `langgraph/` folder
"""
            
    except Exception as e:
        return f"❌ Error uploading to Google Drive: {str(e)}"

@tool
async def list_gdrive_voice_files() -> str:
    """List all voice files in the Google Drive 'Generated Voices' folder.
    
    Returns:
        List of voice files with metadata
    """
    try:
        storage = GoogleDriveVoiceStorage()
        
        if not storage.authenticate():
            return """
❌ **GOOGLE DRIVE AUTHENTICATION FAILED**

**Setup Required:**
1. Download OAuth credentials from Google Cloud Console
2. Save as `langgraph/credentials.json`
3. Enable Google Drive API
"""
        
        folder_id = storage.get_or_create_voice_folder()
        if not folder_id:
            return "❌ Failed to access Google Drive voice folder"
        
        # List files in voice folder
        results = storage.service.files().list(
            q=f"'{folder_id}' in parents",
            fields="files(id, name, description, createdTime, size, webViewLink)"
        ).execute()
        
        files = results.get('files', [])
        
        if not files:
            return """
📁 **GENERATED VOICES FOLDER IS EMPTY**

**No voice files found in Google Drive.**

Use `upload_voice_to_gdrive` to upload generated voices.
"""
        
        file_list = []
        for file in files:
            size_mb = int(file.get('size', 0)) / (1024 * 1024) if file.get('size') else 0
            created = file.get('createdTime', '')[:10]  # Just date
            
            file_info = f"""
**📄 {file['name']}**
- ID: {file['id']}
- Created: {created}
- Size: {size_mb:.1f}MB
- Link: {file['webViewLink']}
"""
            if file.get('description'):
                file_info += f"- Metadata: {file['description'][:100]}..."
            
            file_list.append(file_info)
        
        return f"""
☁️ **GOOGLE DRIVE VOICE FILES**

**📁 Folder:** Generated Voices
**📊 Total Files:** {len(files)}

{chr(10).join(file_list)}

✅ **Access your voice files anytime via Google Drive!**
"""
        
    except Exception as e:
        return f"❌ Error listing Google Drive files: {str(e)}"

# Google Drive voice storage tools
gdrive_voice_tools = [upload_voice_to_gdrive, list_gdrive_voice_files]