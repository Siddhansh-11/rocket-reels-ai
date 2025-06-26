import os
import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.messages import HumanMessage
from supabase import create_client, Client
try:
    from .workflow_state import ContentState, PhaseOutput
except ImportError:
    from workflow_state import ContentState, PhaseOutput
from langchain_core.messages import HumanMessage, AIMessage


class PromptGenerationAgent:
    """Agent for generating image prompts based on scripts."""
    
    def __init__(self):
        # Initialize DeepSeek client instead of Anthropic
        self.deepseek_model = ChatLiteLLM(
            model="deepseek/deepseek-chat",
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            max_tokens=2000,
            temperature=0.7
        )
        self.supabase = self._get_supabase_client()
        
    def _get_supabase_client(self):
        """Get Supabase client with proper configuration."""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise Exception("Missing SUPABASE_URL or SUPABASE_ANON_KEY environment variables")
        
        return create_client(supabase_url, supabase_key)
    
    async def generate_prompts_from_script(self, script_content: str, script_id: Optional[str] = None, num_prompts: int = 5) -> Dict[str, Any]:
        """
        Generate multiple image prompts for different scenes in the script.
        
        Args:
            script_content: The script content to generate prompts from
            script_id: Optional ID of the script in the database
            num_prompts: Number of prompts to generate (default: 5)
            
        Returns:
            Dictionary containing generated prompts and metadata
        """
        try:
            print(f"🎨 Generating {num_prompts} image prompts from script...")
            
            # Generate prompts using DeepSeek
            prompt_generation_prompt = f"""
            You are an expert at creating detailed image generation prompts for social media reels/shorts.
            
            Given this script, generate {num_prompts} different image prompts for key scenes or moments:
            
            SCRIPT:
            {script_content}
            
            Requirements for each prompt:
            1. Be highly descriptive and specific about visual elements
            2. Include style descriptors (e.g., "cinematic", "vibrant", "minimalist")
            3. Specify camera angles, lighting, and composition
            4. Include relevant objects, backgrounds, and atmosphere
            5. Make each prompt suitable for a different part/moment of the script
            6. Keep prompts under 150 words each
            7. Ensure prompts are safe and appropriate for all audiences
            
            Format your response as a JSON array with objects containing:
            - "scene_number": integer (1 to {num_prompts})
            - "scene_description": brief description of what part of the script this represents
            - "prompt": the detailed image generation prompt
            - "style": the visual style (e.g., "photorealistic", "illustration", "3D render")
            - "aspect_ratio": suggested aspect ratio ("9:16" for vertical, "16:9" for horizontal, "1:1" for square)
            
            Return ONLY the JSON array, no other text.
            """
            
            # Call DeepSeek API via LangChain
            response = await self.deepseek_model.ainvoke([HumanMessage(content=prompt_generation_prompt)])
            
            # Parse the response
            prompts_data = json.loads(response.content)
            
            # Store prompts in database
            stored_prompts = []
            for prompt_data in prompts_data:
                # Prepare data for storage
                prompt_record = {
                    'script_id': script_id,
                    'scene_number': prompt_data['scene_number'],
                    'scene_description': prompt_data['scene_description'],
                    'prompt': prompt_data['prompt'],
                    'style': prompt_data['style'],
                    'aspect_ratio': prompt_data['aspect_ratio'],
                    'created_at': datetime.now().isoformat(),
                    'metadata': {
                        'script_snippet': script_content[:200] + '...' if len(script_content) > 200 else script_content,
                        'generation_model': 'deepseek-chat'
                    }
                }
                
                # Store in Supabase
                result = await asyncio.to_thread(
                    lambda: self.supabase.table('prompts').insert(prompt_record).execute()
                )
                
                if result.data:
                    prompt_record['id'] = result.data[0]['id']
                    stored_prompts.append(prompt_record)
                    print(f"✅ Stored prompt {prompt_data['scene_number']}: {prompt_data['scene_description'][:50]}...")
            
            return {
                "status": "success",
                "prompts_generated": len(stored_prompts),
                "prompts": stored_prompts,
                "script_id": script_id,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Error generating prompts: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_prompts_for_script(self, script_id: str) -> List[Dict[str, Any]]:
        """Retrieve all prompts associated with a script."""
        try:
            result = await asyncio.to_thread(
                lambda: self.supabase.table('prompts')
                .select('*')
                .eq('script_id', script_id)
                .order('scene_number')
                .execute()
            )
            return result.data if result.data else []
        except Exception as e:
            print(f"❌ Error retrieving prompts: {str(e)}")
            return []


async def prompt_generation_agent(state: ContentState) -> ContentState:
    """
    Workflow function for prompt generation phase.
    
    This agent:
    1. Retrieves the script from the state or database
    2. Generates multiple image prompts for different scenes
    3. Stores the prompts in the database
    4. Updates the state with the generated prompts
    """
    try:
        print("\n🎨 Starting prompt generation phase...")
        start_time = datetime.now()
        
        # Initialize the agent
        agent = PromptGenerationAgent()
        
        # Get script content from state
        script_content = None
        script_id = None
        
        # Check if we have a script in the previous outputs
        for output in state.phase_outputs:
            if output.phase_name == "script_writing" and output.status == "completed":
                script_data = output.data
                if isinstance(script_data, dict):
                    script_content = script_data.get('script', script_data.get('content'))
                    script_id = script_data.get('id')
                elif isinstance(script_data, str):
                    script_content = script_data
                break
        
        if not script_content:
            # Try to get from messages
            for message in reversed(state.messages):
                if hasattr(message, 'content') and 'script' in message.content.lower():
                    # Extract script content from message
                    content = message.content
                    if '```' in content:
                        # Extract content between code blocks
                        parts = content.split('```')
                        for i, part in enumerate(parts):
                            if i % 2 == 1:  # Odd indices are code blocks
                                script_content = part.strip()
                                break
                    if script_content:
                        break
        
        if not script_content:
            raise Exception("No script found in state. Please generate a script first.")
        
        # Generate prompts
        result = await agent.generate_prompts_from_script(
            script_content=script_content,
            script_id=script_id,
            num_prompts=5  # Starting with 5 prompts as requested
        )
        
        if result['status'] == 'error':
            raise Exception(result['error'])
        
        # Create phase output
        duration = (datetime.now() - start_time).total_seconds()
        phase_output = PhaseOutput(
            phase_name="prompt_generation",
            data=result,
            status="completed",
            duration=duration,
            timestamp=datetime.now().isoformat()
        )
        
        # Update state
        state.phase_outputs.append(phase_output)
        state.current_phase = "image_generation"  # Set next phase
        
        # Add message for visibility
        prompts_summary = "\n".join([
            f"{i+1}. Scene {p['scene_number']}: {p['scene_description']}"
            for i, p in enumerate(result['prompts'][:5])
        ])
        
        state.messages.append(AIMessage(content=f"""
✅ Generated {result['prompts_generated']} image prompts for the script:

{prompts_summary}

Ready to generate images for these scenes!
"""))
        
        return state
        
    except Exception as e:
        print(f"❌ Prompt generation error: {str(e)}")
        
        # Create error phase output
        phase_output = PhaseOutput(
            phase_name="prompt_generation",
            data={"error": str(e)},
            status="error",
            error_message=str(e),
            timestamp=datetime.now().isoformat()
        )
        
        state.phase_outputs.append(phase_output)
        state.messages.append(AIMessage(content=f"❌ Error in prompt generation: {str(e)}"))
        
        return state