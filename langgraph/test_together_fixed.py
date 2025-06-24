import asyncio
import os
import json
from pathlib import Path
from dotenv import load_dotenv
import uuid
import aiohttp
import aiofiles

# Load environment variables
load_dotenv()

# Get Together API key
TOGETHER_API_KEY = os.getenv("TogetherAI_API_KEY")
FREE_FLUX_MODEL = "black-forest-labs/FLUX.1-schnell-Free"

async def ensure_dir_exists(directory):
    """Create directory asynchronously using to_thread if it doesn't exist."""
    if not os.path.exists(directory):
        print(f"Creating directory: {directory}")
        await asyncio.to_thread(os.makedirs, directory, exist_ok=True)
        print(f"Directory created: {directory}")

async def generate_test_image(prompt="Simple blue circle on white background", width=512, height=512):
    """Test function to generate a simple image using Together AI."""
    try:
        print(f"\n🧪 Testing image generation with Together AI...")
        
        if not TOGETHER_API_KEY:
            print("❌ No API key found. Set TogetherAI_API_KEY in your .env file")
            return False
        
        # Import Together client
        try:
            from together import Together
            print("✅ Together package is available")
        except ImportError:
            print("❌ Together package not found - installing...")
            import subprocess
            subprocess.check_call(["pip", "install", "together"])
            from together import Together
            print("✅ Together package installed successfully")
        
        # Generate output path
        output_dir = Path("test_images")
        await ensure_dir_exists(output_dir)
        
        filename = f"test_{uuid.uuid4().hex[:8]}.jpg"
        output_path = output_dir / filename
        
        print(f"\n📝 Generating image with prompt: '{prompt}'")
        print(f"🔍 Image dimensions: {width}x{height}")
        
        # Initialize client
        client = Together(api_key=TOGETHER_API_KEY)
        
        # Generate the image
        response = client.images.generate(
            prompt=prompt,
            model=FREE_FLUX_MODEL,
            steps=3,
            width=width,
            height=height,
            n=1
        )
        
        if hasattr(response, 'data') and len(response.data) > 0:
            if hasattr(response.data[0], 'url'):
                image_url = response.data[0].url
                print(f"✅ Image URL received: {image_url}")
                
                # Download the image
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url) as img_response:
                        if img_response.status == 200:
                            async with aiofiles.open(output_path, 'wb') as f:
                                await f.write(await img_response.read())
                            print(f"✅ Test image saved to {output_path}")
                            return True
                        else:
                            print(f"❌ Failed to download image: HTTP {img_response.status}")
                            return False
            else:
                print("❌ No URL in response")
                return False
        else:
            print("❌ No data in response")
            return False
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

async def run_multiple_tests():
    """Run multiple tests to verify different aspects of image generation."""
    print("📊 RUNNING IMAGE GENERATION TESTS 📊")
    
    # Test 1: Simple circle to verify basic functionality
    print("\n📋 Test 1: Basic image generation")
    test1 = await generate_test_image("Simple blue circle on white background", 512, 512)
    
    # Test 2: More complex prompt with higher resolution
    print("\n📋 Test 2: Complex prompt with higher resolution")
    test2 = await generate_test_image(
        "Professional cinematic shot of a futuristic city with flying cars and holographic billboards, detailed lighting", 
        1024, 
        576
    )
    
    # Test 3: Creative abstract prompt
    print("\n📋 Test 3: Creative abstract prompt")
    test3 = await generate_test_image(
        "Abstract visualization of artificial intelligence thinking, digital art style", 
        768, 
        768
    )
    
    # Summary
    print("\n📝 TEST SUMMARY:")
    print(f"Test 1 (Basic): {'✅ Passed' if test1 else '❌ Failed'}")
    print(f"Test 2 (Complex): {'✅ Passed' if test2 else '❌ Failed'}")
    print(f"Test 3 (Creative): {'✅ Passed' if test3 else '❌ Failed'}")
    
    if test1 or test2 or test3:
        print("\n✅ TOGETHER AI IMAGE GENERATION IS WORKING")
        print("You can now use this in your LangGraph agent with --allow-blocking flag")
    else:
        print("\n❌ TOGETHER AI IMAGE GENERATION IS NOT WORKING")
        print("Check your API key and connection")

if __name__ == "__main__":
    # Run the test
    asyncio.run(run_multiple_tests())
    print("\nDone!")