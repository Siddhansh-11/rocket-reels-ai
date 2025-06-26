"""
Google Drive Storage Integration for Rocket Reels AI
Handles uploading and organizing generated content in Google Drive folders
"""

import os
import json
from typing import Optional, Dict, List
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import logging

logger = logging.getLogger(__name__)

class GDriveStorage:
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    
    def __init__(self, credentials_path: str = "credentials.json", token_path: str = "token.json"):
        """
        Initialize Google Drive storage client
        
        Args:
            credentials_path: Path to Google OAuth2 credentials file
            token_path: Path to store/load access tokens
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self.folder_ids = {}
        self.topic_subfolder_cache = {}  # Cache for topic subfolders to prevent duplicates
        self.uploaded_files_cache = {}  # Cache for uploaded files to prevent duplicates
        self._lock = None  # Will be set to threading.Lock() when needed
        
    def authenticate(self):
        """Authenticate with Google Drive API with improved error handling"""
        import threading
        
        # Initialize lock for thread safety
        if self._lock is None:
            self._lock = threading.Lock()
            
        creds = None
        
        # Load existing token if available
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)
        
        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.warning(f"Token refresh failed: {str(e)}. Re-authenticating...")
                    creds = None
            
            if not creds:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.SCOPES)
                creds = flow.run_local_server(port=8080)
            
            # Save credentials for next run
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
        
        # Build service with proper authentication and timeout
        import socket
        socket.setdefaulttimeout(30)  # Set default timeout for all socket operations
        
        self.service = build('drive', 'v3', credentials=creds, cache_discovery=False)
        logger.info("Successfully authenticated with Google Drive")
        
    def create_folder(self, folder_name: str, parent_folder_id: Optional[str] = None) -> str:
        """
        Create a folder in Google Drive
        
        Args:
            folder_name: Name of the folder to create
            parent_folder_id: ID of parent folder (None for root)
            
        Returns:
            str: ID of the created folder
        """
        if not self.service:
            self.authenticate()
            
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        if parent_folder_id:
            folder_metadata['parents'] = [parent_folder_id]
            
        folder = self.service.files().create(body=folder_metadata, fields='id').execute()
        folder_id = folder.get('id')
        
        logger.info(f"Created folder '{folder_name}' with ID: {folder_id}")
        return folder_id
        
    def setup_project_folders(self, project_name: str = "RocketReelsAI") -> Dict[str, str]:
        """
        Setup the main project folder structure
        
        Args:
            project_name: Name of the main project folder
            
        Returns:
            Dict mapping folder names to their IDs
        """
        if not self.service:
            self.authenticate()
            
        # Create main project folder
        main_folder_id = self.create_folder(project_name)
        self.folder_ids['main'] = main_folder_id
        
        # Create subfolders
        subfolders = [
            'generated_images',
            'voiceover',
            'generated_videos',
            'crawl_data',
            'search_results',
            'prompts'
        ]
        
        for subfolder in subfolders:
            folder_id = self.create_folder(subfolder, main_folder_id)
            self.folder_ids[subfolder] = folder_id
            
        logger.info(f"Setup complete. Created {len(subfolders)} subfolders under '{project_name}'")
        return self.folder_ids
        
    def create_topic_subfolder(self, folder_type: str, topic_name: str) -> str:
        """
        Create a topic-based subfolder within a main folder (thread-safe)
        
        Args:
            folder_type: Main folder type ('generated_images', 'voiceover', etc.)
            topic_name: Name of the topic/script for the subfolder
            
        Returns:
            str: ID of the created subfolder
        """
        if not self.service:
            self.authenticate()
            
        if folder_type not in self.folder_ids:
            raise ValueError(f"Unknown folder type: {folder_type}")
        
        # Clean topic name for folder naming
        clean_topic = self.clean_folder_name(topic_name)
        cache_key = f"{folder_type}:{clean_topic}"
        
        # Initialize lock if not already done
        if self._lock is None:
            import threading
            self._lock = threading.Lock()
            
        # Thread-safe check for existing subfolder
        with self._lock:
            # Check cache first
            if cache_key in self.topic_subfolder_cache:
                logger.info(f"Using cached subfolder '{clean_topic}' in {folder_type}")
                return self.topic_subfolder_cache[cache_key]
            
            # Check if subfolder already exists in Google Drive
            existing_subfolder_id = self.find_subfolder(folder_type, clean_topic)
            if existing_subfolder_id:
                logger.info(f"Using existing subfolder '{clean_topic}' in {folder_type}")
                self.topic_subfolder_cache[cache_key] = existing_subfolder_id
                return existing_subfolder_id
            
            # Create new subfolder
            try:
                subfolder_id = self.create_folder(clean_topic, self.folder_ids[folder_type])
                logger.info(f"Created topic subfolder '{clean_topic}' in {folder_type}")
                
                # Cache the new subfolder ID
                self.topic_subfolder_cache[cache_key] = subfolder_id
                return subfolder_id
            except Exception as e:
                logger.error(f"Failed to create subfolder '{clean_topic}': {str(e)}")
                # If creation fails, try to find it again (might have been created by another thread)
                existing_subfolder_id = self.find_subfolder(folder_type, clean_topic)
                if existing_subfolder_id:
                    self.topic_subfolder_cache[cache_key] = existing_subfolder_id
                    return existing_subfolder_id
                raise
    
    def clean_folder_name(self, name: str) -> str:
        """Clean and format folder name for Google Drive"""
        import re
        # Remove special characters and limit length
        clean_name = re.sub(r'[<>:"/\\|?*]', '', name)
        clean_name = re.sub(r'\s+', '_', clean_name.strip())
        return clean_name[:50]  # Limit to 50 characters
    
    def find_subfolder(self, folder_type: str, subfolder_name: str) -> Optional[str]:
        """Find existing subfolder by name"""
        if not self.service:
            self.authenticate()
            
        parent_id = self.folder_ids[folder_type]
        query = f"'{parent_id}' in parents and name='{subfolder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        
        results = self.service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get('files', [])
        
        return files[0]['id'] if files else None
    
    def check_file_exists(self, filename: str, folder_id: str) -> Optional[str]:
        """Check if a file already exists in the specified folder"""
        try:
            query = f"'{folder_id}' in parents and name='{filename}' and trashed=false"
            results = self.service.files().list(q=query, fields="files(id, name)").execute()
            files = results.get('files', [])
            return files[0]['id'] if files else None
        except Exception as e:
            logger.warning(f"Error checking file existence: {str(e)}")
            return None
    
    def upload_file(self, local_file_path: str, folder_type: str, 
                   gdrive_filename: Optional[str] = None, topic_name: Optional[str] = None) -> str:
        """
        Upload a file to the specified Google Drive folder
        
        Args:
            local_file_path: Path to the local file to upload
            folder_type: Type of folder ('generated_images', 'voiceover', etc.)
            gdrive_filename: Custom filename for Google Drive (optional)
            topic_name: Topic name for creating subfolder (optional)
            
        Returns:
            str: ID of the uploaded file
        """
        if not self.service:
            self.authenticate()
            
        if folder_type not in self.folder_ids:
            raise ValueError(f"Unknown folder type: {folder_type}")
            
        if not os.path.exists(local_file_path):
            raise FileNotFoundError(f"Local file not found: {local_file_path}")
            
        filename = gdrive_filename or os.path.basename(local_file_path)
        
        # Determine target folder ID
        if topic_name:
            # Create/find topic subfolder and upload there
            target_folder_id = self.create_topic_subfolder(folder_type, topic_name)
            upload_location = f"{folder_type}/{self.clean_folder_name(topic_name)}"
        else:
            # Upload to main folder
            target_folder_id = self.folder_ids[folder_type]
            upload_location = folder_type
        
        # Check cache first for very recent uploads
        cache_key = f"{target_folder_id}:{filename}"
        if cache_key in self.uploaded_files_cache:
            logger.info(f"File '{filename}' recently uploaded to {upload_location}. Using cached ID: {self.uploaded_files_cache[cache_key]}")
            return self.uploaded_files_cache[cache_key]
        
        # Check if file already exists in Google Drive
        existing_file_id = self.check_file_exists(filename, target_folder_id)
        if existing_file_id:
            logger.info(f"File '{filename}' already exists in {upload_location}. Skipping upload. File ID: {existing_file_id}")
            # Cache the existing file ID
            self.uploaded_files_cache[cache_key] = existing_file_id
            return existing_file_id
        
        file_metadata = {
            'name': filename,
            'parents': [target_folder_id]
        }
        
        media = MediaFileUpload(local_file_path)
        
        # Retry upload with exponential backoff
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                file = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                
                file_id = file.get('id')
                logger.info(f"Uploaded '{filename}' to {upload_location} folder. File ID: {file_id}")
                
                # Cache the uploaded file ID
                self.uploaded_files_cache[cache_key] = file_id
                return file_id
                
            except Exception as e:
                error_str = str(e).lower()
                
                if attempt < max_retries - 1:
                    logger.warning(f"Upload attempt {attempt + 1} failed: {str(e)}. Retrying in {retry_delay}s...")
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    
                    # Re-authenticate if it's an auth issue or SSL issue
                    if any(keyword in error_str for keyword in ["authorization", "unauthorized", "ssl", "wrong version number", "connection reset"]):
                        logger.info("Re-authenticating due to connection/auth error...")
                        try:
                            self.authenticate()
                        except Exception as auth_e:
                            logger.warning(f"Re-authentication failed: {str(auth_e)}")
                else:
                    logger.error(f"Upload failed after {max_retries} attempts: {str(e)}")
                    raise
        
    def upload_multiple_files(self, file_paths: List[str], folder_type: str, topic_name: Optional[str] = None) -> List[str]:
        """
        Upload multiple files to the same folder type
        
        Args:
            file_paths: List of local file paths to upload
            folder_type: Type of folder to upload to
            topic_name: Topic name for creating subfolder (optional)
            
        Returns:
            List of file IDs
        """
        file_ids = []
        for file_path in file_paths:
            try:
                file_id = self.upload_file(file_path, folder_type, topic_name=topic_name)
                file_ids.append(file_id)
            except Exception as e:
                logger.error(f"Failed to upload {file_path}: {str(e)}")
                
        return file_ids
        
    def list_files_in_folder(self, folder_type: str) -> List[Dict]:
        """
        List all files in a specific folder
        
        Args:
            folder_type: Type of folder to list files from
            
        Returns:
            List of file information dictionaries
        """
        if not self.service:
            self.authenticate()
            
        if folder_type not in self.folder_ids:
            raise ValueError(f"Unknown folder type: {folder_type}")
            
        query = f"'{self.folder_ids[folder_type]}' in parents and trashed=false"
        
        results = self.service.files().list(
            q=query,
            fields="files(id, name, createdTime, size)"
        ).execute()
        
        return results.get('files', [])
        
    def delete_file(self, file_id: str):
        """Delete a file from Google Drive"""
        if not self.service:
            self.authenticate()
            
        self.service.files().delete(fileId=file_id).execute()
        logger.info(f"Deleted file with ID: {file_id}")
        
    def get_folder_id(self, folder_type: str) -> str:
        """Get the Google Drive folder ID for a specific folder type"""
        return self.folder_ids.get(folder_type)
        
    def save_folder_ids(self, file_path: str = "gdrive_folders.json"):
        """Save folder IDs and caches to a JSON file for persistence"""
        data = {
            "folder_ids": self.folder_ids,
            "topic_subfolder_cache": self.topic_subfolder_cache,
            "uploaded_files_cache": self.uploaded_files_cache
        }
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved folder IDs and cache to {file_path}")
        
    def load_folder_ids(self, file_path: str = "gdrive_folders.json"):
        """Load folder IDs from a JSON file"""
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Handle both old and new format
            if isinstance(data, dict) and "folder_ids" in data:
                self.folder_ids = data["folder_ids"]
                self.topic_subfolder_cache = data.get("topic_subfolder_cache", {})
                self.uploaded_files_cache = data.get("uploaded_files_cache", {})
            else:
                # Old format - just folder IDs
                self.folder_ids = data
                self.topic_subfolder_cache = {}
                self.uploaded_files_cache = {}
            
            logger.info(f"Loaded folder IDs from {file_path}")
        else:
            logger.warning(f"Folder IDs file not found: {file_path}")


# Usage example and utility functions
def initialize_gdrive_storage(credentials_path: str = "credentials.json") -> GDriveStorage:
    """
    Initialize and setup Google Drive storage with folder structure
    
    Args:
        credentials_path: Path to Google OAuth2 credentials file
        
    Returns:
        Configured GDriveStorage instance
    """
    storage = GDriveStorage(credentials_path)
    
    # Try to load existing folder IDs first
    storage.load_folder_ids()
    
    # If no existing folders, create the structure
    if not storage.folder_ids:
        storage.setup_project_folders()
        storage.save_folder_ids()
    else:
        # Still need to authenticate
        storage.authenticate()
    
    return storage


# Integration helper functions for existing agents
def save_generated_image_to_gdrive(image_path: str, storage: GDriveStorage, topic_name: Optional[str] = None) -> str:
    """Save a generated image to Google Drive with optional topic organization"""
    return storage.upload_file(image_path, 'generated_images', topic_name=topic_name)


def save_voiceover_to_gdrive(audio_path: str, storage: GDriveStorage, topic_name: Optional[str] = None) -> str:
    """Save a voiceover file to Google Drive with optional topic organization"""
    return storage.upload_file(audio_path, 'voiceover', topic_name=topic_name)


def save_video_to_gdrive(video_path: str, storage: GDriveStorage, topic_name: Optional[str] = None) -> str:
    """Save a generated video to Google Drive with optional topic organization"""
    return storage.upload_file(video_path, 'generated_videos', topic_name=topic_name)


def save_crawl_data_to_gdrive(data_path: str, storage: GDriveStorage, topic_name: Optional[str] = None) -> str:
    """Save crawled data to Google Drive with optional topic organization"""
    return storage.upload_file(data_path, 'crawl_data', topic_name=topic_name)


def save_multiple_images_to_gdrive(image_paths: List[str], storage: GDriveStorage, topic_name: str) -> List[str]:
    """Save multiple generated images to Google Drive organized by topic"""
    return storage.upload_multiple_files(image_paths, 'generated_images', topic_name=topic_name)


def extract_topic_from_prompt(prompt: str) -> str:
    """Extract a concise topic name from a prompt for folder organization"""
    import re
    # Take first few words and clean them
    words = prompt.split()[:4]  # First 4 words
    topic = "_".join(words)
    # Remove special characters
    topic = re.sub(r'[^a-zA-Z0-9_\s]', '', topic)
    return topic.strip()[:30]  # Limit to 30 characters


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    print("🚀 Rocket Reels AI - Google Drive Storage Setup")
    print("=" * 50)
    
    try:
        # Check if credentials file exists
        if not os.path.exists("credentials.json"):
            print("❌ Error: credentials.json not found!")
            print("Please place your Google OAuth2 credentials file as 'credentials.json' in this directory")
            exit(1)
        
        print("📁 Initializing Google Drive storage...")
        storage = initialize_gdrive_storage()
        
        print("✅ Google Drive storage initialized successfully!")
        print(f"📂 Created/found {len(storage.folder_ids)} folders:")
        
        for folder_name, folder_id in storage.folder_ids.items():
            print(f"   • {folder_name}: {folder_id}")
        
        print("\n🎯 Ready to use! You can now:")
        print("   • Upload images: storage.upload_file('path/to/image.jpg', 'generated_images')")
        print("   • Upload audio: storage.upload_file('path/to/audio.mp3', 'voiceover')")
        print("   • Upload videos: storage.upload_file('path/to/video.mp4', 'generated_videos')")
        
        # Check for different types of files to upload
        upload_candidates = {}
        
        # Check for images
        if os.path.exists("generated_images"):
            images = [f for f in os.listdir("generated_images") if f.endswith(('.jpg', '.png', '.jpeg', '.gif', '.webp'))]
            if images:
                upload_candidates['generated_images'] = images
        
        # Check for voiceover files
        if os.path.exists("voiceover"):
            audio_files = [f for f in os.listdir("voiceover") if f.endswith(('.mp3', '.wav', '.m4a', '.aac', '.ogg'))]
            if audio_files:
                upload_candidates['voiceover'] = audio_files
        
        # Check for videos
        if os.path.exists("generated_videos"):
            videos = [f for f in os.listdir("generated_videos") if f.endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm'))]
            if videos:
                upload_candidates['generated_videos'] = videos
        
        # Check for other common folders
        for folder_name in ['crawl_data', 'search_results', 'prompts']:
            if os.path.exists(folder_name):
                files = [f for f in os.listdir(folder_name) if os.path.isfile(os.path.join(folder_name, f))]
                if files:
                    upload_candidates[folder_name] = files
        
        if upload_candidates:
            print(f"\n🧪 Found files to upload:")
            for folder, files in upload_candidates.items():
                print(f"   📁 {folder}: {len(files)} files")
            
            print("\nUpload options:")
            print("  1. Upload all files from all folders")
            print("  2. Choose specific folder to upload")
            print("  3. Skip upload")
            choice = input("Choose option (1/2/3): ").strip()
            
            if choice == '1':
                print("📤 Uploading all files...")
                total_uploaded = 0
                for folder_type, files in upload_candidates.items():
                    print(f"  📁 Uploading {len(files)} files to {folder_type}...")
                    file_paths = [os.path.join(folder_type, f) for f in files]
                    file_ids = storage.upload_multiple_files(file_paths, folder_type)
                    total_uploaded += len(file_ids)
                    print(f"    ✅ {len(file_ids)} files uploaded to {folder_type}")
                
                print(f"🎉 Upload complete! {total_uploaded} total files uploaded")
                
            elif choice == '2':
                print("Available folders:")
                folders = list(upload_candidates.keys())
                for i, folder in enumerate(folders, 1):
                    print(f"  {i}. {folder} ({len(upload_candidates[folder])} files)")
                
                try:
                    folder_choice = int(input("Choose folder number: ")) - 1
                    if 0 <= folder_choice < len(folders):
                        selected_folder = folders[folder_choice]
                        files = upload_candidates[selected_folder]
                        print(f"📤 Uploading {len(files)} files to {selected_folder}...")
                        file_paths = [os.path.join(selected_folder, f) for f in files]
                        file_ids = storage.upload_multiple_files(file_paths, selected_folder)
                        print(f"✅ Upload complete! {len(file_ids)} files uploaded")
                    else:
                        print("Invalid folder selection")
                except ValueError:
                    print("Invalid input")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Make sure credentials.json is in the current directory")
        print("2. Install dependencies: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        print("3. Check your internet connection")