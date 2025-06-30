"""
Intelligent Search Agent powered by Deepseek LLM and Firecrawl
Finds high-quality, standalone tech news without hardcoded rules
"""

from langchain_core.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults
from typing import List, Dict, Any, Optional
import asyncio
import json
import re
from datetime import datetime, timedelta
import os
from urllib.parse import urlparse
from dotenv import load_dotenv
import requests

# LangChain imports
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.messages import HumanMessage

# Load environment variables
load_dotenv()

# Initialize Deepseek LLM
deepseek_model = ChatLiteLLM(
    model="deepseek/deepseek-chat",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    max_tokens=2000,
    temperature=0.1
)

# Initialize Firecrawl
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")

# Initialize Tavily search provider with advanced settings
tavily_search = TavilySearchResults(
    max_results=20,  # Get more candidates for better filtering
    search_depth="advanced",
    include_answer=True,
    include_raw_content=True,
    include_images=False
)

class IntelligentSearchService:
    """AI-powered search service that understands context and finds quality content"""
    
    def __init__(self):
        """Initialize the search service"""
        self.llm = deepseek_model
        self.search_provider = tavily_search
        self.firecrawl_api_key = FIRECRAWL_API_KEY
    
    async def search(self, query: str, max_results: int = 8) -> Dict[str, Any]:
        """Execute intelligent search with contextual understanding"""
        try:
            # Step 1: Analyze the query to understand user intent
            search_strategy = await self._analyze_query_intent(query)
            
            # Step 2: Generate optimized search queries based on intent
            search_queries = await self._generate_search_queries(query, search_strategy)
            
            # Step 3: Execute searches with multiple query variations
            all_results = []
            for search_query in search_queries:
                try:
                    results = await asyncio.to_thread(
                        self.search_provider.invoke,
                        {"query": search_query}
                    )
                    all_results.extend(self._extract_structured_results(results))
                except Exception as e:
                    print(f"⚠️ Search query failed: {search_query} - {e}")
                    continue
            
            # Step 4: Use LLM to filter and rank results intelligently
            filtered_results = await self._intelligent_filter_and_rank(query, search_strategy, all_results)
            
            # Step 5: Validate results with Firecrawl to ensure quality
            validated_results = await self._validate_with_firecrawl(filtered_results[:max_results])
            
            return {
                "query": query,
                "search_strategy": search_strategy,
                "search_queries": search_queries,
                "results": validated_results,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Search error: {str(e)}")
            return {
                "query": query,
                "error": str(e),
                "results": [],
                "timestamp": datetime.now().isoformat()
            }
    
    async def _analyze_query_intent(self, query: str) -> Dict[str, Any]:
        """Use LLM to analyze user query and determine search strategy"""
        prompt = f"""Analyze this search query and determine the user's intent: "{query}"

Your task is to understand what the user is looking for and provide a search strategy.

Consider:
1. Is this asking for latest/general tech news or something specific?
2. Are there specific companies, products, or technologies mentioned?
3. What time sensitivity does this have? (breaking news, recent developments, etc.)
4. What type of content would be most valuable? (announcements, analysis, tutorials, etc.)

Return a JSON object with this structure:
{{
  "intent_type": "general_news|specific_topic|company_news|product_news|breaking_news",
  "key_entities": ["list", "of", "important", "keywords"],
  "time_sensitivity": "breaking|recent|any",
  "content_preferences": ["announcements", "analysis", "tutorials", "reviews"],
  "priority_sources": ["list", "of", "preferred", "source", "types"],
  "search_focus": "brief description of what to focus on"
}}

Return ONLY the JSON, no additional text."""

        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            strategy_text = response.content.strip()
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', strategy_text, re.DOTALL)
            if json_match:
                try:
                    strategy = json.loads(json_match.group(0))
                    print(f"🧠 Search strategy: {strategy['intent_type']} - {strategy['search_focus']}")
                    return strategy
                except json.JSONDecodeError:
                    pass
            
            # Fallback strategy
            return {
                "intent_type": "general_news",
                "key_entities": query.split(),
                "time_sensitivity": "recent",
                "content_preferences": ["announcements", "analysis"],
                "priority_sources": ["official", "tech_publications"],
                "search_focus": f"Find recent tech news about {query}"
            }
            
        except Exception as e:
            print(f"Error analyzing query intent: {e}")
            return {
                "intent_type": "general_news",
                "key_entities": query.split(),
                "time_sensitivity": "recent",
                "content_preferences": ["announcements"],
                "priority_sources": ["official"],
                "search_focus": f"Find tech news about {query}"
            }
    
    async def _generate_search_queries(self, original_query: str, strategy: Dict[str, Any]) -> List[str]:
        """Generate multiple optimized search queries based on strategy"""
        prompt = f"""Based on this search strategy, generate 3-4 optimized search queries that will find high-quality, standalone tech articles.

Original query: "{original_query}"
Strategy: {json.dumps(strategy, indent=2)}

Requirements for search queries:
1. Focus on finding standalone articles, not aggregated content
2. Prioritize official sources for companies/products mentioned
3. Include recency indicators if time-sensitive
4. Avoid terms that lead to roundups, newsletters, or category pages

Generate queries that will find:
- Official announcements and press releases
- Specific news articles about individual topics
- Recent developments from authoritative sources

Return a JSON array of 3-4 search query strings:
["query1", "query2", "query3", "query4"]

Return ONLY the JSON array, no additional text."""

        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            queries_text = response.content.strip()
            
            # Extract JSON array
            json_match = re.search(r'\[.*\]', queries_text, re.DOTALL)
            if json_match:
                try:
                    queries = json.loads(json_match.group(0))
                    if isinstance(queries, list):
                        print(f"🔍 Generated {len(queries)} search queries")
                        return queries
                except json.JSONDecodeError:
                    pass
            
            # Fallback queries
            current_year = datetime.now().year
            recent_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            
            return [
                f'"{original_query}" {current_year} -roundup -newsletter -digest',
                f'{original_query} announcement OR release {current_year}',
                f'{original_query} news after:{recent_date}',
                f'{original_query} official blog OR press release'
            ]
            
        except Exception as e:
            print(f"Error generating search queries: {e}")
            return [original_query]
    
    def _extract_structured_results(self, raw_results: Any) -> List[Dict[str, Any]]:
        """Extract structured data from search results"""
        structured_results = []
        
        try:
            if isinstance(raw_results, list):
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
                        if result['url'] and result['title']:
                            structured_results.append(result)
                            
            elif isinstance(raw_results, str):
                # Fallback: extract URLs and create basic structure
                urls = re.findall(r'https?://[^\s\],"\']+', raw_results)
                for url in urls:
                    structured_results.append({
                        'url': url.rstrip('.,;)'),
                        'title': 'Article',
                        'content': '',
                        'score': 0.3,
                        'published_date': '',
                        'domain': urlparse(url).netloc
                    })
                    
        except Exception as e:
            print(f"Error extracting structured results: {e}")
        
        return structured_results
    
    async def _intelligent_filter_and_rank(self, query: str, strategy: Dict[str, Any], results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Use LLM to intelligently filter and rank results"""
        if not results:
            return []
        
        # Limit results to analyze to avoid token limits
        results_to_analyze = results[:15]
        
        # Create analysis prompt
        results_text = ""
        for i, result in enumerate(results_to_analyze, 1):
            results_text += f"{i}. URL: {result['url']}\n"
            results_text += f"   Title: {result['title']}\n"
            results_text += f"   Domain: {result['domain']}\n"
            results_text += f"   Content: {result['content'][:200]}...\n\n"
        
        prompt = f"""Analyze these search results for the query: "{query}"

Search Strategy: {json.dumps(strategy, indent=2)}

Results to analyze:
{results_text}

Your task is to filter and rank these results to find the BEST standalone tech articles that match the user's intent.

PRIORITIZE results that are:
1. Standalone articles about specific topics (not category pages, author pages, or aggregated content)
2. From official sources when relevant (company blogs, press releases, official announcements)
3. Recent and newsworthy content
4. Directly relevant to the user's query
5. From authoritative tech publications

EXCLUDE results that are:
- Newsletter articles or daily/weekly digests
- Author profile pages or category landing pages
- Aggregated roundup content
- Forum posts or community discussions
- Generic section pages (like /tech/, /science/, /category/)

Return a JSON array of the TOP 8 results, ranked from best to worst. Include the complete result data:

[
  {{
    "url": "full_url_here",
    "title": "article_title_here",
    "content": "content_snippet_here",
    "score": 0.9,
    "domain": "domain.com",
    "published_date": "date_if_available",
    "relevance_reason": "brief explanation of why this is relevant and high-quality"
  }}
]

Return ONLY the JSON array with no additional text."""

        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            result_text = response.content
            
            # Extract JSON from response
            json_match = re.search(r'\[.*\]', result_text, re.DOTALL)
            if json_match:
                try:
                    filtered_results = json.loads(json_match.group(0))
                    if isinstance(filtered_results, list):
                        print(f"✅ Filtered to {len(filtered_results)} high-quality articles")
                        return filtered_results
                except json.JSONDecodeError as e:
                    print(f"⚠️ JSON parsing error: {e}")
            
            # Fallback: return top results with basic filtering
            print("⚠️ Using fallback filtering")
            return [r for r in results_to_analyze if not any(exclude in r['url'].lower() 
                   for exclude in ['/category/', '/author/', '/tag/', 'newsletter', 'digest'])][:8]
            
        except Exception as e:
            print(f"Error in intelligent filtering: {e}")
            return results_to_analyze[:8]
    
    async def _validate_with_firecrawl(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Use Firecrawl to validate and enhance article information"""
        if not self.firecrawl_api_key:
            print("⚠️ Firecrawl API key not available, skipping validation")
            return results
        
        validated_results = []
        
        for result in results:
            try:
                # Use Firecrawl to get better article content and metadata
                firecrawl_response = await self._firecrawl_scrape(result['url'])
                
                if firecrawl_response:
                    # Enhance result with Firecrawl data
                    enhanced_result = result.copy()
                    enhanced_result.update({
                        'validated_content': firecrawl_response.get('content', result['content']),
                        'metadata': firecrawl_response.get('metadata', {}),
                        'firecrawl_validated': True
                    })
                    validated_results.append(enhanced_result)
                else:
                    # Keep original result if Firecrawl fails
                    result['firecrawl_validated'] = False
                    validated_results.append(result)
                    
            except Exception as e:
                print(f"⚠️ Firecrawl validation failed for {result['url']}: {e}")
                result['firecrawl_validated'] = False
                validated_results.append(result)
        
        return validated_results
    
    async def _firecrawl_scrape(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape URL using Firecrawl API"""
        if not self.firecrawl_api_key:
            return None
        
        try:
            headers = {
                'Authorization': f'Bearer {self.firecrawl_api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'url': url,
                'formats': ['markdown', 'html'],
                'includeTags': ['title', 'meta', 'article'],
                'excludeTags': ['nav', 'footer', 'aside', 'script'],
                'onlyMainContent': True
            }
            
            response = await asyncio.to_thread(
                requests.post,
                'https://api.firecrawl.dev/v1/scrape',
                headers=headers,
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"⚠️ Firecrawl API error {response.status_code} for {url}")
                return None
                
        except Exception as e:
            print(f"⚠️ Firecrawl request failed for {url}: {e}")
            return None

# Create global search service
search_service = IntelligentSearchService()

@tool
async def search_tech_news(query: str, max_results: int = 8) -> str:
    """
    Intelligent search for technology news using AI-powered analysis and Firecrawl validation.
    
    Args:
        query: The search query for tech news
        max_results: Maximum number of results to return (default: 8)
        
    Returns:
        Formatted search results with high-quality standalone articles
    """
    try:
        # Execute intelligent search
        results = await search_service.search(query, max_results)
        
        if "error" in results:
            return f"❌ Search error: {results['error']}"
        
        articles = results.get("results", [])
        
        if not articles:
            return f"❌ No high-quality standalone tech articles found for: {query}"
        
        # Format the results with enhanced information
        formatted_output = f"""
🚀 **INTELLIGENT TECH NEWS SEARCH** 
📅 **Search Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔍 **Query:** {query}
🧠 **Search Strategy:** {results.get('search_strategy', {}).get('intent_type', 'general')} - {results.get('search_strategy', {}).get('search_focus', 'Find relevant tech news')}
📰 **Found:** {len(articles)} high-quality standalone articles

**🔗 TOP ARTICLES:**
"""
        
        # Add each article with enhanced information
        for i, article in enumerate(articles, 1):
            domain = article.get('domain', urlparse(article['url']).netloc)
            title = article.get('title', 'Untitled Article')
            content_preview = article.get('validated_content', article.get('content', ''))[:200]
            relevance_reason = article.get('relevance_reason', 'High-quality standalone article')
            firecrawl_status = "✅ Validated" if article.get('firecrawl_validated') else "⚠️ Not validated"
            
            formatted_output += f"""
{i}. **{title}**
   🔗 {article['url']}
   🏢 Source: {domain}
   📝 Preview: {content_preview}{"..." if len(content_preview) >= 200 else ""}
   ✅ Why selected: {relevance_reason}
   🔍 Status: {firecrawl_status}

"""
        
        # Add strategy information
        if results.get('search_queries'):
            formatted_output += f"""
**🧠 SEARCH INTELLIGENCE:**
- Strategy Type: {results.get('search_strategy', {}).get('intent_type', 'general')}
- Search Queries Used: {len(results.get('search_queries', []))}
- Key Focus: {results.get('search_strategy', {}).get('search_focus', 'General tech news')}

"""
        
        # Add instructions
        formatted_output += """
**📋 NEXT STEPS:**
- To crawl a specific article: `Crawl article number [1-8]` or `Crawl this URL: [paste URL here]`
- For a different search: `Search for [new query]`
- These are all standalone articles, not aggregated content or category pages
"""
        
        return formatted_output
        
    except Exception as e:
        return f"❌ Search error: {str(e)}"

@tool 
async def extract_article_urls(search_results: str) -> List[str]:
    """
    Extract article URLs from formatted search results.
    
    Args:
        search_results: Formatted search results from a previous search
        
    Returns:
        List of article URLs
    """
    try:
        urls = re.findall(r'🔗 (https?://[^\s\],"\']+)', search_results)
        
        # Clean and deduplicate URLs
        unique_urls = []
        for url in urls:
            clean_url = url.rstrip('.,;)')
            if clean_url not in unique_urls:
                unique_urls.append(clean_url)
        
        return unique_urls
        
    except Exception as e:
        print(f"Error extracting URLs: {e}")
        return []

@tool
async def search_official_sources(query: str, max_results: int = 8) -> str:
    """
    Search specifically for content from official company sources about the query.
    Uses intelligent search with priority for official announcements.
    
    Args:
        query: Search query for official information
        max_results: Maximum number of results to return
        
    Returns:
        Formatted search results focusing on official sources
    """
    try:
        # Modify query to prioritize official sources
        official_query = f"{query} site:openai.com OR site:anthropic.com OR site:google.com OR site:microsoft.com OR site:apple.com OR site:meta.com OR site:nvidia.com OR site:tesla.com official announcement OR press release"
        
        # Use the intelligent search with official source focus
        results = await search_service.search(official_query, max_results)
        
        if "error" in results:
            return f"❌ Search error: {results['error']}"
        
        articles = results.get("results", [])
        
        # Format results with official source emphasis
        formatted_output = f"""
📢 **OFFICIAL SOURCE SEARCH RESULTS** 
📅 **Search Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔍 **Query:** {query}
🎯 **Focus:** Official company sources, announcements, and press releases
📰 **Found:** {len(articles)} official sources

**🔗 TOP OFFICIAL SOURCES:**
"""
        
        for i, article in enumerate(articles, 1):
            domain = article.get('domain', urlparse(article['url']).netloc)
            title = article.get('title', 'Official Announcement')
            content_preview = article.get('validated_content', article.get('content', ''))[:150]
            
            formatted_output += f"""
{i}. **{title}**
   🔗 {article['url']}
   🏢 {domain}
   📝 {content_preview}{"..." if len(content_preview) >= 150 else ""}

"""
        
        formatted_output += """
**📋 NEXT STEPS:**
- To crawl a specific article: `Crawl article number [1-8]` or `Crawl this URL: [paste URL here]`
- For a different search: `Search for [new query]`
"""
        
        return formatted_output
        
    except Exception as e:
        return f"❌ Search error: {str(e)}"

# Export the tools
search_tools = [
    search_tech_news,
    extract_article_urls,
    search_official_sources
]