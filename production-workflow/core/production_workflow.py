import asyncio
import json
import os
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
from agents.scripting_agent import script_generation_tools
from agents.prompt_generation_agent import prompt_generation_tools
from agents.image_generation_agent import image_generation_tools
from agents.voice_generation_agent import voice_tools
from agents.broll_search_agent import broll_search_tools
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
    
    # Parallel generation phase (prompt, image, voice, broll)
    prompts_generated: Annotated[List[Dict], add] = field(default_factory=list)
    images_generated: Annotated[List[str], add] = field(default_factory=list)
    voice_files: Annotated[List[str], add] = field(default_factory=list)
    broll_assets: Dict[str, Any] = field(default_factory=dict)
    
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
        self.workflow.add_node("broll_search", self.broll_search_node)
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
        
        # Image generation and b-roll search follow prompt generation
        self.workflow.add_edge("prompt_generation", "image_generation")
        self.workflow.add_edge("prompt_generation", "broll_search")
        
        # Add a parallel sync node to wait for all three processes
        self.workflow.add_node("parallel_sync", self.parallel_sync_node)
        
        # All three parallel processes lead to parallel_sync
        self.workflow.add_edge("image_generation", "parallel_sync")
        self.workflow.add_edge("voice_generation", "parallel_sync")
        self.workflow.add_edge("broll_search", "parallel_sync")
        
        # Parallel sync leads to asset gathering
        self.workflow.add_edge("parallel_sync", "asset_gathering")
        
        # Asset gathering leads to Notion integration
        self.workflow.add_edge("asset_gathering", "notion_integration")
        
        # Notion integration leads to finalize
        self.workflow.add_edge("notion_integration", "finalize")
        
        # Finalize ends the workflow
        self.workflow.add_edge("finalize", END)
    
    async def prompt_generation_node(self, state: WorkflowState) -> WorkflowState:
        """Generate prompts for image generation (parallel node)"""
        try:
            print("Step 6a: Generating image prompts (parallel)")
            
            if not state.script_content:
                print("No script content available for prompt generation")
                return {
                    "prompts_generated": [],
                    "messages": [AIMessage(content="No script content available for prompt generation")]
                }
            
            prompt_tool = prompt_generation_tools[0]  # generate_prompts_from_script
            
            print(f"DEBUG - Script content length: {len(state.script_content)} characters")
            print(f"DEBUG - Script preview: {state.script_content[:200]}...")
            
            prompts_result = await prompt_tool.ainvoke({
                "script_content": state.script_content,
                "num_prompts": 5
            })
            
            print(f"DEBUG - Generated {len(prompts_result)} prompts")
            for i, prompt in enumerate(prompts_result[:3], 1):
                print(f"  {i}. {prompt.get('visual_description', 'No description')[:50]}...")
            
            if not prompts_result:
                print("No prompts generated from script")
                return {
                    "prompts_generated": [],
                    "messages": [AIMessage(content="Failed to generate prompts from script")]
                }
            
            generated_prompts = [
                {
                    "id": prompt["id"],
                    "prompt": prompt["visual_description"],
                    "type": "scene",
                    "style": prompt.get("mood_style", "dynamic, engaging"),
                    "timing": prompt.get("timing", f"Scene {prompt['scene_number']}")
                } for prompt in prompts_result
            ]
            
            print(f"Generated {len(generated_prompts)} prompts for image generation")
            
            return {
                "prompts_generated": generated_prompts,
                "messages": [AIMessage(content=f"Generated {len(generated_prompts)} LLM-powered image prompts from script content")]
            }
            
        except Exception as e:
            error_msg = f"Prompt generation failed: {str(e)}"
            print(f"{error_msg}")
            return {
                "errors": [error_msg],
                "prompts_generated": [],
                "messages": [AIMessage(content="LLM prompt generation failed")]
            }

    async def search_node(self, state: WorkflowState) -> WorkflowState:
        """Search for trending tech news using intelligent AI-powered search"""
        try:
            print(f"Step 1: Intelligent search for articles about '{state.topic}'")
            state.current_step = "search"
            
            search_tool = search_tools[0]  # search_tech_news
            search_query = state.topic or "latest trending tech news"
            search_results = await search_tool.ainvoke(search_query)
            
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
            print(f"{error_msg}")
            return {
                "current_step": "search",
                "errors": [error_msg],
                "messages": [AIMessage(content="Search failed")]
            }
    
    async def crawl_node(self, state: WorkflowState) -> WorkflowState:
        """Crawl the selected article"""
        try:
            print("Step 2: Crawling article content")
            state.current_step = "crawl"
            
            if not state.search_urls:
                raise Exception("No URLs available to crawl")
            
            crawl_tool = crawl_tools[0]  # crawl_article_content
            crawled_result = await crawl_tool.ainvoke(state.search_urls[0])
            
            if "```json" in crawled_result:
                json_start = crawled_result.find("```json") + 7
                json_end = crawled_result.find("```", json_start)
                json_str = crawled_result[json_start:json_end].strip()
                try:
                    article_data = json.loads(json_str)
                except json.JSONDecodeError:
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
            print(f"{error_msg}")
            return {
                "current_step": "crawl",
                "errors": [error_msg],
                "messages": [AIMessage(content="Crawling failed")]
            }
    
    async def store_article_node(self, state: WorkflowState) -> WorkflowState:
        """Store article in Supabase"""
        try:
            print("Step 3: Storing article in Supabase")
            state.current_step = "store_article"
            
            if not state.article_data:
                raise Exception("No article data available to store")
            
            storage_tool = supabase_tools_sync_wrapped[0]  # store_article_content_sync_wrapped
            
            print(f"DEBUG - Article data type: {type(state.article_data)}")
            print(f"DEBUG - Article data keys: {list(state.article_data.keys()) if isinstance(state.article_data, dict) else 'Not a dict'}")
            
            storage_result = await asyncio.to_thread(storage_tool.invoke, {"article_data": state.article_data})
            
            article_id = ""
            if "Record ID:" in storage_result:
                id_match = re.search(r"Record ID:\s*([a-zA-Z0-9-]+)", storage_result)
                if id_match:
                    article_id = id_match.group(1)
            elif "ID:" in storage_result:
                id_match = re.search(r"ID:\s*([a-zA-Z0-9-]+)", storage_result)
                if id_match:
                    article_id = id_match.group(1)
            
            print(f"DEBUG - Extracted article ID: '{article_id}'")
            
            return {
                "storage_result": storage_result,
                "article_id": article_id,
                "current_step": "store_article",
                "messages": [AIMessage(content=f"Article stored successfully with ID: {article_id}")]
            }
            
        except Exception as e:
            error_msg = f"Article storage failed: {str(e)}"
            print(f"{error_msg}")
            return {
                "current_step": "store_article",
                "errors": [error_msg],
                "messages": [AIMessage(content="Article storage failed")]
            }
    
    async def generate_script_node(self, state: WorkflowState) -> WorkflowState:
        """Generate script content from article data"""
        try:
            print("Step 4: Generating script content")
            
            if not state.article_data:
                return {
                    "errors": ["No article data available for script generation"],
                    "current_step": "script_failed",
                    "messages": [AIMessage(content="No article data for script generation")],
                }
            
            article_data = state.article_data
            article_title = article_data.get("title", "") if isinstance(article_data, dict) else ""
            article_content = article_data.get("content", "") if isinstance(article_data, dict) else ""
            
            print(f"Generating script from:")
            print(f"  - Title: {article_title[:100]}...")
            print(f"  - Content: {len(article_content)} characters")
            
            if not article_content and not article_title:
                return {
                    "errors": ["Article data exists but contains no title or content"],
                    "current_step": "script_failed",
                    "messages": [AIMessage(content="Article data is empty")],
                }
            
            script_tool = script_generation_tools[0]  # generate_youtube_script
            script_result = await script_tool.ainvoke({
                "article_content": article_content,
                "article_title": article_title,
                "platform": "youtube",
                "duration": 60
            })
            
            print(f"Script generation result: {script_result[:200]}...")
            
            script_content = ""
            script_hook = ""
            
            if "**FULL SCRIPT:**" in script_result:
                script_parts = script_result.split("**FULL SCRIPT:**")
                if len(script_parts) > 1:
                    script_content = script_parts[1].split("**📊 Script Metadata:**")[0].strip()
            
            if "**HOOK**:" in script_result:
                hook_lines = script_result.split("**HOOK**:")
                if len(hook_lines) > 1:
                    hook_part = hook_lines[1].split("\n")[0].strip()
                    script_hook = hook_part
            
            if not script_content:
                script_content = script_result
            
            print(f"Extracted script: {len(script_content)} characters")
            print(f"Extracted hook: {script_hook[:50]}...")
            
            return {
                "script_content": script_content,
                "script_hook": script_hook,
                "current_step": "script_complete",
                "messages": [AIMessage(content=f"Generated script: {len(script_content)} characters")],
            }
            
        except Exception as e:
            error_msg = f"Script generation failed: {str(e)}"
            print(f"{error_msg}")
            return {
                "errors": [error_msg],
                "current_step": "script_failed",
                "messages": [AIMessage(content="Script generation failed")],
            }
    
    async def store_script_node(self, state: WorkflowState) -> WorkflowState:
        """Store generated script in Supabase"""
        try:
            print("Step 5: Storing script in Supabase")
            state.current_step = "store_script"
            
            if not state.script_content:
                raise Exception("Missing script content for storage")
            
            article_id = state.article_id if state.article_id else "unknown"
            print(f"DEBUG - Using article ID for script: '{article_id}'")
            
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
            
            script_storage_tool = supabase_tools_sync_wrapped[6]  # store_script_content
            script_storage_result = await asyncio.to_thread(script_storage_tool.invoke, {"script_data": script_data})
            
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
            print(f"{error_msg}")
            return {
                "current_step": "store_script",
                "errors": [error_msg],
                "messages": [AIMessage(content="Script storage failed")]
            }
    
    async def image_generation_node(self, state: WorkflowState) -> WorkflowState:
        """Generate images from prompts (parallel node)"""
        try:
            print("Step 6b: Generating images (parallel)")
            
            if not state.prompts_generated:
                print("No prompts available, skipping image generation")
                return {
                    "images_generated": [],
                    "messages": [AIMessage(content="No prompts available, skipped image generation")]
                }
            
            image_tool = image_generation_tools[0]  # generate_image_flux
            
            generated_images = []
            for prompt_data in state.prompts_generated[:3]:  # Limit to 3 images
                try:
                    image_result = await image_tool.ainvoke({"prompt": prompt_data["prompt"]})
                    result_dict = json.loads(image_result)
                    if result_dict.get("status") == "success":
                        generated_images.append(result_dict["file_path"])  # Store file path directly
                    else:
                        print(f"Image generation failed for prompt: {prompt_data['prompt'][:50]}...")
                except Exception as img_error:
                    print(f"Image generation failed for prompt: {img_error}")
            
            return {
                "images_generated": generated_images,
                "messages": [AIMessage(content=f"Generated {len(generated_images)} images")]
            }
            
        except Exception as e:
            error_msg = f"Image generation failed: {str(e)}"
            print(f"{error_msg}")
            return {
                "errors": [error_msg],
                "images_generated": [],
                "messages": [AIMessage(content="Image generation failed")]
            }
    
    async def parallel_sync_node(self, state: WorkflowState) -> WorkflowState:
        """Synchronization point for parallel processes before asset gathering"""
        try:
            print("Step 7: Synchronizing parallel generation results")
            
            # Check what we have
            summary = []
            if state.images_generated:
                summary.append(f"{len(state.images_generated)} images generated")
            if state.voice_files:
                summary.append(f"{len(state.voice_files)} voice files created")
            if state.broll_assets:
                broll_images = len(state.broll_assets.get('images', []))
                broll_videos = len(state.broll_assets.get('videos', []))
                summary.append(f"{broll_images} b-roll images and {broll_videos} videos found")
            
            return {
                "messages": [AIMessage(content=f"Parallel generation complete: {', '.join(summary)}")]
            }
            
        except Exception as e:
            error_msg = f"Parallel sync failed: {str(e)}"
            print(f"{error_msg}")
            return {
                "errors": [error_msg],
                "messages": [AIMessage(content="Parallel synchronization failed")]
            }
    
    async def broll_search_node(self, state: WorkflowState) -> WorkflowState:
        """Search for b-roll content based on generated prompts (parallel node)"""
        try:
            print("Step 6d: Searching for b-roll content (parallel)")
            
            if not state.prompts_generated:
                print("No prompts available, skipping b-roll search")
                return {
                    "broll_assets": {},
                    "messages": [AIMessage(content="No prompts available, skipped b-roll search")]
                }
            
            broll_tool = broll_search_tools[0]  # search_broll_from_prompts
            
            # Use the same prompts that were used for image generation
            broll_result = await broll_tool.ainvoke({"prompts_data": state.prompts_generated})
            
            try:
                broll_data = json.loads(broll_result)
                print(f"Found {broll_data.get('metadata', {}).get('images_found', 0)} images and {broll_data.get('metadata', {}).get('videos_found', 0)} videos")
                
                return {
                    "broll_assets": broll_data,
                    "messages": [AIMessage(content=f"Found {len(broll_data.get('images', []))} b-roll images and {len(broll_data.get('videos', []))} videos")]
                }
            except json.JSONDecodeError:
                print(f"Failed to parse b-roll results: {broll_result[:200]}...")
                return {
                    "broll_assets": {},
                    "errors": ["Failed to parse b-roll search results"],
                    "messages": [AIMessage(content="B-roll search failed to parse results")]
                }
                
        except Exception as e:
            error_msg = f"B-roll search failed: {str(e)}"
            print(f"{error_msg}")
            return {
                "errors": [error_msg],
                "broll_assets": {},
                "messages": [AIMessage(content="B-roll search failed")]
            }
    
    async def voice_generation_node(self, state: WorkflowState) -> WorkflowState:
        """Generate voiceover from script (parallel node)"""
        try:
            print("Step 6c: Generating voiceover (parallel)")
        
            if not state.script_content:
                print("No script content available, skipping voice generation")
                return {
                    "voice_files": [],
                    "messages": [AIMessage(content="No script content available, skipped voice generation")]
                }
        
            voice_tool = voice_tools[0]  # generate_voiceover
        
            clean_script = state.script_content
            for marker in ["**HOOK:**", "**ACT 1", "**ACT 2", "**ACT 3", "**CONCLUSION", "**"]:
                clean_script = clean_script.replace(marker, "")
            for header in [
                "[0-5s: HOOK]", "[5-15s: INTRODUCTION]", 
                "[15-45s: MAIN CONTENT]", "[45-60s: CONCLUSION/CTA]"
            ]:
                clean_script = clean_script.replace(header, "")
            clean_script = re.sub(r'\n\s*\n', '\n', clean_script).strip()
        
            voice_input = {
                "script_text": clean_script[:1000],
                "voice_name": "audio",  # Use the audio.wav sample for voice cloning
                "emotion": "neutral"
            }
        
            voice_result = await voice_tool.ainvoke(voice_input)
            
            # Extract file path from voice generation result
            voice_files = []
            if voice_result:
                # Try to extract actual file path from the result
                file_path = None
                for line in voice_result.split('\n'):
                    if "Local Path:" in line:
                        file_path = line.split("Local Path:")[1].strip()
                        # Remove markdown formatting
                        file_path = file_path.lstrip('*').strip()
                        break
                
                if file_path and os.path.exists(file_path):
                    voice_files = [file_path]
                    print(f"DEBUG: Extracted voice file path: {file_path}")
                else:
                    # Fallback: store the full result for parsing later
                    voice_files = [voice_result]
                    print(f"DEBUG: Voice file path not found, storing result for later parsing")
        
            return {
                "voice_files": voice_files,
                "messages": [AIMessage(content=f"Generated {len(voice_files)} voice files")]
            }
        
        except Exception as e:
            error_msg = f"Voice generation failed: {str(e)}"
            print(f"{error_msg}")
            return {
                "errors": [error_msg],
                "voice_files": [],
                "messages": [AIMessage(content="Voice generation failed")]
            }
    
    async def asset_gathering_node(self, state: WorkflowState) -> WorkflowState:
        """Organize generated assets in Google Drive project folder (sequential node)"""
        try:
            print("Step 8: Gathering and organizing assets in Google Drive")
            state.current_step = "asset_gathering"
            
            script_data = {
                'title': state.article_data.get('title', state.topic),
                'script_content': state.script_content,
                'script_id': state.script_id,
                'article_id': state.article_id,
                'hook': state.script_hook,
                'visual_suggestions': state.visual_suggestions
            }
            
            folder_tool = asset_gathering_tools[0]  # create_project_folder_structure
            folder_result = await folder_tool.ainvoke({"script_data": script_data})
            
            project_folder_path = ""
            if "Folder Path:" in folder_result:
                folder_path_line = [line for line in folder_result.split('\n') if "Folder Path:" in line][0]
                project_folder_path = folder_path_line.split("Folder Path:")[1].strip()
            
            asset_result = ""
            if project_folder_path:
                organize_tool = asset_gathering_tools[1]  # organize_generated_assets
                asset_result = await organize_tool.ainvoke({
                    'project_folder_path': project_folder_path,
                    'assets_data': {
                        'images': state.images_generated,
                        'voice_files': state.voice_files,
                        'script_content': state.script_content,
                        'prompts': state.prompts_generated,
                        'broll': state.broll_assets
                    }
                })
                
                # Also organize b-roll metadata
                if state.broll_assets:
                    broll_organize_tool = broll_search_tools[1]  # organize_broll_assets
                    broll_result = await broll_organize_tool.ainvoke({
                        'broll_data': state.broll_assets,
                        'project_folder_path': project_folder_path
                    })
                    print(f"B-roll organization: {broll_result[:200]}...")
            
            return {
                "project_folder_path": project_folder_path,
                "asset_organization_result": asset_result or folder_result,
                "current_step": "asset_gathering",
                "messages": [AIMessage(content=f"Assets organized in: {project_folder_path}")]
            }
            
        except Exception as e:
            error_msg = f"Asset gathering failed: {str(e)}"
            print(f"{error_msg}")
            return {
                "current_step": "asset_gathering",
                "errors": [error_msg],
                "messages": [AIMessage(content="Asset gathering failed")]
            }
    
    async def notion_integration_node(self, state: WorkflowState) -> WorkflowState:
        """Create Notion project and set up monitoring (sequential node)"""
        try:
            print("Step 9: Setting up Notion project tracking")
            state.current_step = "notion_integration"
            
            notion_script_data = {
                'title': state.article_data.get('title', state.topic),
                'script_content': state.script_content,
                'script_id': state.script_id,
                'article_id': state.article_id,
                'hook': state.script_hook,
                'visual_suggestions': state.visual_suggestions,
                'folder_path': state.project_folder_path,
                'project_id': state.script_id or state.article_id or "unknown",
                'channels': ['youtube']
            }
            
            notion_tool = notion_tools[0]  # create_notion_project_row
            notion_result = await notion_tool.ainvoke({"script_data": notion_script_data})
            
            notion_project_id = ""
            if "Page ID:" in notion_result:
                id_line = [line for line in notion_result.split('\n') if "Page ID:" in line][0]
                notion_project_id = id_line.split("Page ID:")[1].strip()
            
            if state.project_folder_path:
                monitor_tool = notion_tools[2]  # monitor_gdrive_folder
                monitor_result = await monitor_tool.ainvoke({"folder_path": state.project_folder_path})
                print(f"Monitoring setup: {monitor_result[:100]}...")
            
            return {
                "notion_project_id": notion_project_id,
                "notion_status": "Assets Ready",
                "current_step": "notion_integration",
                "messages": [AIMessage(content=f"Notion project created with ID: {notion_project_id}")]
            }
            
        except Exception as e:
            error_msg = f"Notion integration failed: {str(e)}"
            print(f"{error_msg}")
            return {
                "current_step": "notion_integration",
                "errors": [error_msg],
                "messages": [AIMessage(content="Notion integration failed")]
            }
    
    async def finalize_node(self, state: WorkflowState) -> WorkflowState:
        """Finalize the workflow and compile results"""
        try:
            print("Step 10: Finalizing workflow")
            
            final_summary = f"""
PRODUCTION WORKFLOW COMPLETED

Summary:
- Topic: {state.topic or state.user_query or 'Latest tech news'}
- Article stored: {state.article_id or 'No ID extracted'}
- Script generated: {state.script_id or 'Not stored'}
- Images created: {len(state.images_generated)}
- Voice files: {len(state.voice_files)}
- Prompts generated: {len(state.prompts_generated)}

Asset Organization:
- Project folder: {state.project_folder_path or 'Not created'}
- Asset status: {'Organized' if state.asset_organization_result else 'Failed'}

Notion Integration:
- Project ID: {state.notion_project_id or 'Not created'}
- Status: {state.notion_status or 'Not set'}

Script Preview:
{(state.script_hook[:100] + '...') if state.script_hook else 'No hook extracted'}

Assets Generated:
- Article content: Stored in Supabase ({len(state.article_data.get('content', '')) if state.article_data else 0} chars)
- Script content: Generated ({len(state.script_content)} chars)
- Image prompts: {len(state.prompts_generated)} prompts
- Generated images: {len(state.images_generated)} images
- B-roll images: {len(state.broll_assets.get('images', []))} images
- B-roll videos: {len(state.broll_assets.get('videos', []))} videos
- Voice files: {len(state.voice_files)} files
- Google Drive: Project folder created with organized structure
- Notion workspace: Project tracking row created

Google Drive Structure:
{state.project_folder_path}/
  ├── generated_images/
  ├── voiceover/
  ├── scripts/
  ├── broll/ (contains metadata.json with Pexels links)
  ├── final_draft/ (awaiting editor upload)
  └── resources/

Next Steps:
1. Editor uploads final video to: {state.project_folder_path}/final_draft/
2. Video upload will trigger Notion status update to "Video Ready"
3. Project will be ready for final publishing

Errors encountered: {len(state.errors)}
{chr(10).join(state.errors) if state.errors else 'None'}

Full Script Content:
{state.script_content[:500] + '...' if len(state.script_content) > 500 else state.script_content}

Workflow Complete - Ready for Editor!
"""
            
            return {
                "current_step": "complete",
                "messages": [AIMessage(content=final_summary)]
            }
            
        except Exception as e:
            error_msg = f"Finalization failed: {str(e)}"
            print(f"{error_msg}")
            return {
                "current_step": "complete",
                "errors": [error_msg],
                "messages": [AIMessage(content="Workflow finalization failed")]
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
    initial_state = WorkflowState(
        user_query=user_query,
        topic=topic,
        current_step="search"
    )
    
    print(f"Starting production workflow for topic: '{topic}'")
    print("=" * 60)
    
    try:
        final_state = await production_workflow.ainvoke(initial_state)
        
        print("=" * 60)
        print("Workflow completed successfully!")
        
        return final_state
        
    except Exception as e:
        print(f"Workflow failed: {str(e)}")
        initial_state.errors.append(f"Workflow execution failed: {str(e)}")
        return initial_state

if __name__ == "__main__":
    async def main():
        result = await run_production_workflow("latest AI breakthrough")
        print(f"Final result: {result.current_step}")
    
    asyncio.run(main())