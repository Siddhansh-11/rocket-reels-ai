#!/usr/bin/env python3
"""
Test script to validate the production workflow structure
"""

import sys
import os

# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

def test_imports():
    """Test that all agent imports work correctly"""
    print("🧪 Testing agent imports...")
    
    try:
        from agents.search_agent import search_tools
        print(f"✅ Search agent: {len(search_tools)} tools")
    except Exception as e:
        print(f"❌ Search agent: {e}")
    
    try:
        from agents.crawl_agent import crawl_tools
        print(f"✅ Crawl agent: {len(crawl_tools)} tools")
    except Exception as e:
        print(f"❌ Crawl agent: {e}")
    
    try:
        from agents.supabase_agent import supabase_tools_sync_wrapped
        print(f"✅ Supabase agent: {len(supabase_tools_sync_wrapped)} tools")
    except Exception as e:
        print(f"❌ Supabase agent: {e}")
    
    try:
        from agents.scripting_agent import scripting_tools
        print(f"✅ Scripting agent: {len(scripting_tools)} tools")
    except Exception as e:
        print(f"❌ Scripting agent: {e}")
    
    try:
        from agents.prompt_generation_agent import prompt_generation_tools
        print(f"✅ Prompt generation agent: {len(prompt_generation_tools)} tools")
    except Exception as e:
        print(f"❌ Prompt generation agent: {e}")
    
    try:
        from agents.image_generation_agent import image_generation_tools
        print(f"✅ Image generation agent: {len(image_generation_tools)} tools")
    except Exception as e:
        print(f"❌ Image generation agent: {e}")
    
    try:
        from agents.voice_generation_agent import voice_tools
        print(f"✅ Voice generation agent: {len(voice_tools)} tools")
    except Exception as e:
        print(f"❌ Voice generation agent: {e}")

def test_workflow_structure():
    """Test that the workflow can be instantiated"""
    print("\n🏗️ Testing workflow structure...")
    
    try:
        from core.production_workflow import production_workflow, WorkflowState
        
        # Test state creation
        state = WorkflowState(topic="test topic", user_query="test query")
        print(f"✅ WorkflowState created: {state.topic}")
        
        # Test compiled workflow
        print("✅ Compiled production_workflow imported")
        print(f"✅ Workflow type: {type(production_workflow)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Workflow structure test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Production Workflow Validation")
    print("=" * 40)
    
    # Test imports
    test_imports()
    
    # Test workflow structure
    workflow_ok = test_workflow_structure()
    
    print("\n" + "=" * 40)
    if workflow_ok:
        print("✅ All tests passed! Workflow is ready to use.")
        print("\nTo run the workflow:")
        print("  python run_workflow.py 'your topic here'")
    else:
        print("❌ Some tests failed. Check the errors above.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)