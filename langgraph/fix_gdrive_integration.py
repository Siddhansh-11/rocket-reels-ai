#!/usr/bin/env python3
"""
Fix Google Drive Integration for LangGraph
This script tests and fixes the Google Drive connection
"""

import asyncio
import os
from pathlib import Path

async def test_gdrive_integration():
    """Test Google Drive integration"""
    print("🔧 Testing Google Drive Integration...")
    
    try:
        # Import the fixed modules
        from gdrive_storage import initialize_gdrive_storage, save_generated_image_to_gdrive
        from image_generation_agent import get_gdrive_storage
        
        print("✅ Modules imported successfully")
        
        # Test storage initialization
        print("📁 Testing storage initialization...")
        storage = await get_gdrive_storage()
        
        if storage:
            print("✅ Google Drive storage initialized successfully!")
            print(f"📂 Available folders: {list(storage.folder_ids.keys())}")
            
            # Test if we can find existing images
            images_dir = Path("generated_images")
            if images_dir.exists():
                image_files = list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.png"))
                print(f"📸 Found {len(image_files)} existing images")
                
                if image_files:
                    # Test uploading one image
                    test_image = image_files[0]
                    print(f"🧪 Testing upload with: {test_image.name}")
                    
                    try:
                        file_id = await asyncio.to_thread(
                            save_generated_image_to_gdrive,
                            str(test_image),
                            storage,
                            "MIT_3D_Chips_Test"
                        )
                        print(f"✅ Test upload successful! File ID: {file_id}")
                        return True
                    except Exception as e:
                        print(f"❌ Test upload failed: {str(e)}")
                        return False
            else:
                print("ℹ️  No images found to test upload")
                return True
        else:
            print("❌ Google Drive storage not available")
            return False
            
    except Exception as e:
        print(f"❌ Integration test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("🚀 Google Drive Integration Fixer")
    print("=" * 40)
    
    # Check if credentials exist
    if not os.path.exists("credentials.json"):
        print("❌ credentials.json not found!")
        print("Please place your Google OAuth2 credentials file as 'credentials.json'")
        return
    
    # Test the integration
    success = await test_gdrive_integration()
    
    if success:
        print("\n✅ Google Drive integration is working!")
        print("🎯 LangGraph should now be able to upload images to Google Drive")
    else:
        print("\n❌ Google Drive integration needs attention")
        print("🔧 Please check the error messages above")

if __name__ == "__main__":
    asyncio.run(main())