#!/usr/bin/env python3
"""
Test script to verify the recursion limit fix in the chat agent
"""

import asyncio
import sys
from pathlib import Path
from langchain_core.messages import HumanMessage

# Add orchestrator to path
sys.path.append(str(Path(__file__).parent / "orchestrator"))

from langraph_workflow import create_workflow, ContentState
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env')

async def test_chat_recursion():
    """Test that the chat agent doesn't cause infinite recursion"""
    print("Testing chat agent recursion fix...")
    
    # Create workflow
    workflow = create_workflow()
    app = workflow.compile()
    
    # Create initial state with messages
    initial_state = ContentState(
        workflow_id="recursion-test",
        input_type="prompt",
        input_data={"prompt": "Test recursion"}
    )
    
    # Add initial message
    initial_state.messages.append(HumanMessage(content="Hello, can you help me search for trending AI news?"))
    
    config = {"configurable": {"thread_id": initial_state.workflow_id}, "recursion_limit": 25}
    
    try:
        # Run the workflow with recursion limit
        events = []
        async for event in app.astream(initial_state, config=config):
            events.append(event)
            print(f"Event {len(events)}: {list(event.keys())}")
            
            # After a few iterations, send exit message
            if len(events) == 3:
                # Get the current state and add exit message
                current_state = app.get_state(config)
                current_state.values.messages.append(HumanMessage(content="exit"))
                # Continue with updated state
                async for remaining_event in app.astream(None, config=config):
                    events.append(remaining_event)
                    print(f"Event {len(events)}: {list(remaining_event.keys())}")
                break
        
        print(f"\n✅ Success! Workflow completed after {len(events)} events")
        print("The recursion fix is working correctly.")
        
    except Exception as e:
        if "RecursionLimit" in str(e):
            print(f"\n❌ Failed! Still hitting recursion limit: {e}")
            print("The fix needs more work.")
        else:
            print(f"\n❌ Failed with error: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(test_chat_recursion())