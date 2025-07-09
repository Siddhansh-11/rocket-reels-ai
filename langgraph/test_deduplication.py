#!/usr/bin/env python3
"""
Test Google Drive deduplication
"""

import asyncio
from pathlib import Path
from gdrive_storage import initialize_gdrive_storage, save_generated_image_to_gdrive

async def test_deduplication():
    """Test that the same file is not uploaded twice"""
    print("🧪 Testing Google Drive deduplication...")
    
    try:
        # Initialize storage
        storage = initialize_gdrive_storage()
        
        # Find an existing image to test with
        images_dir = Path("generated_images")
        if not images_dir.exists():
            print("❌ No generated_images folder found!")
            return
        
        image_files = list(images_dir.glob("*.jpg"))
        if not image_files:
            print("❌ No images found to test with!")
            return
        
        test_image = image_files[0]
        topic_name = "Test_Deduplication"
        
        print(f"📤 First upload attempt: {test_image.name}")
        file_id_1 = await asyncio.to_thread(
            save_generated_image_to_gdrive,
            str(test_image),
            storage,
            topic_name
        )
        print(f"✅ First upload result: {file_id_1}")
        
        print(f"📤 Second upload attempt (should be deduplicated): {test_image.name}")
        file_id_2 = await asyncio.to_thread(
            save_generated_image_to_gdrive,
            str(test_image),
            storage,
            topic_name
        )
        print(f"✅ Second upload result: {file_id_2}")
        
        if file_id_1 == file_id_2:
            print("🎉 SUCCESS: Deduplication working! Same file ID returned.")
        else:
            print("❌ FAILURE: Different file IDs - deduplication not working.")
            
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_deduplication())