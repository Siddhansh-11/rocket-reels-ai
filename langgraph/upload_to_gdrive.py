#!/usr/bin/env python3
"""
Upload existing generated images to Google Drive
This script will upload all images from the generated_images folder to Google Drive
"""

import os
import sys
from pathlib import Path
from gdrive_storage import initialize_gdrive_storage, save_multiple_images_to_gdrive

def main():
    print("🚀 Uploading Generated Images to Google Drive")
    print("=" * 50)
    
    try:
        # Initialize Google Drive storage
        print("📁 Initializing Google Drive storage...")
        storage = initialize_gdrive_storage()
        print("✅ Google Drive storage initialized successfully!")
        
        # Find all images in the generated_images folder
        images_dir = Path("generated_images")
        if not images_dir.exists():
            print("❌ No generated_images folder found!")
            return
        
        # Get all image files
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        image_files = []
        
        for ext in image_extensions:
            image_files.extend(list(images_dir.glob(f"*{ext}")))
            image_files.extend(list(images_dir.glob(f"*{ext.upper()}")))
        
        if not image_files:
            print("❌ No images found in generated_images folder!")
            return
        
        print(f"📸 Found {len(image_files)} images to upload")
        
        # Get topic name from user
        topic_name = input("🏷️  Enter topic name for organizing images (e.g., 'MIT 3D Chips'): ").strip()
        if not topic_name:
            topic_name = "Generated_Images"
        
        print(f"📤 Uploading {len(image_files)} images to topic folder: {topic_name}")
        
        # Upload images
        uploaded_count = 0
        failed_count = 0
        
        for image_file in image_files:
            try:
                print(f"⬆️  Uploading {image_file.name}...")
                file_id = storage.upload_file(
                    str(image_file), 
                    'generated_images', 
                    topic_name=topic_name
                )
                print(f"✅ Uploaded {image_file.name} - File ID: {file_id}")
                uploaded_count += 1
            except Exception as e:
                print(f"❌ Failed to upload {image_file.name}: {str(e)}")
                failed_count += 1
        
        print("\n" + "=" * 50)
        print(f"📊 Upload Summary:")
        print(f"✅ Successfully uploaded: {uploaded_count} images")
        print(f"❌ Failed uploads: {failed_count} images")
        print(f"📁 Topic folder: {topic_name}")
        
        if uploaded_count > 0:
            print(f"\n🎉 Images are now available in your Google Drive!")
            print(f"📂 Location: RocketReelsAI > generated_images > {topic_name}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Make sure credentials.json is in the current directory")
        print("2. Check your internet connection")
        print("3. Verify Google Drive API permissions")

if __name__ == "__main__":
    main()