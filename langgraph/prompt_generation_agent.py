from langchain_core.tools import tool
from typing import Dict, List, Optional
import os
import asyncio
import json
from datetime import datetime
import anthropic
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv("../.env")

# Initialize Anthropic client
anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def get_supabase_client():
    """Get Supabase client with proper configuration."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        raise Exception("Missing SUPABASE_URL or SUPABASE_ANON_KEY environment variables")
    
    return create_client(supabase_url, supabase_key)

@tool
def generate_prompts_from_script(script_content: str, num_prompts: int = 5) -> str:
    """
    Generate multiple image prompts for different scenes in a script.
    
    Args:
        script_content: The script content to generate prompts from
        num_prompts: Number of prompts to generate (default: 5)
        
    Returns:
        Formatted string containing generated prompts and metadata
    """
    try:
        print(f"🎨 Generating {num_prompts} image prompts from script...")
        
        # Generate prompts using Claude
        prompt_generation_prompt = f"""
        You are an expert at creating detailed image generation prompts for social media reels/shorts.
        
        Given this script, generate {num_prompts} different image prompts for key scenes or moments:
        
        SCRIPT:
        {script_content}
        
        For each prompt, provide:
        1. Scene timing (e.g., "0-5 seconds", "15-20 seconds")
        2. Visual description (detailed prompt for image generation)
        3. Mood/style (e.g., "modern tech", "futuristic", "professional")
        4. Key elements to include
        
        Format as JSON:
        {{
            "prompts": [
                {{
                    "scene_number": 1,
                    "timing": "0-5 seconds",
                    "visual_description": "Detailed prompt here...",
                    "mood_style": "modern tech",
                    "key_elements": ["element1", "element2"],
                    "technical_specs": "high resolution, cinematic lighting"
                }}
            ]
        }}
        
        Make the prompts specific, detailed, and suitable for AI image generation tools like DALL-E, Midjourney, or Stable Diffusion.
        """
        
        # Generate prompts
        try:
            response = anthropic_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": prompt_generation_prompt
                }]
            )
        except Exception as e:
            print(f"❌ Error calling Anthropic API: {str(e)}")
            return f"❌ Error generating prompts: {str(e)}"
        
        # Parse the response
        prompts_text = response.content[0].text
        
        try:
            # Try to parse as JSON
            prompts_data = json.loads(prompts_text)
            prompts = prompts_data.get("prompts", [])
        except json.JSONDecodeError:
            # If JSON parsing fails, extract manually
            prompts = []
            print("⚠️ JSON parsing failed, extracting prompts manually...")
        
        # Store in database
        supabase = get_supabase_client()
        
        stored_prompts = []
        for i, prompt in enumerate(prompts, 1):
            prompt_data = {
                "script_content_preview": script_content[:200] + "..." if len(script_content) > 200 else script_content,
                "scene_number": prompt.get("scene_number", i),
                "timing": prompt.get("timing", f"Scene {i}"),
                "visual_description": prompt.get("visual_description", ""),
                "mood_style": prompt.get("mood_style", ""),
                "key_elements": prompt.get("key_elements", []),
                "technical_specs": prompt.get("technical_specs", ""),
                "created_at": datetime.now().isoformat(),
                "status": "generated"
            }
            
            # Store in prompts table
            result = supabase.table('prompts').insert(prompt_data).execute()
            
            if result.data:
                stored_prompts.append(result.data[0])
                print(f"✅ Stored prompt {i} in database")
            else:
                print(f"❌ Failed to store prompt {i}")
        
        # Format response
        response_text = f"""🎨 **IMAGE PROMPTS GENERATED**

✅ Generated {len(prompts)} image prompts from script
✅ Stored {len(stored_prompts)} prompts in database

**Generated Prompts:**

"""
        
        for i, prompt in enumerate(prompts, 1):
            response_text += f"""**Scene {i}: {prompt.get('timing', f'Scene {i}')}**
📝 Description: {prompt.get('visual_description', 'No description')[:100]}...
🎭 Mood/Style: {prompt.get('mood_style', 'Not specified')}
🔧 Technical: {prompt.get('technical_specs', 'Standard')}

---
"""
        
        response_text += f"""
**📊 Summary:**
- Total prompts: {len(prompts)}
- Database entries: {len(stored_prompts)}
- Ready for image generation

**💡 Next Steps:**
- Use these prompts with image generation tools
- Generate images for each scene
- Create visual timeline for script
"""
        
        return response_text
        
    except Exception as e:
        error_msg = f"❌ Error generating prompts: {str(e)}"
        print(error_msg)
        return error_msg

@tool
def get_stored_prompts(limit: int = 10, status: str = None) -> str:
    """
    Retrieve stored image prompts from the database.
    
    Args:
        limit: Maximum number of prompts to retrieve
        status: Optional status filter (e.g., 'generated', 'used', 'approved')
        
    Returns:
        Formatted string with stored prompts
    """
    try:
        supabase = get_supabase_client()
        
        query = supabase.table('prompts').select('*').limit(limit).order('created_at', desc=True)
        
        if status:
            query = query.eq('status', status)
        
        result = query.execute()
        
        if not result.data:
            return """📄 **STORED PROMPTS DATABASE**

❌ No prompts found in the database.

**💡 Suggestion:** Generate prompts first by:
- Using generate_prompts_from_script with script content
"""
        
        prompts = result.data
        response_text = f"""📄 **STORED PROMPTS DATABASE**

✅ Found {len(prompts)} prompts in database:

"""
        
        for i, prompt in enumerate(prompts, 1):
            created_date = prompt.get('created_at', '')[:10] if prompt.get('created_at') else 'Unknown'
            description_preview = prompt.get('visual_description', 'No description')[:80] + '...'
            
            response_text += f"""**{i}. Scene {prompt.get('scene_number', i)} - {prompt.get('timing', 'Unknown timing')}**
📝 Description: {description_preview}
🎭 Style: {prompt.get('mood_style', 'Not specified')}
📅 Created: {created_date}
📊 Status: {prompt.get('status', 'Unknown')}
🆔 ID: {prompt.get('id', 'Unknown')}

---
"""
        
        response_text += f"""
**📊 Database Status:** {len(prompts)} prompts available
**💡 Next Steps:** 
- Generate images from these prompts
- Create new prompts from scripts
"""
        
        return response_text
        
    except Exception as e:
        return f"❌ Error retrieving prompts: {str(e)}"

@tool
def get_prompt_by_id(prompt_id: str) -> str:
    """
    Retrieve a specific prompt by ID from the database.
    
    Args:
        prompt_id: The ID of the prompt to retrieve
        
    Returns:
        Full prompt details if found
    """
    try:
        supabase = get_supabase_client()
        
        result = supabase.table('prompts').select('*').eq('id', prompt_id).execute()
        
        if not result.data:
            return f"❌ Prompt not found in database for ID: {prompt_id}"
        
        prompt = result.data[0]
        
        return f"""🎨 **PROMPT RETRIEVED FROM DATABASE**

**Prompt ID:** {prompt['id']}
**Scene Number:** {prompt.get('scene_number', 'Unknown')}
**Timing:** {prompt.get('timing', 'Unknown')}
**Status:** {prompt.get('status', 'Unknown')}
**Created:** {prompt.get('created_at', 'Unknown')}

**Visual Description:**
{prompt.get('visual_description', 'No description available')}

**Mood/Style:** {prompt.get('mood_style', 'Not specified')}

**Key Elements:**
{', '.join(prompt.get('key_elements', []))}

**Technical Specifications:**
{prompt.get('technical_specs', 'Standard specifications')}

**Script Preview:**
{prompt.get('script_content_preview', 'No script preview available')}
"""
        
    except Exception as e:
        return f"❌ Error retrieving prompt: {str(e)}"

@tool
def store_prompt_manually(prompt_data: dict) -> str:
    """
    Manually store a single image prompt in the database.
    
    Args:
        prompt_data: Dictionary containing prompt information:
            - visual_description: The image generation prompt (required)
            - scene_number: Scene number (optional)
            - timing: Scene timing (optional)
            - mood_style: Visual style/mood (optional)
            - key_elements: List of key elements (optional)
            - technical_specs: Technical specifications (optional)
            - script_content_preview: Related script preview (optional)
    
    Returns:
        Confirmation message with storage details
    """
    try:
        # Validate required fields
        if not prompt_data.get('visual_description'):
            return "❌ Error: 'visual_description' is required"
        
        # Prepare storage data
        storage_data = {
            'visual_description': prompt_data['visual_description'],
            'scene_number': prompt_data.get('scene_number', 1),
            'timing': prompt_data.get('timing', 'Scene timing not specified'),
            'mood_style': prompt_data.get('mood_style', 'Standard'),
            'key_elements': prompt_data.get('key_elements', []),
            'technical_specs': prompt_data.get('technical_specs', 'High resolution, professional quality'),
            'script_content_preview': prompt_data.get('script_content_preview', ''),
            'created_at': datetime.now().isoformat(),
            'status': 'manually_added'
        }
        
        supabase = get_supabase_client()
        result = supabase.table('prompts').insert(storage_data).execute()
        
        if result.data:
            prompt_id = result.data[0]['id']
            
            return f"""
✅ **PROMPT SUCCESSFULLY STORED**

**📊 Storage Details:**
- Prompt ID: {prompt_id}
- Scene Number: {storage_data['scene_number']}
- Timing: {storage_data['timing']}
- Style: {storage_data['mood_style']}
- Status: {storage_data['status']}
- Timestamp: {storage_data['created_at']}

**📝 Description Preview:**
{storage_data['visual_description'][:100]}...

**🗄️ Database Status:** Prompt stored and ready for image generation.
"""
        else:
            return "❌ Error storing prompt: No data returned"
        
    except Exception as e:
        return f"❌ Error storing prompt: {str(e)}"

@tool
def update_prompt_status(prompt_id: str, status: str) -> str:
    """
    Update the status of a stored prompt.
    
    Args:
        prompt_id: The ID of the prompt to update
        status: New status (e.g., 'used', 'approved', 'generated_image')
    
    Returns:
        Confirmation message
    """
    try:
        supabase = get_supabase_client()
        
        result = supabase.table('prompts').update({
            "status": status,
            "updated_at": datetime.now().isoformat()
        }).eq('id', prompt_id).execute()
        
        if result.data:
            return f"""
✅ **PROMPT STATUS UPDATED**

**📊 Details:**
- Prompt ID: {prompt_id}
- New Status: {status}
- Updated: {datetime.now().isoformat()}

**🚀 Status Change Applied Successfully**
"""
        else:
            return f"❌ Error updating prompt: Prompt not found"
        
    except Exception as e:
        return f"❌ Error updating prompt status: {str(e)}"

@tool
def delete_prompt(prompt_id: str) -> str:
    """
    Delete a prompt from the database.
    
    Args:
        prompt_id: The ID of the prompt to delete
    
    Returns:
        Confirmation message
    """
    try:
        supabase = get_supabase_client()
        
        result = supabase.table('prompts').delete().eq('id', prompt_id).execute()
        
        if result.data:
            return f"""
✅ **PROMPT DELETED SUCCESSFULLY**

**📊 Details:**
- Prompt ID: {prompt_id}
- Deleted: {datetime.now().isoformat()}

**🗑️ Prompt removed from database**
"""
        else:
            return f"❌ Error deleting prompt: Prompt not found"
        
    except Exception as e:
        return f"❌ Error deleting prompt: {str(e)}"

# Export tools for agent integration
prompt_generation_tools = [
    generate_prompts_from_script,
    get_stored_prompts,
    get_prompt_by_id,
    store_prompt_manually,
    update_prompt_status,
    delete_prompt
]