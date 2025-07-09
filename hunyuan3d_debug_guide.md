# Hunyuan3D-PolyGen Search Debug Guide

This guide provides specific debugging steps for the "Hunyuan3D-PolyGen" search filtering issue where the search agent returns "No high-quality standalone tech articles found" despite having a search strategy.

## Problem Analysis

Based on the codebase analysis, the issue is in the intelligent filtering pipeline where results are being filtered out during the LLM-based analysis phase.

## Root Cause Identification

### 1. Search Query Generation
The query "Hunyuan3D-PolyGen" triggers `specific_topic` strategy which generates:
- `"Hunyuan3D-PolyGen" 2024 -roundup -newsletter -digest`
- `Hunyuan3D-PolyGen announcement OR release 2024`
- `Hunyuan3D-PolyGen news after:2024-07-02`
- `Hunyuan3D-PolyGen official blog OR press release`

### 2. Tavily Search Results
The search likely returns some results, but they're being filtered out in the `_intelligent_filter_and_rank` function.

### 3. LLM Filtering Logic
The Deepseek LLM may be:
- Too strict in filtering niche technical terms
- Failing to understand "Hunyuan3D-PolyGen" as a valid AI model name
- Rejecting results due to domain patterns or content structure

## Debug Steps

### Step 1: Add Debug Logging to Search Agent

Add this debugging code to `/production-workflow/agents/search_agent.py`:

```python
# In _intelligent_filter_and_rank function, add after line 300:
print(f"🔍 DEBUG: Query being analyzed: {query}")
print(f"🔍 DEBUG: Strategy: {strategy}")
print(f"🔍 DEBUG: Results to analyze: {len(results_to_analyze)}")

# Before the LLM analysis (around line 398):
print(f"🔍 DEBUG: Sending to LLM for analysis:")
for i, result in enumerate(results_to_analyze[:3], 1):
    print(f"  {i}. URL: {result['url']}")
    print(f"     Title: {result['title']}")
    print(f"     Content: {result['content'][:100]}...")

# After LLM response (around line 400):
print(f"🔍 DEBUG: LLM response length: {len(result_text)}")
print(f"🔍 DEBUG: LLM response preview: {result_text[:200]}...")
```

### Step 2: Test Individual Components

Create a test script to isolate the issue:

```python
#!/usr/bin/env python3
"""
Debug script specifically for Hunyuan3D-PolyGen search issue
"""

import asyncio
from production_workflow.agents.search_agent import IntelligentSearchService

async def debug_hunyuan3d_search():
    """Debug the Hunyuan3D-PolyGen search process"""
    service = IntelligentSearchService()
    query = "Hunyuan3D-PolyGen"
    
    print(f"🔍 Debugging search for: {query}")
    
    # Step 1: Test query intent analysis
    print("\n1. Query Intent Analysis:")
    strategy = await service._analyze_query_intent(query)
    print(f"Strategy: {strategy}")
    
    # Step 2: Test search query generation
    print("\n2. Search Query Generation:")
    search_queries = await service._generate_search_queries(query, strategy)
    print(f"Generated queries: {search_queries}")
    
    # Step 3: Test raw search results
    print("\n3. Raw Search Results:")
    for i, search_query in enumerate(search_queries, 1):
        print(f"\n  Query {i}: {search_query}")
        try:
            raw_results = await asyncio.to_thread(
                service.search_provider.invoke,
                {"query": search_query}
            )
            structured = service._extract_structured_results(raw_results)
            print(f"  Raw results type: {type(raw_results)}")
            print(f"  Structured results: {len(structured)}")
            if structured:
                print(f"  Sample result: {structured[0]['title']} - {structured[0]['url']}")
        except Exception as e:
            print(f"  Error: {e}")
    
    # Step 4: Test full search
    print("\n4. Full Search Process:")
    results = await service.search(query, max_results=5)
    print(f"Final results: {len(results.get('results', []))}")
    
    if results.get('results'):
        for i, result in enumerate(results['results'], 1):
            print(f"  {i}. {result['title']}")
            print(f"     {result['url']}")
    else:
        print("  No final results - debugging filtering...")

if __name__ == "__main__":
    asyncio.run(debug_hunyuan3d_search())
```

### Step 3: Test with Alternative Queries

Test these variations to isolate the issue:

```python
test_queries = [
    "Hunyuan3D-PolyGen",           # Original
    "Hunyuan3D PolyGen",           # Without hyphen
    "Hunyuan 3D PolyGen",          # With spaces
    "Hunyuan3D",                   # Shortened
    "PolyGen",                     # Second part only
    "Hunyuan3D-PolyGen AI model",  # With context
    "Tencent Hunyuan3D-PolyGen",   # With company
]
```

### Step 4: Check LLM Filtering Logic

The issue might be in the LLM prompt. The current filtering logic is:

```python
# For niche technical terms, it should use more lenient filtering
is_niche_tech = any(char.isdigit() for char in query) or any(keyword in query.lower() for keyword in ['3d', 'ai', 'model', 'gen', 'tech', 'api', 'sdk', 'framework', 'library'])
```

"Hunyuan3D-PolyGen" should trigger `is_niche_tech = True` because:
- Contains digits (`3`)
- Contains `3d` in the name
- Contains `gen` in the name

### Step 5: Check for Response Format Issues

The issue might be that Tavily returns results in an unexpected format for this specific query. Add this debug code:

```python
# In _extract_structured_results function, add:
print(f"🔍 DEBUG: Raw results type: {type(raw_results)}")
print(f"🔍 DEBUG: Raw results content: {str(raw_results)[:1000]}...")

if isinstance(raw_results, str):
    print(f"🔍 DEBUG: String response detected")
    urls = re.findall(r'https?://[^\s\],"\']+', raw_results)
    print(f"🔍 DEBUG: Found URLs: {urls}")
```

## Potential Solutions

### Solution 1: Adjust LLM Filtering for Niche Terms

Modify the LLM prompt to be more lenient for AI model names:

```python
# In _intelligent_filter_and_rank, for niche tech terms:
if is_niche_tech:
    prompt = f"""Analyze these search results for the AI model/technology query: "{query}"

This appears to be a specific AI model or technology name. Be MORE LENIENT in filtering.

INCLUDE results that:
1. Mention "{query}" or related AI/technology terms
2. Discuss AI models, machine learning, or 3D generation
3. Are from research papers, blogs, or tech news sites
4. Even if they're not perfect matches, if they're relevant to AI/tech

ONLY EXCLUDE results that are:
- Completely unrelated to AI/technology
- Spam or advertising with no technical content
- Broken links or error pages

For AI model names like "{query}", cast a WIDER net and include potentially relevant results.
"""
```

### Solution 2: Add Fallback for Zero Results

When LLM filtering returns no results, use a more permissive approach:

```python
# After LLM filtering, if no results:
if not filtered_results and results_to_analyze:
    print("🔄 LLM filtering returned no results, using permissive fallback")
    
    # For AI model names, use keyword matching
    query_keywords = query.lower().replace('-', ' ').split()
    keyword_filtered = []
    
    for result in results_to_analyze:
        result_text = (result.get('title', '') + ' ' + result.get('content', '')).lower()
        if any(keyword in result_text for keyword in query_keywords):
            keyword_filtered.append(result)
    
    if keyword_filtered:
        print(f"✅ Permissive filtering found {len(keyword_filtered)} results")
        return keyword_filtered[:max_results]
```

### Solution 3: Adjust Search Query Strategy

For AI model names, generate more targeted queries:

```python
# In _generate_search_queries, add special handling for AI models:
if any(indicator in query.lower() for indicator in ['3d', 'ai', 'model', 'gen', 'gpt', 'llm']):
    # Add AI-specific query variations
    queries.extend([
        f'{query} AI model research paper',
        f'{query} artificial intelligence',
        f'{query} machine learning',
        f'{query} "AI model"',
        f'{query} github OR arxiv OR huggingface'
    ])
```

## Testing and Validation

1. **Run the debug script** to see exact failure point
2. **Test with alternative queries** to isolate the issue
3. **Check LLM responses** for filtering logic
4. **Verify Tavily results** are being returned
5. **Test fallback mechanisms** work correctly

## Expected Outcomes

After implementing these fixes:
- The search should return relevant results for "Hunyuan3D-PolyGen"
- Debug logging should show where results are being filtered
- Fallback mechanisms should catch edge cases
- The system should handle similar AI model names better

## Implementation Priority

1. **High Priority**: Add debug logging to identify exact failure point
2. **Medium Priority**: Implement permissive fallback for zero results
3. **Low Priority**: Optimize search query generation for AI models

This comprehensive debugging approach should resolve the "Hunyuan3D-PolyGen" search filtering issue.