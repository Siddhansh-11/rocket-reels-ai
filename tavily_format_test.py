#!/usr/bin/env python3
"""
Test script to demonstrate Tavily search result formats and processing logic
"""

import json
import re
import os
from typing import Any, Dict, List
from urllib.parse import urlparse
from dotenv import load_dotenv
from langchain_community.tools.tavily_search import TavilySearchResults

# Load environment variables
load_dotenv()

class TavilyFormatTester:
    """Test different Tavily response formats and processing logic"""
    
    def __init__(self):
        self.tavily_search = TavilySearchResults(
            max_results=10,
            search_depth="advanced",
            include_answer=True,
            include_raw_content=True,
            include_images=False
        )
    
    def test_format_processing(self):
        """Test processing of different response formats"""
        
        # Test Format 1: Dict with 'results' key
        print("=== Testing Format 1: Dict with 'results' key ===")
        format1_example = {
            "results": [
                {
                    "url": "https://example.com/article1",
                    "title": "Example Article 1",
                    "content": "This is the content of article 1...",
                    "score": 0.85,
                    "published_date": "2024-01-01"
                },
                {
                    "url": "https://example.com/article2",
                    "title": "Example Article 2",
                    "content": "This is the content of article 2...",
                    "score": 0.72,
                    "published_date": "2024-01-02"
                }
            ]
        }
        
        results1 = self.extract_structured_results(format1_example)
        print(f"Extracted {len(results1)} results:")
        for i, result in enumerate(results1, 1):
            print(f"  {i}. {result['title']} - {result['url']}")
        
        # Test Format 2: Direct list
        print("\n=== Testing Format 2: Direct list ===")
        format2_example = [
            {
                "url": "https://techcrunch.com/article1",
                "title": "Tech News Article 1",
                "content": "Breaking tech news content...",
                "score": 0.90
            },
            {
                "url": "https://theverge.com/article2", 
                "title": "Tech News Article 2",
                "content": "Another tech news story...",
                "score": 0.78
            }
        ]
        
        results2 = self.extract_structured_results(format2_example)
        print(f"Extracted {len(results2)} results:")
        for i, result in enumerate(results2, 1):
            print(f"  {i}. {result['title']} - {result['url']}")
        
        # Test Format 3: String format
        print("\n=== Testing Format 3: String format ===")
        format3_example = """
        Result 1: https://arstechnica.com/tech-news/article1 - Title: Ars Technica Article
        Result 2: https://engadget.com/tech-news/article2 - Title: Engadget Article
        Some other text with https://wired.com/article3 embedded URL
        """
        
        results3 = self.extract_structured_results(format3_example)
        print(f"Extracted {len(results3)} results:")
        for i, result in enumerate(results3, 1):
            print(f"  {i}. {result['title']} - {result['url']}")
    
    def extract_structured_results(self, raw_results: Any) -> List[Dict[str, Any]]:
        """Extract structured data from search results (from production code)"""
        structured_results = []
        
        try:
            print(f"Debug: Raw results type: {type(raw_results)}")
            if hasattr(raw_results, '__dict__'):
                print(f"Debug: Raw results attributes: {list(raw_results.__dict__.keys())}")
            
            # Handle different response formats from Tavily
            if hasattr(raw_results, 'get') and raw_results.get('results'):
                # Tavily returns a dict with 'results' key
                actual_results = raw_results['results']
                print(f"Debug: Found results key with {len(actual_results)} items")
                return self.extract_structured_results(actual_results)
                
            elif isinstance(raw_results, list):
                print(f"Debug: Processing {len(raw_results)} list items")
                for item in raw_results:
                    if isinstance(item, dict):
                        result = {
                            'url': item.get('url', ''),
                            'title': item.get('title', ''),
                            'content': item.get('content', ''),
                            'score': item.get('score', 0.5),
                            'published_date': item.get('published_date', ''),
                            'domain': urlparse(item.get('url', '')).netloc
                        }
                        # Skip fake Tavily URLs
                        if (result['url'] and result['title'] and 
                            'api.tavily.com' not in result['url'] and 
                            'tavily.com/search' not in result['url']):
                            structured_results.append(result)
                            
            elif isinstance(raw_results, str):
                print(f"Debug: Raw results is string, length: {len(raw_results)}")
                # Fallback: extract URLs and create basic structure
                urls = re.findall(r'https?://[^\s\],"\']+', raw_results)
                for url in urls:
                    clean_url = url.rstrip('.,;)')
                    # Skip fake Tavily API URLs
                    if ('api.tavily.com' not in clean_url and 
                        'tavily.com/search' not in clean_url):
                        structured_results.append({
                            'url': clean_url,
                            'title': 'Article',
                            'content': '',
                            'score': 0.3,
                            'published_date': '',
                            'domain': urlparse(clean_url).netloc
                        })
                        
            elif isinstance(raw_results, dict):
                print(f"Debug: Raw results is dict with keys: {list(raw_results.keys())}")
                # Handle case where Tavily returns a dict with results key
                if 'results' in raw_results:
                    return self.extract_structured_results(raw_results['results'])
                    
        except Exception as e:
            print(f"Error extracting structured results: {e}")
        
        print(f"Debug: Final structured results count: {len(structured_results)}")
        return structured_results
    
    def test_fake_url_filtering(self):
        """Test filtering of fake Tavily URLs"""
        print("\n=== Testing Fake URL Filtering ===")
        
        fake_results = [
            {
                "url": "https://api.tavily.com/fake-search-result",
                "title": "Fake Tavily Result",
                "content": "This should be filtered out"
            },
            {
                "url": "https://tavily.com/search/fake-result",
                "title": "Another Fake Result", 
                "content": "This should also be filtered out"
            },
            {
                "url": "https://example.com/real-article",
                "title": "Real Article",
                "content": "This should be kept"
            }
        ]
        
        results = self.extract_structured_results(fake_results)
        print(f"Original: {len(fake_results)} results")
        print(f"After filtering: {len(results)} results")
        
        for result in results:
            print(f"  Kept: {result['title']} - {result['url']}")
    
    def test_real_tavily_search(self, query: str = "OpenAI GPT-4"):
        """Test with real Tavily API call"""
        print(f"\n=== Testing Real Tavily Search: '{query}' ===")
        
        if not os.getenv('TAVILY_API_KEY'):
            print("❌ TAVILY_API_KEY not found - skipping real API test")
            return
        
        try:
            # Execute real search
            raw_results = self.tavily_search.invoke({"query": query})
            
            print(f"Raw results type: {type(raw_results)}")
            print(f"Raw results preview: {str(raw_results)[:500]}...")
            
            # Process results
            structured_results = self.extract_structured_results(raw_results)
            
            print(f"\nExtracted {len(structured_results)} structured results:")
            for i, result in enumerate(structured_results[:5], 1):
                print(f"  {i}. {result['title']}")
                print(f"     URL: {result['url']}")
                print(f"     Domain: {result['domain']}")
                print(f"     Score: {result['score']}")
                print(f"     Content: {result['content'][:100]}...")
                print()
            
            # Save results for analysis
            with open('/mnt/d/rocket-reels-ai/tavily_test_results.json', 'w') as f:
                json.dump({
                    'query': query,
                    'raw_results': str(raw_results),
                    'structured_results': structured_results
                }, f, indent=2, default=str)
            
            print("Results saved to tavily_test_results.json")
            
        except Exception as e:
            print(f"❌ Real Tavily search failed: {e}")
    
    def test_edge_cases(self):
        """Test edge cases and error handling"""
        print("\n=== Testing Edge Cases ===")
        
        # Test empty results
        empty_results = []
        results = self.extract_structured_results(empty_results)
        print(f"Empty list: {len(results)} results")
        
        # Test None
        none_results = None
        results = self.extract_structured_results(none_results)
        print(f"None input: {len(results)} results")
        
        # Test malformed dict
        malformed_dict = {"not_results": "some_value"}
        results = self.extract_structured_results(malformed_dict)
        print(f"Malformed dict: {len(results)} results")
        
        # Test dict with empty results
        empty_dict = {"results": []}
        results = self.extract_structured_results(empty_dict)
        print(f"Empty results dict: {len(results)} results")
        
        # Test string with no URLs
        no_urls_string = "This is just text with no URLs in it"
        results = self.extract_structured_results(no_urls_string)
        print(f"No URLs string: {len(results)} results")

def main():
    """Main test function"""
    print("🧪 TAVILY FORMAT TESTING SUITE")
    print("=" * 50)
    
    tester = TavilyFormatTester()
    
    # Test different response formats
    tester.test_format_processing()
    
    # Test fake URL filtering
    tester.test_fake_url_filtering()
    
    # Test edge cases
    tester.test_edge_cases()
    
    # Test real API call (if API key available)
    tester.test_real_tavily_search("Hunyuan3D-PolyGen")
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    main()