# Tavily Search Results Format Analysis

This document provides a comprehensive analysis of how Tavily search results are formatted in the codebase, based on examination of working examples and test files.

## TavilySearchResults Configuration

The codebase shows consistent usage of `TavilySearchResults` with these configurations:

### Production Configuration (from `/production-workflow/agents/search_agent.py`)
```python
from langchain_community.tools.tavily_search import TavilySearchResults

tavily_search = TavilySearchResults(
    max_results=20,  # Get more candidates for better filtering
    search_depth="advanced",
    include_answer=True,
    include_raw_content=True,
    include_images=False
)
```

### Basic Configuration (from `/langgraph/search_agent.py`)
```python
tavily_search_tool = TavilySearchResults(
    max_results=10,
    search_depth="advanced"
)
```

## Expected Response Formats

When calling `tavily_search.invoke({"query": search_query})`, Tavily can return results in multiple formats:

### Format 1: Dictionary with 'results' key (Most Common)
```python
{
    "results": [
        {
            "url": "https://example.com/article",
            "title": "Article Title",
            "content": "Article content preview...",
            "score": 0.85,
            "published_date": "2024-01-01",
            "domain": "example.com"
        },
        # ... more results
    ]
}
```

### Format 2: Direct List of Results
```python
[
    {
        "url": "https://example.com/article",
        "title": "Article Title", 
        "content": "Article content preview...",
        "score": 0.85,
        "published_date": "2024-01-01"
    },
    # ... more results
]
```

### Format 3: String Format (Fallback)
```python
"Result 1: https://example.com/article1 - Title: Article 1...
Result 2: https://example.com/article2 - Title: Article 2..."
```

## Individual Result Structure

Each result item contains these fields:

### Required Fields
- `url`: The URL of the article/page
- `title`: The title of the article
- `content`: Preview/snippet of the article content

### Optional Fields
- `score`: Relevance score (0.0 to 1.0)
- `published_date`: Publication date (if available)
- `domain`: Domain name (extracted from URL if not provided)

## Processing Logic in Codebase

The `_extract_structured_results` function in `/production-workflow/agents/search_agent.py` handles all formats:

```python
def _extract_structured_results(self, raw_results: Any) -> List[Dict[str, Any]]:
    """Extract structured data from search results"""
    structured_results = []
    
    try:
        # Handle different response formats from Tavily
        if hasattr(raw_results, 'get') and raw_results.get('results'):
            # Format 1: Dict with 'results' key
            actual_results = raw_results['results']
            return self._extract_structured_results(actual_results)
            
        elif isinstance(raw_results, list):
            # Format 2: Direct list
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
            # Format 3: String format (fallback)
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
                    
    except Exception as e:
        print(f"Error extracting structured results: {e}")
    
    return structured_results
```

## Common Issues and Solutions

### Issue 1: Fake Tavily URLs
**Problem**: Tavily sometimes returns fake URLs like `api.tavily.com` or `tavily.com/search`
**Solution**: Filter these out in processing:
```python
if 'api.tavily.com' not in result['url'] and 'tavily.com/search' not in result['url']:
    # Process the result
```

### Issue 2: Different Response Types
**Problem**: Tavily can return dict, list, or string formats
**Solution**: Use type checking and recursive processing:
```python
if hasattr(raw_results, 'get') and raw_results.get('results'):
    # Handle dict format
elif isinstance(raw_results, list):
    # Handle list format  
elif isinstance(raw_results, str):
    # Handle string format
```

### Issue 3: Missing Fields
**Problem**: Some results may lack required fields
**Solution**: Use `.get()` with defaults:
```python
result = {
    'url': item.get('url', ''),
    'title': item.get('title', ''),
    'content': item.get('content', ''),
    'score': item.get('score', 0.5),
    'published_date': item.get('published_date', ''),
    'domain': urlparse(item.get('url', '')).netloc
}
```

## Debug Examples

### Test Script Usage (from `/test_tavily_debug.py`)
```python
# Test 1: Direct API call
response = requests.post(
    'https://api.tavily.com/search',
    headers={'Authorization': f'Bearer {TAVILY_API_KEY}'},
    json={
        "query": "OpenAI GPT-4 news",
        "search_depth": "advanced",
        "include_answer": True,
        "include_raw_content": True,
        "max_results": 5
    }
)

# Test 2: LangChain wrapper
tavily_search = TavilySearchResults(
    max_results=5,
    search_depth="advanced",
    include_answer=True,
    include_raw_content=True,
    include_images=False
)
result = tavily_search.invoke({"query": "OpenAI GPT-4 news"})
```

## Filtering and Ranking

After extraction, results go through intelligent filtering:

### LLM-Based Filtering
The results are analyzed by an LLM (Deepseek) to:
- Filter out aggregated content (roundups, digests)
- Prioritize standalone articles
- Rank by relevance and quality
- Exclude category/topic pages

### Fallback Filtering
If LLM filtering fails, basic URL pattern exclusion is used:
```python
exclude_patterns = ['/category/', '/author/', '/tag/', 'newsletter', 'digest']
basic_filtered = [r for r in results if not any(exclude in r['url'].lower() 
                 for exclude in exclude_patterns)]
```

## Validation with Firecrawl

Final results are validated using Firecrawl API:
- Enhances content quality
- Validates URL accessibility
- Adds metadata
- Can reduce final count if URLs are inaccessible

## Best Practices

1. **Always handle multiple formats**: Dict, list, and string
2. **Filter fake URLs**: Remove `api.tavily.com` and `tavily.com/search`
3. **Use defaults**: Handle missing fields gracefully
4. **Debug logging**: Log response types and content for troubleshooting
5. **Progressive filtering**: Start broad, then narrow down results
6. **Fallback strategies**: Have backup processing for edge cases

## Example Response Processing

```python
async def process_tavily_results(query: str) -> List[Dict[str, Any]]:
    """Process Tavily search results with proper error handling"""
    try:
        # Execute search
        raw_results = await asyncio.to_thread(
            tavily_search.invoke,
            {"query": query}
        )
        
        # Debug logging
        print(f"Raw results type: {type(raw_results)}")
        if hasattr(raw_results, '__dict__'):
            print(f"Raw results attributes: {list(raw_results.__dict__.keys())}")
        
        # Extract structured results
        structured_results = extract_structured_results(raw_results)
        
        # Filter and validate
        filtered_results = filter_and_rank_results(structured_results)
        
        return filtered_results
        
    except Exception as e:
        print(f"Error processing Tavily results: {e}")
        return []
```

This comprehensive analysis should help understand the expected Tavily search result formats and how to handle them properly in the codebase.