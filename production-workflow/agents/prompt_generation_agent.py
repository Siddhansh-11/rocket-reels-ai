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

# Export tools
prompt_generation_tools = [generate_prompts_from_script]