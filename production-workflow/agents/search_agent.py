from langchain_core.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults
from typing import List, Dict, Any
import asyncio
import json
import re
from datetime import datetime
import os

# Initialize Tavily Search
tavily_search_tool = TavilySearchResults(
    max_results=10,
    search_depth="advanced"
)

def _filter_urls(urls: List[str], query: str, is_general_news: bool) -> List[str]:
    """Filter and prioritize URLs based on query type and relevance."""
    clean_urls = []
    
    # Official sources for tech news
    official_sources = [
        'techcrunch.com', 'theverge.com', 'arstechnica.com',
        'engadget.com', 'zdnet.com', 'cnet.com', 'reuters.com/technology',
        'bloomberg.com/technology', 'wsj.com/tech', 'venturebeat.com',
        'apple.com/newsroom', 'microsoft.com/news', 'google.com/press',
        'openai.com/blog', 'meta.com/news', 'nvidia.com/news',
        'tesla.com/blog', 'spacex.com/news', 'github.com/blog'
    ]
    
    # Excluded terms that indicate aggregated content or topic pages
    aggregated_terms = [
        'roundup', 'wrap-up', 'digest', 'top-25', '25-news',
        'weekly-news', 'daily-news', 'news-summary', 'best-of',
        'compilation', 'collection', 'listicle', '/section/',
        '/technology/', '/tech/', '/category/', '/topic/',
        'section.html', 'category.html', 'index.html'
    ]
    
    # For specific queries, check relevance to query terms
    query_terms = query.lower().split() if not is_general_news else []
    
    # First pass: prioritize official sources
    for url in urls:
        url = url.rstrip('.,;)')
        if any(domain in url.lower() for domain in official_sources):
            if not any(term in url.lower() for term in aggregated_terms):
                # For specific queries, check if URL contains query terms
                if not is_general_news:
                    url_relevance = sum(1 for term in query_terms if term in url.lower())
                    if url_relevance == 0:
                        continue
                
                # Check for article indicators
                current_year = datetime.now().strftime('/%Y/')
                recent_indicators = [current_year, '/article/', '/story/', '/news/', '-', '_']
                if any(indicator in url for indicator in recent_indicators):
                    if url not in clean_urls:
                        clean_urls.append(url)
    
    # Second pass: add other quality URLs if needed
    target_count = 5 if is_general_news else 8
    if len(clean_urls) < target_count:
        for url in urls:
            url = url.rstrip('.,;)')
            if not any(term in url.lower() for term in aggregated_terms):
                # For specific queries, check relevance
                if not is_general_news:
                    url_relevance = sum(1 for term in query_terms if term in url.lower())
                    if url_relevance == 0:
                        continue
                
                # Check for article indicators
                current_year = datetime.now().strftime('/%Y/')
                recent_indicators = [current_year, '/article/', '/story/', '/news/', '-', '_']
                if any(indicator in url for indicator in recent_indicators):
                    if url not in clean_urls and len(url) > 10:
                        clean_urls.append(url)
                    if len(clean_urls) >= target_count:
                        break
    
    return clean_urls[:target_count]

@tool
async def search_trending_tech_news(query: str = "latest trending tech news") -> str:
    """Search for trending technology news articles from official sources.
    Intelligently handles both general news requests and specific queries.
    
    Args:
        query: Search query for tech news (defaults to latest trending tech news)
        
    Returns:
        Formatted list of trending tech news with URLs and summaries
    """
    try:
        current_date = datetime.now()
        
        # Detect query type and adjust search strategy
        is_general_news = any(term in query.lower() for term in [
            "latest", "trending", "recent", "news", "today", "breaking", "current"
        ]) and len(query.split()) <= 4
        
        if is_general_news:
            # For general news requests, use broad search with date filtering
            yesterday = current_date.strftime('%Y-%m-%d')
            search_query = f"latest tech news {current_date.strftime('%Y')} after:{yesterday} -\"roundup\" -\"wrap up\" -\"top 25\" -\"weekly\" -\"daily digest\" site:techcrunch.com OR site:theverge.com OR site:arstechnica.com OR site:engadget.com"
        else:
            # For specific queries, focus on exact terms with broader time range
            search_query = f'"{query}" OR {query} {current_date.strftime('%Y')} technology news -\"roundup\" -\"wrap up\" -\"list\" -\"collection\""'
        
        print(f"🔍 Searching for: {search_query}")
        
        # Perform search
        search_results = await asyncio.to_thread(tavily_search_tool.invoke, {"query": search_query})
        
        # Parse and format results
        results_text = str(search_results)
        
        # Extract URLs and titles
        urls = re.findall(r'https?://[^\s\],"\']+', results_text)
        
        # Clean URLs and filter based on query type
        clean_urls = _filter_urls(urls, query, is_general_news)
        
        # Format the results based on query type
        if is_general_news:
            # For general news, provide 5 single article URLs only
            top_urls = clean_urls[:5]
            formatted_results = f"""
🚀 **LATEST TECH NEWS** 
📅 **Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**📰 TOP 5 TECH NEWS ARTICLES:**
"""
            for i, url in enumerate(top_urls, 1):
                formatted_results += f"{i}. {url}\n"
            
            formatted_results += f"""
**📋 NEXT STEPS:**
Choose which article to crawl: "Crawl article number [1-5]"
"""
        else:
            # For specific queries, provide detailed results for review
            formatted_results = f"""
🔍 **SEARCH RESULTS FOR: {query}** 
📅 **Search Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🎯 **Filter:** Specific query results from official sources

**📰 SEARCH RESULTS:**
{search_results}

**🔗 OFFICIAL SOURCE URLS FOUND:**
"""
            
            for i, url in enumerate(clean_urls[:8], 1):  # Show top 8 URLs
                formatted_results += f"{i}. {url}\n"
            
            formatted_results += f"""

**📋 NEXT STEPS:**
Please review the articles above and tell me which specific article(s) you'd like me to crawl for full content.

**Examples:**
- "Crawl article number 1"
- "Get full content from the TechCrunch article"
- "Scrape the article about [specific topic]"
- "Crawl this URL: [paste specific URL]"
"""
        
        return formatted_results
        
    except Exception as e:
        return f"❌ Error searching for tech news: {str(e)}"

@tool 
async def extract_article_urls(search_results: str, query: str = "") -> List[str]:
    """Extract clean URLs from search results.
    
    Args:
        search_results: Raw search results text
        query: Original search query for relevance filtering
        
    Returns:
        List of clean URLs found in the search results
    """
    try:
        urls = re.findall(r'https?://[^\s\],"\']+', search_results)
        
        # Determine if it's a general news query
        is_general_news = any(term in query.lower() for term in [
            "latest", "trending", "recent", "news", "today", "breaking", "current"
        ]) and len(query.split()) <= 4 if query else True
        
        # Use the same filtering logic as the main search function
        clean_urls = _filter_urls(urls, query or "general news", is_general_news)
        
        return clean_urls
        
    except Exception as e:
        print(f"Error extracting URLs: {e}")
        return []

@tool
async def smart_tech_search(query: str) -> str:
    """Smart search that adapts to different query types with improved relevance.
    
    Args:
        query: Search query (can be specific tools, general news, or tech topics)
        
    Returns:
        Formatted search results optimized for the query type
    """
    try:
        current_date = datetime.now()
        
        # Enhanced query analysis
        query_lower = query.lower()
        
        # Specific tech tool/product search
        is_specific_tool = any(term in query_lower for term in [
            'cli', 'api', 'sdk', 'library', 'framework', 'tool', 'app', 'software',
            'gemini', 'claude', 'openai', 'chatgpt', 'github', 'vscode', 'docker'
        ])
        
        # General news search
        is_general_news = any(term in query_lower for term in [
            "latest", "trending", "recent", "news", "today", "breaking", "current"
        ]) and len(query.split()) <= 4
        
        # Company/startup search
        is_company_search = any(term in query_lower for term in [
            'startup', 'company', 'funding', 'acquisition', 'ipo', 'investment'
        ])
        
        # Build optimized search query
        if is_specific_tool:
            # Focus on exact matches and documentation
            search_query = f'"{query}" OR "{query} release" OR "{query} update" OR "{query} announcement" technology news {current_date.strftime("%Y")} -"list" -"roundup" -"comparison"'
        elif is_company_search:
            search_query = f'"{query}" business technology news {current_date.strftime("%Y")} -"roundup" -"weekly" site:techcrunch.com OR site:theverge.com OR site:venturebeat.com'
        elif is_general_news:
            yesterday = current_date.strftime('%Y-%m-%d')
            search_query = f"latest tech news {current_date.strftime('%Y')} after:{yesterday} -\"roundup\" -\"wrap up\" -\"top 25\" site:techcrunch.com OR site:theverge.com OR site:arstechnica.com OR site:engadget.com"
        else:
            # Balanced search for other topics
            search_query = f'{query} technology news {current_date.strftime("%Y")} -"roundup" -"wrap up" -"list"'
        
        print(f"🧠 Smart Search Query: {search_query}")
        
        # Perform search with higher result count for specific queries
        max_results = 15 if is_specific_tool else 10
        tavily_tool = TavilySearchResults(max_results=max_results, search_depth="advanced")
        search_results = await asyncio.to_thread(tavily_tool.invoke, {"query": search_query})
        
        # Extract and filter URLs
        results_text = str(search_results)
        urls = re.findall(r'https?://[^\s\],"\']+', results_text)
        clean_urls = _filter_urls(urls, query, is_general_news)
        
        # Enhanced scoring for specific tools
        if is_specific_tool:
            clean_urls = _score_and_rank_urls(clean_urls, query)
        
        # Format results based on query type
        if is_general_news:
            formatted_results = f"""
🚀 **LATEST TECH NEWS** 
📅 **Date:** {current_date.strftime('%Y-%m-%d %H:%M:%S')}

**📰 TOP 5 TECH NEWS ARTICLES:**
"""
            for i, url in enumerate(clean_urls[:5], 1):
                formatted_results += f"{i}. {url}\n"
        else:
            formatted_results = f"""
🔍 **SMART SEARCH RESULTS: {query}** 
📅 **Date:** {current_date.strftime('%Y-%m-%d %H:%M:%S')}
🎯 **Query Type:** {'Specific Tool' if is_specific_tool else 'Company/Business' if is_company_search else 'General Topic'}

**📰 SEARCH RESULTS:**
{search_results}

**🔗 RELEVANT URLS FOUND:**
"""
            for i, url in enumerate(clean_urls[:8], 1):
                formatted_results += f"{i}. {url}\n"
        
        formatted_results += f"""
**📋 NEXT STEPS:**
Choose which article to crawl: "Crawl article number [1-{min(len(clean_urls), 8)}]"
"""
        
        return formatted_results
        
    except Exception as e:
        return f"❌ Smart search error: {str(e)}"

def _score_and_rank_urls(urls: List[str], query: str) -> List[str]:
    """Score and rank URLs based on relevance to specific query terms."""
    query_terms = query.lower().split()
    scored_urls = []
    
    for url in urls:
        score = 0
        url_lower = url.lower()
        
        # Exact query match in URL
        if query.lower() in url_lower:
            score += 10
        
        # Individual term matches
        for term in query_terms:
            if term in url_lower:
                score += 2
        
        # Bonus for official/documentation sites
        if any(domain in url_lower for domain in ['github.com', 'docs.', 'blog.', '.dev', 'developer.']):
            score += 3
        
        # Bonus for recent articles (contain year)
        if str(datetime.now().year) in url:
            score += 1
        
        scored_urls.append((score, url))
    
    # Sort by score (descending) and return URLs
    scored_urls.sort(key=lambda x: x[0], reverse=True)
    return [url for score, url in scored_urls]

# Create search agent tools list
search_tools = [search_trending_tech_news, extract_article_urls, smart_tech_search]