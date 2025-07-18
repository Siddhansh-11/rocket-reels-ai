from langchain_core.tools import tool
from typing import List, Dict
import os
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv
import re
import uuid

# Load environment variables
load_dotenv("../.env")

# Initialize DeepSeek client
deepseek_model = ChatLiteLLM(
    model="deepseek/deepseek-chat",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    max_tokens=2000,
    temperature=0.5  # Lowered temperature for more consistent output
)

def extract_prompts_from_llm_response(response_text: str, num_prompts: int = 5) -> List[Dict]:
    """
    Extract prompts from LLM response using the PROMPT format.
    
    Args:
        response_text: The raw response from the LLM
        num_prompts: Number of prompts to extract (default: 5)
    
    Returns:
        List of dictionaries containing prompt metadata
    """
    print("🔍 Extracting prompts from LLM response...")
    print(f"📝 Response preview: {response_text[:200]}...")

    prompts = []
    
    # Look for PROMPT X: format
    prompt_pattern = r'PROMPT\s*(\d+):\s*(.+?)(?=PROMPT\s*\d+:|$|\n\n)'
    matches = re.findall(prompt_pattern, response_text, re.IGNORECASE | re.DOTALL)
    
    if matches:
        print(f"✅ Found {len(matches)} prompts using PROMPT pattern")
        for i, (num, description) in enumerate(matches[:num_prompts]):
            description = description.strip()
            if len(description) > 20:  # Ensure meaningful descriptions
                prompts.append({
                    "id": str(uuid.uuid4()),
                    "scene_number": int(num) if num.isdigit() else i + 1,
                    "timing": f"{i * 12}-{(i + 1) * 12} seconds",
                    "visual_description": description,
                    "mood_style": "dynamic, engaging",
                    "key_elements": [],  # Can be populated later if needed
                    "technical_specs": "high resolution, cinematic"
                })
        return prompts[:num_prompts]
    
    print("❌ No PROMPT patterns found in LLM response")
    return []

@tool
def generate_prompts_from_script(script_content: str, num_prompts: int = 5) -> List[Dict]:
    """
    Generate multiple image prompts for different scenes in a script using LLM.
    
    Args:
        script_content: The script content to generate prompts from
        num_prompts: Number of prompts to generate (default: 5)
        
    Returns:
        List of dictionaries containing prompt metadata
    """
    try:
        print(f"🎨 Generating {num_prompts} content-specific image prompts from script...")
        print(f"📝 Script length: {len(script_content)} characters")
        
        # Create a specific prompt for the LLM
        llm_prompt = f"""Analyze the following script content and create {num_prompts} specific visual image prompts.

SCRIPT CONTENT:
{script_content[:1500]}

Your task: Create {num_prompts} image generation prompts that are directly related to the provided script content.

IMPORTANT RULES:
1. Base prompts ONLY on the actual script content provided.
2. Avoid generic tech/business prompts unless explicitly mentioned in the script.
3. Reference specific concepts, people, events, or objects mentioned in the script.
4. Each prompt must be unique, visually descriptive, and at least 30 characters long.
5. Use the following format exactly, with no additional text before or after:

PROMPT 1: [Specific visual description based on script content]
PROMPT 2: [Specific visual description based on script content]
PROMPT 3: [Specific visual description based on script content]
PROMPT 4: [Specific visual description based on script content]
PROMPT 5: [Specific visual description based on script content]

Example format:
PROMPT 1: Professional visualization of a futuristic AI interface from the script, showing a glowing terminal with code execution
PROMPT 2: Illustration depicting a specific AI agent from the script fixing bugs in a vibrant code editor
"""

        # Call LLM
        print("🔄 Calling DeepSeek LLM for content analysis...")
        response = deepseek_model.invoke([HumanMessage(content=llm_prompt)])
        llm_response = response.content.strip()
        
        print(f"📥 LLM Response length: {len(llm_response)} characters")
        print(f"📄 Response preview: {llm_response[:300]}...")
        
        # Extract prompts from LLM response
        prompts = extract_prompts_from_llm_response(llm_response, num_prompts)
        
        if not prompts:
            print("❌ No valid prompts extracted from LLM response")
            return []
        
        print(f"✅ Generated {len(prompts)} content-specific prompts")
        return prompts
        
    except Exception as e:
        print(f"❌ Error generating content-specific prompts: {str(e)}")
        return []

@tool
def generate_shot_specific_prompts(shot_breakdown: List[Dict]) -> List[Dict]:
    """
    Generate shot-specific visual prompts based on individual shots from script analysis.
    
    Args:
        shot_breakdown: List of shot dictionaries with text, type, and metadata
        
    Returns:
        List of dictionaries containing shot-specific visual prompts
    """
    try:
        print(f"🎯 Generating shot-specific prompts for {len(shot_breakdown)} shots...")
        
        shot_prompts = []
        
        for shot in shot_breakdown:
            shot_number = shot.get('shot_number', 0)
            shot_text = shot.get('text', '')
            shot_type = shot.get('type', 'talking_head')
            section = shot.get('section', '')
            
            if not shot_text:
                continue
                
            print(f"Processing shot {shot_number}: {shot_text[:50]}...")
            
            # Generate prompt based on shot type
            visual_prompt = generate_prompt_for_shot_type(shot_text, shot_type, section)
            
            shot_prompts.append({
                "id": str(uuid.uuid4()),
                "shot_number": shot_number,
                "original_text": shot_text,
                "shot_type": shot_type,
                "section": section,
                "visual_description": visual_prompt,
                "prompt": visual_prompt,  # For backward compatibility
                "mood_style": get_mood_for_shot_type(shot_type),
                "technical_specs": "9:16 vertical format, high resolution, professional lighting"
            })
        
        print(f"✅ Generated {len(shot_prompts)} shot-specific prompts")
        return shot_prompts
        
    except Exception as e:
        print(f"❌ Error generating shot-specific prompts: {str(e)}")
        return []

def generate_prompt_for_shot_type(shot_text: str, shot_type: str, section: str) -> str:
    """Generate appropriate visual prompt based on shot type and content"""
    
    # Use AI to generate contextually relevant visual prompts
    system_prompt = """You are an expert visual director for social media content. Create a single, cohesive visual prompt for image generation based on the script text provided.

REQUIREMENTS:
1. Write ONE unified prompt (40-60 words) that captures the complete visual scene
2. Extract specific concepts, technologies, interfaces, or events from the script text
3. Make visuals directly relevant to the actual content, not generic imagery
4. Always end with "vertical 9:16 format" for social media
5. Write as a single flowing description, not broken into sections

SHOT TYPE GUIDELINES:
- talking_head: Focus on the TOPIC being discussed, not the person. Use relevant backgrounds, objects, or visual metaphors that support the content
- screen_recording: Actual interfaces, apps, websites, or digital elements from the script
- broll: Cinematic visuals that directly support the story being told

AVOID UNNECESSARY PEOPLE:
- Don't include "person", "presenter", "content creator", "tech analyst" unless the script specifically mentions a person
- Focus on objects, interfaces, environments, concepts, and visual metaphors instead
- Use "showing", "displaying", "featuring" instead of "person holding" or "presenter with"

EXAMPLE FORMATS:
Instead of: "Young tech entrepreneur holding smartphone with messaging app interface..."
Use: "Smartphone displaying messaging app interface with Bluetooth mesh network visualization glowing between devices in crowded concert venue with colorful stage lights, vertical 9:16 format"

Instead of: "Tech analyst pointing at screen showing AI chatbot..."
Use: "AI chatbot interface displaying controversial messages with glowing red error alerts, dark cyberpunk-style digital background, vertical 9:16 format"

Create ONE cohesive prompt that focuses on the subject matter, not the presenter."""

    user_prompt = f"""
Shot Type: {shot_type}
Section: {section}
Script Text: "{shot_text}"

Analyze this script text and create a specific visual prompt for image generation. Extract the key people, concepts, events, or elements mentioned and translate them into compelling visuals that directly support this part of the story.
"""

    try:
        response = deepseek_model.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ])
        
        visual_prompt = response.content.strip()
        
        # Clean up the response
        visual_prompt = visual_prompt.strip('"\'')
        
        # Ensure format specification is included
        if "9:16" not in visual_prompt and "vertical" not in visual_prompt.lower():
            visual_prompt += ", vertical 9:16 format"
            
        return visual_prompt
        
    except Exception as e:
        print(f"Error generating visual prompt with AI: {str(e)}")
        # Generic fallback that works for any content
        return f"Professional {shot_type} shot supporting the narrative, clean modern aesthetic, vertical 9:16 format"

def extract_visual_context(text: str) -> str:
    """Extract key visual concepts from text for fallback scenarios"""
    # Use AI to extract visual concepts
    try:
        response = deepseek_model.invoke([
            {"role": "system", "content": "Extract 2-3 key visual concepts from this text in a few words."},
            {"role": "user", "content": text}
        ])
        return response.content.strip()
    except:
        # Generic fallback
        return "professional setting"

def extract_emotion_from_text(text: str) -> str:
    """Extract emotional context from shot text"""
    text_lower = text.lower()
    
    if any(word in text_lower for word in ['terrifying', 'shocking', 'scary', 'frightening']):
        return "shocked and concerned"
    elif any(word in text_lower for word in ['excited', 'amazing', 'incredible', 'awesome']):
        return "excited and enthusiastic"
    elif any(word in text_lower for word in ['surprised', 'unexpected', 'wow', 'unbelievable']):
        return "surprised and amazed"
    elif any(word in text_lower for word in ['serious', 'important', 'critical', 'significant']):
        return "serious and focused"
    elif any(word in text_lower for word in ['confused', 'unclear', 'strange', 'weird']):
        return "confused and thoughtful"
    else:
        return "confident and engaging"

def get_mood_for_shot_type(shot_type: str) -> str:
    """Get appropriate mood/style for shot type"""
    mood_map = {
        'talking_head': 'professional, engaging, direct',
        'talking_head_emotional': 'dramatic, expressive, dynamic',
        'screen_recording': 'clean, modern, tech-focused',
        'broll': 'cinematic, atmospheric, high-impact'
    }
    return mood_map.get(shot_type, 'professional, engaging')

# Export tools
prompt_generation_tools = [generate_prompts_from_script, generate_shot_specific_prompts]