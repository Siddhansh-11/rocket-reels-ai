#!/usr/bin/env python3
"""Test the orchestrator chat agent from langgraph environment"""

import sys
import os
import asyncio
sys.path.append('../orchestrator')

from langchain_core.messages import HumanMessage, AIMessage

# Test if we can import the orchestrator chat agent
try:
    from chat_agent import run_chat_agent, chat_agent, MODEL_AVAILABLE
    print("✅ Successfully imported orchestrator chat agent")
except ImportError as e:
    print(f"❌ Failed to import orchestrator chat agent: {e}")
    sys.exit(1)

async def test_chat_agent():
    """Test the orchestrator chat agent"""
    print("\n🧪 Testing Orchestrator Chat Agent...\n")
    
    print(f"📊 Model available: {MODEL_AVAILABLE}")
    print(f"🤖 Chat agent created: {chat_agent is not None}")
    
    if not MODEL_AVAILABLE or chat_agent is None:
        print("⚠️ Chat agent not properly initialized")
        return False
    
    # Test queries
    test_queries = [
        "show stored articles",
        "check database status", 
        "search AI news",
        "help"
    ]
    
    success_count = 0
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📨 Test {i}/{len(test_queries)}: '{query}'")
        print("-" * 50)
        
        try:
            # Run the chat agent
            result = await run_chat_agent(query)
            
            # Check if we got a valid response
            if result and len(result) > 50:
                print(f"✅ Success! Response length: {len(result)} characters")
                print(f"📤 Preview: {result[:150]}...")
                success_count += 1
            else:
                print(f"⚠️ Short response: {result}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        print("-" * 50)
    
    print(f"\n📊 Test Summary: {success_count}/{len(test_queries)} tests passed")
    return success_count == len(test_queries)

async def test_workflow_integration():
    """Test integration with workflow state"""
    print("\n🎯 Testing Workflow Integration...\n")
    
    try:
        # Import workflow components
        from workflow_state import ContentState
        from langraph_workflow import chat_agent as workflow_chat_agent
        import uuid
        
        # Create a test state
        state = ContentState(
            workflow_id=str(uuid.uuid4()),
            messages=[HumanMessage(content="show stored articles")]
        )
        
        # Run the workflow chat agent function
        result_state = await workflow_chat_agent(state)
        
        # Check if we got a response
        if result_state.messages and len(result_state.messages) > 1:
            last_message = result_state.messages[-1]
            if isinstance(last_message, AIMessage):
                print(f"✅ Workflow integration successful!")
                print(f"📤 Response: {last_message.content[:200]}...")
                return True
            else:
                print(f"⚠️ Last message not an AI message: {type(last_message)}")
        else:
            print(f"⚠️ No response added to state")
            
        return False
        
    except Exception as e:
        print(f"❌ Workflow integration error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting Orchestrator Chat Agent Tests from LangGraph environment\n")
    
    async def main():
        # Test 1: Basic chat agent functionality
        basic_success = await test_chat_agent()
        
        # Test 2: Workflow integration
        workflow_success = await test_workflow_integration()
        
        print(f"\n{'='*60}")
        print("📊 FINAL TEST RESULTS")
        print(f"{'='*60}")
        print(f"🔧 Basic Chat Agent: {'✅ PASS' if basic_success else '❌ FAIL'}")
        print(f"🔄 Workflow Integration: {'✅ PASS' if workflow_success else '❌ FAIL'}")
        
        if basic_success and workflow_success:
            print(f"\n🎉 ALL TESTS PASSED! Chat agent is working correctly.")
        else:
            print(f"\n⚠️ Some tests failed. Check the output above for details.")
        
        return basic_success and workflow_success
    
    success = asyncio.run(main())
    sys.exit(0 if success else 1)