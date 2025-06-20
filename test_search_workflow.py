#!/usr/bin/env python3
"""
Test script for search functionality in the workflow
"""

import asyncio
import sys
from pathlib import Path
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

# Add orchestrator to path
sys.path.append(str(Path(__file__).parent / "orchestrator"))

# Load environment variables
load_dotenv('.env')

from langraph_workflow import create_workflow, ContentState
import uuid

async def test_search():
    """Test search functionality"""
    print("🔍 Testing Search Workflow...")
    
    # Create workflow
    workflow = create_workflow()
    app = workflow.compile()
    
    # Create initial state with a search message
    initial_state = ContentState(
        workflow_id=str(uuid.uuid4()),
        messages=[HumanMessage(content="news")],  # Simple news query
        input_type="chat",  # Mark as chat type
        input_data={}
    )
    
    print(f"📝 Initial message: 'news'")
    print(f"🆔 Workflow ID: {initial_state.workflow_id}")
    
    config = {
        "configurable": {"thread_id": initial_state.workflow_id},
        "recursion_limit": 50
    }
    
    try:
        print("\n🚀 Running workflow...")
        
        # Collect all events
        events = []
        async for event in app.astream(initial_state, config=config):
            events.append(event)
            # Print the event type
            for key, value in event.items():
                print(f"\n📍 Node: {key}")
                if hasattr(value, 'messages') and value.messages:
                    # Print the last message
                    last_msg = value.messages[-1]
                    print(f"💬 Response: {last_msg.content[:200]}...")
        
        print(f"\n✅ Workflow completed successfully!")
        print(f"📊 Total events: {len(events)}")
        
        # Get final state
        final_state = app.get_state(config)
        if final_state.values.messages:
            print("\n🎯 Final Messages:")
            for i, msg in enumerate(final_state.values.messages):
                msg_type = "Human" if hasattr(msg, '__class__') and msg.__class__.__name__ == "HumanMessage" else "System"
                print(f"{i+1}. [{msg_type}] {msg.content[:100]}...")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_search())