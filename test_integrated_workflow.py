#!/usr/bin/env python3
"""
Test the integrated workflow with news agent and human-in-the-loop
"""
import asyncio
import requests
import json
import sys
import os

# Add orchestrator to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'orchestrator'))

from langraph_workflow import run_workflow

def test_news_integration_workflow():
    """Test workflow with news integration and human selection"""
    url = "http://localhost:8001/workflow/start"
    
    payload = {
        "input_type": "prompt",
        "input_data": {
            "prompt": "Latest developments in AI and machine learning that developers should know about",
            "style": "educational",
            "include_news": True  # Flag to fetch news articles
        }
    }
    
    print("🚀 Starting workflow with news integration...")
    print(f"Prompt: {payload['input_data']['prompt']}")
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        result = response.json()
        print("\n✅ Workflow started successfully!")
        print(f"Status: {result['status']}")
        print(f"Review URL: {result['review_url']}")
        print("\n🔍 Expected workflow:")
        print("1. Input processing")
        print("2. Research with news fetching")
        print("3. 📰 HUMAN REVIEW: Select news articles")
        print("4. Content planning")
        print("5. Script writing")
        print("6. Visual generation")
        print("\n👀 Open the review URL to participate in article selection!")
        print("🔗 LangSmith URL: https://smith.langchain.com/project/rocket-reels-ai")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to orchestrator")
        print("Make sure the services are running: docker-compose up")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

async def test_prompt_workflow():
    """Test workflow with a simple prompt"""
    print("🧪 Testing Prompt Workflow")
    print("=" * 50)
    
    try:
        result = await run_workflow(
            input_type="prompt",
            input_data={
                "prompt": "Latest AI trends for developers",
                "style": "educational"
            }
        )
        
        print(f"✅ Workflow completed!")
        print(f"   Workflow ID: {result.workflow_id}")
        print(f"   Status: {result.status}")
        print(f"   Current Phase: {result.current_phase}")
        print(f"   Total Cost: ${result.total_cost:.2f}")
        print(f"   Phases Completed: {len(result.phase_outputs)}")
        
        if result.errors:
            print(f"⚠️  Errors: {len(result.errors)}")
            for error in result.errors:
                print(f"     - {error}")
        
        return True
        
    except Exception as e:
        print(f"❌ Workflow failed: {e}")
        return False

async def test_youtube_workflow():
    """Test workflow with YouTube URL"""
    print("\n🧪 Testing YouTube Workflow")
    print("=" * 50)
    
    try:
        result = await run_workflow(
            input_type="youtube",
            input_data={
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            }
        )
        
        print(f"✅ YouTube workflow completed!")
        print(f"   Workflow ID: {result.workflow_id}")
        print(f"   Total Cost: ${result.total_cost:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ YouTube workflow failed: {e}")
        return False

async def main():
    """Run all workflow tests"""
    print("🚀 Rocket Reels AI - Integrated Workflow Test")
    print("=" * 60)
    
    # Test 1: Prompt workflow
    test1_success = await test_prompt_workflow()
    
    # Test 2: YouTube workflow
    test2_success = await test_youtube_workflow()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print(f"   Prompt Workflow: {'✅ PASSED' if test1_success else '❌ FAILED'}")
    print(f"   YouTube Workflow: {'✅ PASSED' if test2_success else '❌ FAILED'}")
    
    if test1_success and test2_success:
        print("\n🎉 All tests passed! Your Rocket Reels AI is working correctly.")
        print("\n🌐 Access your system:")
        print("   - Human Review: http://localhost:8000")
        print("   - API Docs: http://localhost:8001/docs")
        print("   - Start Workflow: http://localhost:8001/start-workflow")
    else:
        print("\n⚠️  Some tests failed. Check the error messages above.")

if __name__ == "__main__":
    # main()
    asyncio.run(main())