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
async def search_content_ideas(query: str = "trending content ideas") -> str:
    """Search for trending content ideas and topics for video creation.
    
    Args:
        query: Search query for content ideas (defaults to trending content ideas)
        
    Returns:
        Formatted list of trending content ideas with URLs and summaries
    """
    try:
        # Enhanced search query for better results
        search_query = f"{query} {datetime.now().strftime('%Y')} viral trending topics"
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
            'engadget.com', 'zdnet.com', 'cnet.com', 'reuters.com',
            'bloomberg.com', 'wsj.com', 'venturebeat.com', 'mashable.com',
            'youtube.com', 'tiktok.com', 'instagram.com'
        ]
        
        # Prioritize quality sources
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
        
        # Format the results
        formatted_results = f"""
🎬 **TRENDING CONTENT IDEAS FOUND** 
📅 **Search Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔍 **Query:** {query}

**📰 SEARCH RESULTS:**
{search_results}

**🔗 RELEVANT URLS FOUND:**
"""
        
        for i, url in enumerate(clean_urls[:8], 1):  # Show top 8 URLs
            formatted_results += f"{i}. {url}\n"
        
        formatted_results += f"""

**📋 NEXT STEPS:**
You can now use these search results to inform your content creation workflow.
The search results contain trending topics and ideas that can be used for script writing and content planning.
"""
        
        return formatted_results
        
    except Exception as e:
        return f"❌ Error searching for content ideas: {str(e)}"

@tool 
async def extract_trending_topics(search_results: str) -> List[str]:
    """Extract trending topics from search results.
    
    Args:
        search_results: Raw search results text
        
    Returns:
        List of trending topics extracted from the search results
    """
    try:
        # Common trending topic keywords
        trending_keywords = [
            'AI', 'artificial intelligence', 'ChatGPT', 'machine learning',
            'blockchain', 'cryptocurrency', 'NFT', 'metaverse', 'VR', 'AR',
            'startup', 'tech news', 'innovation', 'breakthrough', 'viral',
            'trending', 'social media', 'TikTok', 'Instagram', 'YouTube'
        ]
        
        topics = []
        text_lower = search_results.lower()
        
        for keyword in trending_keywords:
            if keyword.lower() in text_lower:
                topics.append(keyword)
        
        # Also extract quoted phrases that might be trending topics
        quoted_phrases = re.findall(r'"([^"]*)"', search_results)
        for phrase in quoted_phrases:
            if len(phrase.split()) <= 4 and len(phrase) > 3:  # Short phrases only
                topics.append(phrase)
        
        return list(set(topics))[:10]  # Return unique topics, max 10
        
    except Exception as e:
        print(f"Error extracting topics: {e}")
        return []

# Create search agent tools list
search_tools = [search_content_ideas, extract_trending_topics]

async def search_tech_news(query: str) -> Dict[str, Any]:
    """
    Search for tech news based on query.
    This is the main function called by the workflow.
    
    Args:
        query: The search query from the user
        
    Returns:
        Dict with search results and formatted output
    """
    try:
        # Check for Tavily API key
        tavily_api_key = os.getenv("TAVILY_API_KEY")
        
        if not tavily_api_key or tavily_api_key == "your_tavily_api_key":
            # Return mock data for testing
            formatted_results = f"""🚀 **TRENDING TECH NEWS**
📅 **Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

**Top Tech Stories:**

1. **OpenAI Announces GPT-5 with Breakthrough Reasoning**
🔗 https://techcrunch.com/2024/openai-gpt5
OpenAI's latest model shows unprecedented reasoning capabilities...

2. **Apple Vision Pro 2 Features Leaked**
🔗 https://theverge.com/apple-vision-pro-2
Next-gen AR headset to feature 8K displays and lighter design...

3. **Google's Quantum Breakthrough**
🔗 https://arstechnica.com/google-quantum
New quantum processor achieves practical quantum advantage...

4. **Tesla Robotaxi Fleet Launch**
🔗 https://electrek.co/tesla-robotaxi
Autonomous taxi service begins in major cities...

5. **Microsoft AI Copilot Updates**
🔗 https://zdnet.com/microsoft-copilot
AI coding assistant can now build entire applications...

💡 **Note:** Using mock data. Set TAVILY_API_KEY in .env for real results."""
            
            return {
                "status": "success",
                "results": formatted_results,
                "is_mock": True
            }
        
        # Use Tavily for real search
        search_query = f"latest trending technology news {query} {datetime.now().strftime('%Y-%m')}"
        
        # Initialize with API key
        tavily_search = TavilySearchResults(
            max_results=10,
            search_depth="advanced",
            api_key=tavily_api_key
        )
        
        # Perform search
        search_results = await asyncio.to_thread(tavily_search.invoke, {"query": search_query})
        
        # Format results
        formatted_results = f"""🚀 **TRENDING TECH NEWS**
📅 **Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
🔍 **Query:** {query}

**Search Results:**

"""
        
        if isinstance(search_results, list):
            for i, result in enumerate(search_results[:5], 1):
                if isinstance(result, dict):
                    title = result.get('title', 'No title')
                    url = result.get('url', '')
                    content = result.get('content', '')[:200] + '...'
                    
                    formatted_results += f"""**{i}. {title}**
🔗 {url}
{content}

"""
        
        return {
            "status": "success", 
            "results": formatted_results,
            "is_mock": False
        }
        
    except Exception as e:
        return {
            "status": "error",
            "results": f"❌ Error searching: {str(e)}",
            "error": str(e)
        }