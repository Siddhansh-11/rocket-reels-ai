import os
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from dotenv import load_dotenv

from workflow_state import ContentState, PhaseOutput, PhaseStatus, ReviewStatus
from mcp_client import MCPClient
from human_review import HumanReviewInterface
from orchestration_agent import run_orchestration_agent
from langchain_community.chat_models import ChatLiteLLM

# Import crawl and storage functions statically to avoid blocking I/O
try:
    from enhanced_crawl_agent import enhanced_crawl_with_media_ocr
    from enhanced_storage_agent import store_enhanced_article, format_storage_result
    CRAWL_IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Could not import crawl/storage modules: {e}")
    CRAWL_IMPORTS_AVAILABLE = False

# Load environment
load_dotenv('.env')

# Initialize components
mcp_client = MCPClient()
review_interface = HumanReviewInterface()

# Initialize DeepSeek model for agent functionality
deepseek_model = ChatLiteLLM(
    model="deepseek/deepseek-chat",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    max_tokens=4000,
    temperature=0.1
)

# Phase definitions
WORKFLOW_PHASES = [
    "input_processing",
    "search_content_ideas",
    "research", 
    "planning",
    "script_writing",
    "visual_generation",
    "assembly",
    "export",
    "distribution",
    "analytics"
]

async def process_input(state: ContentState) -> ContentState:
    """Process initial input using Input MCP server"""
    try:
        # Call appropriate MCP tool based on input type
        if state.input_type == "youtube":
            result = await mcp_client.call_tool(
                "input-processor",
                "process_youtube",
                {"url": state.input_data["url"]}
            )
        elif state.input_type == "file":
            result = await mcp_client.call_tool(
                "input-processor", 
                "process_file",
                {
                    "file_path": state.input_data["file_path"],
                    "file_type": state.input_data.get("file_type", "auto")
                }
            )
        else:  # prompt
            result = await mcp_client.call_tool(
                "input-processor",
                "process_prompt",
                {
                    "prompt": state.input_data["prompt"],
                    "style": state.input_data.get("style", "educational")
                }
            )
        
        output = PhaseOutput(
            phase_name="input_processing",
            data=result,
            status=PhaseStatus.COMPLETED,
            cost_usd=0.01  # Minimal cost for processing
        )
        state.add_phase_output("input_processing", output)
        state.current_phase = "search_content_ideas"
        
    except Exception as e:
        output = PhaseOutput(
            phase_name="input_processing",
            data={},
            status=PhaseStatus.FAILED,
            error=str(e)
        )
        state.add_phase_output("input_processing", output)
        state.errors.append({"phase": "input_processing", "error": str(e)})
    
    return state

async def crawl_and_store_agent(state: ContentState) -> ContentState:
    """Crawl article and store in Supabase using enhanced crawl with Mistral OCR"""
    try:
        # Check if imports are available
        if not CRAWL_IMPORTS_AVAILABLE:
            error_msg = "❌ Crawl and storage modules not available. Please check imports."
            state.messages.append(AIMessage(content=error_msg))
            return state
        
        # Update phase to crawl mode
        state.current_phase = "crawl_and_store"
        
        # Get the last human message to extract URL
        last_human_message = None
        if state.messages:
            for msg in reversed(state.messages):
                if (hasattr(msg, 'type') and msg.type == 'human') or msg.__class__.__name__ == 'HumanMessage':
                    last_human_message = msg.content
                    break
        
        if not last_human_message:
            error_msg = "No URL found to crawl. Please provide a URL to crawl."
            state.messages.append(AIMessage(content=error_msg))
            return state
        
        # Extract URL from message
        import re
        url = None
        
        # Check if it's an article number selection
        article_match = re.search(r'\b(?:article\s*)?([1-8])\b', last_human_message.lower())
        if article_match:
            article_num = int(article_match.group(1))
            # Find the search results in previous messages
            for msg in reversed(state.messages):
                if msg.__class__.__name__ == 'SystemMessage' and 'ARTICLE URLS FOUND:' in msg.content:
                    # Extract URL by article number
                    url_lines = msg.content.split('\n')
                    for line in url_lines:
                        if line.strip().startswith(f"{article_num}."):
                            url_match = re.search(r'https?://[^\s]+', line)
                            if url_match:
                                url = url_match.group(0).rstrip('.,;)')
                                break
                    break
                    
                # Also check AIMessage for search results
                if msg.__class__.__name__ == 'AIMessage' and 'ARTICLE URLS FOUND:' in msg.content:
                    # Extract URL by article number
                    url_lines = msg.content.split('\n')
                    for line in url_lines:
                        if line.strip().startswith(f"{article_num}."):
                            url_match = re.search(r'https?://[^\s]+', line)
                            if url_match:
                                url = url_match.group(0).rstrip('.,;)')
                                break
                    break
        
        # If no article number, try direct URL extraction
        if not url:
            url_pattern = r'https?://[^\s<>"\'{|}|\\^`\[\]]+'
            urls = re.findall(url_pattern, last_human_message)
            if urls:
                url = urls[0]  # Use first URL found
        
        if not url:
            error_msg = f"No valid URL found. Please specify an article number (1-8) or provide a direct URL."
            state.messages.append(AIMessage(content=error_msg))
            return state
        
        # Step 1: Enhanced crawl with Mistral OCR
        print(f"🕷️ Enhanced crawling with Mistral OCR: {url}")
        article_data = await enhanced_crawl_with_media_ocr(url)
        
        # Step 2: Store in Supabase using enhanced storage
        print(f"🗄️ Storing enhanced article in Supabase...")
        storage_result_data = await store_enhanced_article(article_data)
        storage_result = format_storage_result(storage_result_data)
        
        # Format comprehensive results
        ocr_summary = ""
        if article_data.get("ocr_results"):
            ocr_summary = f"**🔍 OCR Results:** Processed {len(article_data['ocr_results'])} images with text extraction"
        
        media_insights = ""
        if article_data.get("media_insights"):
            media_insights = f"**👁️ Media Insights:** {'; '.join(article_data['media_insights'][:3])}"
        
        combined_result = f"""✅ **ENHANCED CRAWL AND STORAGE WITH MISTRAL OCR COMPLETED**

**📰 Article Details:**
- Title: {article_data.get('title', 'No title')[:60]}...
- Domain: {article_data.get('domain', 'Unknown')}
- Word Count: {article_data.get('word_count', 0)}
- Method: {article_data.get('method', 'enhanced_crawl')}

**📄 Content Preview:**
{article_data.get('content', 'No content')[:300]}...

**🎯 Key Points:**
{chr(10).join([f"• {point}" for point in article_data.get('key_points', [])[:3]])}

**📷 Media Processing:**
- Images Found: {len(article_data.get('image_urls', []))}
{ocr_summary}
{media_insights}

**📝 Extracted Text from Images:**
{article_data.get('extracted_text_from_images', 'No text extracted from images')[:200]}...

---

{storage_result}

**🔗 Article URL:** {url}
**🤖 Enhanced with Mistral AI OCR and content analysis**
**📊 Ready for script generation and content creation!**"""
        
        # Add results to messages for chat visibility
        state.messages.append(AIMessage(content=combined_result))
        
        # Add phase output for tracking
        output = PhaseOutput(
            phase_name="crawl_and_store",
            data={
                "url": url,
                "article_data": article_data,
                "storage_result": storage_result,
                "enhanced_features": {
                    "ocr_enabled": bool(article_data.get("ocr_results")),
                    "images_processed": len(article_data.get("image_urls", [])),
                    "text_extracted": bool(article_data.get("extracted_text_from_images")),
                    "mistral_analysis": bool(article_data.get("media_insights"))
                }
            },
            status=PhaseStatus.COMPLETED,
            cost_usd=0.08  # Higher cost due to Mistral OCR processing
        )
        
        state.add_phase_output("crawl_and_store", output)
        
        return state
        
    except Exception as e:
        error_message = f"❌ Error in enhanced crawl and storage: {str(e)}"
        state.messages.append(AIMessage(content=error_message))
        
        output = PhaseOutput(
            phase_name="crawl_and_store",
            data={},
            status=PhaseStatus.FAILED,
            error=str(e)
        )
        state.add_phase_output("crawl_and_store", output)
        
        return state

async def research_content(state: ContentState) -> ContentState:
    """Research content using Research MCP server"""
    try:
        input_data = state.input_processing.data
        
        result = await mcp_client.call_tool(
            "research",
            "research_topic",
            {
                "input_data": input_data,
                "depth": "standard"
            }
        )
        
        # Also find trending angles
        angles = await mcp_client.call_tool(
            "research",
            "find_trending_angle",
            {
                "topic": input_data.get("topic", input_data.get("title", "")),
                "target_audience": "general"
            }
        )
        
        combined_result = {
            "research": result,
            "trending_angles": angles
        }
        
        output = PhaseOutput(
            phase_name="research",
            data=combined_result,
            status=PhaseStatus.COMPLETED,
            cost_usd=0.05  # API costs
        )
        state.add_phase_output("research", output)
        state.current_phase = "planning"
        
    except Exception as e:
        output = PhaseOutput(
            phase_name="research",
            data={},
            status=PhaseStatus.FAILED,
            error=str(e)
        )
        state.add_phase_output("research", output)
        state.errors.append({"phase": "research", "error": str(e)})
    
    return state

async def plan_content(state: ContentState) -> ContentState:
    """Create content plan using Planner MCP server"""
    try:
        research_data = state.research.data
        
        # Create content plan
        plan = await mcp_client.call_tool(
            "content-planner",
            "create_content_plan",
            {
                "research": research_data["research"],
                "content_type": "educational",
                "duration": 45
            }
        )
        
        # Generate visual suggestions
        visuals = await mcp_client.call_tool(
            "content-planner",
            "generate_visual_suggestions",
            {"content_plan": plan}
        )
        
        combined_result = {
            "content_plan": plan,
            "visual_suggestions": visuals
        }
        
        output = PhaseOutput(
            phase_name="planning",
            data=combined_result,
            status=PhaseStatus.COMPLETED,
            cost_usd=0.03
        )
        state.add_phase_output("planning", output)
        state.current_phase = "script_writing"
        
    except Exception as e:
        output = PhaseOutput(
            phase_name="planning",
            data={},
            status=PhaseStatus.FAILED,
            error=str(e)
        )
        state.add_phase_output("planning", output)
        state.errors.append({"phase": "planning", "error": str(e)})
    
    return state

async def write_script(state: ContentState) -> ContentState:
    """Generate script using Script MCP server"""
    try:
        plan_data = state.planning.data["content_plan"]
        
        # Generate script
        script = await mcp_client.call_tool(
            "script-writer",
            "generate_script",
            {
                "plan": plan_data,
                "style": "energetic",
                "template": "educational"
            }
        )
        
        # Validate script
        validation = await mcp_client.call_tool(
            "script-writer",
            "validate_script",
            {"script": script["script"]}
        )
        
        script["validation"] = validation
        
        output = PhaseOutput(
            phase_name="script_writing",
            data=script,
            status=PhaseStatus.COMPLETED,
            cost_usd=0.10  # Higher cost for creative generation
        )
        state.add_phase_output("script_writing", output)
        state.current_phase = "visual_generation"
        
    except Exception as e:
        output = PhaseOutput(
            phase_name="script_writing",
            data={},
            status=PhaseStatus.FAILED,
            error=str(e)
        )
        state.add_phase_output("script_writing", output)
        state.errors.append({"phase": "script_writing", "error": str(e)})
    
    return state

async def search_content_ideas(state: ContentState) -> ContentState:
    """Search for trending content ideas using the orchestration agent"""
    try:
        # Determine search query based on input
        if state.input_type == "prompt":
            search_query = f"trending content ideas about {state.input_data.get('prompt', 'general topics')}"
        elif state.input_type == "youtube":
            search_query = "trending YouTube content ideas"
        else:
            search_query = "trending content ideas"
        
        # Use the orchestration agent to search
        search_result = await run_orchestration_agent(f"Search for: {search_query}")
        
        output = PhaseOutput(
            phase_name="search_content_ideas",
            data={"search_results": search_result, "query": search_query},
            status=PhaseStatus.COMPLETED,
            cost_usd=0.02  # Minimal cost for search
        )
        state.add_phase_output("search_content_ideas", output)
        state.current_phase = "research"
        
        # Add search results to messages for chat context
        state.messages.append(HumanMessage(content=f"Search query: {search_query}"))
        state.messages.append(AIMessage(content=f"Search results: {search_result}"))
        
    except Exception as e:
        output = PhaseOutput(
            phase_name="search_content_ideas",
            data={},
            status=PhaseStatus.FAILED,
            error=str(e)
        )
        state.add_phase_output("search_content_ideas", output)
        state.errors.append({"phase": "search_content_ideas", "error": str(e)})
    
    return state

async def search_agent(state: ContentState) -> ContentState:
    """Search agent that handles news and tech queries"""
    try:
        # Import the search function from search_agent
        from search_agent import search_tech_news
        
        # Update phase to search mode
        state.current_phase = "search"
        
        # Get the last human message
        last_human_message = None
        if state.messages:
            for msg in reversed(state.messages):
                # Check both the class name and type attribute
                if (hasattr(msg, 'type') and msg.type == 'human') or msg.__class__.__name__ == 'HumanMessage':
                    last_human_message = msg.content
                    break
        
        if not last_human_message:
            # No message found
            error_msg = f"No human message found to process. Found {len(state.messages)} messages total."
            state.messages.append(AIMessage(content=error_msg))
            return state
        
        # Use the real search function
        search_result = await search_tech_news(last_human_message)
        
        # Add the results to messages for chat visibility
        # Use AIMessage for assistant responses in chat interface
        state.messages.append(AIMessage(content=search_result["results"]))
        
        # Add phase output for tracking
        output = PhaseOutput(
            phase_name="search",
            data={
                "query": last_human_message, 
                "results": search_result["results"],
                "is_mock": search_result.get("is_mock", False)
            },
            status=PhaseStatus.COMPLETED,
            cost_usd=search_result.get("cost", 0.02)
        )
        
        state.add_phase_output("search", output)
        
        return state
        
    except Exception as e:
        error_message = f"❌ Error in search agent: {str(e)}"
        state.messages.append(AIMessage(content=error_message))
        
        # Add error phase output
        output = PhaseOutput(
            phase_name="search",
            data={},
            status=PhaseStatus.FAILED,
            error=str(e)
        )
        state.add_phase_output("search", output)
        
        return state

async def generate_visuals(state: ContentState) -> ContentState:
    """Generate visuals using Visual MCP server"""
    try:
        script_data = state.script_writing.data
        visual_plan = state.planning.data.get("visual_suggestions", {})
        
        # Generate visuals
        visuals = await mcp_client.call_tool(
            "visual-generator",
            "generate_visuals",
            {
                "script": script_data,
                "visual_plan": visual_plan
            }
        )
        
        # Create thumbnail
        thumbnail = await mcp_client.call_tool(
            "visual-generator",
            "create_thumbnail",
            {
                "title": script_data.get("hook", "Amazing Content"),
                "style": "bold"
            }
        )
        
        combined_result = {
            "visuals": visuals,
            "thumbnail": thumbnail
        }
        
        output = PhaseOutput(
            phase_name="visual_generation",
            data=combined_result,
            status=PhaseStatus.COMPLETED,
            cost_usd=0.20  # Placeholder cost - would be higher with real generation
        )
        state.add_phase_output("visual_generation", output)
        state.current_phase = "assembly"
        
    except Exception as e:
        output = PhaseOutput(
            phase_name="visual_generation",
            data={},
            status=PhaseStatus.FAILED,
            error=str(e)
        )
        state.add_phase_output("visual_generation", output)
        state.errors.append({"phase": "visual_generation", "error": str(e)})
    
    return state

async def human_review(state: ContentState) -> ContentState:
    """Human review checkpoint"""
    # Mark current phase as awaiting review
    current_output = getattr(state, state.current_phase.replace("-", "_"))
    if current_output:
        current_output.status = PhaseStatus.AWAITING_REVIEW
    
    # Get review from human
    review = await review_interface.get_review(state)
    state.add_review(state.current_phase, review)
    
    # Handle review decision
    if review.status == ReviewStatus.APPROVED:
        # Move to next phase
        current_index = WORKFLOW_PHASES.index(state.current_phase)
        if current_index < len(WORKFLOW_PHASES) - 1:
            state.current_phase = WORKFLOW_PHASES[current_index + 1]
    elif review.status == ReviewStatus.REVISION_REQUESTED:
        # Stay in current phase for revision
        state.retry_count += 1
    else:  # REJECTED
        # Mark workflow as failed
        if current_output:
            current_output.status = PhaseStatus.FAILED
    
    return state

async def human_select_article(state: ContentState) -> ContentState:
    """Wait for human to select an article from search results"""
    # This node simply passes through - the actual selection happens
    # when the human sends their next message
    return state

def should_continue_from_search(state: ContentState) -> str:
    """Determine if we should wait for article selection after search"""
    # Check if the last search had results with URLs
    if state.search and state.search.data.get("results"):
        results = state.search.data["results"]
        if "ARTICLE URLS FOUND:" in results and "Which article would you like me to crawl" in results:
            return "human_select_article"
    return "end"

def should_continue_from_start(state: ContentState) -> str:
    """Determine next step from start"""
    # Check if this is a chat message
    if state.messages and len(state.messages) > 0:
        last_message = state.messages[-1].content.lower().strip()
        
        # Check if previous message contains search results with article URLs
        has_article_urls = False
        if len(state.messages) >= 2:
            prev_message = state.messages[-2].content
            has_article_urls = "ARTICLE URLS FOUND:" in prev_message
        
        # Check for direct article number selection (when previous message had URLs)
        import re
        article_match = re.search(r'^([1-8])$', last_message)  # Just a number by itself
        if article_match and has_article_urls:
            return "crawl_agent"
        
        # Check for crawl commands or article selection with keywords
        if any(keyword in last_message for keyword in ['crawl', 'scrape', 'extract', 'article']):
            # Check if it's selecting an article number
            article_match = re.search(r'\b(?:article\s*)?([1-8])\b', last_message)
            if article_match or 'http' in last_message:
                return "crawl_agent"
        
        # Check for direct URL
        if 'http' in last_message:
            return "crawl_agent"
        
        # Route to search agent for other chat messages
        return "search_agent"
    
    # For content creation workflows (prompt, youtube, file)
    return "process_input"

def should_continue_from_chat(state: ContentState) -> str:
    """Determine next step from chat agent"""
    # Check if we should exit the chat
    if state.messages:
        last_message = state.messages[-1].content.lower()
        exit_keywords = ['exit', 'quit', 'done', 'stop', 'bye', 'goodbye']
        if any(keyword in last_message for keyword in exit_keywords):
            return "end"
    
    # Check message count to prevent infinite loops
    if len(state.messages) > 50:  # Safety limit
        return "end"
    
    # Continue chatting
    return "chat_agent"

# Build the workflow graph
def create_workflow() -> StateGraph:
    """Create the LangGraph workflow"""
    workflow = StateGraph(ContentState)
    
    # Add nodes for each phase
    workflow.add_node("process_input", process_input)
    workflow.add_node("search_ideas", search_content_ideas)
    workflow.add_node("research_content", research_content)
    workflow.add_node("plan_content", plan_content)
    workflow.add_node("write_script", write_script)
    workflow.add_node("generate_visuals", generate_visuals)
    
    # Add search agent
    workflow.add_node("search_agent", search_agent)
    
    # Add crawl and storage agent
    workflow.add_node("crawl_agent", crawl_and_store_agent)
    
    # Add human review nodes
    for phase in ["input_processing", "search_content_ideas", "research", "planning", "script_writing", "visual_generation"]:
        workflow.add_node(f"human_review_{phase}", human_review)
    
    # Add human-in-the-loop node for search results
    workflow.add_node("human_select_article", human_select_article)
    
    # Add edges - conditional entry point
    workflow.add_conditional_edges(
        "__start__",
        should_continue_from_start,
        {
            "process_input": "process_input",
            "search_agent": "search_agent",
            "crawl_agent": "crawl_agent",
        }
    )
    
    # Connect phases to their review nodes
    workflow.add_edge("process_input", "human_review_input_processing")
    workflow.add_edge("search_ideas", "human_review_search_content_ideas")
    workflow.add_edge("research_content", "human_review_research")
    workflow.add_edge("plan_content", "human_review_planning")
    workflow.add_edge("write_script", "human_review_script_writing")
    workflow.add_edge("generate_visuals", "human_review_visual_generation")
    
    # Add simple progression for now
    workflow.add_edge("human_review_input_processing", "search_ideas")
    workflow.add_edge("human_review_search_content_ideas", "research_content")
    workflow.add_edge("human_review_research", "plan_content")
    workflow.add_edge("human_review_planning", "write_script")
    workflow.add_edge("human_review_script_writing", "generate_visuals")
    workflow.add_edge("human_review_visual_generation", END)
    
    # Search agent now goes to human selection or end
    workflow.add_conditional_edges(
        "search_agent",
        should_continue_from_search,
        {
            "human_select_article": "human_select_article",
            "end": END
        }
    )
    
    # Human selection waits for next input, then routes appropriately
    workflow.add_conditional_edges(
        "human_select_article",
        lambda state: "end",  # Always end after human selection node
        {
            "end": END
        }
    )
    
    # Add crawl agent exit
    workflow.add_edge("crawl_agent", END)
    
    return workflow

# Create and compile the workflow
app = create_workflow().compile()

async def run_workflow(input_type: str, input_data: Dict[str, Any]) -> ContentState:
    """Run the complete workflow"""
    # Create initial state
    initial_state = ContentState(
        workflow_id=str(uuid.uuid4()),
        input_type=input_type,
        input_data=input_data
    )
    
    # Run the workflow with increased recursion limit
    config = {
        "configurable": {"thread_id": initial_state.workflow_id},
        "recursion_limit": 50  # Increased limit to handle chat loops
    }
    
    async for event in app.astream(initial_state, config=config):
        print(f"Phase completed: {event}")
        # In production, would update UI/database here
    
    # Get final state
    final_state = app.get_state(config)
    return final_state.values

# Example usage
if __name__ == "__main__":
    async def test_workflow():
        result = await run_workflow(
            input_type="prompt",
            input_data={
                "prompt": "5 ChatGPT tips for productivity",
                "style": "educational"
            }
        )
        print(f"Workflow completed: {result.workflow_id}")
        print(f"Total cost: ${result.total_cost_usd:.2f}")
    
    asyncio.run(test_workflow())