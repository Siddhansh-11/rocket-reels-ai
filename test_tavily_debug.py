#!/usr/bin/env python3
"""
Debug script to test Tavily API directly and see what's happening
"""

import os
import json
import requests
from langchain_community.tools.tavily_search import TavilySearchResults
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test the API key
TAVILY_API_KEY = "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"

print("=== TAVILY API DEBUG TEST ===")
print(f"API Key: {TAVILY_API_KEY}")
print(f"API Key format looks correct: {TAVILY_API_KEY.startswith('tvly-')}")

# Test 1: Direct API call to Tavily
print("\n1. Testing direct Tavily API call...")
try:
    headers = {
        'Authorization': f'Bearer {TAVILY_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    data = {
        "query": "OpenAI GPT-4 news",
        "search_depth": "advanced",
        "include_answer": True,
        "include_raw_content": True,
        "max_results": 5
    }
    
    response = requests.post(
        'https://api.tavily.com/search',
        headers=headers,
        json=data,
        timeout=30
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Response type: {type(result)}")
        print(f"Response keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        
        if 'results' in result:
            print(f"Number of results: {len(result['results'])}")
            for i, item in enumerate(result['results'][:3]):
                print(f"  Result {i+1}:")
                print(f"    URL: {item.get('url', 'No URL')}")
                print(f"    Title: {item.get('title', 'No title')}")
                print(f"    Content length: {len(item.get('content', ''))}")
        
        # Save full response for analysis
        with open('/mnt/d/rocket-reels-ai/tavily_debug_response.json', 'w') as f:
            json.dump(result, f, indent=2)
        print("Full response saved to tavily_debug_response.json")
        
    else:
        print(f"Error response: {response.text}")
        
except Exception as e:
    print(f"Direct API call failed: {e}")

# Test 2: Test with LangChain wrapper
print("\n2. Testing LangChain TavilySearchResults...")
try:
    # Set the API key in environment
    os.environ['TAVILY_API_KEY'] = TAVILY_API_KEY
    
    tavily_search = TavilySearchResults(
        max_results=5,
        search_depth="advanced",
        include_answer=True,
        include_raw_content=True,
        include_images=False
    )
    
    print("TavilySearchResults initialized successfully")
    
    # Test the search
    result = tavily_search.invoke({"query": "OpenAI GPT-4 news"})
    
    print(f"LangChain result type: {type(result)}")
    print(f"LangChain result: {result}")
    
    # Save LangChain response
    with open('/mnt/d/rocket-reels-ai/langchain_tavily_response.json', 'w') as f:
        json.dump(result, f, indent=2, default=str)
    print("LangChain response saved to langchain_tavily_response.json")
    
except Exception as e:
    print(f"LangChain wrapper failed: {e}")

# Test 3: Check environment variables
print("\n3. Environment variable check...")
print(f"TAVILY_API_KEY from env: {os.getenv('TAVILY_API_KEY')}")
print(f"All env vars with 'TAVILY': {[k for k in os.environ.keys() if 'TAVILY' in k]}")

# Test 4: Check if there's an issue with the search query
print("\n4. Testing different search queries...")
test_queries = [
    "OpenAI",
    "technology news",
    "artificial intelligence",
    "GPT-4"
]

for query in test_queries:
    try:
        os.environ['TAVILY_API_KEY'] = TAVILY_API_KEY
        tavily_search = TavilySearchResults(max_results=3)
        result = tavily_search.invoke({"query": query})
        print(f"Query '{query}': {type(result)} - {len(str(result))} chars")
        
        # Check for fake URLs
        result_str = str(result)
        if 'api.tavily.com' in result_str or 'tavily.com/search' in result_str:
            print(f"  ⚠️ WARNING: Found fake Tavily URLs in response for query '{query}'")
            
    except Exception as e:
        print(f"Query '{query}' failed: {e}")

print("\n=== TEST COMPLETE ===")