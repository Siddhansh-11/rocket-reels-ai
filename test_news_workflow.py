#!/usr/bin/env python3
"""Test script for news search and article selection workflow"""

import asyncio
from orchestrator.langraph_workflow import app, ContentState
from langchain_core.messages import HumanMessage, SystemMessage
import uuid

async def test_news_search_workflow():
    """Test the news search with human-in-the-loop workflow"""
    print("🚀 Starting News Search Workflow Test\n")
    
    # Test 1: Search for news
    print("Test 1: Searching for news...")
    initial_state = ContentState(
        workflow_id=f"test_workflow_{uuid.uuid4()}",
        messages=[HumanMessage(content="news")]
    )
    
    config = {
        "configurable": {"thread_id": initial_state.workflow_id},
        "recursion_limit": 10
    }
    
    # Run the workflow
    result = await app.ainvoke(initial_state, config=config)
    
    # Check if news results were added to messages
    print("\n📰 Search Results:")
    for msg in result['messages']:
        if isinstance(msg, SystemMessage) and "TECH NEWS" in msg.content:
            print(msg.content[:500] + "...\n")
            break
    
    # Test 2: Select an article
    print("\nTest 2: Selecting article #1...")
    result['messages'].append(HumanMessage(content="1"))
    
    # Run workflow again with article selection
    result2 = await app.ainvoke(result, config=config)
    
    # Check if crawl was attempted
    print("\n🕷️ Crawl Results:")
    for msg in result2['messages']:
        if isinstance(msg, SystemMessage) and ("CRAWL" in msg.content or "article" in msg.content.lower()):
            print(msg.content[:500] + "...\n")
    
    print("✅ Workflow test completed!")
    
    return result2

async def test_direct_crawl():
    """Test direct URL crawl"""
    print("\n\nTest 3: Direct URL crawl...")
    
    initial_state = ContentState(
        workflow_id=f"test_workflow_{uuid.uuid4()}",
        messages=[HumanMessage(content="crawl https://techcrunch.com/2025/06/13/openai-chatgpt-canvas/")]
    )
    
    config = {
        "configurable": {"thread_id": initial_state.workflow_id},
        "recursion_limit": 10
    }
    
    result = await app.ainvoke(initial_state, config=config)
    
    print("\n🕷️ Direct Crawl Results:")
    for msg in result['messages']:
        if isinstance(msg, SystemMessage):
            print(msg.content[:500] + "...\n")
    
    return result

if __name__ == "__main__":
    print("=" * 60)
    print("NEWS SEARCH AND ARTICLE SELECTION WORKFLOW TEST")
    print("=" * 60)
    
    # Run tests
    asyncio.run(test_news_search_workflow())
    # asyncio.run(test_direct_crawl())