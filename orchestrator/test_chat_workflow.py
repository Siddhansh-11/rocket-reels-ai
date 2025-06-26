#!/usr/bin/env python3
"""Test the chat agent directly in the workflow"""

import asyncio
from langchain_core.messages import HumanMessage, AIMessage
from workflow_state import ContentState
from langraph_workflow import app
import uuid

async def test_chat_agent():
    """Test the chat agent with various queries"""
    
    print("🧪 Testing Chat Agent in Workflow...\n")
    
    # Test queries
    test_queries = [
        "show stored articles",
        "search AI news",
        "check database status",
        "help"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"📨 Test Query: '{query}'")
        print(f"{'='*60}")
        
        # Create initial state with just a human message
        initial_state = ContentState(
            workflow_id=str(uuid.uuid4()),
            messages=[HumanMessage(content=query)]
        )
        
        # Run the workflow
        config = {
            "configurable": {"thread_id": initial_state.workflow_id},
            "recursion_limit": 10
        }
        
        try:
            # Run the workflow
            result = await app.ainvoke(initial_state, config=config)
            
            # Extract the response
            if result and result.messages:
                # Find the last AI message
                for msg in reversed(result.messages):
                    if isinstance(msg, AIMessage):
                        print(f"\n🤖 Response:\n{msg.content}")
                        break
            else:
                print("❌ No response received")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"\n{'='*60}")
        await asyncio.sleep(1)  # Small delay between tests

async def test_interactive_chat():
    """Test interactive chat mode"""
    print("\n🎯 Interactive Chat Mode (type 'exit' to quit)")
    print("Try: 'show stored articles', 'search AI news', etc.\n")
    
    while True:
        query = input("\n💬 You: ")
        if query.lower() in ['exit', 'quit', 'q']:
            break
            
        # Create state with message
        initial_state = ContentState(
            workflow_id=str(uuid.uuid4()),
            messages=[HumanMessage(content=query)]
        )
        
        config = {
            "configurable": {"thread_id": initial_state.workflow_id},
            "recursion_limit": 10
        }
        
        try:
            # Run workflow
            result = await app.ainvoke(initial_state, config=config)
            
            # Extract response
            if result and result.messages:
                for msg in reversed(result.messages):
                    if isinstance(msg, AIMessage):
                        print(f"\n🤖 Assistant: {msg.content}")
                        break
            else:
                print("❌ No response received")
                
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🚀 Starting Chat Agent Tests\n")
    
    # Run basic tests
    asyncio.run(test_chat_agent())
    
    # Run interactive mode
    print("\n" + "="*60)
    choice = input("\nRun interactive mode? (y/n): ")
    if choice.lower() == 'y':
        asyncio.run(test_interactive_chat())
    
    print("\n✅ Tests completed!")