from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langchain_community.chat_models import ChatLiteLLM
from langgraph.prebuilt import create_react_agent
import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, Any, List
import json

# Import orchestrator agents with proper error handling
STORAGE_AVAILABLE = False
SCRIPTING_AVAILABLE = False

try:
    from .enhanced_storage_agent import get_supabase_client
    STORAGE_AVAILABLE = True
except ImportError:
    try:
        from enhanced_storage_agent import get_supabase_client
        STORAGE_AVAILABLE = True
    except ImportError:
        print("⚠️ Warning: Enhanced storage agent not available")

try:
    from .scripting_agent import store_script_content, retrieve_scripts, check_scripts_table_access
    SCRIPTING_AVAILABLE = True
except ImportError:
    try:
        from scripting_agent import store_script_content, retrieve_scripts, check_scripts_table_access
        SCRIPTING_AVAILABLE = True
    except ImportError:
        print("⚠️ Warning: Scripting agent not available")

# Load environment variables from multiple locations
env_loaded = False
for env_path in ['.env', '../.env', '../../.env']:
    if os.path.exists(env_path):
        load_dotenv(env_path)
        env_loaded = True
        print(f"✅ Loaded environment from {env_path}")
        break

if not env_loaded:
    print("⚠️ Warning: No .env file found")

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
async def retrieve_stored_articles(limit: int = 10) -> str:
    """Retrieve and display stored articles from Supabase database.
    
    Args:
        limit: Maximum number of articles to retrieve (default: 10)
        
    Returns:
        Formatted string with stored articles information
    """
    try:
        if not STORAGE_AVAILABLE:
            return "❌ Storage functionality not available. Please check imports."
        
        # Use asyncio.to_thread for sync Supabase operations
        def sync_query():
            supabase = get_supabase_client()
            return supabase.table('articles').select('id,title,url,domain,word_count,created_at').limit(limit).order('created_at', desc=True).execute()
        
        # Query articles from database
        result = await asyncio.to_thread(sync_query)
        
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
async def check_script_table() -> str:
    """Check if scripts table is accessible and show recent scripts.
    
    Returns:
        Formatted string with scripts table status and recent scripts
    """
    try:
        if not STORAGE_AVAILABLE:
            return "❌ Storage functionality not available. Please check imports."
            
        # Use asyncio.to_thread for sync Supabase operations
        def sync_check():
            supabase = get_supabase_client()
            # Try to query the scripts table
            result = supabase.table('scripts').select('id,platform,created_at').limit(5).order('created_at', desc=True).execute()
            
            # Check table accessibility
            script_count_result = supabase.table('scripts').select('id', count='exact').execute()
            total_scripts = script_count_result.count if script_count_result.count is not None else 0
            
            return result, total_scripts
        
        result, total_scripts = await asyncio.to_thread(sync_check)
        
        table_accessible = True
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
async def retrieve_stored_scripts(limit: int = 10, platform: str = None) -> str:
    """Retrieve and display scripts from Supabase database.
    
    Args:
        limit: Maximum number of scripts to retrieve (default: 10)
        platform: Optional platform filter (youtube, tiktok, instagram, linkedin)
        
    Returns:
        Formatted string with stored scripts information
    """
    try:
        if not STORAGE_AVAILABLE:
            return "❌ Storage functionality not available. Please check imports."
            
        # Use asyncio.to_thread for sync Supabase operations
        def sync_query():
            supabase = get_supabase_client()
            
            # Build query
            query = supabase.table('scripts').select('id,article_id,platform,style,template,duration,created_at,content')
            
            # Apply platform filter if provided
            if platform:
                query = query.eq('platform', platform.lower())
                
            # Execute query
            return query.limit(limit).order('created_at', desc=True).execute()
        
        result = await asyncio.to_thread(sync_query)
        
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
async def route_to_search(query: str = "") -> str:
    """Route user to search for news/content when they want to search.
    
    Args:
        query: The search query or topic
        
    Returns:
        Routing instructions for search functionality
    """
    # This is a simple routing tool, no async operations needed
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
async def route_to_crawl(url_or_request: str = "") -> str:
    """Route user to crawl agent when they want to crawl content.
    
    Args:
        url_or_request: URL or crawl request description
        
    Returns:
        Routing instructions for crawl functionality
    """
    # This is a simple routing tool, no async operations needed
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
async def retrieve_script_by_id_and_generate_prompts(script_id: str, num_prompts: int = 5) -> str:
    """Retrieve a specific script by ID and generate image prompts from it.
    
    Args:
        script_id: The UUID of the script to retrieve
        num_prompts: Number of prompts to generate (default: 5)
        
    Returns:
        Generated prompts for the script
    """
    try:
        if not STORAGE_AVAILABLE:
            return "❌ Storage functionality not available. Please check imports."
        
        # Get script by ID from database
        def sync_query():
            supabase = get_supabase_client()
            # Get script by specific ID
            result = supabase.table('scripts').select('*').eq('id', script_id).execute()
            return result
        
        result = await asyncio.to_thread(sync_query)
        
        if not result.data or len(result.data) == 0:
            return f"❌ Script with ID {script_id} not found in database."
        
        # Get the script
        script = result.data[0]
        script_content = script.get('content', '')
        platform = script.get('platform', 'Unknown')
        style = script.get('style', 'Unknown')
        
        if not script_content:
            return "❌ Script content is empty."
        
        # Generate prompts using DeepSeek
        if not MODEL_AVAILABLE:
            return "❌ Model not available for prompt generation."
        
        prompt = f"""Based on this {platform} video script (style: {style}), generate {num_prompts} detailed image prompts for key visual scenes.

Script content:
{script_content}

For each prompt:
1. Identify a key moment or scene from the script
2. Create a detailed, cinematic image prompt
3. Include visual style, lighting, composition details
4. Make it suitable for AI image generation (DALL-E, Midjourney, etc.)
5. Consider the platform ({platform}) and style ({style}) in your prompts

Format as:
1. [Scene timestamp/description]: [Detailed visual prompt]
2. [Scene timestamp/description]: [Detailed visual prompt]
etc."""

        response = await asyncio.to_thread(
            model.invoke,
            [SystemMessage(content="You are an expert at creating detailed, cinematic image prompts from video scripts. Focus on visual storytelling and composition."),
             HumanMessage(content=prompt)]
        )
        
        return f"""🎨 **IMAGE PROMPTS GENERATED FROM SCRIPT**

**Script ID:** {script_id}
**Platform:** {platform}
**Style:** {style}

{response.content}

**💡 Next Steps:**
- Use these prompts with AI image generators (DALL-E 3, Midjourney, Stable Diffusion)
- Or use "generate image" command with specific prompts
- Adjust prompts as needed for your platform
"""
        
    except Exception as e:
        return f"❌ Error generating prompts: {str(e)}"

@tool
async def generate_prompts_from_script(script_number: int = 4, num_prompts: int = 5) -> str:
    """Generate image prompts from a stored script without triggering image generation.
    
    Args:
        script_number: The script number to generate prompts from (default: 4 for Trump script)
        num_prompts: Number of prompts to generate (default: 5)
        
    Returns:
        Generated prompts for the script
    """
    try:
        if not STORAGE_AVAILABLE:
            return "❌ Storage functionality not available. Please check imports."
        
        # Get scripts from database
        def sync_query():
            supabase = get_supabase_client()
            # Get the 4th script (Trump related)
            result = supabase.table('scripts').select('id,content,platform,style').limit(script_number).order('created_at', desc=True).execute()
            return result
        
        result = await asyncio.to_thread(sync_query)
        
        if not result.data or len(result.data) < script_number:
            return f"❌ Script #{script_number} not found. Please check available scripts first."
        
        # Get the specific script (index script_number - 1)
        script = result.data[script_number - 1]
        script_content = script.get('content', '')
        
        if not script_content:
            return "❌ Script content is empty."
        
        # Generate prompts using DeepSeek
        if not MODEL_AVAILABLE:
            return "❌ Model not available for prompt generation."
        
        prompt = f"""Based on this video script, generate {num_prompts} detailed image prompts for key visual scenes.

Script content:
{script_content[:1500]}...

For each prompt:
1. Identify a key moment or scene
2. Create a detailed, cinematic image prompt
3. Include visual style, lighting, composition
4. Make it suitable for AI image generation

Format as:
1. [Scene description]: [Detailed prompt]
2. [Scene description]: [Detailed prompt]
etc."""

        response = await asyncio.to_thread(
            model.invoke,
            [SystemMessage(content="You are an expert at creating detailed image prompts from video scripts."),
             HumanMessage(content=prompt)]
        )
        
        return f"""🎨 **IMAGE PROMPTS GENERATED FROM SCRIPT #{script_number}**

{response.content}

**💡 Next Steps:**
- Use these prompts with AI image generators (DALL-E 3, Midjourney, etc.)
- Or use "generate image" command with specific prompts
- Adjust prompts as needed for your platform
"""
        
    except Exception as e:
        return f"❌ Error generating prompts: {str(e)}"

@tool
async def route_to_script_generation(request: str = "") -> str:
    """Route user to script generation when they want to create scripts.
    
    Args:
        request: Script generation request description
        
    Returns:
        Routing instructions for script generation
    """
    # This is a simple routing tool, no async operations needed
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
SYSTEM_PROMPT = f"""You are Rocket Reels AI Chat Assistant specialized in helping users manage their content creation workflow.

📅 Today's date: {today}

🔧 YOUR AVAILABLE TOOLS AND WHEN TO USE THEM:

1. **retrieve_stored_articles** - MUST USE when user asks about:
   - "show articles", "stored articles", "what articles do I have"
   - "articles about [topic]", "find articles on [subject]"
   - "list articles", "database articles"

2. **retrieve_stored_scripts** - MUST USE when user asks about:
   - "show scripts", "stored scripts", "generated scripts"
   - "scripts for [platform]", "my scripts"
   - "list scripts", "script database"

3. **check_script_table** - MUST USE when user asks about:
   - "check database", "table access", "script table status"
   - "database health", "verify access"

4. **retrieve_script_by_id_and_generate_prompts** - MUST USE when user asks about:
   - "retrieve script id [UUID]", "get script [UUID] and generate prompts"
   - "script id [UUID]", "generate prompts from script id"
   - Whenever a specific script ID (UUID) is mentioned

5. **generate_prompts_from_script** - MUST USE when user asks about:
   - "generate prompts", "create prompts from script"
   - "image prompts", "prompts for images"
   - "from the 4th script", "trump script prompts"

6. **route_to_search** - MUST USE when user asks about:
   - "search for [topic]", "find news about [subject]"
   - "latest news", "trending topics"
   - "search", "look for articles"

7. **route_to_crawl** - MUST USE when user asks about:
   - "crawl [url]", "extract content from [url]"
   - "scrape website", "get article content"
   - "crawl article [number]" (after search results)

8. **route_to_script_generation** - MUST USE when user asks about:
   - "generate script", "create script from article"
   - "make video script", "write script"
   - "script for [platform]"

🎯 IMPORTANT INSTRUCTIONS:
- ALWAYS use tools - never respond without calling at least one tool
- If unsure which tool to use, check multiple tools
- Tools are async, so they will be called automatically
- After calling a tool, analyze its output and provide helpful context
- Be specific about what was found or what the user should do next

📋 WORKFLOW REMINDERS:
1. Search → Find articles
2. Crawl → Extract and store content
3. Generate → Create scripts from stored content
4. Retrieve → View stored articles and scripts

Remember: You MUST use tools for EVERY request. Do not provide generic responses."""

# Chat tools list
chat_tools = [
    retrieve_stored_articles,
    check_script_table,
    retrieve_stored_scripts,
    retrieve_script_by_id_and_generate_prompts,
    generate_prompts_from_script,
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
        print(f"\n🔄 Chat Agent Processing: '{message[:50]}...'")
        
        if not MODEL_AVAILABLE or chat_agent is None:
            print("⚠️ Model not available - using fallback routing")
            return handle_direct_routing(message)
        
        print("✅ Using LangGraph react agent")
        
        # Create messages list following the LangGraph pattern
        messages = [HumanMessage(content=message)]
        
        # Invoke the agent with proper message format
        try:
            result = await chat_agent.ainvoke({"messages": messages})
        except Exception as invoke_error:
            print(f"❌ Agent invocation error: {invoke_error}")
            # Try with a simpler format
            result = await chat_agent.ainvoke(message)
        
        print(f"📤 Agent response type: {type(result)}")
        
        # Handle different response formats
        if isinstance(result, dict):
            # Standard LangGraph response format
            if "messages" in result and result["messages"]:
                # Get the last message from the agent
                for msg in reversed(result["messages"]):
                    if hasattr(msg, 'content') and msg.content:
                        content = msg.content
                        # Skip tool invocation messages
                        if not content.startswith("Invoking:") and not content.startswith("Tool:"):
                            print(f"✅ Extracted content from message")
                            return content
                
                # If all messages are tool invocations, return the last one
                last_msg = result["messages"][-1]
                if hasattr(last_msg, 'content'):
                    return last_msg.content
                    
            # Alternative response format
            elif "output" in result:
                return result["output"]
                
        elif isinstance(result, str):
            # Direct string response
            return result
            
        elif hasattr(result, 'content'):
            # Message-like object
            return result.content
            
        # Fallback
        print("⚠️ Could not extract proper response, using fallback")
        return handle_direct_routing(message)
            
    except Exception as e:
        print(f"❌ Chat agent error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Provide helpful fallback
        return f"""❌ I encountered an error processing your request.

**Error:** {str(e)}

**💡 You can try these commands directly:**
- "show stored articles" - View articles in database
- "show stored scripts" - View generated scripts
- "search AI news" - Search for news
- "crawl [URL]" - Extract article content
- "generate script" - Create scripts from articles

Or try rephrasing your request."""

def handle_direct_routing(message: str) -> str:
    """Handle routing when LLM is not available - direct pattern matching."""
    message_lower = message.lower()
    
    print(f"📍 Direct routing for: '{message_lower[:50]}...'")
    
    # Use asyncio to run async tools in sync context
    import asyncio
    
    try:
        # Route based on keywords - more specific patterns first
        if any(phrase in message_lower for phrase in ['stored articles', 'show articles', 'list articles', 'database articles']):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(retrieve_stored_articles())
            
        elif any(phrase in message_lower for phrase in ['stored scripts', 'show scripts', 'list scripts']):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(retrieve_stored_scripts())
            
        elif any(phrase in message_lower for phrase in ['check table', 'script table', 'database status']):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(check_script_table())
            
        elif any(word in message_lower for word in ['search', 'find', 'news', 'latest']):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(route_to_search(message))
            
        elif any(word in message_lower for word in ['crawl', 'scrape', 'extract']):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(route_to_crawl(message))
            
        elif any(word in message_lower for word in ['script', 'generate', 'create']):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(route_to_script_generation(message))
            
        else:
            return """🤖 **Chat Agent - Direct Mode**

I can help you with these commands:

📚 **Content Management:**
- **"show stored articles"** - View all articles in database
- **"show stored scripts"** - View generated scripts
- **"check database"** - Verify database access

🔍 **Content Discovery:**
- **"search [topic]"** - Search for news/content
- **"crawl [url]"** - Extract and store article content

🎬 **Content Creation:**
- **"generate script"** - Create scripts from stored articles

💡 **Examples:**
- "search AI news"
- "show stored articles"
- "crawl https://example.com/article"
- "generate script from article"

What would you like to do?"""
            
    except Exception as e:
        print(f"❌ Direct routing error: {str(e)}")
        return f"❌ Error in direct routing: {str(e)}"

# Note: Removed sync wrapper to prevent blocking I/O issues in async environment
# The workflow now calls run_chat_agent directly (async)

# Test function for debugging
async def test_chat_agent():
    """Test the chat agent with various commands."""
    print("\n🧪 Testing Chat Agent...")
    
    test_messages = [
        "show stored articles",
        "search AI news",
        "check database status",
        "help"
    ]
    
    for msg in test_messages:
        print(f"\n📨 Testing: '{msg}'")
        response = await run_chat_agent(msg)
        print(f"📤 Response preview: {response[:200]}...")
        print("-" * 50)
    
    print("\n✅ Chat agent testing complete!")

if __name__ == "__main__":
    # Run test when executed directly
    import asyncio
    asyncio.run(test_chat_agent())