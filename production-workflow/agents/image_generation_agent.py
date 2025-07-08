from langchain_core.tools import tool
import os
import base64
import asyncio
import aiohttp
import aiofiles
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

# Using FLUX Schnell Free model
FLUX_MODEL = "black-forest-labs/FLUX.1-schnell-Free"

# Check if Together AI client is available
try:
    from together import Together
    TOGETHER_AVAILABLE = True
except ImportError:
    TOGETHER_AVAILABLE = False
    print("Together AI Python client not available. Install with: pip install together")

async def ensure_dir_exists(directory):
    """Create directory asynchronously using to_thread if it doesn't exist."""
    if not os.path.exists(directory):
        await asyncio.to_thread(os.makedirs, directory, exist_ok=True)

async def generate_image_with_together(
    prompt: str, 
    output_path: Optional[str] = None,
    width: int = 576,
    height: int = 1024,
    model: str = FLUX_MODEL,
    steps: int = 4  # Schnell model default steps
) -> Dict[str, Any]:
    """Generate an image using Together AI's FLUX Schnell Free model.
    
    Args:
        prompt (str): Text description of the image to generate
        output_path (str, optional): Path to save the image. If None, returns image details only.
        width (int): Width of the generated image (default: 576 for 9:16 portrait)
        height (int): Height of the generated image (default: 1024 for 9:16 portrait)
        model (str): Model to use for generation
        
    Returns:
        dict: Response data containing image URL or base64 data and file path
    """
    print(f"Generating image using Together AI ({model})...")
    print(f"Dimensions: {width}x{height} (9:16 portrait for social media)")
    print(f"Prompt: {prompt}")
    
    try:
        if not TOGETHER_AVAILABLE:
            return {"error": "Together AI client not available. Install with: pip install together"}
            
        client = Together(api_key=TOGETHER_API_KEY)
        
        response = client.images.generate(
            prompt=prompt,
            model=model,
            width=width,
            height=height,
            steps=steps,
            n=1
        )
        
        if hasattr(response, 'data') and len(response.data) > 0:
            if hasattr(response.data[0], 'url'):
                image_url = response.data[0].url
                print(f"Found image URL: {image_url}")
                
                if output_path:
                    await ensure_dir_exists(os.path.dirname(output_path))
                    async with aiohttp.ClientSession() as session:
                        async with session.get(image_url) as img_response:
                            if img_response.status == 200:
                                async with aiofiles.open(output_path, 'wb') as f:
                                    await f.write(await img_response.read())
                                print(f"Image saved to {output_path}")
                
                print("Image generation successful!")
                return {
                    "status": "success",
                    "image_url": image_url,
                    "file_path": output_path
                }
            
            elif hasattr(response.data[0], 'b64_json') and response.data[0].b64_json:
                image_b64 = response.data[0].b64_json
                
                if output_path:
                    await ensure_dir_exists(os.path.dirname(output_path))
                    image_data = base64.b64decode(image_b64)
                    image = await asyncio.to_thread(lambda: Image.open(io.BytesIO(image_data)))
                    await asyncio.to_thread(lambda: image.save(output_path))
                    print(f"Image saved to {output_path}")
                
                print("Image generation successful!")
                return {
                    "status": "success",
                    "base64_image": image_b64[:100] + "...",
                    "file_path": output_path
                }
        
        print("No image data found in response")
        return {"error": "No image data in response", "response": str(response)}
                
    except Exception as e:
        print(f"Exception: {str(e)}")
        return {"error": str(e)}

@tool
async def generate_image_flux(prompt: str, model: str = FLUX_MODEL, width: int = 576, height: int = 1024, steps: int = 4) -> str:
    """Generate an image using Together AI's FLUX Schnell Free API.
    
    Args:
        prompt: Detailed description of the image to generate
        model: Model to use (default: FLUX.1-schnell-Free)
        width: Width of the generated image (default: 576 for 9:16 portrait)
        height: Height of the generated image (default: 1024 for 9:16 portrait)
        steps: Number of inference steps (default: 4 for Schnell)
    
    Returns:
        JSON string with image details and file path
    """
    try:
        import uuid
        
        filename = f"{uuid.uuid4().hex[:8]}.jpg"
        base_dir = Path(__file__).parent.parent
        output_dir = base_dir / "assets" / "generated_images"
        await ensure_dir_exists(output_dir)
        output_path = output_dir / filename
        
        result = await generate_image_with_together(
            prompt=prompt,
            output_path=str(output_path),
            width=width,
            height=height,
            model=model,
            steps=steps
        )
        
        if "error" in result:
            return json.dumps({
                "error": result["error"], 
                "status": "failed", 
                "fallback": "Use manual image generation with DALL-E 3, Canva, or Leonardo.ai"
            })
            
        response_data = {
            "status": "success",
            "file_path": str(output_path),
            "image_url": result.get("image_url", ""),
            "prompt": prompt
        }
        
        return json.dumps(response_data)
        
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
        output_directory = Path(output_dir)
        await ensure_dir_exists(output_directory)
        
        results = {}
        cues = []
        
        if isinstance(visual_timing, dict) and "cues" in visual_timing:
            cues = visual_timing["cues"]
        elif isinstance(visual_timing, str):
            import re
            timestamp_descriptions = re.findall(r'(\d+:\d+)\s*-\s*([^\n•]+)', visual_timing)
            bullet_descriptions = re.findall(r'•\s+([^\n•]+)', visual_timing)
            
            for i, (timestamp, description) in enumerate(timestamp_descriptions):
                cues.append({
                    "timestamp": timestamp,
                    "description": description.strip(),
                    "priority": "high" if "HIGH PRIORITY" in visual_timing else "medium"
                })
            
            for i, description in enumerate(bullet_descriptions):
                if len(cues) < 5:
                    cues.append({
                        "timestamp": f"scene_{i+1+len(cues)}",
                        "description": description.strip(),
                        "priority": "medium"
                    })
        
        for i, cue in enumerate(cues[:5]):
            timestamp = cue.get("timestamp", f"scene_{i+1}")
            description = cue.get("description", "")
            
            if description:
                safe_timestamp = str(timestamp).replace(':', '_').replace(' ', '_')
                output_path = output_directory / f"{safe_timestamp}.jpg"
                
                enhanced_prompt = (
                    f"Professional cinematic shot: {description}, "
                    f"high quality, detailed, 9:16 portrait aspect ratio, vertical composition, "
                    f"social media optimized, film still, professional lighting"
                )
                
                result = await generate_image_with_together(
                    prompt=enhanced_prompt,
                    output_path=str(output_path)
                )
                
                result_data = {
                    "file_path": str(output_path) if "error" not in result else None,
                    "description": description,
                    "status": "success" if "error" not in result else "failed",
                    "error": result.get("error", None) if "error" in result else None,
                    "prompt": enhanced_prompt
                }
                
                results[str(timestamp)] = result_data
        
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
    try:
        if not TOGETHER_AVAILABLE:
            try:
                print("Attempting to install Together AI package...")
                await asyncio.to_thread(lambda: __import__('subprocess').check_call(["pip", "install", "together"]))
                print("Together AI package installed successfully")
                # Update module-level variable
                globals()['TOGETHER_AVAILABLE'] = True
            except Exception as e:
                return json.dumps({
                    "status": "error", 
                    "message": f"Together AI client installation failed: {str(e)}",
                    "action": "Install the Together package manually with: pip install together"
                })
        
        if not TOGETHER_API_KEY:
            return json.dumps({
                "status": "error", 
                "message": "Together AI API key not found in environment variables",
                "action": "Check your .env file and ensure TogetherAI_API_KEY is properly set"
            })
        
        from together import Together
        client = Together(api_key=TOGETHER_API_KEY)
        
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
            "model": FLUX_MODEL,
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
        
        high_priority = re.findall(r'HIGH PRIORITY VISUALS:(.*?)(?:MEDIUM PRIORITY|$)', visual_timing_str, re.DOTALL)
        high_priority_cues = re.findall(r'•\s+(.*?)(?=\n•|\n\n|$)', high_priority[0] if high_priority else "", re.DOTALL)
        
        medium_priority = re.findall(r'MEDIUM PRIORITY VISUALS:(.*?)(?:LOW PRIORITY|B-ROLL|$)', visual_timing_str, re.DOTALL)
        medium_priority_cues = re.findall(r'•\s+(.*?)(?=\n•|\n\n|$)', medium_priority[0] if medium_priority else "", re.DOTALL)
        
        b_roll = re.findall(r'B-ROLL FOOTAGE NEEDED:(.*?)(?:\n\n|$)', visual_timing_str, re.DOTALL)
        b_roll_cues = re.findall(r'•\s+(.*?)(?=\n•|\n\n|$)', b_roll[0] if b_roll else "", re.DOTALL)
        
        all_cues = []
        
        for i, cue in enumerate(high_priority_cues):
            timestamp_match = re.search(r'(\d+:\d+)', cue)
            timestamp = timestamp_match.group(1) if timestamp_match else f"high_{i}"
            description = cue.strip()
            if timestamp_match:
                try:
                    description = description.split('-', 1)[1].strip() if '-' in description else description
                except IndexError:
                    description = description.strip()
                
            all_cues.append({
                "timestamp": timestamp,
                "description": description,
                "priority": "high"
            })
        
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

image_generation_tools = [
    generate_image_flux,
    generate_from_visual_timing,
    check_image_generation_status,
    extract_visual_cues_from_timing
]