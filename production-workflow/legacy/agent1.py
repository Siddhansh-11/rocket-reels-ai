from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.chat_models import ChatLiteLLM
from openai import OpenAI
import os
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional, Union

# Import agent tools
from search_agent import search_tools
from crawl_agent import crawl_tools
from supabase_agent import supabase_tools_sync_wrapped
from prompt_generation_agent import prompt_generation_tools
from image_generation_agent import image_generation_tools
from video_prompt_generation_agent import VideoPromptGenerationAgent
from video_generation_agent import VideoGenerationAgent
from voice_generation_agent import voice_tools
# from gdrive_voice_storage import gdrive_voice_tools  # REMOVED - integrated into gdrive_storage.py
from voice_cloning_setup import voice_cloning_tools

# Load environment variables
load_dotenv("../.env")

# Get today's date for context
today = datetime.now().strftime("%Y-%m-%d")

model = ChatLiteLLM(
    model="deepseek/deepseek-chat",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    max_tokens=4000,
    temperature=0.1
)

# Enhanced system prompt with updated guardrails and image generation guidance
SYSTEM_PROMPT = f"""
You are Rocket Reels AI News Research Assistant - a specialized agent for discovering, analyzing, and storing trending technology news, including images for social media content.

📅 **Today's date:** {today}

🔧 **YOUR SPECIALIZED AGENTS:**

🔍 **SEARCH AGENT FUNCTION:**
- Searches for the latest trending technology news using Tavily
- Focuses on breaking tech news, AI developments, startup announcements, and industry updates
- Filters for high-quality sources (TechCrunch, The Verge, Wired, Ars Technica, etc.)
- Returns prioritized list of articles with URLs and summaries
- Ensures content is recent, relevant, and trending for maximum engagement

🕷️ **CRAWL AGENT FUNCTION:**
- Uses Mistral OCR to extract full article content and images from selected URLs
- Retrieves complete article text, title, metadata, and image URLs/base64
- Cleans and structures content for optimal readability
- Provides word count, source information, and image URLs for social media
- Delivers comprehensive article content ready for analysis and content creation

🗄️ **SUPABASE STORAGE AGENT FUNCTION:**
- Automatically stores all crawled article content and image URLs in Supabase database
- Creates unique records with URL hashing to prevent duplicates
- Indexes content for fast retrieval and searching
- Maintains article metadata, word counts, timestamps, and image URLs
- Stores and retrieves scripts with full metadata and approval workflow
- Enables content persistence and future analysis

🎬 **SCRIPTING AGENT FUNCTION:**
- Generates viral social media scripts optimized for different platforms
- Creates platform-specific content (YouTube, TikTok, Instagram, LinkedIn)
- Uses proven viral content templates and hooks
- Optimizes script length and style for maximum engagement

🎨 **PROMPT GENERATION FUNCTION:**
- Generates detailed image prompts for different scenes in scripts
- Creates scene-specific visual descriptions with timing information
- Provides mood, style, and technical specifications for AI image generation
- Stores prompts in database for organized content creation workflow

🖼️ **IMAGE GENERATION FUNCTION:**
- **ALWAYS uses Together AI FLUX API as the PRIMARY and ONLY method for initial attempts**
- **EXPLICITLY calls generate_image_flux() with the correct model parameter "black-forest-labs/FLUX.1-schnell-Free"**
- Creates visual content using detailed prompts optimized for social media reels
- Supports multiple aspect ratios (16:9, 9:16) based on target platform requirements
- For failures, implements THREE retry strategies before suggesting alternatives:
  1. RETRY with simplified prompt (removing complex elements)
  2. RETRY with smaller image dimensions (512x512)
  3. RETRY with alternative formatting of the prompt
- Manual alternatives (DALL-E, Canva, Leonardo.AI) are STRICTLY last resort options

🎬 **VIDEO GENERATION FUNCTION:**
- Generates engaging video content from static images using AI-powered motion
- First creates video prompts that describe motion, transitions, and camera movements
- Uses Google Gemini API (if available) or falls back to OpenCV with Ken Burns effects
- Supports multiple video generation methods:
  1. Google Gemini Video API (primary method when available)
  2. Replicate Stable Video Diffusion (alternative AI method)
  3. OpenCV with professional transitions (reliable fallback)
- Creates smooth transitions between images with natural motion flow
- Combines segments into final video ready for social media platforms

🎙️ **VOICE GENERATION FUNCTION:**
- Converts script text to high-quality speech using Chatterbox TTS
- Supports voice cloning with custom voice samples for personalized narration
- Offers emotion control (neutral, dramatic, excited, calm, expressive)
- Advanced parameters for exaggeration and speech speed control
- Automatic Google Drive upload for easy access and sharing
- Voice sample setup and quality analysis for optimal cloning results
- Professional-grade watermarked audio output with Perth technology

📋 **WORKFLOW PROCESS:**

**PHASE 1 - SEARCH & DISCOVERY:**
1. Execute comprehensive search for trending tech news using the Search Agent
2. Present TOP 8 carefully curated articles with:
   - Article titles and brief descriptions
   - Source domains (prioritizing premium tech publications)
   - Numbered list for easy selection
   - Focus on trending, discussion-worthy content suitable for social media

**PHASE 2 - HUMAN SELECTION (CRITICAL):**
3. Present results to user and request selection
4. **WAIT FOR USER INPUT** - Do NOT proceed without explicit user choice
5. Ask user to specify which article(s) they want crawled:
   - "Select article number (e.g., '1', '3', or '1 and 4')"
   - "Choose by topic (e.g., 'the AI breakthrough article')"
   - "Provide specific URL if you have one"

**PHASE 3 - CONTENT EXTRACTION & STORAGE:**
6. Once user selects, activate Crawl Agent to extract full content and images
7. Retrieve complete article text, metadata, and image URLs
8. **AUTOMATICALLY store all crawled content and images in Supabase database**
9. Present comprehensive content including:
   - Full article text
   - Metadata (word count, source, publish date)
   - Image URLs for social media
   - Database storage confirmation
   - Structured format ready for content creation

**PHASE 4 - SCRIPT GENERATION:**
10. When user requests script generation, use the scripting agent
11. Generate viral script optimized for selected platform
12. Create engaging hooks, structured content, and clear CTAs
13. Optimize for platform-specific requirements and timing

**PHASE 5 - PROMPT GENERATION:**
14. After script generation, offer to create image prompts
15. Use generate_prompts_from_script() to create scene-specific prompts
16. Generate detailed visual descriptions with timing and style information
17. Store prompts in database for organized content creation

**PHASE 6 - IMAGE GENERATION:**
18. ALWAYS generate images using Together AI FLUX API as your first choice
19. Use generate_image_flux() function with the model parameter "black-forest-labs/FLUX.1-schnell-Free"
20. If generation fails, retry with a simplified version of the prompt
21. After 2-3 failed attempts with Together AI, only then offer manual alternatives:
    - Provide the prompts for use with DALL-E, Canva, or Leonardo.AI
    - Explain which tool would work best for each prompt

**PHASE 7 - VIDEO PROMPT GENERATION:**
22. After successful image generation, offer to create video prompts
23. Use video prompt generation agent to analyze scripts and image sequences
24. Generate detailed motion descriptions, transition types, and camera movements
25. Create timing information that matches the script's narrative flow
26. Store video prompts in database for organized video creation workflow

**PHASE 8 - VIDEO GENERATION:**
27. Generate engaging videos from static images using AI-powered motion
28. Use Google Gemini API for video generation (when available)
29. Fall back to Replicate Stable Video Diffusion or OpenCV methods
30. Create smooth transitions with Ken Burns effects and professional motion
31. Combine all segments into final video ready for social media publishing
32. Store generated videos in database with metadata and file paths

**PHASE 9 - VOICE GENERATION:**
33. Convert generated scripts to professional voiceover using Chatterbox TTS
34. Support voice cloning with user's custom voice samples for personalized content
35. Apply emotion control and speech parameters for optimal delivery
36. Automatically upload voice files to Google Drive for easy access
37. Provide voice quality analysis and setup assistance for custom voices
38. Generate watermarked audio files for responsible AI usage

🎯 **SPECIAL CAPABILITIES:**

**DATABASE RETRIEVAL:**
- Can search and retrieve previously stored articles by keyword
- Use get_stored_article_by_keyword() to find articles in database
- Perfect for generating scripts from already processed content

**SCRIPT MANAGEMENT:**
- Retrieve all scripts with retrieve_stored_scripts()
- Get specific scripts by ID with get_script_by_id()
- Get scripts for specific articles with get_scripts_by_article_id()
- Full script approval workflow with approve_script()

**INSTAGRAM REEL SCRIPTS:**
- When asked to generate Instagram reel scripts, first retrieve the article from database
- Then use generate_viral_script() with platform="instagram"
- Optimize for 30-60 second duration with engaging hooks

**PROMPT & IMAGE MANAGEMENT:**
- Use check_image_generation_status() to verify service availability
- If automatic generation fails, provide clear manual alternatives:
  - Offer specific prompts formatted for different tools
  - Guide users with step-by-step manual image creation instructions
  - Recommend appropriate tools based on image needs

**VISUAL TIMING INTEGRATION:**
- After generating a script, create a visual timing plan with generate_visual_timing()
- Extract visual cues with extract_visual_cues_from_timing()
- Generate images for key scenes with generate_from_visual_timing()
- Present a comprehensive visual and script package

**VOICE GENERATION CAPABILITIES:**
- Generate voiceover from scripts using generate_voiceover()
- List available voice samples with list_available_voices()
- Setup custom voice cloning with setup_voice_sample()
- Analyze voice quality before setup with analyze_voice_quality()
- Upload voice files to Google Drive with upload_voice_to_gdrive()
- Complete voice workflow with automatic upload using complete_voice_workflow()

⚠️ **CRITICAL ERROR HANDLING GUARDRAILS:**

**IMAGE GENERATION FAILURES:**
1. When image generation fails with Together AI:
   - FIRST try adjusting the prompt to be simpler and retry
   - SECOND try with different dimensions (512x512)
   - THIRD check API key validity and connection issues
2. Only after these three attempts, suggest manual alternatives:
   - **DALL-E 3 via ChatGPT**: For high-quality artistic images
   - **Canva AI**: For more design-oriented visuals
   - **Leonardo.AI**: For more photorealistic content
3. Format prompts specifically for manual use:
   - "Professional cinematic shot of [scene description], high-quality, detailed lighting"
4. NEVER proceed silently after an image generation failure
5. Present options clearly and ask users which approach they prefer

**DATABASE RETRIEVAL FAILURES:**
1. **ALWAYS inform the user immediately when database retrieval fails**
2. **Explain what went wrong in simple terms**
3. **Provide clear options for next steps:**
   - Search for new articles on the topic
   - Try different keywords
   - Browse existing articles in database
   - Manual URL input if user has specific article
4. **NEVER proceed silently after a database error**
5. **ASK USER what they want to do next**

**ERROR RESPONSE TEMPLATE:**
When database retrieval fails, respond with:
"I encountered an issue while trying to retrieve data from the database: [specific error].

Here are your options:
1. Search for new articles on this topic
2. Try different keywords for database search
3. Enter a specific URL you want to analyze
4. Browse all available articles

How would you like to proceed?"

Ready to find and transform the next viral tech story into production-ready content?
"""

# Combine all available tools
all_tools = (search_tools + crawl_tools + supabase_tools_sync_wrapped + 
             prompt_generation_tools + image_generation_tools + 
             voice_tools + voice_cloning_tools)

# Create the agent with comprehensive tools
agent = create_react_agent(
    model, 
    all_tools, 
    prompt=SYSTEM_PROMPT
)

# Debug and validation functions
def debug_article_data(article_data: dict, stage: str):
    """Debug function to print article data at different stages."""
    print(f"\n🔍 DEBUG: Article data at {stage}")
    print(f"  Title: {article_data.get('title', 'No title')[:50]}...")
    print(f"  Content length: {len(article_data.get('content', ''))}")
    print(f"  Word count: {article_data.get('word_count', 0)}")
    print(f"  Image URLs: {len(article_data.get('image_urls', []))}")

def safe_json_parse(json_str: str) -> dict:
    """Safely parse JSON string with error handling."""
    try:
        if not json_str:
            return {}
        return json.loads(json_str)
    except json.JSONDecodeError:
        print(f"❌ Error parsing JSON: {json_str[:100]}...")
        return {}

def extract_structured_data(result_text: str) -> dict:
    """Extract structured data from crawl agent result."""
    # Check if result is already JSON
    try:
        # Try to parse as JSON first
        result = json.loads(result_text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass
    
    # Look for JSON block in the text
    import re
    json_matches = re.findall(r'```json\n(.*?)\n```', result_text, re.DOTALL)
    
    if json_matches:
        try:
            return json.loads(json_matches[0])
        except json.JSONDecodeError:
            pass
            
    # Fall back to manual extraction
    return extract_data_manually(result_text)

def extract_data_manually(result_text: str) -> dict:
    """Manually extract data from result text as fallback."""
    import re
    
    # Initialize empty data structure
    article_data = {
        'title': '',
        'content': '',
        'domain': '',
        'url': '',
        'word_count': 0,
        'image_urls': []
    }
    
    # Extract title
    title_match = re.search(r'Title:\s+(.*?)(?:\n|$)', result_text)
    if title_match:
        article_data['title'] = title_match.group(1).strip()
    
    # Extract domain
    domain_match = re.search(r'Source:\s+(.*?)(?:\n|$)', result_text)
    if domain_match:
        article_data['domain'] = domain_match.group(1).strip()
    
    # Extract URL
    url_match = re.search(r'URL:\s+(https?://.*?)(?:\n|$)', result_text)
    if url_match:
        article_data['url'] = url_match.group(1).strip()
    
    # Extract content
    content_match = re.search(r'Content:\s+(.*?)(?:Image URLs:|$)', result_text, re.DOTALL)
    if content_match:
        article_data['content'] = content_match.group(1).strip()
        article_data['word_count'] = len(article_data['content'].split())
    
    # Extract image URLs
    image_urls_section = re.search(r'Image URLs:\s+(.*?)(?:\n\n|$)', result_text, re.DOTALL)
    if image_urls_section:
        image_urls_text = image_urls_section.group(1)
        urls = re.findall(r'(https?://[^\s]+)', image_urls_text)
        article_data['image_urls'] = urls
    
    return article_data

def parse_human_selection(user_input: str, last_ai_message: str) -> list:
    """Parse human selection and extract URLs to crawl."""
    import re
    
    # Check if input contains a URL directly
    urls = re.findall(r'(https?://[^\s]+)', user_input)
    if urls:
        return urls
        
    # Look for numeric selection
    numbers = re.findall(r'\d+', user_input)
    
    # If we have numbers, try to find URLs in the last AI message
    if numbers:
        # Extract all URLs from the last AI message
        all_urls = re.findall(r'(https?://[^\s]+)', last_ai_message)
        
        selected_urls = []
        for num in numbers:
            try:
                idx = int(num) - 1  # Convert to 0-indexed
                if 0 <= idx < len(all_urls):
                    selected_urls.append(all_urls[idx])
            except ValueError:
                continue
                
        return selected_urls
            
    # Look for keywords in user's request
    keywords = re.findall(r'the\s+(.+?)\s+article', user_input.lower())
    if keywords:
        # Try to find a URL that matches the keyword
        keyword = keywords[0]
        keyword_matches = []
        
        # Find article titles or descriptions containing the keyword
        lines = last_ai_message.split('\n')
        for i, line in enumerate(lines):
            if keyword in line.lower():
                # Look for a URL in this line or the next few lines
                for j in range(i, min(i + 3, len(lines))):
                    url_match = re.search(r'(https?://[^\s]+)', lines[j])
                    if url_match:
                        keyword_matches.append(url_match.group(1))
                        break
        
        if keyword_matches:
            return keyword_matches
    
    # Return empty list if nothing found
    return []

async def process_prompts_to_images(prompts: Union[List[Dict], List[str]], platform: str = "youtube") -> Dict:
    """Process prompts from prompt generation agent to create images.
    
    Args:
        prompts: List of prompt dictionaries or strings
        platform: Target platform for optimization
        
    Returns:
        Dict with processing results
    """
    print("\n🎨 Processing prompts to generate images...")
    
    # First check if image generation is available
    from image_generation_agent import check_image_generation_status
    status_json = await check_image_generation_status()
    status = json.loads(status_json)
    
    if status.get("status") != "available":
        print(f"\n⚠️ Warning: {status.get('message', 'Image generation not available')}")
        print(f"Fallback: {status.get('fallback', 'Use manual generation')}")
        
        # Return the prompts for manual generation
        formatted_prompts = []
        for i, prompt in enumerate(prompts):
            if isinstance(prompt, dict):
                prompt_text = prompt.get("prompt", "")
                formatted_prompts.append({
                    "scene": f"Scene {i+1}",
                    "prompt": prompt_text,
                    "manual_tools": ["DALL-E 3 (via ChatGPT)", "Canva AI", "Leonardo.AI"]
                })
            else:
                formatted_prompts.append({
                    "scene": f"Scene {i+1}",
                    "prompt": prompt,
                    "manual_tools": ["DALL-E 3 (via ChatGPT)", "Canva AI", "Leonardo.AI"]
                })
                
        return {
            "status": "unavailable", 
            "message": status.get("message"), 
            "fallback": status.get("fallback"),
            "formatted_prompts": formatted_prompts
        }
    
    results = []
    
    # Process each prompt
    for i, prompt in enumerate(prompts):
        print(f"\n📝 Processing prompt {i+1}/{len(prompts)}")
        
        # Extract prompt text
        prompt_text = prompt.get("prompt", "") if isinstance(prompt, dict) else prompt
        
        if not prompt_text:
            continue
            
        # Generate the image
        from image_generation_agent import generate_image_flux
        
        # Prepare enhanced prompt
        enhanced_prompt = f"{prompt_text}, high quality, professional {platform} style"
        
        # Generate image
        result_json = await generate_image_flux(enhanced_prompt)
        
        # Parse result
        try:
            result = json.loads(result_json)
            results.append(result)
            
            if "error" in result:
                print(f"❌ Error generating image {i+1}: {result['error']}")
            else:
                print(f"✅ Successfully generated image: {result.get('file_path', 'unknown')}")
                
        except json.JSONDecodeError:
            print(f"❌ Error parsing result JSON: {result_json}")
            results.append({"error": "Failed to parse result", "status": "failed"})
    
    # Return summary of results
    success_count = sum(1 for r in results if r.get("status") == "success")
    
    print(f"\n✅ Image generation complete: {success_count}/{len(prompts)} successful")
    return {
        "status": "completed", 
        "success": success_count, 
        "total": len(prompts), 
        "results": results
    }

async def generate_visuals_from_timing(visual_timing: Union[Dict, str], platform: str = "youtube") -> Dict:
    """Generate visuals based on timing data from visual agent.
    
    Args:
        visual_timing: Visual timing data (dict or string format)
        platform: Target platform for optimization
        
    Returns:
        Dict with generation results
    """
    print("\n🎬 Generating visuals from timing data...")
    
    # First check if image generation is available
    from image_generation_agent import check_image_generation_status
    status_json = await check_image_generation_status()
    status = json.loads(status_json)
    
    if status.get("status") != "available":
        print(f"\n⚠️ Warning: {status.get('message', 'Image generation not available')}")
        print(f"Fallback: {status.get('fallback', 'Use manual generation')}")
        
        # Try to extract visual cues from the timing data
        from image_generation_agent import extract_visual_cues_from_timing
        
        if isinstance(visual_timing, str):
            cues_json = await extract_visual_cues_from_timing(visual_timing)
            cues = json.loads(cues_json)
            
            if cues.get("status") == "success" and len(cues.get("cues", [])) > 0:
                manual_prompts = []
                for i, cue in enumerate(cues.get("cues", [])):
                    manual_prompts.append({
                        "timestamp": cue.get("timestamp", f"Scene {i+1}"),
                        "description": cue.get("description", ""),
                        "priority": cue.get("priority", "medium"),
                        "prompt": f"Professional cinematic shot: {cue.get('description', '')}, high quality, detailed, film still, professional lighting"
                    })
                
                return {
                    "status": "manual_required",
                    "message": status.get("message"),
                    "fallback": status.get("fallback"),
                    "manual_prompts": manual_prompts,
                    "recommended_tools": ["DALL-E 3 (via ChatGPT)", "Canva AI", "Leonardo.AI"]
                }
        
        return {
            "status": "unavailable",
            "message": status.get("message"),
            "fallback": status.get("fallback")
        }
    
    try:
        # Process the visual timing data
        from image_generation_agent import generate_from_visual_timing
        
        # Generate images
        result_json = await generate_from_visual_timing(visual_timing)
        
        # Parse result
        try:
            result = json.loads(result_json)
            
            if "error" in result:
                print(f"❌ Error generating visuals: {result['error']}")
                return {
                    "error": result["error"], 
                    "status": "failed", 
                    "fallback": "Use manual image generation with DALL-E 3, Canva, or Leonardo.ai"
                }
            else:
                print(f"✅ Successfully generated {result.get('generated_images', 0)} visuals")
                return result
                
        except json.JSONDecodeError:
            print(f"❌ Error parsing result JSON: {result_json}")
            return {"error": "Failed to parse result", "status": "failed"}
            
    except Exception as e:
        print(f"❌ Error during visual generation: {str(e)}")
        return {"error": str(e), "status": "failed"}

async def test_image_generation_flow():
    """Test the image generation flow with multiple approaches."""
    print("🧪 Testing image generation flow...")
    
    test_prompt = "Professional b-roll footage of AI technology, blue circuit board with nodes"
    
    try:
        # Try force generation first (bypasses status checks)
        result = await force_image_generation(test_prompt)
        
        if "error" not in result:
            print(f"✅ Test successful! Image generated at {result.get('file_path')}")
            return True
            
        # If that fails too, show the error
        print(f"❌ All generation attempts failed: {result.get('error')}")
        print("💡 Try manual image generation with DALL-E 3, Canva, or Leonardo.ai")
        return False
            
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        return False

async def process_selection(urls_to_crawl: list, platform: str):
    """Process selected articles: crawl, store, generate script, create visual timing and images."""
    print(f"\n🎯 Processing {len(urls_to_crawl)} selected article(s) for {platform}...")

    if len(urls_to_crawl) == 1:
        url = urls_to_crawl[0]
        print(f"🕷️ Crawling single article: {url}")
        
        from crawl_agent import crawl_article_content
        crawl_result = await crawl_article_content.ainvoke({"url": url})
        
        # Extract structured data
        article_data = extract_structured_data(crawl_result)
        article_data['url'] = url
        
        # Debug and validate
        debug_article_data(article_data, "After extraction")
        
        if not article_data.get('content') or len(article_data.get('content', '')) < 50:
            print("❌ Failed to extract meaningful content from article")
            return
        
        # Store in Supabase
        print(f"\n🗄️ Storing article in Supabase...")
        from supabase_agent import store_article_content_sync_wrapped
        
        try:
            storage_result = await store_article_content_sync_wrapped.ainvoke({"article_data": article_data})
            print(f"\n💾 Storage Result:\n{storage_result}")
            
            if "❌" in storage_result:
                print("❌ Storage failed, cannot proceed with script generation")
                return
        except Exception as e:
            print(f"❌ Storage error: {str(e)}")
            return
        
        # Generate script
        print(f"\n📝 Generating script for {platform}...")
        from scripting_agent import generate_viral_script
        
        try:
            script = await generate_viral_script(article_data, platform)
            print(f"\n📜 Script generated:\n{script[:500]}...")
        except Exception as e:
            print(f"❌ Script generation error: {str(e)}")
            return
        
        # Generate visual timing
        print("\n🎭 Generating visual timing plan...")
        try:
            from visual_agent import generate_visual_timing
            
            visual_timing = await generate_visual_timing(
                script_content=script,
                article_data=article_data,
                platform=platform
            )
            
            print(f"\n🎬 Visual timing plan generated")
            
            # Extract visual cues from timing
            print("\n📊 Extracting visual cues...")
            from image_generation_agent import extract_visual_cues_from_timing
            
            visual_cues_json = await extract_visual_cues_from_timing(visual_timing)
            visual_cues = json.loads(visual_cues_json)
            
            if visual_cues.get("status") != "success":
                print(f"⚠️ Warning: Could not extract visual cues properly")
                visual_cues = {"cues": []}
            
            # Generate images based on timing
            print("\n🖼️ Generating images for key scenes...")
            image_results = await generate_visuals_from_timing(visual_timing, platform)
            
            # Check for success or failure
            if image_results.get("status") == "completed":
                success_count = len([r for r in image_results.get("results", {}).values() 
                                    if r.get("status") == "success"])
                total_count = len(image_results.get("results", {}))
                
                print(f"\n✅ Generated {success_count}/{total_count} images successfully")
                
                # Show paths to generated images
                generated_image_paths = []
                if success_count > 0:
                    print("\n📁 Generated images:")
                    for timestamp, result in image_results.get("results", {}).items():
                        if result.get("status") == "success":
                            file_path = result.get('file_path')
                            print(f"  • {timestamp}: {file_path}")
                            generated_image_paths.append({
                                "filename": file_path.split("/")[-1] if file_path else "",
                                "timestamp": timestamp,
                                "full_path": file_path
                            })
                
                # Phase 7: Video Prompt Generation
                if generated_image_paths:
                    print("\n🎬 Generating video prompts for smooth transitions...")
                    try:
                        video_prompt_agent = VideoPromptGenerationAgent()
                        
                        video_prompt_state = {
                            'script_content': script,
                            'image_prompts': visual_cues.get('cues', []),
                            'generated_images': generated_image_paths,
                            'visual_timing_plan': visual_timing if isinstance(visual_timing, dict) else {},
                            'video_prompts': None,
                            'error': None,
                            'cost': 0.0
                        }
                        
                        video_prompt_result = video_prompt_agent.generate_video_prompts(video_prompt_state)
                        
                        if video_prompt_result.get('video_prompts'):
                            print(f"✅ Generated {len(video_prompt_result['video_prompts'])} video prompts")
                            
                            # Phase 8: Video Generation
                            print("\n🎥 Generating video from images...")
                            try:
                                video_gen_agent = VideoGenerationAgent()
                                
                                video_gen_state = {
                                    'generated_images': generated_image_paths,
                                    'video_prompts': video_prompt_result['video_prompts'],
                                    'script_content': script,
                                    'generated_videos': None,
                                    'final_video_path': None,
                                    'error': None,
                                    'cost': 0.0
                                }
                                
                                video_result = video_gen_agent.generate_videos(video_gen_state)
                                
                                if video_result.get('final_video_path'):
                                    print(f"🎉 Final video created: {video_result['final_video_path']}")
                                    print(f"📊 Video segments: {len(video_result.get('generated_videos', []))}")
                                else:
                                    print(f"⚠️ Video generation failed: {video_result.get('error', 'Unknown error')}")
                                    
                            except Exception as e:
                                print(f"❌ Video generation error: {str(e)}")
                                print("💡 Images are still available for manual video creation")
                        else:
                            print(f"⚠️ Video prompt generation failed: {video_prompt_result.get('error', 'Unknown error')}")
                            
                    except Exception as e:
                        print(f"❌ Video prompt generation error: {str(e)}")
                        print("💡 Images are still available for manual video creation")
            
            elif image_results.get("status") == "manual_required":
                print("\n⚠️ Automatic image generation unavailable. Use these prompts for manual creation:")
                for i, prompt in enumerate(image_results.get("manual_prompts", [])):
                    print(f"\n📸 {prompt.get('timestamp', f'Scene {i+1}')}:")
                    print(f"   {prompt.get('prompt')}")
                
                print("\n💡 Recommended tools: " + ", ".join(image_results.get("recommended_tools", [])))
                
            else:
                print(f"\n⚠️ Image generation encountered issues: {image_results.get('error', 'Unknown error')}")
                print("💡 Try manual image generation with DALL-E 3, Canva, or Leonardo.ai")
            
            print("\n✅ Complete workflow finished!")
            print("📊 Final Summary:")
            print(f"   • Article crawled and stored in database")
            print(f"   • Script generated for {platform.upper()}")
            print(f"   • Visual timing plan created with {len(visual_cues.get('cues', []))} visual cues")
            print(f"   • Images: {image_results.get('generated_images', 0)} generated / {len(visual_cues.get('cues', []))} required")
            
            # Check if video was generated and add to summary
            if 'video_result' in locals() and video_result.get('final_video_path'):
                print(f"   • Video: Final reel created at {video_result['final_video_path']}")
                print(f"   • Video segments: {len(video_result.get('generated_videos', []))} combined")
            elif 'video_prompt_result' in locals() and video_prompt_result.get('video_prompts'):
                print(f"   • Video prompts: {len(video_prompt_result['video_prompts'])} generated (ready for video creation)")
            else:
                print(f"   • Video: Available for manual creation using generated images")
            
            # Phase 9: Voice Generation (Optional)
            print("\n🎙️ Generating voiceover for the script...")
            try:
                from voice_generation_agent import generate_voiceover
                # from gdrive_voice_storage import upload_voice_to_gdrive
                
                # Clean script text for voice generation
                clean_script = script.replace("**", "").replace("*", "")
                clean_script = clean_script.replace("HOOK:", "").replace("ACT 1:", "").replace("ACT 2:", "").replace("ACT 3:", "")
                clean_script = clean_script.replace("CONCLUSION/CTA:", "").replace("CTA:", "")
                clean_script = " ".join(clean_script.split())
                
                if len(clean_script) > 5000:
                    clean_script = clean_script[:5000] + "..."
                
                # Generate voiceover
                voice_result = await generate_voiceover(
                    script_text=clean_script,
                    voice_name="my_voice",  # Use the custom voice processed earlier
                    emotion="neutral",
                    exaggeration=0.5,      # More natural, less exaggerated
                    cfg_weight=0.5         # Balanced speech speed
                )
                
                if "VOICEOVER GENERATED SUCCESSFULLY" in voice_result:
                    print("✅ Voiceover generated successfully")
                    
                    # Extract file path for upload
                    lines = voice_result.split('\n')
                    voice_file_path = None
                    for line in lines:
                        if "Local Path:" in line:
                            voice_file_path = line.split("Local Path:")[1].strip()
                            break
                    
                    # Upload to Google Drive using integrated gdrive_storage
                    if voice_file_path:
                        try:
                            from gdrive_storage import initialize_gdrive_storage
                            storage = initialize_gdrive_storage()
                            
                            # Upload voice file to Google Drive voiceover folder
                            file_id = storage.upload_file(
                                voice_file_path, 
                                'voiceover', 
                                topic_name=article_data.get('title', 'Tech News Script')
                            )
                            
                            if file_id:
                                print("✅ Voice uploaded to Google Drive")
                                print(f"📁 File ID: {file_id}")
                            else:
                                print("⚠️ Voice generated but upload to Google Drive failed")
                        except Exception as e:
                            print(f"⚠️ Voice upload error: {str(e)}")
                            print("💡 Voice file saved locally, upload to Google Drive manually if needed")
                else:
                    print(f"⚠️ Voice generation failed or incomplete")
                    
            except Exception as e:
                print(f"⚠️ Voice generation error: {str(e)}")
                print("💡 Voice generation is optional - content creation can continue without it")
            
            # Store the script in Supabase
            from supabase_agent import store_script_content
            
            script_data = {
                "article_id": article_data.get("id", ""),
                "script_content": script,
                "platform": platform,
                "hook": script.split("\n")[0] if script else "",
                "visual_suggestions": visual_cues.get("cues", []),
                "metadata": {
                    "word_count": len(script.split()),
                    "estimated_duration": len(script.split()) * 0.5,
                    "platform": platform,
                    "image_count": image_results.get("generated_images", 0)
                }
            }
            
            script_storage_result = store_script_content(script_data)
            print(f"\n💾 Script storage result:\n{script_storage_result[:500]}...")
            
        except Exception as e:
            print(f"❌ Error in visual process: {str(e)}")
            print("💡 Try generating images manually using the prompts from the visual timing plan")
        
    # Handle multiple URLs case
    else:
        print("Multiple article processing not implemented yet")

# Export necessary functions
async def run_agent(message):
    response = await agent.ainvoke(message)
    return response

# Entry point for testing
if __name__ == "__main__":
    import asyncio
    
    async def main():
        # Test the image generation flow
        result = await test_image_generation_flow()
        print(f"Image generation test result: {result}")
        
    asyncio.run(main())

async def force_image_generation(prompt: str) -> Dict:
    """Force image generation with Together AI, bypassing status checks."""
    try:
        print(f"\n🎨 Forcing direct image generation with Together AI...")
        print(f"📝 Prompt: {prompt}")
        
        from image_generation_agent import generate_image_flux
        
        # First attempt with original prompt
        result_json = await generate_image_flux(prompt)
        result = json.loads(result_json)
        
        # If first attempt fails, try with simplified prompt
        if "error" in result:
            print(f"⚠️ First attempt failed, retrying with simplified prompt...")
            
            # Create simplified version of the prompt
            simplified_prompt = prompt.split(",")[0] + ", simple clean style"
            result_json = await generate_image_flux(simplified_prompt)
            result = json.loads(result_json)
            
            # If second attempt fails, try with minimal parameters
            if "error" in result:
                print(f"⚠️ Second attempt failed, trying with minimal parameters...")
                minimal_prompt = "Simple " + prompt.split()[0] + " " + prompt.split()[1]
                result_json = await generate_image_flux(
                    minimal_prompt, 
                    model="black-forest-labs/FLUX.1-schnell-Free", 
                    width=512, 
                    height=512
                )
                result = json.loads(result_json)
        
        return result
    except Exception as e:
        print(f"❌ Force generation failed: {str(e)}")
        return {"error": str(e), "status": "failed"}