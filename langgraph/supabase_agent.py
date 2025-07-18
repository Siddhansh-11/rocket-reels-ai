from langchain_core.tools import tool
from typing import Dict, List, Optional
from supabase import create_client, Client
import asyncio
import os
from datetime import datetime
import json
import hashlib

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_ANON_KEY")

def get_supabase_client():
    """Get synchronized Supabase client."""
    return create_client(supabase_url, supabase_key)

@tool
def store_article_content_sync_wrapped(article_data: dict) -> str:
    """Store article using sync client - main storage function.
    
    Args:
        article_data: Dictionary containing article data with required fields:
            - url: Article URL (required)
            - title: Article title 
            - content: Article content (required)
            - domain: Article domain
            - word_count: Word count
            - image_urls: List of image URLs
            - image_metadata: Image metadata dict
            - metadata: Additional metadata dict
    
    Returns:
        Confirmation message with storage details
    """
    
    def sync_storage_operation():
        try:
            print(f"🔍 DEBUG - Received article_data: {type(article_data)}")
            print(f"🔍 DEBUG - Article data keys: {list(article_data.keys()) if isinstance(article_data, dict) else 'Not a dict'}")
            
            # Handle nested data structure if needed
            if isinstance(article_data, dict):
                if len(article_data) == 1 and 'article_data' in article_data:
                    actual_data = article_data['article_data']
                    print("🔍 DEBUG - Found nested article_data, unwrapping")
                elif len(article_data) == 0:
                    print("❌ DEBUG - Received empty dictionary")
                    return "❌ Error: Received empty article data dictionary"
                else:
                    actual_data = article_data
            else:
                return "❌ Error: Invalid data type provided"
            
            print(f"🔍 DEBUG - Actual data keys: {list(actual_data.keys()) if isinstance(actual_data, dict) else 'Not a dict'}")
            
            # Enhanced validation
            if not isinstance(actual_data, dict):
                return "❌ Error: Article data must be a dictionary"
            
            if not actual_data.get('url'):
                print(f"❌ DEBUG - Missing URL. Available keys: {list(actual_data.keys())}")
                return "❌ Error: Missing required 'url' field"
            
            if not actual_data.get('content'):
                print(f"❌ DEBUG - Missing content. Available keys: {list(actual_data.keys())}")
                return "❌ Error: Missing required 'content' field"
            
            print(f"✅ DEBUG - Validation passed. URL: {actual_data['url'][:50]}...")
            
            # Initialize sync client
            supabase = get_supabase_client()
            
            # Create URL hash for uniqueness
            url_hash = hashlib.md5(actual_data['url'].encode()).hexdigest()
            
            # Prepare storage data with robust defaults
            storage_data = {
                'url': actual_data['url'],
                'url_hash': url_hash,
                'title': actual_data.get('title', 'No title'),
                'content': actual_data['content'],
                'image_urls': actual_data.get('image_urls', []),
                'stored_image_urls': actual_data.get('image_urls', []),
                'image_metadata': actual_data.get('image_metadata', {}),
                'image_storage_metadata': actual_data.get('image_metadata', {}),
                'domain': actual_data.get('domain', 'Unknown'),
                'word_count': actual_data.get('word_count', len(actual_data['content'].split())),
                'character_count': len(actual_data['content']),
                'metadata': actual_data.get('metadata', {}),
                'crawled_at': datetime.now().isoformat(),
                'created_at': datetime.now().isoformat(),
                'status': 'stored'
            }
            
            print(f"✅ DEBUG - Storage data prepared. Title: {storage_data['title'][:30]}...")
            
            # Check if article exists
            existing = supabase.table('articles').select('id, url').eq('url_hash', url_hash).execute()
            
            if existing.data:
                # Update existing
                result = supabase.table('articles').update(storage_data).eq('url_hash', url_hash).execute()
                action = "updated"
                record_id = existing.data[0]['id']
                print(f"✅ DEBUG - Article updated. ID: {record_id}")
            else:
                # Insert new
                result = supabase.table('articles').insert(storage_data).execute()
                action = "stored"
                record_id = result.data[0]['id'] if result.data else "unknown"
                print(f"✅ DEBUG - Article inserted. ID: {record_id}")
            
            return f"""
✅ **ARTICLE SUCCESSFULLY {action.upper()} IN SUPABASE**

**📊 Storage Details:**
- Record ID: {record_id}
- URL Hash: {url_hash[:12]}...
- Title: {storage_data['title'][:50]}...
- Word Count: {storage_data['word_count']}
- Character Count: {storage_data['character_count']}
- Images Stored: {len(storage_data['image_urls'])}
- Domain: {storage_data['domain']}
- Action: {action.title()}
- Timestamp: {storage_data['crawled_at']}

**🗄️ Database Status:** Article content securely stored and ready for future retrieval.
"""
            
        except Exception as e:
            print(f"❌ DEBUG - Exception in sync_storage_operation: {str(e)}")
            return f"❌ Error storing article in Supabase: {str(e)}"
    
    # Run the sync operation
    try:
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(sync_storage_operation)
                return future.result()
        except RuntimeError:
            return sync_storage_operation()
    except Exception as e:
        print(f"❌ DEBUG - Exception in wrapper: {str(e)}")
        return f"❌ Error in storage operation: {str(e)}"

@tool
def store_multiple_articles(articles_data: list) -> str:
    """Store multiple crawled articles in Supabase database.
    
    Args:
        articles_data: List of article dictionaries
        
    Returns:
        Confirmation message with batch storage details
    """
    try:
        stored_count = 0
        updated_count = 0
        errors = []
        
        print(f"🔍 Debug: Received {len(articles_data)} articles to store")
        
        supabase = get_supabase_client()
        
        for i, article_data in enumerate(articles_data, 1):
            try:
                # Validate required fields
                if not isinstance(article_data, dict):
                    errors.append(f"Article {i}: Data is not a dictionary")
                    continue
                
                if not article_data.get('url') or not article_data.get('content'):
                    errors.append(f"Article {i}: Missing URL or content field")
                    continue
                
                # Create a unique hash for the article URL
                url_hash = hashlib.md5(article_data['url'].encode()).hexdigest()
                
                # Prepare data for insertion
                storage_data = {
                    'url': article_data['url'],
                    'url_hash': url_hash,
                    'title': article_data.get('title', f'Article {i}'),
                    'content': article_data['content'],
                    'image_urls': article_data.get('image_urls', []),
                    'stored_image_urls': article_data.get('image_urls', []),
                    'image_metadata': article_data.get('image_metadata', {}),
                    'image_storage_metadata': article_data.get('image_metadata', {}),
                    'domain': article_data.get('domain', 'unknown.com'),
                    'word_count': article_data.get('word_count', len(article_data['content'].split())),
                    'character_count': len(article_data['content']),
                    'metadata': article_data.get('metadata', {}),
                    'crawled_at': datetime.now().isoformat(),
                    'created_at': datetime.now().isoformat(),
                    'status': 'stored'
                }
                
                # Check if article already exists
                existing = supabase.table('articles').select('id').eq('url_hash', url_hash).execute()
                
                if existing.data:
                    # Update existing record
                    result = supabase.table('articles').update(storage_data).eq('url_hash', url_hash).execute()
                    updated_count += 1
                else:
                    # Insert new record
                    result = supabase.table('articles').insert(storage_data).execute()
                    stored_count += 1
                        
            except Exception as e:
                errors.append(f"Article {i}: {str(e)}")
        
        result_message = f"""
✅ **BATCH STORAGE COMPLETED IN SUPABASE**

**📊 Storage Summary:**
- New Articles Stored: {stored_count}
- Existing Articles Updated: {updated_count}
- Total Processed: {len(articles_data)}
- Errors: {len(errors)}

**📅 Batch Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        if errors:
            result_message += f"\n\n**⚠️ Errors encountered:**\n" + "\n".join(errors[:5])
        
        result_message += "\n\n**🗄️ Database Status:** All valid article content securely stored and indexed for future retrieval."
        
        return result_message
        
    except Exception as e:
        return f"❌ Error in batch storage: {str(e)}"

@tool
def retrieve_stored_articles(domain: str = None, limit: int = 10) -> str:
    """Retrieve stored articles from Supabase database.
    
    Args:
        domain: Optional domain filter (e.g., 'techcrunch.com')
        limit: Maximum number of articles to retrieve
        
    Returns:
        Formatted list of stored articles
    """
    try:
        supabase = get_supabase_client()
        
        # Check if supabase client was created successfully
        if not supabase:
            return "❌ Error: Unable to connect to database. Please check your Supabase configuration."
        
        query = supabase.table('articles').select('id,url,title,domain,word_count,crawled_at').order('crawled_at', desc=True).limit(limit)
        
        if domain:
            query = query.ilike('domain', f'%{domain}%')
        
        response = query.execute()
        
        # Check if response is valid
        if not response or not hasattr(response, 'data'):
            return "❌ Error: Invalid response from database. Please try again."
        
        if not response.data:
            return "📭 No articles found in the database."
        
        articles_list = "🗄️ **STORED ARTICLES FROM SUPABASE DATABASE**\n\n"
        
        for i, article in enumerate(response.data, 1):
            # Handle potential None values
            title = article.get('title', 'No title') or 'No title'
            url = article.get('url', 'No URL') or 'No URL'
            domain = article.get('domain', 'unknown') or 'unknown'
            word_count = article.get('word_count', 0) or 0
            crawled_at = article.get('crawled_at', 'Unknown date') or 'Unknown date'
            
            articles_list += f"""
**{i}. {title[:60]}...**
- ID: {article.get('id', 'Unknown')}
- URL: {url}
- Domain: {domain}
- Word Count: {word_count}
- Stored: {crawled_at[:19] if len(str(crawled_at)) > 19 else crawled_at}
---
"""
        
        return articles_list
        
    except Exception as e:
        return f"❌ Error retrieving articles: {str(e)}\n\n**Possible solutions:**\n1. Check database connection\n2. Verify Supabase credentials\n3. Try again in a moment\n4. Contact support if issue persists"

@tool
def get_article_by_url(url: str) -> str:
    """Retrieve a specific article by URL from Supabase.
    
    Args:
        url: The URL of the article to retrieve
        
    Returns:
        Full article content if found
    """
    try:
        url_hash = hashlib.md5(url.encode()).hexdigest()
        supabase = get_supabase_client()
        
        response = supabase.table('articles').select('*').eq('url_hash', url_hash).execute()
        
        if not response.data:
            return f"❌ Article not found in database for URL: {url}"
        
        article = response.data[0]
        
        return f"""
📰 **ARTICLE RETRIEVED FROM SUPABASE**

**Title:** {article['title']}
**URL:** {article['url']}
**Domain:** {article['domain']}
**Word Count:** {article['word_count']}
**Stored:** {article['crawled_at']}

**Content:**
{article['content']}
"""
        
    except Exception as e:
        return f"❌ Error retrieving article: {str(e)}"

@tool
def get_stored_article_by_keyword(keyword: str, limit: int = 1) -> str:
    """Retrieve stored articles from database by keyword search.
    
    Args:
        keyword: Search term to find in title or content
        limit: Maximum number of articles to return
    
    Returns:
        Article data in formatted string or error message
    """
    try:
        supabase = get_supabase_client()
        
        # Check if supabase client was created successfully
        if not supabase:
            return f"""❌ **DATABASE CONNECTION FAILED**

**What happened:** Unable to connect to the Supabase database

**What we can do next:**
1. 🔍 **Search for new articles** about "{keyword}"
2. 🔄 **Try again** in a moment
3. 🔗 **Provide a specific URL** if you have one
4. 📞 **Contact support** if issue persists

**What would you like me to do?** Please let me know your preference."""
        
        # Search for articles with keyword in title or content
        response = supabase.table('articles').select('*').or_(
            f'title.ilike.%{keyword}%,content.ilike.%{keyword}%'
        ).limit(limit).execute()
        
        # Check if response is valid
        if not response or not hasattr(response, 'data'):
            return f"""❌ **DATABASE QUERY FAILED**

**What happened:** The database search for "{keyword}" encountered an error

**What we can do next:**
1. 🔍 **Search for new articles** about "{keyword}"
2. 📋 **Browse all articles** in the database
3. 🔄 **Try different keywords**
4. 🔗 **Provide a specific URL** if you have one

**What would you like me to do?** Please let me know your preference."""
        
        if response.data:
            article = response.data[0]  # Get first match
            
            # Handle potential None values
            title = article.get('title', 'No title') or 'No title'
            url = article.get('url', 'No URL') or 'No URL'
            domain = article.get('domain', 'unknown') or 'unknown'
            content = article.get('content', 'No content') or 'No content'
            word_count = article.get('word_count', 0) or 0
            created_at = article.get('created_at', 'Unknown date') or 'Unknown date'
            image_urls = article.get('image_urls', []) or []
            
            return f"""
✅ **ARTICLE FOUND IN DATABASE**

**📰 Title:** {title}
**🔗 URL:** {url}
**🌐 Domain:** {domain}
**📊 Word Count:** {word_count}
**📅 Stored:** {created_at}

**📄 Content Preview:**
{content[:500]}...

**🖼️ Images Available:** {len(image_urls)} images
**📊 Full Article Ready for Script Generation**

**Full Content:**
{content}
"""
        else:
            return f"""❌ **NO ARTICLES FOUND**

**What happened:** No articles found with keyword "{keyword}" in our database

**What we can do next:**
1. 🔍 **Search for new articles** about "{keyword}"
2. 📋 **Browse existing articles** to see what's available
3. 🔄 **Try different keywords** (e.g., "quantum", "India quantum", "quantum breakthrough")
4. 🔗 **Provide a specific URL** if you have one

**What would you like me to do?** Please let me know your preference."""
                
    except Exception as e:
        return f"""❌ **DATABASE ERROR OCCURRED**

**What happened:** {str(e)}

**What we can do next:**
1. 🔍 **Search for new articles** about "{keyword}"
2. 📋 **Browse existing articles** in the database
3. 🔄 **Try again** in a moment
4. 🔗 **Provide a specific URL** if you have one

**What would you like me to do?** Please let me know your preference."""

@tool
def get_article_id_by_url(url: str) -> str:
    """Get article ID by URL for script linking.
    
    Args:
        url: The URL of the article
    
    Returns:
        Article ID if found, None otherwise
    """
    try:
        url_hash = hashlib.md5(url.encode()).hexdigest()
        supabase = get_supabase_client()
        
        response = supabase.table('articles').select('id,title').eq('url_hash', url_hash).execute()
        
        if response.data:
            return response.data[0]['id']
        else:
            return None
        
    except Exception as e:
        return None

@tool
def store_script_content(script_data: dict) -> str:
    """Store generated script in Supabase database linked to article.
    
    Args:
        script_data: Dictionary containing:
            - article_id: UUID of the related article
            - platform: Target platform (youtube, tiktok, etc.)
            - script_content: The generated script
            - hook: The script hook
            - visual_suggestions: List of visual suggestions
            - metadata: Additional script metadata
    
    Returns:
        Confirmation message with storage details
    """
    try:
        # Validate required fields
        required_fields = ['article_id', 'script_content', 'platform']
        for field in required_fields:
            if not script_data.get(field):
                return f"❌ Error: Missing required '{field}' field"
        
        # Prepare storage data
        storage_data = {
            'article_id': script_data['article_id'],
            'platform': script_data['platform'].lower(),
            'script_content': script_data['script_content'],
            'hook': script_data.get('hook', ''),
            'visual_suggestions': script_data.get('visual_suggestions', []),
            'metadata': script_data.get('metadata', {}),
            'approved': script_data.get('approved', False),
            'created_at': datetime.now().isoformat()
        }
        
        supabase = get_supabase_client()
        result = supabase.table('scripts').insert(storage_data).execute()
        
        if result.data:
            script_id = result.data[0]['id']
            
            return f"""
✅ **SCRIPT SUCCESSFULLY STORED IN SUPABASE**

**📊 Storage Details:**
- Script ID: {script_id}
- Article ID: {storage_data['article_id']}
- Platform: {storage_data['platform'].upper()}
- Script Length: {len(storage_data['script_content'])} characters
- Visual Suggestions: {len(storage_data['visual_suggestions'])} items
- Status: Pending Approval
- Timestamp: {storage_data['created_at']}

**🗄️ Database Status:** Script stored and linked to article.
"""
        else:
            return "❌ Error storing script: No data returned"
        
    except Exception as e:
        return f"❌ Error storing script in Supabase: {str(e)}"

@tool
def retrieve_stored_scripts(platform: str = None, limit: int = 10, approved_only: bool = False) -> str:
    """Retrieve stored scripts from Supabase database.
    
    Args:
        platform: Optional platform filter (e.g., 'youtube', 'tiktok')
        limit: Maximum number of scripts to retrieve
        approved_only: If True, only return approved scripts
        
    Returns:
        Formatted list of stored scripts
    """
    try:
        supabase = get_supabase_client()
        
        if not supabase:
            return "❌ Error: Unable to connect to database. Please check your Supabase configuration."
        
        # Build query with joins to get article title
        query = supabase.table('scripts').select(
            'id,article_id,platform,script_content,hook,visual_suggestions,approved,created_at,articles(title,url,domain)'
        ).order('created_at', desc=True).limit(limit)
        
        if platform:
            query = query.eq('platform', platform.lower())
            
        if approved_only:
            query = query.eq('approved', True)
        
        response = query.execute()
        
        if not response or not hasattr(response, 'data'):
            return "❌ Error: Invalid response from database. Please try again."
        
        if not response.data:
            return "📭 No scripts found in the database."
        
        scripts_list = "📜 **STORED SCRIPTS FROM SUPABASE DATABASE**\n\n"
        
        for i, script in enumerate(response.data, 1):
            # Handle potential None values
            script_id = script.get('id', 'Unknown')
            platform = script.get('platform', 'unknown') or 'unknown'
            script_content = script.get('script_content', 'No content') or 'No content'
            hook = script.get('hook', 'No hook') or 'No hook'
            visual_count = len(script.get('visual_suggestions', []))
            approved = script.get('approved', False)
            created_at = script.get('created_at', 'Unknown date') or 'Unknown date'
            
            # Get article info
            article_info = script.get('articles', {}) or {}
            article_title = article_info.get('title', 'Unknown Article') if article_info else 'Unknown Article'
            article_url = article_info.get('url', 'No URL') if article_info else 'No URL'
            
            status_emoji = "✅" if approved else "⏳"
            status_text = "Approved" if approved else "Pending"
            
            scripts_list += f"""
**{i}. {article_title[:50]}... - {platform.upper()}**
- Script ID: {script_id}
- Article URL: {article_url}
- Platform: {platform.upper()}
- Hook: {hook[:50]}...
- Visual Suggestions: {visual_count}
- Status: {status_emoji} {status_text}
- Created: {created_at[:19] if len(str(created_at)) > 19 else created_at}
- Content Preview: {script_content[:100]}...
---
"""
        
        return scripts_list
        
    except Exception as e:
        return f"❌ Error retrieving scripts: {str(e)}\n\n**Possible solutions:**\n1. Check database connection\n2. Verify Supabase credentials\n3. Try again in a moment\n4. Contact support if issue persists"

@tool
def get_script_by_id(script_id: str) -> str:
    """Retrieve a specific script by ID from Supabase.
    
    Args:
        script_id: The ID of the script to retrieve
        
    Returns:
        Full script content if found
    """
    try:
        supabase = get_supabase_client()
        
        response = supabase.table('scripts').select(
            'id,article_id,platform,script_content,hook,visual_suggestions,approved,created_at,metadata,articles(title,url,domain)'
        ).eq('id', script_id).execute()
        
        if not response.data:
            return f"❌ Script not found in database for ID: {script_id}"
        
        script = response.data[0]
        article_info = script.get('articles', {}) or {}
        
        return f"""
📜 **SCRIPT RETRIEVED FROM SUPABASE**

**Script ID:** {script['id']}
**Article Title:** {article_info.get('title', 'Unknown Article')}
**Article URL:** {article_info.get('url', 'No URL')}
**Platform:** {script['platform'].upper()}
**Status:** {"✅ Approved" if script['approved'] else "⏳ Pending"}
**Created:** {script['created_at']}

**Hook:**
{script['hook']}

**Script Content:**
{script['script_content']}

**Visual Suggestions:**
{', '.join(script.get('visual_suggestions', []))}

**Metadata:**
{json.dumps(script.get('metadata', {}), indent=2)}
"""
        
    except Exception as e:
        return f"❌ Error retrieving script: {str(e)}"

@tool
def get_scripts_by_article_id(article_id: str) -> str:
    """Retrieve all scripts for a specific article.
    
    Args:
        article_id: The ID of the article
        
    Returns:
        List of scripts for the article
    """
    try:
        supabase = get_supabase_client()
        
        response = supabase.table('scripts').select(
            'id,platform,script_content,hook,visual_suggestions,approved,created_at'
        ).eq('article_id', article_id).order('created_at', desc=True).execute()
        
        if not response.data:
            return f"❌ No scripts found for article ID: {article_id}"
        
        scripts_list = f"📜 **SCRIPTS FOR ARTICLE {article_id}**\n\n"
        
        for i, script in enumerate(response.data, 1):
            status_emoji = "✅" if script['approved'] else "⏳"
            status_text = "Approved" if script['approved'] else "Pending"
            
            scripts_list += f"""
**{i}. {script['platform'].upper()} Script**
- Script ID: {script['id']}
- Status: {status_emoji} {status_text}
- Hook: {script['hook'][:50]}...
- Visual Suggestions: {len(script.get('visual_suggestions', []))}
- Created: {script['created_at'][:19]}
- Content: {script['script_content'][:100]}...
---
"""
        
        return scripts_list
        
    except Exception as e:
        return f"❌ Error retrieving scripts for article: {str(e)}"

@tool
def approve_script(script_id: str) -> str:
    """Approve a script and mark it as ready for use.
    
    Args:
        script_id: UUID of the script to approve
    
    Returns:
        Confirmation message
    """
    try:
        supabase = get_supabase_client()
        
        result = supabase.table('scripts').update({
            "approved": True, 
            "updated_at": datetime.now().isoformat()
        }).eq('id', script_id).execute()
        
        if result.data:
            return f"""
✅ **SCRIPT APPROVED SUCCESSFULLY**

**📊 Details:**
- Script ID: {script_id}
- Status: Approved ✅
- Ready for content creation!

**🚀 Next Steps:** Script is now ready for social media content creation.
"""
        else:
            return f"❌ Error approving script: Script not found"
        
    except Exception as e:
        return f"❌ Error approving script: {str(e)}"

# Create the main tools list with all functions
supabase_tools_sync_wrapped = [
    store_article_content_sync_wrapped,
    store_multiple_articles,
    retrieve_stored_articles,
    get_article_by_url,
    get_stored_article_by_keyword,
    get_article_id_by_url,
    store_script_content,
    retrieve_stored_scripts,
    get_script_by_id,
    get_scripts_by_article_id,
    approve_script
]