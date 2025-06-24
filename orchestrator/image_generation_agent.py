import os
import asyncio
import json
import base64
from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx
from supabase import create_client, Client
from .workflow_state import ContentState, PhaseOutput
from langchain_core.messages import HumanMessage, AIMessage


class ImageGenerationAgent:
    """Agent for generating images from prompts using various AI services."""
    
    def __init__(self):
        self.supabase = self._get_supabase_client()
        # You can configure different image generation services here
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.stability_api_key = os.getenv("STABILITY_API_KEY")
        self.replicate_api_key = os.getenv("REPLICATE_API_KEY")
        self.aiml_api_key = os.getenv("AIML_API_KEY")
        
    def _get_supabase_client(self):
        """Get Supabase client with proper configuration."""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise Exception("Missing SUPABASE_URL or SUPABASE_ANON_KEY environment variables")
        
        return create_client(supabase_url, supabase_key)
    
    async def generate_image_dalle3(self, prompt: str, style: str = "vivid", size: str = "1024x1024") -> Dict[str, Any]:
        """Generate image using OpenAI DALL-E 3."""
        if not self.openai_api_key:
            return {"status": "error", "error": "OpenAI API key not configured"}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/images/generations",
                    headers={
                        "Authorization": f"Bearer {self.openai_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "dall-e-3",
                        "prompt": prompt,
                        "n": 1,
                        "size": size,
                        "quality": "hd",
                        "style": style
                    },
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "status": "success",
                        "image_url": data["data"][0]["url"],
                        "revised_prompt": data["data"][0].get("revised_prompt", prompt),
                        "model": "dall-e-3"
                    }
                else:
                    return {"status": "error", "error": f"API error: {response.text}"}
                    
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def generate_image_stability(self, prompt: str, aspect_ratio: str = "16:9") -> Dict[str, Any]:
        """Generate image using Stability AI."""
        if not self.stability_api_key:
            return {"status": "error", "error": "Stability API key not configured"}
        
        # Convert aspect ratio to dimensions
        dimension_map = {
            "16:9": (1024, 576),
            "9:16": (576, 1024),
            "1:1": (1024, 1024)
        }
        width, height = dimension_map.get(aspect_ratio, (1024, 1024))
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                    headers={
                        "Authorization": f"Bearer {self.stability_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "text_prompts": [{"text": prompt, "weight": 1}],
                        "cfg_scale": 7,
                        "width": width,
                        "height": height,
                        "steps": 30,
                        "samples": 1
                    },
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # Stability returns base64 encoded images
                    image_data = data["artifacts"][0]["base64"]
                    return {
                        "status": "success",
                        "image_base64": image_data,
                        "model": "stable-diffusion-xl"
                    }
                else:
                    return {"status": "error", "error": f"API error: {response.text}"}
                    
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def generate_image_aiml(self, prompt: str, model: str = "flux/dev") -> Dict[str, Any]:
        """Generate image using AIML API with Flux models."""
        if not self.aiml_api_key:
            return {"status": "error", "error": "AIML API key not configured"}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.aimlapi.com/v1/images/generations",
                    headers={
                        "Authorization": f"Bearer {self.aiml_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "prompt": prompt,
                        "model": model,
                    },
                    timeout=120.0  # Flux models may take longer
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # AIML API returns the image URL in the response
                    image_url = None
                    if isinstance(data, dict):
                        # Check for different possible response formats
                        if 'url' in data:
                            image_url = data['url']
                        elif 'data' in data and isinstance(data['data'], list) and len(data['data']) > 0:
                            image_url = data['data'][0].get('url')
                        elif 'images' in data and isinstance(data['images'], list) and len(data['images']) > 0:
                            image_url = data['images'][0].get('url')
                    
                    if image_url:
                        return {
                            "status": "success",
                            "image_url": image_url,
                            "model": model,
                            "revised_prompt": prompt  # Flux doesn't revise prompts
                        }
                    else:
                        return {"status": "error", "error": f"No image URL in response: {data}"}
                else:
                    return {"status": "error", "error": f"API error: {response.text}"}
                    
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def generate_images_from_prompts(self, prompts: List[Dict[str, Any]], service: str = "openai") -> Dict[str, Any]:
        """
        Generate images for multiple prompts.
        
        Args:
            prompts: List of prompt dictionaries with prompt text and metadata
            service: Image generation service to use ("openai", "stability", etc.)
            
        Returns:
            Dictionary containing generated images and metadata
        """
        try:
            print(f"🖼️ Generating {len(prompts)} images using {service}...")
            
            generated_images = []
            
            for i, prompt_data in enumerate(prompts):
                print(f"  Generating image {i+1}/{len(prompts)}: {prompt_data['scene_description'][:50]}...")
                
                # Generate image based on service
                if service == "openai":
                    # Map aspect ratio to DALL-E 3 sizes
                    size_map = {
                        "16:9": "1792x1024",
                        "9:16": "1024x1792",
                        "1:1": "1024x1024"
                    }
                    size = size_map.get(prompt_data.get('aspect_ratio', '1:1'), "1024x1024")
                    
                    result = await self.generate_image_dalle3(
                        prompt=prompt_data['prompt'],
                        style=prompt_data.get('style', 'vivid'),
                        size=size
                    )
                elif service == "stability":
                    result = await self.generate_image_stability(
                        prompt=prompt_data['prompt'],
                        aspect_ratio=prompt_data.get('aspect_ratio', '1:1')
                    )
                elif service == "aiml":
                    # Use Flux model for AIML
                    model = "flux/dev"  # Can be made configurable
                    result = await self.generate_image_aiml(
                        prompt=prompt_data['prompt'],
                        model=model
                    )
                else:
                    result = {"status": "error", "error": f"Unknown service: {service}"}
                
                if result['status'] == 'success':
                    # Prepare image record
                    image_record = {
                        'prompt_id': prompt_data.get('id'),
                        'prompt': prompt_data['prompt'],
                        'scene_number': prompt_data['scene_number'],
                        'scene_description': prompt_data['scene_description'],
                        'image_url': result.get('image_url'),
                        'image_base64': result.get('image_base64'),
                        'revised_prompt': result.get('revised_prompt', prompt_data['prompt']),
                        'model': result['model'],
                        'style': prompt_data.get('style'),
                        'aspect_ratio': prompt_data.get('aspect_ratio'),
                        'created_at': datetime.now().isoformat(),
                        'metadata': {
                            'generation_service': service,
                            'original_prompt_data': prompt_data
                        }
                    }
                    
                    # Store in Supabase
                    stored_result = await asyncio.to_thread(
                        lambda: self.supabase.table('generated_images').insert(image_record).execute()
                    )
                    
                    if stored_result.data:
                        image_record['id'] = stored_result.data[0]['id']
                        generated_images.append(image_record)
                        print(f"  ✅ Generated and stored image for scene {prompt_data['scene_number']}")
                else:
                    print(f"  ❌ Failed to generate image: {result['error']}")
                
                # Add small delay to avoid rate limits
                if i < len(prompts) - 1:
                    await asyncio.sleep(1)
            
            return {
                "status": "success",
                "images_generated": len(generated_images),
                "images": generated_images,
                "service": service,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Error generating images: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_images_for_prompts(self, prompt_ids: List[str]) -> List[Dict[str, Any]]:
        """Retrieve generated images for specific prompts."""
        try:
            result = await asyncio.to_thread(
                lambda: self.supabase.table('generated_images')
                .select('*')
                .in_('prompt_id', prompt_ids)
                .order('scene_number')
                .execute()
            )
            return result.data if result.data else []
        except Exception as e:
            print(f"❌ Error retrieving images: {str(e)}")
            return []


async def image_generation_agent(state: ContentState) -> ContentState:
    """
    Workflow function for image generation phase.
    
    This agent:
    1. Retrieves the prompts from the previous phase
    2. Generates images for each prompt using AI services
    3. Stores the generated images
    4. Updates the state with the results
    """
    try:
        print("\n🖼️ Starting image generation phase...")
        start_time = datetime.now()
        
        # Initialize the agent
        agent = ImageGenerationAgent()
        
        # Get prompts from previous phase
        prompts = None
        for output in reversed(state.phase_outputs):
            if output.phase_name == "prompt_generation" and output.status == "completed":
                prompts_data = output.data
                if isinstance(prompts_data, dict) and 'prompts' in prompts_data:
                    prompts = prompts_data['prompts']
                break
        
        if not prompts:
            raise Exception("No prompts found in state. Please generate prompts first.")
        
        # Determine which service to use (can be configured via environment or state)
        service = os.getenv("IMAGE_GENERATION_SERVICE", "openai")
        
        # Generate images
        result = await agent.generate_images_from_prompts(
            prompts=prompts,
            service=service
        )
        
        if result['status'] == 'error':
            raise Exception(result['error'])
        
        # Create phase output
        duration = (datetime.now() - start_time).total_seconds()
        phase_output = PhaseOutput(
            phase_name="image_generation",
            data=result,
            status="completed",
            duration=duration,
            timestamp=datetime.now().isoformat()
        )
        
        # Update state
        state.phase_outputs.append(phase_output)
        state.current_phase = "visual_assembly"  # Or next appropriate phase
        
        # Add message for visibility
        images_summary = "\n".join([
            f"{i+1}. Scene {img['scene_number']}: {img['scene_description'][:50]}... ✅"
            for i, img in enumerate(result['images'][:5])
        ])
        
        state.messages.append(AIMessage(content=f"""
✅ Generated {result['images_generated']} images successfully!

Images created:
{images_summary}

All images have been stored and are ready for video assembly.
Service used: {result['service']}
"""))
        
        return state
        
    except Exception as e:
        print(f"❌ Image generation error: {str(e)}")
        
        # Create error phase output
        phase_output = PhaseOutput(
            phase_name="image_generation",
            data={"error": str(e)},
            status="error",
            error_message=str(e),
            timestamp=datetime.now().isoformat()
        )
        
        state.phase_outputs.append(phase_output)
        state.messages.append(AIMessage(content=f"❌ Error in image generation: {str(e)}"))
        
        return state