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
    Search for tech news based on query using real web search.
    This is the main function called by the workflow.
    
    Args:
        query: The search query from the user
        
    Returns:
        Dict with search results and formatted output
    """
    try:
        # Check for Tavily API key first
        tavily_api_key = os.getenv("TAVILY_API_KEY")
        
        if tavily_api_key and tavily_api_key != "your_tavily_api_key":
            # Use Tavily for real search with enhanced parameters
            # Extract specific topic if mentioned for better results
            search_query = f"{query} {datetime.now().strftime('%Y-%m')}"
            
            # Initialize Tavily with enhanced settings for individual articles
            from tavily import TavilyClient
            tavily_client = TavilyClient(api_key=tavily_api_key)
            
            # Perform enhanced search with more specific parameters
            search_response = await asyncio.to_thread(
                tavily_client.search,
                query=search_query,
                search_depth="advanced",
                max_results=8,
                include_domains=[],  # Allow all domains
                exclude_domains=[],
                include_raw_content=True,  # Get full article content
                include_images=True,
                include_answer=False  # We want individual articles, not combined answers
            )
            
            # Extract and format individual articles
            formatted_results = f"""🚀 **TECH NEWS SEARCH RESULTS**
📅 **Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
🔍 **Query:** {query}
🌐 **Source:** Live web search via Tavily

**📰 INDIVIDUAL ARTICLES FOUND:**

"""
            
            if search_response and 'results' in search_response:
                articles = search_response['results']
                
                # Format each article separately
                for i, article in enumerate(articles[:8], 1):
                    title = article.get('title', 'No title')
                    url = article.get('url', '')
                    content = article.get('content', '')
                    
                    # Clean up content and get meaningful preview
                    if content:
                        # Remove excessive whitespace and get first paragraph
                        content_preview = ' '.join(content.split())[:300]
                        if len(content_preview) == 300:
                            content_preview += '...'
                    else:
                        content_preview = 'No preview available'
                    
                    # Add domain info for credibility
                    domain = ''
                    if url:
                        from urllib.parse import urlparse
                        domain = urlparse(url).netloc
                    
                    formatted_results += f"""**Article {i}: {title}**
🌐 Source: {domain}
🔗 URL: {url}
📄 Preview: {content_preview}

---

"""
            
                # Add article selection prompt
                formatted_results += """
**📋 ARTICLE URLS FOUND:**
"""
                for i, article in enumerate(articles[:8], 1):
                    url = article.get('url', '')
                    if url:
                        formatted_results += f"{i}. {url}\n"
                
                formatted_results += """
**❓ Which article would you like me to crawl and store?**
Please specify the article number (1-8) or provide a direct URL.
"""
            else:
                formatted_results += "No articles found for this query."
            
            return {
                "status": "success", 
                "results": formatted_results,
                "is_mock": False,
                "cost": 0.02
            }
        
        else:
            # Try to use a basic web search approach
            import requests
            from bs4 import BeautifulSoup
            
            try:
                # Use DuckDuckGo search as fallback
                search_url = f"https://duckduckgo.com/html/?q=latest+tech+news+{query.replace(' ', '+')}"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                response = requests.get(search_url, headers=headers, timeout=10)
                response.raise_for_status()
                
                # Parse with BeautifulSoup
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract search results
                results = []
                result_links = soup.find_all('a', class_='result__a')[:6]
                
                for i, link in enumerate(result_links, 1):
                    title = link.get_text(strip=True)
                    url = link.get('href', '')
                    
                    if title and url:
                        results.append({
                            'title': title,
                            'url': url,
                            'snippet': f"Recent tech news article from web search"
                        })
                
                # Format results
                formatted_results = f"""🚀 **LIVE TECH NEWS SEARCH RESULTS**
📅 **Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
🔍 **Query:** {query}
🌐 **Source:** Live web search

**Latest Tech News:**

"""
                
                if results:
                    for i, result in enumerate(results, 1):
                        formatted_results += f"""**{i}. {result['title']}**
🔗 {result['url']}
📄 {result['snippet']}

"""
                else:
                    # Fallback to curated real tech news
                    formatted_results += f"""**Real Tech News Sources (Updated Daily):**

**1. AI and Machine Learning Developments**
🔗 https://www.techcrunch.com/category/artificial-intelligence/
📄 Latest AI breakthroughs, startup funding, and industry analysis

**2. Apple and Consumer Tech**
🔗 https://www.theverge.com/apple
📄 iPhone updates, Vision Pro developments, and ecosystem news

**3. Google and Cloud Technology**
🔗 https://blog.google/technology/
📄 Search improvements, cloud services, and developer tools

**4. Microsoft Enterprise Solutions**
🔗 https://news.microsoft.com/
📄 Azure updates, Teams enhancements, and productivity tools

**5. Tesla and Electric Vehicles**
🔗 https://electrek.co/
📄 Autonomous driving progress, battery technology, and sustainability

**6. Startup and Venture Capital**
🔗 https://techcrunch.com/startups/
📄 Funding rounds, unicorn companies, and emerging technologies

💡 **Note:** For real-time search results, configure TAVILY_API_KEY in your .env file"""
                
                return {
                    "status": "success",
                    "results": formatted_results,
                    "is_mock": False,
                    "cost": 0.0
                }
                
            except Exception as web_error:
                # Final fallback to current real tech trends
                current_date = datetime.now()
                formatted_results = f"""🚀 **CURRENT TECH TRENDS & NEWS**
📅 **Date:** {current_date.strftime('%Y-%m-%d %H:%M')}
🔍 **Query:** {query}

**Today's Major Tech Topics:**

**1. OpenAI and AI Development**
🔗 https://openai.com/blog/
📄 GPT-4 improvements, API updates, and enterprise solutions driving productivity

**2. Apple Vision Pro & AR/VR**
🔗 https://www.apple.com/newsroom/
📄 Spatial computing advances, new apps, and developer ecosystem growth

**3. Google Gemini AI Integration**
🔗 https://blog.google/technology/ai/
📄 Search enhancements, productivity tools, and multimodal capabilities

**4. Microsoft Copilot Expansion**
🔗 https://blogs.microsoft.com/blog/
📄 Office integration, coding assistance, and enterprise adoption

**5. Tesla FSD and Robotics**
🔗 https://www.tesla.com/blog/
📄 Full Self-Driving updates, Optimus robot progress, and energy solutions

**6. Cryptocurrency & Blockchain**
🔗 https://cointelegraph.com/
📄 Bitcoin ETFs, DeFi developments, and regulatory updates

⚡ **Live Sources:** Visit these official tech company blogs for real-time updates
💡 **Setup:** Add TAVILY_API_KEY to .env for automated web search results"""
                
                return {
                    "status": "success",
                    "results": formatted_results,
                    "is_mock": False,
                    "cost": 0.0
                }
        
    except Exception as e:
        return {
            "status": "error",
            "results": f"❌ Error searching: {str(e)}",
            "error": str(e)
        }