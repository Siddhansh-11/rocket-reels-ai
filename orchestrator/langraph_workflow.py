import os
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv

from workflow_state import ContentState, PhaseOutput, PhaseStatus, ReviewStatus
from mcp_client import MCPClient
from human_review import HumanReviewInterface

# Load environment
load_dotenv('../config/.env')

# Initialize components
mcp_client = MCPClient()
review_interface = HumanReviewInterface()
memory = MemorySaver()  # Use SQLite in production

# Phase definitions
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
        state.current_phase = "research"
        
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

def should_continue(state: ContentState) -> str:
    """Determine next step in workflow"""
    # Check if workflow is complete or failed
    if state.current_phase == "completed":
        return "end"
    
    if any(phase.status == PhaseStatus.FAILED for phase in [
        state.input_processing, state.research, state.planning,
        state.script_writing, state.visual_generation
    ] if phase):
        return "end"
    
    # Check if we need human review
    latest_review = state.reviews.get(state.current_phase)
    if not latest_review:
        return f"human_review_{state.current_phase}"
    
    if latest_review.status == ReviewStatus.APPROVED:
        return state.current_phase
    elif latest_review.status == ReviewStatus.REVISION_REQUESTED:
        return state.current_phase  # Retry current phase
    else:
        return "end"

# Build the workflow graph
def create_workflow() -> StateGraph:
    """Create the LangGraph workflow"""
    workflow = StateGraph(ContentState)
    
    # Add nodes for each phase
    workflow.add_node("process_input", process_input)
    workflow.add_node("research_content", research_content)
    workflow.add_node("plan_content", plan_content)
    workflow.add_node("write_script", write_script)
    workflow.add_node("generate_visuals", generate_visuals)
    
    # Add human review nodes
    for phase in ["input_processing", "research", "planning", "script_writing", "visual_generation"]:
        workflow.add_node(f"human_review_{phase}", human_review)
    
    # Add edges
    workflow.set_entry_point("process_input")
    
    # Connect phases to their review nodes
    workflow.add_edge("process_input", "human_review_input_processing")
    workflow.add_edge("research_content", "human_review_research")
    workflow.add_edge("plan_content", "human_review_planning")
    workflow.add_edge("write_script", "human_review_script_writing")
    workflow.add_edge("generate_visuals", "human_review_visual_generation")
    
    # Add simple progression for now
    workflow.add_edge("human_review_input_processing", "research_content")
    workflow.add_edge("human_review_research", "plan_content")
    workflow.add_edge("human_review_planning", "write_script")
    workflow.add_edge("human_review_script_writing", "generate_visuals")
    workflow.add_edge("human_review_visual_generation", END)
    
    return workflow

# Create and compile the workflow
app = create_workflow().compile(checkpointer=memory)

async def run_workflow(input_type: str, input_data: Dict[str, Any]) -> ContentState:
    """Run the complete workflow"""
    # Create initial state
    initial_state = ContentState(
        workflow_id=str(uuid.uuid4()),
        input_type=input_type,
        input_data=input_data
    )
    
    # Run the workflow
    config = {"configurable": {"thread_id": initial_state.workflow_id}}
    
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