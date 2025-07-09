#!/usr/bin/env python3
"""
Test script for the fixed search agent
"""
import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'production-workflow'))

try:
    from agents.search_agent import search_tech_news
    
    async def test_search():
        print("Testing search agent with query: 'soham parekh'")
        result = await search_tech_news('soham parekh')
        print("Result:")
        print(result)
    
    if __name__ == "__main__":
        asyncio.run(test_search())
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()