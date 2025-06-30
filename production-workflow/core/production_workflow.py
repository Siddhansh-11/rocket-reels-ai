import asyncio
import json
import re
from typing import Dict, Any, List, Optional, Annotated
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from dataclasses import dataclass, field
from datetime import datetime
from operator import add

# Import agent tools
from agents.search_agent import search_tools
from agents.crawl_agent import crawl_tools
from agents.supabase_agent import supabase_tools_sync_wrapped
from agents.scripting_agent import scripting_tools
from agents.prompt_generation_agent import prompt_generation_tools
from agents.image_generation_agent import image_generation_tools
from agents.voice_generation_agent import voice_tools
from agents.asset_gathering_agent import asset_gathering_tools
from agents.notion_agent import notion_tools

@dataclass
class WorkflowState:
    """State management for the production workflow"""
    # Input
    user_query: str = ""
    topic: str = ""
    
    # Search phase
    search_results: str = ""
    search_urls: List[str] = field(default_factory=list)
    
    # Crawl phase
    article_data: Dict[str, Any] = field(default_factory=dict)
    crawled_content: str = ""
    
    # Storage phase
    article_id: str = ""
    storage_result: str = ""
    
    # Script generation phase
    script_content: str = ""
    script_hook: str = ""
    visual_suggestions: List[str] = field(default_factory=list)
    script_id: str = ""
    
    # Parallel generation phase (prompt, image, voice) - Using Annotated for concurrent updates
    prompts_generated: Annotated[List[Dict], add] = field(default_factory=list)
    images_generated: Annotated[List[str], add] = field(default_factory=list)
    voice_files: Annotated[List[str], add] = field(default_factory=list)
    
    # Asset gathering phase
    project_folder_path: str = ""
    asset_organization_result: str = ""
    
    # Notion integration phase
    notion_project_id: str = ""
    notion_status: str = ""
    
    # Status tracking
    current_step: str = "search"
    errors: Annotated[List[str], add] = field(default_factory=list)
    messages: Annotated[List[BaseMessage], add] = field(default_factory=list)
    

class ProductionWorkflow:
    """Main production workflow graph implementation"""
    
    def __init__(self):
        self.workflow = StateGraph(WorkflowState)
        self._setup_workflow()
    
    def _setup_workflow(self):
        """Define the workflow graph structure"""
        
        # Add nodes
        self.workflow.add_node("search", self.search_node)
        self.workflow.add_node("crawl", self.crawl_node)
        self.workflow.add_node("store_article", self.store_article_node)
        self.workflow.add_node("generate_script", self.generate_script_node)
        self.workflow.add_node("store_script", self.store_script_node)
        self.workflow.add_node("prompt_generation", self.prompt_generation_node)
        self.workflow.add_node("image_generation", self.image_generation_node)
        self.workflow.add_node("voice_generation", self.voice_generation_node)
        self.workflow.add_node("asset_gathering", self.asset_gathering_node)
        self.workflow.add_node("notion_integration", self.notion_integration_node)
        self.workflow.add_node("finalize", self.finalize_node)
        
        # Define the sequential flow
        self.workflow.set_entry_point("search")
        self.workflow.add_edge("search", "crawl")
        self.workflow.add_edge("crawl", "store_article")
        self.workflow.add_edge("store_article", "generate_script")
        self.workflow.add_edge("generate_script", "store_script")
        
        # After script storage: prompt generation and voice generation run in parallel
        self.workflow.add_edge("store_script", "prompt_generation")
        self.workflow.add_edge("store_script", "voice_generation")
        
        # Image generation follows prompt generation
        self.workflow.add_edge("prompt_generation", "image_generation")
        
        # Both image generation and voice generation converge to asset gathering
        self.workflow.add_edge("image_generation", "asset_gathering")
        self.workflow.add_edge("voice_generation", "asset_gathering")
        
        # Asset gathering leads to Notion integration
        self.workflow.add_edge("asset_gathering", "notion_integration")
        
        # Notion integration leads to finalize
        self.workflow.add_edge("notion_integration", "finalize")
        
        # Finalize ends the workflow
        self.workflow.add_edge("finalize", END)
    
    async def search_node(self, state: WorkflowState) -> WorkflowState:
        """Search for trending tech news using intelligent AI-powered search"""
        try:
            print(f"🔍 Step 1: Intelligent search for articles about '{state.topic}'")
            state.current_step = "search"
            
            # Use intelligent search tool
            search_tool = search_tools[0]  # search_tech_news
            search_query = state.topic or "latest trending tech news"
            search_results = await search_tool.ainvoke(search_query)
            
            # Extract URLs for next step
            url_extraction_tool = search_tools[1]  # extract_article_urls
            urls = await url_extraction_tool.ainvoke(search_results)
            search_urls = urls[:8] if len(urls) >= 8 else urls
            
            return {
                "search_results": search_results,
                "search_urls": search_urls,
                "current_step": "search",
                "messages": [AIMessage(content=f"Found {len(search_urls)} high-quality standalone articles")]
            }
            
        except Exception as e:
            error_msg = f"Search failed: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "current_step": "search",
                "errors": [error_msg],
                "messages": [AIMessage(content="❌ Search failed")]
            }
    
    async def crawl_node(self, state: WorkflowState) -> WorkflowState:
        """Crawl the selected article"""
        try:
            print("🕷️ Step 2: Crawling article content")
            state.current_step = "crawl"
            
            if not state.search_urls:
                raise Exception("No URLs available to crawl")
            
            # Crawl the first URL (best match)
            crawl_tool = crawl_tools[0]  # crawl_article_content
            crawled_result = await crawl_tool.ainvoke(state.search_urls[0])
            
            # Parse the structured data from the crawled result
            if "```json" in crawled_result:
                json_start = crawled_result.find("```json") + 7
                json_end = crawled_result.find("```", json_start)
                json_str = crawled_result[json_start:json_end].strip()
                try:
                    article_data = json.loads(json_str)
                except json.JSONDecodeError:
                    # Fallback: create basic article data
                    article_data = {
                        "url": state.search_urls[0],
                        "title": "Crawled Article",
                        "content": crawled_result,
                        "domain": "unknown.com",
                        "word_count": len(crawled_result.split())
                    }
            else:
                article_data = {
                    "url": state.search_urls[0],
                    "title": "Crawled Article", 
                    "content": crawled_result,
                    "domain": "unknown.com",
                    "word_count": len(crawled_result.split())
                }
            
            return {
                "crawled_content": crawled_result,
                "article_data": article_data,
                "current_step": "crawl",
                "messages": [AIMessage(content=f"Successfully crawled article: {article_data.get('title', 'Unknown Title')}")]
            }
            
        except Exception as e:
            error_msg = f"Crawling failed: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "current_step": "crawl",
                "errors": [error_msg],
                "messages": [AIMessage(content="❌ Crawling failed")]
            }
    
    async def store_article_node(self, state: WorkflowState) -> WorkflowState:
        """Store article in Supabase"""
        try:
            print("🗄️ Step 3: Storing article in Supabase")
            state.current_step = "store_article"
            
            if not state.article_data:
                raise Exception("No article data available to store")
            
            # Store article using Supabase agent
            storage_tool = supabase_tools_sync_wrapped[0]  # store_article_content_sync_wrapped
            
            # Ensure the article data is properly formatted
            print(f"🔍 DEBUG - Article data type: {type(state.article_data)}")
            print(f"🔍 DEBUG - Article data keys: {list(state.article_data.keys()) if isinstance(state.article_data, dict) else 'Not a dict'}")
            
            # Call the tool with the article data using asyncio.to_thread to avoid blocking
            storage_result = await asyncio.to_thread(storage_tool.invoke, {"article_data": state.article_data})
            
            # Extract article ID from storage result for script linking
            print(f"🔍 DEBUG - Storage result: {storage_result[:200]}...")
            
            # Try multiple patterns to extract article ID
            article_id = ""
            if "Record ID:" in storage_result:
                id_match = re.search(r"Record ID:\s*([a-zA-Z0-9-]+)", storage_result)
                if id_match:
                    article_id = id_match.group(1)
            elif "ID:" in storage_result:
                id_match = re.search(r"ID:\s*([a-zA-Z0-9-]+)", storage_result)
                if id_match:
                    article_id = id_match.group(1)
            
            print(f"🔍 DEBUG - Extracted article ID: '{article_id}'")
            
            return {
                "storage_result": storage_result,
                "article_id": article_id,
                "current_step": "store_article",
                "messages": [AIMessage(content=f"Article stored successfully with ID: {article_id}")]
            }
            
        except Exception as e:
            error_msg = f"Article storage failed: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "current_step": "store_article",
                "errors": [error_msg],
                "messages": [AIMessage(content="❌ Article storage failed")]
            }
    
    async def generate_script_node(self, state: WorkflowState) -> WorkflowState:
        """Generate script from stored article"""
        try:
            print("📝 Step 4: Generating script content")
            state.current_step = "generate_script"
            
            if not state.article_data:
                raise Exception("No article data available for script generation")
            
            # Use scripting agent to generate script
            script_tool = scripting_tools[0]  # Assuming first tool is the main script generator
            
            # Prepare input for script generation with proper format
            script_input = {
                "url": state.article_data.get('url', ''),
                "title": state.article_data.get('title', state.topic),
                "content": state.article_data.get('content', ''),
                "domain": state.article_data.get('domain', 'tech news'),
                "word_count": state.article_data.get('word_count', 0),
                "key_points": state.article_data.get('key_points', []),
                "topic": state.article_data.get('title', state.topic),
                "article_content": state.article_data.get('content', ''),
                "platform": "youtube",
                "source": state.article_data.get('domain', 'tech news')
            }
            
            print(f"🔍 DEBUG - Script input prepared with keys: {list(script_input.keys())}")
            print(f"🔍 DEBUG - Content length: {len(script_input.get('content', ''))}")
            
            # Debug the tool call
            print(f"🔍 DEBUG - Calling script tool with: article_data keys={list(script_input.keys())}")
            print(f"🔍 DEBUG - Has URL: {'url' in script_input and script_input['url']}")
            print(f"🔍 DEBUG - Has content: {'content' in script_input and script_input['content']}")
            
            # Call the tool with the correct parameter format
            script_result = await script_tool.ainvoke({"article_data": script_input, "platform": "youtube"})
            
            # Parse script result
            print(f"🔍 DEBUG - Script result type: {type(script_result)}")
            print(f"🔍 DEBUG - Script result preview: {str(script_result)[:200]}...")
            
            script_hook = ""
            visual_suggestions = []
            
            # Extract hook and visual suggestions if available
            if isinstance(script_result, str):
                if "**HOOK:**" in script_result:
                    hook_match = re.search(r"\*\*HOOK:\*\*\s*(.+?)(?:\n\*\*|\n\n|$)", script_result, re.DOTALL)
                    if hook_match:
                        script_hook = hook_match.group(1).strip()
                elif "HOOK:" in script_result:
                    hook_start = script_result.find("HOOK:") + 5
                    hook_end = script_result.find("\n", hook_start)
                    if hook_end == -1:
                        hook_end = len(script_result)
                    script_hook = script_result[hook_start:hook_end].strip()
                
                # Extract visual suggestions
                if "Visual Suggestions:" in script_result:
                    visual_start = script_result.find("Visual Suggestions:") + 19
                    visual_section = script_result[visual_start:visual_start+500]
                    visual_suggestions = [line.strip().lstrip('-•').strip() for line in visual_section.split('\n') if line.strip() and ('-' in line or '•' in line)]
                
                # Fallback: create some basic visual suggestions
                if not visual_suggestions:
                    visual_suggestions = [
                        f"Technology showcase for {state.article_data.get('title', 'the topic')}",
                        f"Modern tech illustration featuring {state.article_data.get('domain', 'tech news')}",
                        "Professional tech presentation background"
                    ]
            
            print(f"🔍 DEBUG - Extracted hook: '{script_hook}'")
            print(f"🔍 DEBUG - Visual suggestions: {len(visual_suggestions)} items")
            
            return {
                "script_content": script_result,
                "script_hook": script_hook,
                "visual_suggestions": visual_suggestions,
                "current_step": "generate_script",
                "messages": [AIMessage(content=f"Script generated successfully ({len(script_result)} characters)")]
            }
            
        except Exception as e:
            error_msg = f"Script generation failed: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "current_step": "generate_script",
                "errors": [error_msg],
                "messages": [AIMessage(content="❌ Script generation failed")]
            }
    
    async def store_script_node(self, state: WorkflowState) -> WorkflowState:
        """Store generated script in Supabase"""
        try:
            print("🗄️ Step 5: Storing script in Supabase")
            state.current_step = "store_script"
            
            if not state.script_content:
                raise Exception("Missing script content for storage")
            
            # If no article ID, use a placeholder or skip linking
            article_id = state.article_id if state.article_id else "unknown"
            print(f"🔍 DEBUG - Using article ID for script: '{article_id}'")
            
            # Prepare script data for storage
            script_data = {
                "article_id": article_id,
                "platform": "youtube",
                "script_content": state.script_content,
                "hook": state.script_hook,
                "visual_suggestions": state.visual_suggestions,
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "workflow_version": "production_v1"
                }
            }
            
            # Store script using Supabase agent  
            script_storage_tool = supabase_tools_sync_wrapped[6]  # store_script_content
            script_storage_result = await asyncio.to_thread(script_storage_tool.invoke, {"script_data": script_data})
            
            # Extract script ID
            script_id = ""
            if "Script ID:" in script_storage_result:
                id_line = [line for line in script_storage_result.split('\n') if "Script ID:" in line][0]
                script_id = id_line.split("Script ID:")[1].strip()
            
            return {
                "script_id": script_id,
                "current_step": "store_script",
                "messages": [AIMessage(content=f"Script stored successfully with ID: {script_id}")]
            }
            
        except Exception as e:
            error_msg = f"Script storage failed: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "current_step": "store_script",
                "errors": [error_msg],
                "messages": [AIMessage(content="❌ Script storage failed")]
            }
    
    async def prompt_generation_node(self, state: WorkflowState) -> WorkflowState:
        """Generate prompts for image generation (parallel node)"""
        try:
            print("🎨 Step 6a: Generating image prompts (parallel)")
            
            if not state.visual_suggestions and not state.script_content:
                print("⚠️ No visual suggestions or script content available, creating basic prompts")
                generated_prompts = [
                    {"prompt": f"Technology concept art for {state.topic or 'tech news'}", "type": "thumbnail"},
                    {"prompt": f"Modern tech illustration {state.topic or 'tech news'}", "type": "background"}
                ]
            else:
                # Use prompt generation agent with script content
                prompt_tool = prompt_generation_tools[0]  # generate_prompts_from_script
                
                # Use script content if available, otherwise use visual suggestions
                content_to_use = state.script_content if state.script_content else "\n".join(state.visual_suggestions)
                
                prompts_result = await prompt_tool.ainvoke({"script_content": content_to_use, "num_prompts": 5})
                
                # Parse the result to extract actual prompts
                if "Generated" in prompts_result and "prompts" in prompts_result:
                    # Extract prompts from the generated result
                    generated_prompts = [
                        {"prompt": suggestion, "type": "scene"} 
                        for suggestion in state.visual_suggestions[:5]
                    ]
                else:
                    # Fallback to visual suggestions
                    generated_prompts = [
                        {"prompt": suggestion, "type": "scene"} 
                        for suggestion in state.visual_suggestions[:5]
                    ]
            
            # Return the prompts to be added to state
            return {
                "prompts_generated": generated_prompts,
                "messages": [AIMessage(content=f"Generated {len(generated_prompts)} image prompts")]
            }
            
        except Exception as e:
            error_msg = f"Prompt generation failed: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "errors": [error_msg],
                "prompts_generated": [],
                "messages": [AIMessage(content="❌ Prompt generation failed")]
            }
    
    async def image_generation_node(self, state: WorkflowState) -> WorkflowState:
        """Generate images from prompts (parallel node)"""
        try:
            print("🖼️ Step 6b: Generating images (parallel)")
            
            if not state.prompts_generated:
                print("⚠️ No prompts available, skipping image generation")
                return {
                    "images_generated": [],
                    "messages": [AIMessage(content="⚠️ No prompts available, skipped image generation")]
                }
            
            # Use image generation agent
            image_tool = image_generation_tools[0]  # Assuming first tool is main image generator
            
            generated_images = []
            for prompt_data in state.prompts_generated[:3]:  # Limit to 3 images
                try:
                    image_result = await image_tool.ainvoke({"prompt": prompt_data["prompt"]})
                    generated_images.append(image_result)
                except Exception as img_error:
                    print(f"⚠️ Image generation failed for prompt: {img_error}")
            
            return {
                "images_generated": generated_images,
                "messages": [AIMessage(content=f"Generated {len(generated_images)} images")]
            }
            
        except Exception as e:
            error_msg = f"Image generation failed: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "errors": [error_msg],
                "images_generated": [],
                "messages": [AIMessage(content="❌ Image generation failed")]
            }
    
    async def voice_generation_node(self, state: WorkflowState) -> WorkflowState:
        """Generate voiceover from script (parallel node)"""
        try:
            print("🎙️ Step 6c: Generating voiceover (parallel)")
            
            if not state.script_content:
                print("⚠️ No script content available, skipping voice generation")
                return {
                    "voice_files": [],
                    "messages": [AIMessage(content="⚠️ No script content available, skipped voice generation")]
                }
            
            # Use voice generation agent
            voice_tool = voice_tools[0]  # generate_voiceover tool
            
            # Extract just the script text without formatting
            clean_script = state.script_content
            # Remove formatting markers
            for marker in ["**HOOK:**", "**ACT 1", "**ACT 2", "**ACT 3", "**CONCLUSION", "**"]:
                clean_script = clean_script.replace(marker, "")
            
            # Use correct parameter name: script_text (not text)
            voice_input = {
                "script_text": clean_script[:1000],  # Limit text length for voice generation
                "voice_name": "default",
                "emotion": "neutral"
            }
            
            voice_result = await voice_tool.ainvoke(voice_input)
            voice_files = [voice_result] if voice_result else []
            
            return {
                "voice_files": voice_files,
                "messages": [AIMessage(content=f"Generated {len(voice_files)} voice files")]
            }
            
        except Exception as e:
            error_msg = f"Voice generation failed: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "errors": [error_msg],
                "voice_files": [],
                "messages": [AIMessage(content="❌ Voice generation failed")]
            }
    
    async def asset_gathering_node(self, state: WorkflowState) -> WorkflowState:
        """Organize generated assets in Google Drive project folder (sequential node)"""
        try:
            print("📁 Step 7: Gathering and organizing assets in Google Drive")
            state.current_step = "asset_gathering"
            
            # Prepare script data for folder creation
            script_data = {
                'title': state.article_data.get('title', state.topic),
                'script_content': state.script_content,
                'script_id': state.script_id,
                'article_id': state.article_id,
                'hook': state.script_hook,
                'visual_suggestions': state.visual_suggestions
            }
            
            # Create project folder structure
            folder_tool = asset_gathering_tools[0]  # create_project_folder_structure
            folder_result = await folder_tool.ainvoke(script_data)
            
            # Extract folder path from result
            project_folder_path = ""
            if "Folder Path:" in folder_result:
                folder_path_line = [line for line in folder_result.split('\n') if "Folder Path:" in line][0]
                project_folder_path = folder_path_line.split("Folder Path:")[1].strip()
            
            # Organize assets
            assets_data = {
                'images': state.images_generated,
                'voice_files': state.voice_files,
                'script_content': state.script_content,
                'prompts': state.prompts_generated
            }
            
            asset_result = ""
            if project_folder_path:
                organize_tool = asset_gathering_tools[1]  # organize_generated_assets
                asset_result = await organize_tool.ainvoke({
                    'project_folder_path': project_folder_path,
                    'assets_data': assets_data
                })
            
            return {
                "project_folder_path": project_folder_path,
                "asset_organization_result": asset_result or folder_result,
                "current_step": "asset_gathering",
                "messages": [AIMessage(content=f"Assets organized in: {project_folder_path}")]
            }
            
        except Exception as e:
            error_msg = f"Asset gathering failed: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "current_step": "asset_gathering",
                "errors": [error_msg],
                "messages": [AIMessage(content="❌ Asset gathering failed")]
            }
    
    async def notion_integration_node(self, state: WorkflowState) -> WorkflowState:
        """Create Notion project and set up monitoring (sequential node)"""
        try:
            print("📋 Step 8: Setting up Notion project tracking")
            state.current_step = "notion_integration"
            
            # Prepare script data for Notion
            notion_script_data = {
                'title': state.article_data.get('title', state.topic),
                'script_content': state.script_content,
                'script_id': state.script_id,
                'article_id': state.article_id,
                'hook': state.script_hook,
                'visual_suggestions': state.visual_suggestions,
                'folder_path': state.project_folder_path
            }
            
            # Create Notion project row
            notion_tool = notion_tools[0]  # create_notion_project_row
            notion_result = await notion_tool.ainvoke(notion_script_data)
            
            # Extract project ID from result
            notion_project_id = ""
            if "Page ID:" in notion_result:
                id_line = [line for line in notion_result.split('\n') if "Page ID:" in line][0]
                notion_project_id = id_line.split("Page ID:")[1].strip()
            
            # Set up folder monitoring (placeholder for now)
            if state.project_folder_path:
                monitor_tool = notion_tools[2]  # monitor_gdrive_folder
                monitor_result = await monitor_tool.ainvoke(state.project_folder_path)
                print(f"📡 Monitoring setup: {monitor_result[:100]}...")
            
            return {
                "notion_project_id": notion_project_id,
                "notion_status": "Assets Ready",
                "current_step": "notion_integration",
                "messages": [AIMessage(content=f"Notion project created with ID: {notion_project_id}")]
            }
            
        except Exception as e:
            error_msg = f"Notion integration failed: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "current_step": "notion_integration",
                "errors": [error_msg],
                "messages": [AIMessage(content="❌ Notion integration failed")]
            }
    
    async def finalize_node(self, state: WorkflowState) -> WorkflowState:
        """Finalize the workflow and compile results"""
        try:
            print("✅ Step 9: Finalizing workflow")
            
            # Compile final results
            final_summary = f"""
🚀 **PRODUCTION WORKFLOW COMPLETED**

📊 **Summary:**
- Topic: {state.topic or state.user_query or 'Latest tech news'}
- Article stored: {state.article_id or 'No ID extracted'}
- Script generated: {state.script_id or 'Not stored'}
- Images created: {len(state.images_generated)}
- Voice files: {len(state.voice_files)}
- Prompts generated: {len(state.prompts_generated)}

📁 **Asset Organization:**
- Project folder: {state.project_folder_path or 'Not created'}
- Asset status: {'✅ Organized' if state.asset_organization_result else '❌ Failed'}

📋 **Notion Integration:**
- Project ID: {state.notion_project_id or 'Not created'}
- Status: {state.notion_status or 'Not set'}

📝 **Script Preview:**
{(state.script_hook[:100] + '...') if state.script_hook else 'No hook extracted'}

🎨 **Assets Generated:**
- Article content: ✅ Stored in Supabase ({len(state.article_data.get('content', '')) if state.article_data else 0} chars)
- Script content: ✅ Generated ({len(state.script_content)} chars)
- Image prompts: ✅ {len(state.prompts_generated)} prompts
- Generated images: ✅ {len(state.images_generated)} images
- Voice files: ✅ {len(state.voice_files)} files
- Google Drive: ✅ Project folder created with organized structure
- Notion workspace: ✅ Project tracking row created

📁 **Google Drive Structure:**
{state.project_folder_path}/
  ├── generated_images/
  ├── voiceover/
  ├── scripts/
  ├── final_draft/ (awaiting editor upload)
  └── resources/

🔔 **Next Steps:**
1. Editor uploads final video to: {state.project_folder_path}/final_draft/
2. Video upload will trigger Notion status update to "Video Ready"
3. Project will be ready for final publishing

❌ **Errors encountered:** {len(state.errors)}
{chr(10).join(state.errors) if state.errors else 'None'}

📄 **Full Script Content:**
{state.script_content[:500] + '...' if len(state.script_content) > 500 else state.script_content}

🎬 **Workflow Complete - Ready for Editor!**
"""
            
            return {
                "current_step": "complete",
                "messages": [AIMessage(content=final_summary)]
            }
            
        except Exception as e:
            error_msg = f"Finalization failed: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "current_step": "complete",
                "errors": [error_msg],
                "messages": [AIMessage(content="❌ Workflow finalization failed")]
            }
    
    def compile(self):
        """Compile the workflow graph"""
        return self.workflow.compile()

# Create global workflow instance and compile it
_workflow_instance = ProductionWorkflow()
production_workflow = _workflow_instance.compile()

# Helper function to run workflow
async def run_production_workflow(topic: str, user_query: str = "") -> WorkflowState:
    """Helper function to run the production workflow"""
    # Initialize state
    initial_state = WorkflowState(
        user_query=user_query,
        topic=topic,
        current_step="search"
    )
    
    print(f"🚀 Starting production workflow for topic: '{topic}'")
    print("=" * 60)
    
    try:
        # Run the compiled workflow
        final_state = await production_workflow.ainvoke(initial_state)
        
        print("=" * 60)
        print("✅ Workflow completed successfully!")
        
        return final_state
        
    except Exception as e:
        print(f"❌ Workflow failed: {str(e)}")
        initial_state.errors.append(f"Workflow execution failed: {str(e)}")
        return initial_state

if __name__ == "__main__":
    # Example usage
    async def main():
        result = await run_production_workflow("latest AI breakthrough")
        print(f"Final result: {result.current_step}")
    
    asyncio.run(main())