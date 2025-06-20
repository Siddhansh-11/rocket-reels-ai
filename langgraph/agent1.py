from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.chat_models import ChatLiteLLM
from openai import OpenAI
import os
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv

# Import agent tools
from search_agent import search_tools
from crawl_agent import crawl_tools
from supabase_agent import supabase_tools_sync_wrapped  # Remove the non-existent imports

# Load environment variables
load_dotenv("../.env")

# Get today's date for context
today = datetime.now().strftime("%Y-%m-%d")

model = ChatLiteLLM(
    model="deepseek/deepseek-chat",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    max_tokens=4000,
    temperature=0.1
)

# Enhanced system prompt with error handling guardrails
SYSTEM_PROMPT = f"""
You are Rocket Reels AI News Research Assistant - a specialized agent for discovering, analyzing, and storing trending technology news, including images for social media content.

📅 **Today's date:** {today}

🔧 **YOUR SPECIALIZED AGENTS:**

🔍 **SEARCH AGENT FUNCTION:**
- Searches for the latest trending technology news using Tavily
- Focuses on breaking tech news, AI developments, startup announcements, and industry updates
- Filters for high-quality sources (TechCrunch, The Verge, Wired, Ars Technica, etc.)
- Returns prioritized list of articles with URLs and summaries
- Ensures content is recent, relevant, and trending for maximum engagement

🕷️ **CRAWL AGENT FUNCTION:**
- Uses Mistral OCR to extract full article content and images from selected URLs
- Retrieves complete article text, title, metadata, and image URLs/base64
- Cleans and structures content for optimal readability
- Provides word count, source information, and image URLs for social media
- Delivers comprehensive article content ready for analysis and content creation

🗄️ **SUPABASE STORAGE AGENT FUNCTION:**
- Automatically stores all crawled article content and image URLs in Supabase database
- Creates unique records with URL hashing to prevent duplicates
- Indexes content for fast retrieval and searching
- Maintains article metadata, word counts, timestamps, and image URLs
- Enables content persistence and future analysis

🎬 **SCRIPTING AGENT FUNCTION:**
- Generates viral social media scripts optimized for different platforms
- Creates platform-specific content (YouTube, TikTok, Instagram, LinkedIn)
- Uses proven viral content templates and hooks
- Optimizes script length and style for maximum engagement

📋 **WORKFLOW PROCESS:**

**PHASE 1 - SEARCH & DISCOVERY:**
1. Execute comprehensive search for trending tech news using the Search Agent
2. Present TOP 8 carefully curated articles with:
   - Article titles and brief descriptions
   - Source domains (prioritizing premium tech publications)
   - Numbered list for easy selection
   - Focus on trending, discussion-worthy content suitable for social media

**PHASE 2 - HUMAN SELECTION (CRITICAL):**
3. Present results to user and request selection
4. **WAIT FOR USER INPUT** - Do NOT proceed without explicit user choice
5. Ask user to specify which article(s) they want crawled:
   - "Select article number (e.g., '1', '3', or '1 and 4')"
   - "Choose by topic (e.g., 'the AI breakthrough article')"
   - "Provide specific URL if you have one"

**PHASE 3 - CONTENT EXTRACTION & STORAGE:**
6. Once user selects, activate Crawl Agent to extract full content and images
7. Retrieve complete article text, metadata, and image URLs
8. **AUTOMATICALLY store all crawled content and images in Supabase database**
9. Present comprehensive content including:
   - Full article text
   - Metadata (word count, source, publish date)
   - Image URLs for social media
   - Database storage confirmation
   - Structured format ready for content creation

**PHASE 4 - SCRIPT GENERATION:**
10. When user requests script generation, use the scripting agent
11. Generate viral script optimized for selected platform
12. Create engaging hooks, structured content, and clear CTAs
13. Optimize for platform-specific requirements and timing

🎯 **SPECIAL CAPABILITIES:**

**DATABASE RETRIEVAL:**
- Can search and retrieve previously stored articles by keyword
- Use get_stored_article_by_keyword() to find articles in database
- Perfect for generating scripts from already processed content

**INSTAGRAM REEL SCRIPTS:**
- When asked to generate Instagram reel scripts, first retrieve the article from database
- Then use generate_viral_script() with platform="instagram"
- Optimize for 30-60 second duration with engaging hooks

⚠️ **CRITICAL ERROR HANDLING GUARDRAILS:**

**DATABASE RETRIEVAL FAILURES:**
1. **ALWAYS inform the user immediately when database retrieval fails**
2. **Explain what went wrong in simple terms**
3. **Provide clear options for next steps:**
   - Search for new articles on the topic
   - Try different keywords
   - Browse existing articles in database
   - Manual URL input if user has specific article
4. **NEVER proceed silently after a database error**
5. **ASK USER what they want to do next**

**ERROR RESPONSE TEMPLATE:**
When database retrieval fails, respond with:

"❌ **DATABASE RETRIEVAL FAILED**

**What happened:** [Explain the error in simple terms]

**What we can do next:**
1. 🔍 **Search for new articles** about [topic] 
2. 📋 **Browse existing articles** in the database
3. 🔗 **Provide a specific URL** if you have one
4. 🔄 **Try different keywords** for database search

**What would you like me to do?** Please let me know your preference."

**TOOL USAGE RULES:**
- For keyword searches in database: Use `get_stored_article_by_keyword()`
- For browsing all articles: Use `retrieve_stored_articles()`
- For specific URL retrieval: Use `get_article_by_url()`
- ALWAYS handle tool failures gracefully with user communication

🎯 **SUCCESS CRITERIA:**
- Articles must be TRENDING and recent (within last 7 days preferred)
- Content should be suitable for social media content creation, including images
- Focus on technology, AI, startups, and innovation news
- Ensure high engagement potential for video and image-based content
- All content automatically stored for future reference
- Complete end-to-end workflow from discovery to production-ready content
- Wait for explicit user selection before crawling
- **ALWAYS communicate errors clearly to users**

⚠️ **CRITICAL RULES:**
- NEVER crawl articles without user selection
- ALWAYS present search results first
- ALWAYS wait for human input before proceeding to crawl phase
- AUTOMATICALLY store all crawled content and images in database
- Focus on trending, shareable tech content with visual appeal
- Prioritize quality sources over quantity
- Generate both script and visual timing for complete content creation
- **IMMEDIATELY inform users of any errors and ask for guidance**

🚀 **YOUR MISSION:**
Help users discover trending tech news, extract full content and images, automatically store everything, generate viral scripts, and create detailed visual production plans for engaging social media content.

**When errors occur, be transparent, helpful, and always ask the user how they want to proceed.**

Ready to find and transform the next viral tech story into production-ready content?
"""

# Combine all available tools
all_tools = search_tools + crawl_tools + supabase_tools_sync_wrapped

# Create the agent with comprehensive tools
agent = create_react_agent(
    model, 
    all_tools, 
    prompt=SYSTEM_PROMPT
)

# Debug and validation functions
def debug_article_data(article_data: dict, stage: str):
    """Debug function to print article data at different stages."""
    print(f"\n🔍 DEBUG - {stage}:")
    print(f"   Keys: {list(article_data.keys()) if isinstance(article_data, dict) else 'Not a dict'}")
    if isinstance(article_data, dict):
        print(f"   URL: {article_data.get('url', 'MISSING')}")
        print(f"   Title: {article_data.get('title', 'MISSING')[:50]}..." if article_data.get('title') else "   Title: MISSING")
        print(f"   Content length: {len(article_data.get('content', ''))}")

def safe_json_parse(json_str: str) -> dict:
    """Safely parse JSON string with error handling."""
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {str(e)}")
        return {}

def extract_structured_data(result_text: str) -> dict:
    """Extract structured data from crawl agent result."""
    if "STRUCTURED DATA" in result_text:
        try:
            # Find JSON block
            json_start = result_text.find('```json\n') + 8
            json_end = result_text.find('\n```', json_start)
            json_data = result_text[json_start:json_end]
            
            # Try to parse JSON
            parsed_data = safe_json_parse(json_data)
            if parsed_data:
                return parsed_data
            
            # If parsing fails, try to extract manually
            print("⚠️ JSON parsing failed, extracting data manually...")
            return extract_data_manually(result_text)
            
        except Exception as e:
            print(f"❌ Error extracting structured data: {str(e)}")
            return extract_data_manually(result_text)
    
    return extract_data_manually(result_text)

def extract_data_manually(result_text: str) -> dict:
    """Manually extract data from result text as fallback."""
    data = {}
    
    # Try to extract URL from the result text (improved regex)
    import re
    url_patterns = [
        r'https?://[^\s\)\]]+',  # Standard URL pattern
        r'URL:\s*(https?://[^\s\)\]]+)',  # URL with label
        r'\*\*URL:\*\*\s*(https?://[^\s\)\]]+)',  # Markdown URL
        r'🔗\s*URL:\s*(https?://[^\s\)\]]+)'  # Emoji URL
    ]
    
    for pattern in url_patterns:
        url_match = re.search(pattern, result_text)
        if url_match:
            if pattern.startswith('https'):
                data['url'] = url_match.group(0)
            else:
                data['url'] = url_match.group(1)
            break
    
    # Extract title (improved)
    title_patterns = [
        r'\*\*📰 Title:\*\*\s*([^\n]+)',
        r'\*\*Title:\*\*\s*([^\n]+)',
        r'Title:\s*([^\n]+)',
        r'# ([^\n]+)'  # Markdown header
    ]
    
    for pattern in title_patterns:
        title_match = re.search(pattern, result_text)
        if title_match:
            data['title'] = title_match.group(1).strip()
            break
    
    # Extract domain (improved)
    domain_patterns = [
        r'\*\*🌐 Domain:\*\*\s*([^\n]+)',
        r'\*\*Domain:\*\*\s*([^\n]+)',
        r'Domain:\s*([^\n]+)'
    ]
    
    for pattern in domain_patterns:
        domain_match = re.search(pattern, result_text)
        if domain_match:
            data['domain'] = domain_match.group(1).strip()
            break
    
    # If no domain found, extract from URL
    if not data.get('domain') and data.get('url'):
        from urllib.parse import urlparse
        try:
            parsed_url = urlparse(data['url'])
            data['domain'] = parsed_url.netlnetloc
        except:
            data['domain'] = 'unknown.com'
    
    # Extract word count
    word_patterns = [
        r'(\d+)\s+words',
        r'Word Count:\s*(\d+)',
        r'\*\*Word Count:\*\*\s*(\d+)'
    ]
    
    for pattern in word_patterns:
        word_match = re.search(pattern, result_text)
        if word_match:
            data['word_count'] = int(word_match.group(1))
            break
    
    # Extract content (improved)
    content_patterns = [
        r'\*\*📄 FULL ARTICLE CONTENT:\*\*\s*\n(.*?)(?=\*\*🖼️|\*\*🗄️|$)',
        r'\*\*FULL ARTICLE CONTENT:\*\*\s*\n(.*?)(?=\*\*|$)',
        r'CONTENT:\s*\n(.*?)(?=\*\*|$)',
        r'Content:\s*\n(.*?)(?=\*\*|$)'
    ]
    
    for pattern in content_patterns:
        content_match = re.search(pattern, result_text, re.DOTALL)
        if content_match:
            data['content'] = content_match.group(1).strip()
            break
    
    # If no content found using patterns, take a larger chunk
    if not data.get('content'):
        # Look for any substantial text block
        lines = result_text.split('\n')
        content_lines = []
        capturing = False
        
        for line in lines:
            # Start capturing after content headers
            if any(keyword in line.lower() for keyword in ['content:', 'article content', 'full article']):
                capturing = True
                continue
            
            # Stop at certain markers
            if capturing and any(marker in line for marker in ['**🖼️', '**🗄️', '```', '---']):
                break
            
            # Collect content lines
            if capturing and line.strip() and not line.startswith('**') and not line.startswith('#'):
                content_lines.append(line.strip())
        
        if content_lines:
            data['content'] = '\n'.join(content_lines)
    
    # Extract image URLs (improved)
    image_patterns = [
        r'- (https?://[^\s]+\.(?:jpg|jpeg|png|gif|webp))',
        r'Image:\s*(https?://[^\s]+\.(?:jpg|jpeg|png|gif|webp))',
        r'\*\*(https?://[^\s]+\.(?:jpg|jpeg|png|gif|webp))\*\*'
    ]
    
    image_urls = []
    for pattern in image_patterns:
        image_urls.extend(re.findall(pattern, result_text, re.IGNORECASE))
    
    data['image_urls'] = list(set(image_urls))  # Remove duplicates
    
    # Set robust defaults for required fields
    data.setdefault('url', 'https://unknown.com/article')
    data.setdefault('title', 'Extracted Article Title')
    data.setdefault('content', result_text[:1000] if len(result_text) > 100 else 'Content extraction incomplete')
    data.setdefault('domain', 'unknown.com')
    data.setdefault('word_count', len(data.get('content', '').split()))
    data.setdefault('image_urls', [])
    data.setdefault('image_metadata', {})
    data.setdefault('metadata', {})
    
    return data

def parse_human_selection(user_input: str, last_ai_message: str) -> list:
    """Parse human selection and extract URLs to crawl."""
    urls_to_crawl = []
    
    # Extract URLs from the last AI message (search results)
    import re
    urls_in_message = re.findall(r'https?://[^\s\)]+', last_ai_message)
    
    # Parse user selection
    user_input_lower = user_input.lower().strip()
    
    # Check for direct URL input
    if user_input.startswith('http'):
        urls_to_crawl.append(user_input)
        return urls_to_crawl
    
    # Check for number selections
    numbers = re.findall(r'\b(\d+)\b', user_input)
    if numbers:
        for num_str in numbers:
            try:
                index = int(num_str) - 1  # Convert to 0-based index
                if 0 <= index < len(urls_in_message):
                    urls_to_crawl.append(urls_in_message[index])
            except (ValueError, IndexError):
                continue
    
    return urls_to_crawl

# Updated process_selection function
async def process_selection(urls_to_crawl: list, platform: str):
    """Process selected articles: crawl, store, generate script, and create visual timing."""
    print(f"\n🎯 Processing {len(urls_to_crawl)} selected article(s) for {platform}...")

    if len(urls_to_crawl) == 1:
        url = urls_to_crawl[0]
        print(f"🕷️ Crawling single article: {url}")
        
        from crawl_agent import crawl_article_content
        crawl_result = await crawl_article_content.ainvoke({"url": url})
        
        # Extract structured data
        article_data = extract_structured_data(crawl_result)
        article_data['url'] = url
        
        # Debug and validate
        debug_article_data(article_data, "After extraction")
        
        if not article_data.get('content') or len(article_data.get('content', '')) < 50:
            print("❌ Failed to extract meaningful content from article")
            return
        
        # Store in Supabase
        print(f"\n🗄️ Storing article in Supabase...")
        from supabase_agent import store_article_content_sync_wrapped
        
        try:
            storage_result = await store_article_content_sync_wrapped.ainvoke({"article_data": article_data})
            print(f"\n💾 Storage Result:\n{storage_result}")
            
            if "❌" in storage_result:
                print("❌ Storage failed, cannot proceed with script generation")
                return
        except Exception as e:
            print(f"❌ Storage error: {str(e)}")
            return
        
        print(f"\n✅ Complete workflow finished for {platform}!")
        print("📊 Summary:")
        print(f"   • Article crawled and stored")
        print(f"   • Ready for script generation")
        print(f"   • Ready for visual timing creation")
        
    # Handle multiple URLs case...
    else:
        print("Multiple article processing not implemented yet")