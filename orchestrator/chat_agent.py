from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langchain_community.chat_models import ChatLiteLLM
from langgraph.prebuilt import create_react_agent
import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, Any, List

# Import orchestrator agents
try:
    from .enhanced_storage_agent import get_supabase_client
    from .scripting_agent import store_script_content, retrieve_scripts, check_scripts_table_access
except ImportError:
    # Fallback for when running as script
    from enhanced_storage_agent import get_supabase_client
    from scripting_agent import store_script_content, retrieve_scripts, check_scripts_table_access

# Load environment variables
load_dotenv('.env')
load_dotenv()  # Also try current directory

# Get today's date for context
today = datetime.now().strftime("%Y-%m-%d")

# Initialize model with error handling
try:
    model = ChatLiteLLM(
        model="deepseek/deepseek-chat",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        max_tokens=4000,
        temperature=0.1
    )
    MODEL_AVAILABLE = True
    print("✅ DeepSeek model initialized successfully")
except Exception as e:
    print(f"⚠️ Warning: Could not initialize DeepSeek model: {e}")
    model = None
    MODEL_AVAILABLE = False

# Define orchestrator chat tools
@tool
def retrieve_stored_articles(limit: int = 10) -> str:
    """Retrieve and display stored articles from Supabase database."""
    try:
        supabase = get_supabase_client()
        
        # Query articles from database
        result = supabase.table('articles').select('id,title,url,domain,word_count,created_at').limit(limit).order('created_at', desc=True).execute()
        
        if not result.data:
            return """📄 **STORED ARTICLES DATABASE**

❌ No articles found in the database.

**💡 Suggestion:** Try crawling some articles first by:
- Searching for news: "search AI news"
- Crawling a URL: "crawl https://example.com"
"""
        
        articles = result.data
        message = f"""📄 **STORED ARTICLES DATABASE**

✅ Found {len(articles)} articles in Supabase:

"""
        for i, article in enumerate(articles, 1):
            created_date = article.get('created_at', '')[:10] if article.get('created_at') else 'Unknown'
            message += f"""**{i}. {article.get('title', 'Untitled')[:60]}...**
🌐 Domain: {article.get('domain', 'Unknown')}
📊 Words: {article.get('word_count', 0)}
📅 Stored: {created_date}
🔗 URL: {article.get('url', 'N/A')[:50]}...
🆔 ID: {article.get('id', '')[:8]}...

---
"""
        
        message += f"""
**🗄️ Database Status:** {len(articles)} articles available for script generation
**💡 Next Steps:** 
- Generate scripts: "create script from article 1"
- Search more: "search tech news"
- Crawl new content: "crawl https://example.com"
"""
        return message
        
    except Exception as e:
        return f"❌ Error retrieving articles from database: {str(e)}"

@tool
def check_script_table() -> str:
    """Check if scripts table is accessible and show recent scripts."""
    try:
        supabase = get_supabase_client()
        
        # Try to query the scripts table
        result = supabase.table('scripts').select('id,platform,created_at').limit(5).order('created_at', desc=True).execute()
        
        # Check table accessibility
        table_accessible = True
        script_count_result = supabase.table('scripts').select('id', count='exact').execute()
        total_scripts = script_count_result.count if script_count_result.count is not None else 0
        
        message = f"""✅ **SCRIPTS TABLE ACCESS CHECK**

**Database Status:** Scripts table is accessible
**Total Scripts:** {total_scripts}
**Table Accessible:** {table_accessible}

"""
        
        if result.data:
            message += "**Recent Scripts:**\n"
            for script in result.data:
                created_date = script.get('created_at', '')[:10] if script.get('created_at') else 'Unknown'
                message += f"- ID: {script.get('id', '')[:8]}... | Platform: {script.get('platform', 'Unknown')} | Created: {created_date}\n"
        
        message += "\n**🗄️ The scripts table is fully accessible from the orchestrator!**"
        
        return message
        
    except Exception as e:
        return f"❌ Error accessing scripts table: {str(e)}"

@tool
def retrieve_stored_scripts(limit: int = 10, platform: str = None) -> str:
    """Retrieve and display scripts from Supabase database."""
    try:
        supabase = get_supabase_client()
        
        # Build query
        query = supabase.table('scripts').select('id,article_id,platform,style,template,duration,created_at,content')
        
        # Apply platform filter if provided
        if platform:
            query = query.eq('platform', platform.lower())
            
        # Execute query
        result = query.limit(limit).order('created_at', desc=True).execute()
        
        if not result.data:
            return """📝 **STORED SCRIPTS DATABASE**

❌ No scripts found in the database.

**💡 Suggestion:** Scripts are generated from crawled articles:
1. Search for news: "search AI news"
2. Crawl an article: Select article number or provide URL
3. Generate scripts: "generate scripts from last article"
"""
        
        scripts = result.data
        message = f"""📝 **STORED SCRIPTS DATABASE**

✅ Found {len(scripts)} scripts in Supabase:

"""
        for i, script in enumerate(scripts, 1):
            created_date = script.get('created_at', '')[:10] if script.get('created_at') else 'Unknown'
            content_preview = script.get('content', 'No content')[:100] + '...' if script.get('content') else 'No content'
            
            message += f"""**{i}. {script.get('platform', 'Unknown').upper()} Script**
🆔 Script ID: {script.get('id', '')[:8]}...
📄 Article ID: {script.get('article_id', '')[:8]}...
🎨 Style: {script.get('style', 'Unknown')}
📋 Template: {script.get('template', 'Unknown')}
⏱️ Duration: {script.get('duration', 'N/A')} seconds
📅 Created: {created_date}

**Preview:** {content_preview}

---
"""
        
        message += f"""
**🗄️ Database Status:** {len(scripts)} scripts available
**💡 Next Steps:** 
- View full script content
- Update script content
- Generate more scripts from articles
"""
        
        return message
        
    except Exception as e:
        return f"❌ Error retrieving scripts from database: {str(e)}"

@tool
def route_to_search(query: str = "") -> str:
    """Route user to search for news/content when they want to search."""
    return f"""🔍 **SEARCH REQUEST DETECTED**

To search for: "{query}"

**Please use the search functionality:**
- For news search: Use the search agent
- For trending content: Ask "search for trending AI news"
- For specific topics: Ask "search for [your topic]"

**💡 I can help with:**
- Retrieving stored articles from database
- Checking script table access
- Managing stored content
- Routing to appropriate agents
"""

@tool
def route_to_crawl(url_or_request: str = "") -> str:
    """Route user to crawl agent when they want to crawl content."""
    return f"""🕷️ **CRAWL REQUEST DETECTED**

To crawl: "{url_or_request}"

**Please use the crawl functionality:**
- Provide specific URL to crawl
- Or search first, then select article to crawl

**💡 Crawling process:**
1. Search for articles first
2. Select which article to crawl
3. Content gets automatically stored in database
4. Then you can generate scripts from it
"""

@tool
def route_to_script_generation(request: str = "") -> str:
    """Route user to script generation when they want to create scripts."""
    return f"""🎬 **SCRIPT GENERATION REQUEST DETECTED**

Request: "{request}"

**To generate scripts, you need:**
1. First ensure you have articles stored in database
2. Use script generation functionality
3. Scripts will be linked to stored articles

**💡 Check if you have articles first:**
- Use: "retrieve stored articles"
- Or search and crawl new content first

**Script generation works with stored article data.**
"""

# System prompt for intelligent chat agent
SYSTEM_PROMPT = f"""
You are Rocket Reels AI Chat Assistant. You have access to tools and MUST use them.

When a user asks about stored articles, you MUST call the retrieve_stored_articles tool.
When a user asks about stored scripts, you MUST call the retrieve_stored_scripts tool.
When a user asks about crawling, you MUST call the route_to_crawl tool.
When a user asks about searching, you MUST call the route_to_search tool.

For example, if user says "provide stored articles about spotify", you should:
1. Call retrieve_stored_articles tool
2. Look through the results for Spotify-related content
3. Provide the relevant information

You have these tools available:
- retrieve_stored_articles
- retrieve_stored_scripts  
- check_script_table
- route_to_search
- route_to_crawl
- route_to_script_generation

Always use the appropriate tool first before responding.
"""

# Chat tools list
chat_tools = [
    retrieve_stored_articles,
    check_script_table,
    retrieve_stored_scripts,
    route_to_search,
    route_to_crawl,
    route_to_script_generation
]

# Create the react agent using LangGraph pattern (simpler and more reliable)
if MODEL_AVAILABLE and model is not None:
    print(f"✅ Creating react agent with {len(chat_tools)} tools")
    chat_agent = create_react_agent(
        model=model,
        tools=chat_tools,
        prompt=SYSTEM_PROMPT
    )
    print("✅ React agent created successfully")
else:
    print("⚠️ Chat agent not created - model not available")
    chat_agent = None

async def run_chat_agent(message: str) -> str:
    """Run the intelligent chat agent with user message."""
    try:
        print(f"🔄 Processing message: '{message}'")
        
        if not MODEL_AVAILABLE or chat_agent is None:
            print("⚠️ Using fallback routing - agent not available")
            return handle_direct_routing(message)
        
        print("✅ Using react agent for processing")
        # Use LangGraph react agent pattern - pass messages list
        messages = [HumanMessage(content=message)]
        result = await chat_agent.ainvoke({"messages": messages})
        
        print(f"📤 Agent result: {type(result)}")
        print(f"📤 Result keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
        
        # Extract the last AI message content
        if result and "messages" in result and result["messages"]:
            last_message = result["messages"][-1]
            print(f"📨 Last message type: {type(last_message)}")
            if hasattr(last_message, 'content'):
                return last_message.content
            else:
                return str(last_message)
        else:
            return "I apologize, but I couldn't process your request. Please try again."
            
    except Exception as e:
        print(f"❌ Chat agent error: {str(e)}")
        return f"❌ Error in chat agent: {str(e)}"

def handle_direct_routing(message: str) -> str:
    """Handle routing when LLM is not available - direct pattern matching."""
    message_lower = message.lower()
    
    # Route based on keywords
    if any(word in message_lower for word in ['search', 'find', 'news', 'latest']):
        return route_to_search(message)
    elif any(word in message_lower for word in ['crawl', 'scrape', 'extract']):
        return route_to_crawl(message)
    elif any(word in message_lower for word in ['script', 'generate', 'create']):
        return route_to_script_generation(message)
    elif any(word in message_lower for word in ['articles', 'stored', 'database', 'retrieve']):
        return retrieve_stored_articles()
    elif any(word in message_lower for word in ['scripts', 'show scripts']):
        return retrieve_stored_scripts()
    elif any(word in message_lower for word in ['check', 'table', 'access']):
        return check_script_table()
    else:
        return """🤖 **Chat Agent - Direct Mode**

Available commands:
- **"search [topic]"** - Search for news/content
- **"crawl [url]"** - Crawl and store content  
- **"generate script"** - Create scripts from stored articles
- **"show articles"** - Display stored articles
- **"show scripts"** - Display stored scripts
- **"check table"** - Verify database access

💡 Example: "search AI news" or "show stored articles"
"""

# Note: Removed sync wrapper to prevent blocking I/O issues in async environment
# The workflow now calls run_chat_agent directly (async)