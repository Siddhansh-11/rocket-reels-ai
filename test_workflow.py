#!/usr/bin/env python3
"""
Test script for Rocket Reels AI workflow
"""
import asyncio
import requests
import json
import sys

def test_prompt_workflow():
    """Test workflow with a prompt input"""
    url = "http://localhost:8001/workflow/start"
    
    payload = {
        "input_type": "prompt",
        "input_data": {
            "prompt": "5 ChatGPT tips that will 10x your productivity as a developer",
            "style": "educational"
        }
    }
    
    print("🚀 Starting workflow with prompt input...")
    print(f"Prompt: {payload['input_data']['prompt']}")
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        result = response.json()
        print("\n✅ Workflow started successfully!")
        print(f"Review URL: {result['review_url']}")
        print("\n👀 Open the review URL in your browser to approve/revise each phase")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to orchestrator")
        print("Make sure the services are running: docker-compose up")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

def test_youtube_workflow():
    """Test workflow with YouTube input"""
    url = "http://localhost:8001/workflow/start"
    
    payload = {
        "input_type": "youtube",
        "input_data": {
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Example URL
        }
    }
    
    print("🚀 Starting workflow with YouTube input...")
    print(f"URL: {payload['input_data']['url']}")
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        result = response.json()
        print("\n✅ Workflow started successfully!")
        print(f"Review URL: {result['review_url']}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

def test_quick_workflow():
    """Test the quick test endpoint"""
    url = "http://localhost:8001/workflow/test"
    
    print("🚀 Running quick test workflow...")
    
    try:
        response = requests.post(url)
        response.raise_for_status()
        
        result = response.json()
        print("\n✅ Test completed!")
        print(f"Workflow ID: {result['workflow_id']}")
        print(f"Total Cost: ${result['total_cost']:.2f}")
        print(f"Phases Completed: {' → '.join(result['phases_completed'])}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

def main():
    """Main test function"""
    print("🚀 Rocket Reels AI - Workflow Test")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        test_type = sys.argv[1]
        if test_type == "youtube":
            test_youtube_workflow()
        elif test_type == "quick":
            test_quick_workflow()
        else:
            test_prompt_workflow()
    else:
        print("\nUsage:")
        print("  python test_workflow.py          # Test with prompt")
        print("  python test_workflow.py youtube  # Test with YouTube URL")
        print("  python test_workflow.py quick    # Quick test (auto-approve)")
        print("\nRunning default prompt test...\n")
        test_prompt_workflow()

if __name__ == "__main__":
    main()