from langchain_core.tools import tool
import os
import base64
import asyncio
import aiohttp  # Replace requests with aiohttp
import aiofiles  # For async file operations
from dotenv import load_dotenv
from pathlib import Path
import io
import json
from PIL import Image
from typing import Dict, List, Any, Optional, Union

# Load environment variables
load_dotenv()

# Get Together AI API key
TOGETHER_API_KEY = os.getenv("TogetherAI_API_KEY")

# The free FLUX model that works with free tier
FREE_FLUX_MODEL = "black-forest-labs/FLUX.1-schnell-Free"

# Check if Together AI client is available
try:
    from together import Together
    TOGETHER_AVAILABLE = True
except ImportError:
    TOGETHER_AVAILABLE = False
    print("⚠️ Together AI Python client not available. Install with: pip install together")

async def ensure_dir_exists(directory):
    """Create directory asynchronously using to_thread if it doesn't exist."""
    if not os.path.exists(directory):
        await asyncio.to_thread(os.makedirs, directory, exist_ok=True)

async def generate_image_with_together(
    prompt: str, 
    output_path: Optional[str] = None,
    width: int = 1024,
    height: int = 576  # 16:9 aspect ratio
) -> Dict[str, Any]:
    """Generate an image using Together AI's free FLUX model.
    
    Args:
        prompt (str): Text description of the image to generate
        output_path (str, optional): Path to save the image. If None, displays image details only.
        width (int): Width of the generated image
        height (int): Height of the generated image
        
    Returns:
        dict: Response data containing image URL or error message
    """
    print(f"\n🔄 Generating image using Together AI ({FREE_FLUX_MODEL})...")
    print(f"📝 Prompt: {prompt}")
    
    try:
        # Check if Together AI client is available
        if not TOGETHER_AVAILABLE:
            return {"error": "Together AI client not available. Install with: pip install together"}
            
        # Initialize the client with API key
        client = Together(api_key=TOGETHER_API_KEY)
        
        # Generate the image with parameters for free tier
        response = client.images.generate(
            prompt=prompt,
            model=FREE_FLUX_MODEL,
            steps=3,  # Setting steps explicitly within the allowed range (1-4)
            width=width,
            height=height,
            n=1  # Generate 1 image
        )
        
        # Check if the response has data and URL
        if hasattr(response, 'data') and len(response.data) > 0:
            # Check if the response contains a URL
            if hasattr(response.data[0], 'url'):
                image_url = response.data[0].url
                print(f"Found image URL: {image_url}")
                
                # Download the image using aiohttp instead of requests
                if output_path:
                    # Create directory asynchronously if it doesn't exist
                    await ensure_dir_exists(os.path.dirname(output_path))
                    
                    # Download and save the image asynchronously
                    async with aiohttp.ClientSession() as session:
                        async with session.get(image_url) as img_response:
                            if img_response.status == 200:
                                # Save the image asynchronously
                                async with aiofiles.open(output_path, 'wb') as f:
                                    await f.write(await img_response.read())
                                print(f"✅ Image saved to {output_path}")
                    
                print("✅ Image generation successful!")
                return {
                    "status": "success",
                    "image_url": image_url,
                    "file_path": output_path
                }
            
            # Try to get base64 data if URL is not available
            elif hasattr(response.data[0], 'b64_json') and response.data[0].b64_json:
                image_b64 = response.data[0].b64_json
                
                if output_path:
                    # Create directory asynchronously if it doesn't exist
                    await ensure_dir_exists(os.path.dirname(output_path))
                    
                    # Save the image asynchronously
                    image_data = base64.b64decode(image_b64)
                    # Run PIL operations in a thread since they're blocking
                    image = await asyncio.to_thread(lambda: Image.open(io.BytesIO(image_data)))
                    await asyncio.to_thread(lambda: image.save(output_path))
                    print(f"✅ Image saved to {output_path}")
                
                print("✅ Image generation successful!")
                return {
                    "status": "success",
                    "base64_image": image_b64[:100] + "...",  # Truncated for display
                    "file_path": output_path
                }
        
        print("❌ No image data found in response")
        return {"error": "No image data in response", "response": str(response)}
                
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return {"error": str(e)}

@tool
async def generate_image_flux(prompt: str, model: str = FREE_FLUX_MODEL, width: int = 1024, height: int = 576) -> str:
    """Generate an image using Together AI's FLUX API.
    
    Args:
        prompt: Detailed description of the image to generate
        model: Model to use (default: free tier model)
        width: Width of the generated image
        height: Height of the generated image
    
    Returns:
        JSON string with image details and URL
    """
    try:
        import uuid
        
        # Generate a unique filename
        filename = f"{uuid.uuid4().hex[:8]}.jpg"
        output_dir = Path("generated_images")
        # Ensure directory exists asynchronously
        await ensure_dir_exists(output_dir)
        output_path = output_dir / filename
        
        # Generate the image
        result = await generate_image_with_together(
            prompt=prompt,
            output_path=str(output_path),
            width=width,
            height=height
        )
        
        if "error" in result:
            return json.dumps({
                "error": result["error"], 
                "status": "failed", 
                "fallback": "Use manual image generation with DALL-E 3, Canva, or Leonardo.ai"
            })
            
        # Return successful result with all necessary information
        return json.dumps({
            "status": "success",
            "file_path": str(output_path),
            "image_url": result.get("image_url", ""),
            "prompt": prompt
        })
        
    except Exception as e:
        return json.dumps({
            "error": str(e), 
            "status": "failed", 
            "fallback": "Use manual image generation with DALL-E 3, Canva, or Leonardo.ai"
        })

@tool
async def generate_from_visual_timing(visual_timing: Union[Dict, str], output_dir: str = "scene_images") -> str:
    """Generate images from visual timing plan."""
    try:
        # Ensure the output directory exists asynchronously
        output_directory = Path(output_dir)
        await ensure_dir_exists(output_directory)
        
        results = {}
        cues = []
        
        # Parse visual timing data based on its type
        if isinstance(visual_timing, dict) and "cues" in visual_timing:
            # Direct access to cues
            cues = visual_timing["cues"]
        elif isinstance(visual_timing, str):
            # Parse string format - look for timestamp patterns
            import re
            
            # Try to extract visual cues with format "00:00 - Description"
            timestamp_descriptions = re.findall(r'(\d+:\d+)\s*-\s*([^\n•]+)', visual_timing)
            
            # Also look for bullet point format "• Description"
            bullet_descriptions = re.findall(r'•\s+([^\n•]+)', visual_timing)
            
            # Format timestamp descriptions
            for i, (timestamp, description) in enumerate(timestamp_descriptions):
                cues.append({
                    "timestamp": timestamp,
                    "description": description.strip(),
                    "priority": "high" if "HIGH PRIORITY" in visual_timing else "medium"
                })
            
            # Format bullet point descriptions
            for i, description in enumerate(bullet_descriptions):
                if len(cues) < 5:  # Limit to 5 total images
                    cues.append({
                        "timestamp": f"scene_{i+1+len(cues)}",
                        "description": description.strip(),
                        "priority": "medium"
                    })
        
        # Generate images for each cue (limit to 5 total)
        for i, cue in enumerate(cues[:5]):
            timestamp = cue.get("timestamp", f"scene_{i+1}")
            description = cue.get("description", "")
            
            if description:
                # Clean timestamp for filename
                safe_timestamp = str(timestamp).replace(':', '_').replace(' ', '_')
                output_path = output_directory / f"{safe_timestamp}.jpg"
                
                # Create an enhanced prompt with B-roll cinematic style
                enhanced_prompt = (
                    f"Professional cinematic shot: {description}, "
                    f"high quality, detailed, 16:9 aspect ratio, film still, professional lighting"
                )
                
                # Generate the image
                result = await generate_image_with_together(
                    prompt=enhanced_prompt,
                    output_path=str(output_path)
                )
                
                # Store the result
                results[str(timestamp)] = {
                    "file_path": str(output_path) if "error" not in result else None,
                    "description": description,
                    "status": "success" if "error" not in result else "failed",
                    "error": result.get("error", None) if "error" in result else None,
                    "prompt": enhanced_prompt
                }
        
        return json.dumps({
            "status": "completed",
            "generated_images": len(results),
            "results": results
        })
        
    except Exception as e:
        return json.dumps({
            "error": str(e), 
            "status": "failed",
            "fallback": "Consider using manual image generation for key scenes"
        })

@tool
async def check_image_generation_status() -> str:
    """Check if image generation services are available and functioning."""
    global TOGETHER_AVAILABLE
    try:
        # Check if Together AI client is available
        if not TOGETHER_AVAILABLE:
            try:
                # Try to install together package automatically using asyncio.to_thread
                print("📦 Attempting to install Together AI package...")
                await asyncio.to_thread(lambda: __import__('subprocess').check_call(["pip", "install", "together"]))
                print("✅ Together AI package installed successfully")
                TOGETHER_AVAILABLE = True
            except Exception as e:
                return json.dumps({
                    "status": "error", 
                    "message": f"Together AI client installation failed: {str(e)}",
                    "action": "Install the Together package manually with: pip install together"
                })
            
        # Check API key
        if not TOGETHER_API_KEY:
            return json.dumps({
                "status": "error", 
                "message": "Together AI API key not found in environment variables",
                "action": "Check your .env file and ensure TogetherAI_API_KEY is properly set"
            })
        
        # Try with minimal parameters to verify API works
        from together import Together
        client = Together(api_key=TOGETHER_API_KEY)
        
        # Simple API call to verify connection
        test_response = client.models.list()
        available_models = [model.id for model in test_response.data if "FLUX" in model.id]
        
        if not available_models:
            return json.dumps({
                "status": "warning",
                "message": "API connection works but no FLUX models available for your account",
                "action": "Proceed with generate_image_flux anyway with model=black-forest-labs/FLUX.1-schnell-Free",
                "use_default_model": True
            })
        
        return json.dumps({
            "status": "available", 
            "service": "Together AI", 
            "model": FREE_FLUX_MODEL,
            "available_models": available_models,
            "message": "Image generation is fully operational",
            "action": "Proceed with generate_image_flux directly"
        })
    except Exception as e:
        return json.dumps({
            "status": "error", 
            "message": f"Error checking image service: {str(e)}",
            "action": "Troubleshoot API connection or proceed with generate_image_flux anyway"
        })

@tool
async def extract_visual_cues_from_timing(visual_timing_str: str) -> str:
    """Extract visual cues from a timing string for image generation."""
    try:
        import re
        
        # Extract high priority visuals
        high_priority = re.findall(r'HIGH PRIORITY VISUALS:(.*?)(?:MEDIUM PRIORITY|$)', visual_timing_str, re.DOTALL)
        high_priority_cues = re.findall(r'•\s+(.*?)(?=\n•|\n\n|$)', high_priority[0] if high_priority else "", re.DOTALL)
        
        # Extract medium priority visuals
        medium_priority = re.findall(r'MEDIUM PRIORITY VISUALS:(.*?)(?:LOW PRIORITY|B-ROLL|$)', visual_timing_str, re.DOTALL)
        medium_priority_cues = re.findall(r'•\s+(.*?)(?=\n•|\n\n|$)', medium_priority[0] if medium_priority else "", re.DOTALL)
        
        # Extract B-roll suggestions
        b_roll = re.findall(r'B-ROLL FOOTAGE NEEDED:(.*?)(?:\n\n|$)', visual_timing_str, re.DOTALL)
        b_roll_cues = re.findall(r'•\s+(.*?)(?=\n•|\n\n|$)', b_roll[0] if b_roll else "", re.DOTALL)
        
        # Combine and format all cues
        all_cues = []
        
        # Add high priority cues
        for i, cue in enumerate(high_priority_cues):
            # Extract timestamp if available
            timestamp_match = re.search(r'(\d+:\d+)', cue)
            timestamp = timestamp_match.group(1) if timestamp_match else f"high_{i}"
            
            # Clean description
            description = cue.strip()
            if timestamp_match:
                try:
                    description = description.split('-', 1)[1].strip() if '-' in description else description
                except IndexError:
                    # Handle the case where split doesn't produce enough elements
                    description = description.strip()
                
            all_cues.append({
                "timestamp": timestamp,
                "description": description,
                "priority": "high"
            })
        
        # Add medium priority cues (top 3)
        for i, cue in enumerate(medium_priority_cues[:3]):
            timestamp_match = re.search(r'(\d+:\d+)', cue)
            timestamp = timestamp_match.group(1) if timestamp_match else f"medium_{i}"
            
            description = cue.strip()
            if timestamp_match:
                try:
                    description = description.split('-', 1)[1].strip() if '-' in description else description
                except IndexError:
                    description = description.strip()
                
            all_cues.append({
                "timestamp": timestamp,
                "description": description,
                "priority": "medium"
            })
        
        # Add top B-roll suggestions
        for i, cue in enumerate(b_roll_cues[:2]):
            all_cues.append({
                "timestamp": f"b_roll_{i}",
                "description": cue.strip(),
                "priority": "low"
            })
        
        return json.dumps({
            "status": "success",
            "cues": all_cues,
            "total_cues": len(all_cues),
            "message": "Visual cues extracted successfully"
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Error extracting visual cues: {str(e)}",
            "cues": []
        })

# Create the tools list to export
image_generation_tools = [
    generate_image_flux,
    generate_from_visual_timing,
    check_image_generation_status,
    extract_visual_cues_from_timing
]