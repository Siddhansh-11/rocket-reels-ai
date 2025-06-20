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

@tool
async def search_trending_tech_news(query: str = "latest trending tech news") -> str:
    """Search for trending technology news articles.
    
    Args:
        query: Search query for tech news (defaults to latest trending tech news)
        
    Returns:
        Formatted list of trending tech news with URLs and summaries
    """
    try:
        # Enhanced search query for better results
        search_query = f"{query} {datetime.now().strftime('%Y')} technology breaking news"
        print(f"🔍 Searching for: {search_query}")
        
        # Perform search
        search_results = await asyncio.to_thread(tavily_search_tool.invoke, {"query": search_query})
        
        # Parse and format results
        results_text = str(search_results)
        
        # Extract URLs and titles
        urls = re.findall(r'https?://[^\s\],"\']+', results_text)
        
        # Clean URLs
        clean_urls = []
        priority_domains = [
            'techcrunch.com', 'theverge.com', 'wired.com', 'arstechnica.com',
            'engadget.com', 'zdnet.com', 'cnet.com', 'reuters.com/technology',
            'bloomberg.com/technology', 'wsj.com/tech', 'venturebeat.com'
        ]
        
        # Prioritize quality tech news sources
        for url in urls:
            url = url.rstrip('.,;)')
            if any(domain in url for domain in priority_domains):
                if url not in clean_urls:
                    clean_urls.append(url)
        
        # Add other URLs if we don't have enough
        if len(clean_urls) < 5:
            for url in urls:
                url = url.rstrip('.,;)')
                if url not in clean_urls and len(url) > 10:
                    clean_urls.append(url)
                if len(clean_urls) >= 8:
                    break
        
        # Format the results for human selection
        formatted_results = f"""
🚀 **TRENDING TECH NEWS FOUND** 
📅 **Search Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔍 **Query:** {query}

**📰 SEARCH RESULTS:**
{search_results}

**🔗 PRIORITY ARTICLE URLS FOUND:**
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

**💡 WAITING FOR HUMAN INPUT:** Which article would you like me to crawl for full content?
"""
        
        return formatted_results
        
    except Exception as e:
        return f"❌ Error searching for tech news: {str(e)}"

@tool 
async def extract_article_urls(search_results: str) -> List[str]:
    """Extract clean URLs from search results.
    
    Args:
        search_results: Raw search results text
        
    Returns:
        List of clean URLs found in the search results
    """
    try:
        urls = re.findall(r'https?://[^\s\],"\']+', search_results)
        
        # Clean and filter URLs
        clean_urls = []
        priority_domains = [
            'techcrunch.com', 'theverge.com', 'wired.com', 'arstechnica.com',
            'engadget.com', 'zdnet.com', 'cnet.com', 'reuters.com/technology',
            'bloomberg.com/technology', 'wsj.com/tech'
        ]
        
        # Prioritize quality tech news sources
        for url in urls:
            url = url.rstrip('.,;)')
            if any(domain in url for domain in priority_domains):
                if url not in clean_urls:
                    clean_urls.append(url)
        
        # Add other URLs if we don't have enough
        if len(clean_urls) < 5:
            for url in urls:
                url = url.rstrip('.,;)')
                if url not in clean_urls and len(url) > 10:
                    clean_urls.append(url)
                if len(clean_urls) >= 8:
                    break
        
        return clean_urls[:8]  # Return top 8 URLs
        
    except Exception as e:
        print(f"Error extracting URLs: {e}")
        return []

# Create search agent tools list
search_tools = [search_trending_tech_news, extract_article_urls]