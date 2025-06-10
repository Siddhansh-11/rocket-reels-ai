import os
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tracers import LangChainTracer
from langsmith import Client
from dotenv import load_dotenv

# Import from core modules
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))

from models.workflow_state import ContentState, PhaseOutput, PhaseStatus, ReviewStatus
from mcp_client import MCPClient
from human_review import HumanReviewInterface

# Load environment
load_dotenv('../config/.env')

# Initialize LangSmith
langsmith_client = Client(
    api_url="https://api.smith.langchain.com",
    api_key=os.getenv("LANGSMITH_API_KEY")
)

# Initialize components
mcp_client = MCPClient()
review_interface = HumanReviewInterface()
memory = MemorySaver()

# Create tracer
tracer = LangChainTracer(
    project_name="rocket-reels-ai",
    client=langsmith_client
)

# Complete workflow phases
WORKFLOW_PHASES = [
    "input_processing",
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
        with tracer.trace("process_input") as trace:
            trace.add_tags(["input_processing"])
            trace.log({"input_type": state.input_type})
            
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
                cost_usd=0.01
            )
            state.add_phase_output("input_processing", output)
            state.current_phase = "research"
            
            trace.log({"status": "completed", "next_phase": "research"})
        
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

async def research_content(state: ContentState) -> ContentState:
    """Research content using Research MCP server with news integration"""
    try:
        with tracer.trace("research_content") as trace:
            trace.add_tags(["research", "news_integration"])
            
            input_data = state.input_processing.data
            
            # Use enhanced research with news integration
            result = await mcp_client.call_tool(
                "research",
                "research_topic",
                {
                    "input_data": input_data,
                    "depth": "standard"
                }
            )
            
            trace.log({"research_completed": True})
            
            # Check if human selection is needed for news articles
            news_results = result.get('news_results', {})
            if news_results.get('requires_human_selection') and news_results.get('articles'):
                # Prepare human review for article selection
                review_data = {
                    "phase": "research_article_selection",
                    "question": "Select which news articles to use for the video content:",
                    "options": [
                        {
                            "id": article["id"],
                            "title": article["title"],
                            "source": article["source"],
                            "description": article["description"],
                            "preview": article["full_content"][:200] + "..."
                        }
                        for article in news_results["articles"]
                    ],
                    "selection_type": "multiple",
                    "max_selections": 3
                }
                
                state.pending_reviews["article_selection"] = review_data
                state.current_phase = "human_review_article_selection"
                
                output = PhaseOutput(
                    phase_name="research",
                    data={
                        "research": result,
                        "human_review_required": True,
                        "review_type": "article_selection"
                    },
                    status=PhaseStatus.PENDING_REVIEW,
                    cost_usd=0.05
                )
                
                trace.log({"status": "pending_human_review"})
                
            else:
                output = PhaseOutput(
                    phase_name="research",
                    data=result,
                    status=PhaseStatus.COMPLETED,
                    cost_usd=0.05
                )
                state.current_phase = "planning"
                
                trace.log({"status": "completed", "next_phase": "planning"})
            
            state.add_phase_output("research", output)
            
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
        with tracer.trace("plan_content") as trace:
            trace.add_tags(["planning"])
            
            research_data = state.research.data
            
            result = await mcp_client.call_tool(
                "planner",
                "create_content_plan",
                {
                    "research_data": research_data,
                    "target_duration": 60,
                    "platform": "instagram"
                }
            )
            
            output = PhaseOutput(
                phase_name="planning",
                data=result,
                status=PhaseStatus.COMPLETED,
                cost_usd=0.03
            )
            state.add_phase_output("planning", output)
            state.current_phase = "script_writing"
            
            trace.log({"status": "completed", "next_phase": "script_writing"})
        
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
        with tracer.trace("write_script") as trace:
            trace.add_tags(["script_writing"])
            
            plan_data = state.planning.data
            research_data = state.research.data
            
            result = await mcp_client.call_tool(
                "script-writer",
                "write_script",
                {
                    "content_plan": plan_data,
                    "research_data": research_data,
                    "style": "energetic"
                }
            )
            
            output = PhaseOutput(
                phase_name="script_writing",
                data=result,
                status=PhaseStatus.COMPLETED,
                cost_usd=0.08
            )
            state.add_phase_output("script_writing", output)
            state.current_phase = "visual_generation"
            
            trace.log({"status": "completed", "next_phase": "visual_generation"})
        
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

async def generate_visuals(state: ContentState) -> ContentState:
    """Generate visuals using Visual MCP server"""
    try:
        with tracer.trace("generate_visuals") as trace:
            trace.add_tags(["visual_generation"])
            
            script_data = state.script_writing.data
            visual_plan = state.planning.data.get("visual_suggestions", {})
            
            result = await mcp_client.call_tool(
                "visual-generator",
                "generate_visuals",
                {
                    "script": script_data,
                    "visual_plan": visual_plan
                }
            )
            
            output = PhaseOutput(
                phase_name="visual_generation",
                data=result,
                status=PhaseStatus.COMPLETED,
                cost_usd=0.20
            )
            state.add_phase_output("visual_generation", output)
            state.current_phase = "assembly"
            
            trace.log({"status": "completed", "next_phase": "assembly"})
        
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

async def assemble_video(state: ContentState) -> ContentState:
    """Assemble final video using Assembly MCP server"""
    try:
        with tracer.trace("assemble_video") as trace:
            trace.add_tags(["assembly"])
            
            script_data = state.script_writing.data
            visuals_data = state.visual_generation.data
            
            result = await mcp_client.call_tool(
                "assembly",
                "assemble_video",
                {
                    "script": script_data,
                    "visuals": visuals_data.get("generated_visuals", []),
                    "audio": {
                        "voice_id": "rachel",
                        "style": "energetic",
                        "background_music": "upbeat"
                    },
                    "transitions": [{"type": "fade", "duration": 0.5}],
                    "output_settings": {"resolution": "1080x1920", "fps": 30}
                }
            )
            
            output = PhaseOutput(
                phase_name="assembly",
                data=result,
                status=PhaseStatus.COMPLETED,
                cost_usd=0.15
            )
            state.add_phase_output("assembly", output)
            state.current_phase = "export"
            
            trace.log({"status": "completed", "next_phase": "export"})
        
    except Exception as e:
        output = PhaseOutput(
            phase_name="assembly",
            data={},
            status=PhaseStatus.FAILED,
            error=str(e)
        )
        state.add_phase_output("assembly", output)
        state.errors.append({"phase": "assembly", "error": str(e)})
    
    return state

async def export_video(state: ContentState) -> ContentState:
    """Export video for platforms using Export MCP server"""
    try:
        with tracer.trace("export_video") as trace:
            trace.add_tags(["export"])
            
            assembly_data = state.assembly.data
            video_path = assembly_data.get("video_path")
            
            result = await mcp_client.call_tool(
                "export",
                "export_for_platforms",
                {
                    "source_video": video_path,
                    "platforms": ["instagram", "tiktok", "youtube_shorts"],
                    "quality": "high"
                }
            )
            
            output = PhaseOutput(
                phase_name="export",
                data=result,
                status=PhaseStatus.COMPLETED,
                cost_usd=0.05
            )
            state.add_phase_output("export", output)
            state.current_phase = "distribution"
            
            trace.log({"status": "completed", "next_phase": "distribution"})
        
    except Exception as e:
        output = PhaseOutput(
            phase_name="export",
            data={},
            status=PhaseStatus.FAILED,
            error=str(e)
        )
        state.add_phase_output("export", output)
        state.errors.append({"phase": "export", "error": str(e)})
    
    return state

async def distribute_content(state: ContentState) -> ContentState:
    """Distribute content using Distribution MCP server"""
    try:
        with tracer.trace("distribute_content") as trace:
            trace.add_tags(["distribution"])
            
            export_data = state.export.data
            script_data = state.script_writing.data
            
            result = await mcp_client.call_tool(
                "distribution",
                "publish_to_platforms",
                {
                    "exports": export_data.get("exports", []),
                    "caption": script_data.get("social_caption", ""),
                    "hashtags": script_data.get("hashtags", []),
                    "platforms": ["instagram", "tiktok"],
                    "schedule_time": None  # Publish immediately
                }
            )
            
            output = PhaseOutput(
                phase_name="distribution",
                data=result,
                status=PhaseStatus.COMPLETED,
                cost_usd=0.02
            )
            state.add_phase_output("distribution", output)
            state.current_phase = "analytics"
            
            trace.log({"status": "completed", "next_phase": "analytics"})
        
    except Exception as e:
        output = PhaseOutput(
            phase_name="distribution",
            data={},
            status=PhaseStatus.FAILED,
            error=str(e)
        )
        state.add_phase_output("distribution", output)
        state.errors.append({"phase": "distribution", "error": str(e)})
    
    return state

async def collect_analytics(state: ContentState) -> ContentState:
    """Collect analytics using Analytics MCP server"""
    try:
        with tracer.trace("collect_analytics") as trace:
            trace.add_tags(["analytics"])
            
            distribution_data = state.distribution.data
            published_videos = distribution_data.get("published_videos", [])
            
            result = await mcp_client.call_tool(
                "analytics",
                "collect_platform_metrics",
                {
                    "video_ids": [v["video_id"] for v in published_videos],
                    "platforms": [v["platform"] for v in published_videos]
                }
            )
            
            output = PhaseOutput(
                phase_name="analytics",
                data=result,
                status=PhaseStatus.COMPLETED,
                cost_usd=0.01
            )
            state.add_phase_output("analytics", output)
            state.current_phase = "completed"
            state.status = "completed"
            
            trace.log({"status": "completed", "workflow_finished": True})
        
    except Exception as e:
        output = PhaseOutput(
            phase_name="analytics",
            data={},
            status=PhaseStatus.FAILED,
            error=str(e)
        )
        state.add_phase_output("analytics", output)
        state.errors.append({"phase": "analytics", "error": str(e)})
    
    return state

# Human review function
async def human_review(state: ContentState) -> ContentState:
    """Human review checkpoint"""
    try:
        current_phase = state.current_phase.replace("human_review_", "")
        phase_output = getattr(state, current_phase, None)
        
        if not phase_output:
            state.errors.append({"phase": "human_review", "error": f"No output found for phase {current_phase}"})
            return state
        
        # Request human review
        review_id = str(uuid.uuid4())
        review_data = {
            "phase": current_phase,
            "data": phase_output.data,
            "question": f"Please review the {current_phase} output. Approve to continue or request revisions.",
            "type": "approval"
        }
        
        await review_interface.request_review(review_id, review_data)
        
        # Wait for review (in production, this would be event-driven)
        review_result = await review_interface.wait_for_review(review_id, timeout=300)
        
        if review_result.get("status") == "approved":
            # Move to next phase
            current_index = WORKFLOW_PHASES.index(current_phase)
            if current_index < len(WORKFLOW_PHASES) - 1:
                state.current_phase = WORKFLOW_PHASES[current_index + 1]
            else:
                state.current_phase = "completed"
                state.status = "completed"
        else:
            # Go back to the phase for revision
            state.current_phase = current_phase
            
    except Exception as e:
        state.errors.append({"phase": "human_review", "error": str(e)})
    
    return state

def create_workflow() -> StateGraph:
    """Create the complete LangGraph workflow"""
    workflow = StateGraph(ContentState)
    
    # Add all phase nodes
    workflow.add_node("process_input", process_input)
    workflow.add_node("research_content", research_content)
    workflow.add_node("plan_content", plan_content)
    workflow.add_node("write_script", write_script)
    workflow.add_node("generate_visuals", generate_visuals)
    workflow.add_node("assemble_video", assemble_video)
    workflow.add_node("export_video", export_video)
    workflow.add_node("distribute_content", distribute_content)
    workflow.add_node("collect_analytics", collect_analytics)
    
    # Add human review nodes
    for phase in WORKFLOW_PHASES:
        workflow.add_node(f"human_review_{phase}", human_review)
    
    # Set entry point
    workflow.set_entry_point("process_input")
    
    # Connect phases with human review checkpoints
    workflow.add_edge("process_input", "human_review_input_processing")
    workflow.add_edge("human_review_input_processing", "research_content")
    workflow.add_edge("research_content", "human_review_research")
    workflow.add_edge("human_review_research", "plan_content")
    workflow.add_edge("plan_content", "human_review_planning")
    workflow.add_edge("human_review_planning", "write_script")
    workflow.add_edge("write_script", "human_review_script_writing")
    workflow.add_edge("human_review_script_writing", "generate_visuals")
    workflow.add_edge("generate_visuals", "human_review_visual_generation")
    workflow.add_edge("human_review_visual_generation", "assemble_video")
    workflow.add_edge("assemble_video", "human_review_assembly")
    workflow.add_edge("human_review_assembly", "export_video")
    workflow.add_edge("export_video", "human_review_export")
    workflow.add_edge("human_review_export", "distribute_content")
    workflow.add_edge("distribute_content", "human_review_distribution")
    workflow.add_edge("human_review_distribution", "collect_analytics")
    workflow.add_edge("collect_analytics", END)
    
    return workflow

# Create and compile the workflow
app = create_workflow().compile(
    checkpointer=memory,
    debug=True
)

async def run_workflow(input_type: str, input_data: Dict[str, Any]) -> ContentState:
    """Run the complete workflow with LangSmith tracing"""
    workflow_id = str(uuid.uuid4())
    
    with tracer.trace("rocket_reels_workflow", inputs={"input_type": input_type, "workflow_id": workflow_id}) as trace:
        trace.add_tags(["workflow", "video_generation"])
        
        initial_state = ContentState(
            workflow_id=workflow_id,
            input_type=input_type,
            input_data=input_data,
            current_phase="input_processing",
            created_at=datetime.now(),
            status="running"
        )
        
        trace.log({"initial_state": "created", "workflow_id": workflow_id})
        
        try:
            final_state = await app.ainvoke(
                initial_state,
                config={
                    "configurable": {"thread_id": workflow_id},
                    "callbacks": [tracer]
                }
            )
            
            trace.log({
                "status": "completed",
                "final_phase": final_state.current_phase,
                "total_cost": final_state.total_cost,
                "errors": len(final_state.errors)
            })
            
            return final_state
            
        except Exception as e:
            trace.log({"status": "failed", "error": str(e)})
            raise

if __name__ == "__main__":
    async def test_workflow():
        result = await run_workflow(
            input_type="prompt",
            input_data={
                "prompt": "Latest AI trends for developers",
                "style": "educational"
            }
        )
        print(f"Workflow completed: {result.workflow_id}")
        print(f"Total cost: ${result.total_cost:.2f}")
    
    asyncio.run(test_workflow())