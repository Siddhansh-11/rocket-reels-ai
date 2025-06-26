"""
Video Prompt Generation Agent for Rocket Reels AI

This agent analyzes scripts and image sequences to generate prompts for video generation.
It creates motion descriptions, transition suggestions, and timing information for creating
smooth, natural-flowing videos from static images.
"""

import json
import os
from typing import Dict, List, TypedDict, Optional
import requests
from datetime import datetime
import time

class VideoPromptGenerationState(TypedDict):
    script_content: str
    image_prompts: List[Dict]
    generated_images: List[Dict]
    visual_timing_plan: Dict
    video_prompts: Optional[List[Dict]]
    error: Optional[str]
    cost: float

class VideoPromptGenerationAgent:
    def __init__(self):
        self.deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
        if not self.deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY not found in environment variables")
        
        self.deepseek_url = "https://api.deepseek.com/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.deepseek_api_key}",
            "Content-Type": "application/json"
        }
    
    def generate_video_prompts(self, state: VideoPromptGenerationState) -> VideoPromptGenerationState:
        """Generate video prompts from script, images, and visual timing"""
        try:
            print("\n🎬 Starting Video Prompt Generation...")
            
            if not state.get('script_content'):
                state['error'] = "No script content provided"
                return state
            
            if not state.get('generated_images'):
                state['error'] = "No generated images found"
                return state
            
            # Extract relevant information
            script = state['script_content']
            images = state['generated_images']
            image_prompts = state.get('image_prompts', [])
            visual_timing = state.get('visual_timing_plan', {})
            
            # Create context for video prompt generation
            context = self._create_context(script, images, image_prompts, visual_timing)
            
            # Generate video prompts
            video_prompts = self._generate_prompts(context)
            
            if video_prompts:
                state['video_prompts'] = video_prompts
                print(f"\n✅ Generated {len(video_prompts)} video prompts")
                
                # Display prompts
                for i, prompt in enumerate(video_prompts, 1):
                    print(f"\n📹 Video Segment {i}:")
                    print(f"   Duration: {prompt['duration']}s")
                    print(f"   Transition: {prompt['transition_type']}")
                    print(f"   Motion: {prompt['motion_description'][:100]}...")
            else:
                state['error'] = "Failed to generate video prompts"
            
            return state
            
        except Exception as e:
            state['error'] = f"Video prompt generation failed: {str(e)}"
            print(f"\n❌ Error: {state['error']}")
            return state
    
    def _create_context(self, script: str, images: List[Dict], 
                       image_prompts: List[Dict], visual_timing: Dict) -> str:
        """Create context for the AI to understand the content"""
        
        # Map images to their prompts
        image_context = []
        for i, img in enumerate(images):
            prompt_info = image_prompts[i] if i < len(image_prompts) else {}
            image_context.append({
                "index": i + 1,
                "filename": img.get('filename', ''),
                "scene_description": prompt_info.get('prompt', ''),
                "timing": prompt_info.get('timing', f"{i*3}-{(i+1)*3}s")
            })
        
        context = f"""
Script Content:
{script}

Available Images ({len(images)} total):
{json.dumps(image_context, indent=2)}

Visual Timing Plan:
{json.dumps(visual_timing, indent=2) if visual_timing else "No timing plan available"}

Total video duration should be approximately {len(images) * 3} seconds.
"""
        return context
    
    def _generate_prompts(self, context: str) -> List[Dict]:
        """Generate video prompts using DeepSeek AI"""
        
        prompt = f"""You are a video director creating smooth, engaging videos from static images.

Context:
{context}

Generate video prompts for creating a dynamic video from these images. For each transition between images, provide:

1. **Motion Description**: How objects/camera should move (pan, zoom, rotate, etc.)
2. **Transition Type**: How to transition between images (fade, swipe, zoom, morph, etc.)
3. **Duration**: How long this segment should be (in seconds)
4. **Effects**: Any additional effects (particles, overlays, blur, etc.)
5. **Mood**: The emotional tone for this segment

Focus on creating natural flow that matches the script narrative. Consider:
- Ken Burns effect for static shots
- Smooth transitions that maintain viewer engagement
- Motion that enhances the story being told
- Pacing that matches the script's energy

Return a JSON array with video prompts for each segment. Example format:
[
  {{
    "segment_index": 1,
    "from_image": 1,
    "to_image": 2,
    "motion_description": "Slow zoom in on the main subject while panning slightly right",
    "transition_type": "crossfade",
    "duration": 3.5,
    "effects": ["subtle_vignette", "light_particles"],
    "mood": "inspiring",
    "camera_movement": {{"type": "ken_burns", "start": "center", "end": "top_right", "zoom": 1.2}}
  }}
]

Generate prompts for all image transitions plus intro and outro if needed."""

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "You are an expert video director and motion designer."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.8,
            "max_tokens": 2000,
            "response_format": {"type": "json_object"}
        }
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.deepseek_url,
                    headers=self.headers,
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if 'choices' in result and len(result['choices']) > 0:
                        content = result['choices'][0]['message']['content']
                        
                        # Parse JSON response
                        try:
                            parsed = json.loads(content)
                            # Extract prompts array from various possible structures
                            if isinstance(parsed, list):
                                return parsed
                            elif isinstance(parsed, dict):
                                if 'prompts' in parsed:
                                    return parsed['prompts']
                                elif 'video_prompts' in parsed:
                                    return parsed['video_prompts']
                                elif 'segments' in parsed:
                                    return parsed['segments']
                        except json.JSONDecodeError:
                            print(f"Failed to parse JSON response: {content[:200]}...")
                            continue
                
                elif response.status_code == 429:  # Rate limit
                    wait_time = (attempt + 1) * 5
                    print(f"Rate limited. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                
                else:
                    print(f"API error: {response.status_code} - {response.text}")
                    
            except requests.exceptions.Timeout:
                print(f"Request timeout on attempt {attempt + 1}")
                continue
            except Exception as e:
                print(f"Request failed: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2)
        
        # Fallback: Generate basic prompts
        return self._generate_fallback_prompts(len(context.split('Available Images')[1].split('total')[0]))
    
    def _generate_fallback_prompts(self, num_images: int) -> List[Dict]:
        """Generate basic video prompts as fallback"""
        prompts = []
        
        # Intro
        prompts.append({
            "segment_index": 0,
            "from_image": None,
            "to_image": 1,
            "motion_description": "Fade in from black with slight zoom",
            "transition_type": "fade_in",
            "duration": 2.0,
            "effects": ["fade_from_black"],
            "mood": "engaging",
            "camera_movement": {"type": "zoom_in", "zoom": 1.1}
        })
        
        # Image transitions
        for i in range(num_images - 1):
            prompts.append({
                "segment_index": i + 1,
                "from_image": i + 1,
                "to_image": i + 2,
                "motion_description": f"Ken Burns effect with {'zoom in' if i % 2 == 0 else 'pan across'}",
                "transition_type": ["crossfade", "swipe_left", "zoom_transition"][i % 3],
                "duration": 3.0,
                "effects": [],
                "mood": "dynamic",
                "camera_movement": {
                    "type": "ken_burns",
                    "start": "center",
                    "end": ["top_right", "bottom_left", "center"][i % 3],
                    "zoom": 1.15
                }
            })
        
        # Outro
        prompts.append({
            "segment_index": num_images,
            "from_image": num_images,
            "to_image": None,
            "motion_description": "Slow zoom out with fade to black",
            "transition_type": "fade_out",
            "duration": 2.0,
            "effects": ["fade_to_black"],
            "mood": "concluding",
            "camera_movement": {"type": "zoom_out", "zoom": 0.9}
        })
        
        return prompts

def video_prompt_generation_node(state: VideoPromptGenerationState) -> VideoPromptGenerationState:
    """Node function for LangGraph integration"""
    agent = VideoPromptGenerationAgent()
    return agent.generate_video_prompts(state)

if __name__ == "__main__":
    # Test the agent
    test_state = VideoPromptGenerationState(
        script_content="A revolutionary AI system transforms how we create content...",
        image_prompts=[
            {"prompt": "Futuristic AI interface", "timing": "0-3s"},
            {"prompt": "Content creation dashboard", "timing": "3-6s"}
        ],
        generated_images=[
            {"filename": "ai_interface.jpg"},
            {"filename": "dashboard.jpg"}
        ],
        visual_timing_plan={
            "total_duration": 6,
            "segments": [
                {"start": 0, "end": 3, "description": "Intro"},
                {"start": 3, "end": 6, "description": "Main content"}
            ]
        },
        video_prompts=None,
        error=None,
        cost=0.0
    )
    
    agent = VideoPromptGenerationAgent()
    result = agent.generate_video_prompts(test_state)
    
    if result['video_prompts']:
        print("\n✅ Video prompts generated successfully!")
        print(json.dumps(result['video_prompts'], indent=2))
    else:
        print(f"\n❌ Failed: {result.get('error')}")