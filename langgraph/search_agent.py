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
    """Search for trending technology news articles from official sources.
    Filters out aggregated news articles and focuses on single, latest announcements.
    
    Args:
        query: Search query for tech news (defaults to latest trending tech news)
        
    Returns:
        Formatted list of trending tech news with URLs and summaries
    """
    try:
        # Enhanced search query for recent individual articles - exclude aggregated content and old articles
        current_date = datetime.now()
        yesterday = current_date.strftime('%Y-%m-%d')
        search_query = f"{query} {current_date.strftime('%Y')} technology breaking news after:{yesterday} -\"roundup\" -\"wrap up\" -\"top 25\" -\"25 news\" -\"news digest\" -\"weekly roundup\" -\"daily digest\" -\"section\" -\"topic\" -\"category\" -\"/technology/\" -\"/tech/\" site:techcrunch.com OR site:theverge.com OR site:arstechnica.com OR site:engadget.com"
        print(f"🔍 Searching for: {search_query}")
        
        # Perform search
        search_results = await asyncio.to_thread(tavily_search_tool.invoke, {"query": search_query})
        
        # Parse and format results
        results_text = str(search_results)
        
        # Extract URLs and titles
        urls = re.findall(r'https?://[^\s\],"\']+', results_text)
        
        # Clean URLs and filter out aggregated content
        clean_urls = []
        official_sources = [
            'techcrunch.com', 'theverge.com', 'arstechnica.com',
            'engadget.com', 'zdnet.com', 'cnet.com', 'reuters.com/technology',
            'bloomberg.com/technology', 'wsj.com/tech', 'venturebeat.com',
            'apple.com/newsroom', 'microsoft.com/news', 'google.com/press',
            'openai.com/blog', 'meta.com/news', 'nvidia.com/news',
            'tesla.com/blog', 'spacex.com/news'
        ]
        
        # Excluded terms that indicate aggregated content or topic pages
        aggregated_terms = [
            'roundup', 'wrap-up', 'digest', 'top-25', '25-news',
            'weekly-news', 'daily-news', 'news-summary', 'best-of',
            'compilation', 'collection', 'listicle', '/section/',
            '/technology/', '/tech/', '/category/', '/topic/',
            'section.html', 'category.html', 'index.html'
        ]
        
        # Prioritize official sources and single-topic articles with specific article indicators
        for url in urls:
            url = url.rstrip('.,;)')
            # Check if it's from official sources
            if any(domain in url.lower() for domain in official_sources):
                # Check if it's not an aggregated article or topic page
                if not any(term in url.lower() for term in aggregated_terms):
                    # Prefer URLs that look like individual articles (have dates, titles, or article indicators)
                    current_year = datetime.now().strftime('/%Y/')
                    recent_indicators = [current_year, '/article/', '/story/', '/news/', '-', '_']
                    if any(indicator in url for indicator in recent_indicators):
                        if url not in clean_urls:
                            clean_urls.append(url)
        
        # Add other quality URLs if we don't have enough from official sources
        if len(clean_urls) < 5:
            for url in urls:
                url = url.rstrip('.,;)')
                # Skip aggregated content URLs and topic pages
                if not any(term in url.lower() for term in aggregated_terms):
                    # Only add URLs that look like individual articles
                    current_year = datetime.now().strftime('/%Y/')
                    recent_indicators = [current_year, '/article/', '/story/', '/news/', '-', '_']
                    if any(indicator in url for indicator in recent_indicators):
                        if url not in clean_urls and len(url) > 10:
                            clean_urls.append(url)
                        if len(clean_urls) >= 8:
                            break
        
        # Format the results for human selection
        formatted_results = f"""
🚀 **OFFICIAL TECH NEWS FOUND** 
📅 **Search Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔍 **Query:** {query}
🎯 **Filter:** Single articles from official sources (no aggregated content)

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
        
        # Clean and filter URLs - prioritize official sources
        clean_urls = []
        official_sources = [
            'techcrunch.com', 'theverge.com', 'arstechnica.com',
            'engadget.com', 'zdnet.com', 'cnet.com', 'reuters.com/technology',
            'bloomberg.com/technology', 'wsj.com/tech', 'venturebeat.com',
            'apple.com/newsroom', 'microsoft.com/news', 'google.com/press',
            'openai.com/blog', 'meta.com/news', 'nvidia.com/news',
            'tesla.com/blog', 'spacex.com/news'
        ]
        
        # Excluded terms that indicate aggregated content or topic pages
        aggregated_terms = [
            'roundup', 'wrap-up', 'digest', 'top-25', '25-news',
            'weekly-news', 'daily-news', 'news-summary', 'best-of',
            'compilation', 'collection', 'listicle', '/section/',
            '/technology/', '/tech/', '/category/', '/topic/',
            'section.html', 'category.html', 'index.html'
        ]
        
        # Prioritize official sources and single-topic articles with specific article indicators
        for url in urls:
            url = url.rstrip('.,;)')
            # Check if it's from official sources
            if any(domain in url.lower() for domain in official_sources):
                # Check if it's not an aggregated article or topic page
                if not any(term in url.lower() for term in aggregated_terms):
                    # Prefer URLs that look like individual articles (have dates, titles, or article indicators)
                    current_year = datetime.now().strftime('/%Y/')
                    recent_indicators = [current_year, '/article/', '/story/', '/news/', '-', '_']
                    if any(indicator in url for indicator in recent_indicators):
                        if url not in clean_urls:
                            clean_urls.append(url)
        
        # Add other quality URLs if we don't have enough from official sources
        if len(clean_urls) < 5:
            for url in urls:
                url = url.rstrip('.,;)')
                # Skip aggregated content URLs and topic pages
                if not any(term in url.lower() for term in aggregated_terms):
                    # Only add URLs that look like individual articles
                    current_year = datetime.now().strftime('/%Y/')
                    recent_indicators = [current_year, '/article/', '/story/', '/news/', '-', '_']
                    if any(indicator in url for indicator in recent_indicators):
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