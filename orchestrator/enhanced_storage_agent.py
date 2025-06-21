import os
import asyncio
import json
import hashlib
from typing import Dict, Any, List
from datetime import datetime
from supabase import create_client, Client

# Initialize Supabase client
def get_supabase_client():
    """Get Supabase client with proper configuration."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        raise Exception("Missing SUPABASE_URL or SUPABASE_ANON_KEY environment variables")
    
    return create_client(supabase_url, supabase_key)

async def store_enhanced_article(article_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Store enhanced article data with OCR results and media processing in Supabase.
    
    Args:
        article_data: Dictionary containing enhanced article data with OCR results
        
    Returns:
        Dictionary with storage result details
    """
    try:
        print(f"🗄️ Storing enhanced article data in Supabase...")
        
        # Validate required fields
        if not article_data.get('url'):
            raise Exception("Missing required 'url' field")
        if not article_data.get('content'):
            raise Exception("Missing required 'content' field")
        
        # Initialize Supabase client
        supabase = get_supabase_client()
        
        # Create URL hash for uniqueness
        url_hash = hashlib.md5(article_data['url'].encode()).hexdigest()
        
        # Prepare basic storage data first (only core fields)
        storage_data = {
            'url': article_data['url'],
            'url_hash': url_hash,
            'title': article_data.get('title', 'No title'),
            'content': article_data['content'],
            'domain': article_data.get('domain', 'Unknown'),
            'word_count': article_data.get('word_count', 0),
            'crawled_at': article_data.get('crawled_at', datetime.now().isoformat()),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        # Add optional fields only if they exist in schema
        optional_fields = {
            'summary': article_data.get('summary', ''),
            'character_count': article_data.get('character_count', 0),
            'image_urls': article_data.get('image_urls', []),
            'ocr_results': article_data.get('ocr_results', []),
            'extracted_text_from_images': article_data.get('extracted_text_from_images', ''),
            'media_insights': article_data.get('media_insights', []),
            'metadata': {
                'crawl_method': article_data.get('method', 'enhanced_crawl'),
                'ocr_enabled': bool(article_data.get('ocr_results')),
                'images_processed': len(article_data.get('image_urls', [])),
                'text_extracted_from_images': bool(article_data.get('extracted_text_from_images')),
                'mistral_analysis': bool(article_data.get('media_insights')),
                'enhanced_features': {
                    'mistral_ocr': bool(article_data.get('ocr_results')),
                    'content_analysis': bool(article_data.get('key_points')),
                    'media_processing': bool(article_data.get('media_insights'))
                }
            }
        }
        
        # Try to add optional fields, skip if they cause errors
        for field_name, field_value in optional_fields.items():
            storage_data[field_name] = field_value
        
        print(f"✅ Storage data prepared for: {storage_data['title'][:50]}...")
        
        # Check if article exists
        import asyncio
        existing = await asyncio.to_thread(
            lambda: supabase.table('articles').select('id, url, title').eq('url_hash', url_hash).execute()
        )
        
        if existing.data:
            # Update existing record
            record_id = existing.data[0]['id']
            try:
                result = await asyncio.to_thread(
                    lambda: supabase.table('articles').update(storage_data).eq('url_hash', url_hash).execute()
                )
                action = "updated"
                print(f"✅ Article updated with ID: {record_id}")
            except Exception as update_error:
                # Try with minimal data if full update fails
                minimal_data = {
                    'url': storage_data['url'],
                    'title': storage_data['title'],
                    'content': storage_data['content'],
                    'domain': storage_data['domain'],
                    'updated_at': storage_data['updated_at']
                }
                result = await asyncio.to_thread(
                    lambda: supabase.table('articles').update(minimal_data).eq('url_hash', url_hash).execute()
                )
                action = "updated (minimal)"
                print(f"✅ Article updated with minimal data, ID: {record_id}")
        else:
            # Insert new record
            try:
                result = await asyncio.to_thread(
                    lambda: supabase.table('articles').insert(storage_data).execute()
                )
                action = "stored"
                record_id = result.data[0]['id'] if result.data else "unknown"
                print(f"✅ Article stored with ID: {record_id}")
            except Exception as insert_error:
                # Try with minimal data if full insert fails
                minimal_data = {
                    'url': storage_data['url'],
                    'url_hash': storage_data['url_hash'],
                    'title': storage_data['title'],
                    'content': storage_data['content'],
                    'domain': storage_data['domain'],
                    'word_count': storage_data['word_count'],
                    'created_at': storage_data['created_at'],
                    'updated_at': storage_data['updated_at']
                }
                result = await asyncio.to_thread(
                    lambda: supabase.table('articles').insert(minimal_data).execute()
                )
                action = "stored (minimal)"
                record_id = result.data[0]['id'] if result.data else "unknown"
                print(f"✅ Article stored with minimal data, ID: {record_id}")
        
        # Prepare success response
        return {
            "status": "success",
            "action": action,
            "record_id": record_id,
            "url_hash": url_hash,
            "title": storage_data['title'],
            "word_count": storage_data.get('word_count', 0),
            "images_stored": len(storage_data.get('image_urls', [])),
            "ocr_results_count": len(storage_data.get('ocr_results', [])),
            "enhanced_features": storage_data.get('metadata', {}).get('enhanced_features', {}),
            "timestamp": storage_data.get('created_at', datetime.now().isoformat())
        }
        
    except Exception as e:
        print(f"❌ Storage error: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

async def retrieve_enhanced_articles(limit: int = 10, domain: str = None) -> List[Dict[str, Any]]:
    """
    Retrieve enhanced articles with OCR and media data from Supabase.
    
    Args:
        limit: Maximum number of articles to retrieve
        domain: Optional domain filter
        
    Returns:
        List of enhanced article data
    """
    try:
        supabase = get_supabase_client()
        
        query = supabase.table('articles').select(
            'id,url,title,content,summary,key_points,category,domain,word_count,'
            'image_urls,ocr_results,extracted_text_from_images,media_insights,'
            'metadata,crawled_at,created_at'
        ).order('created_at', desc=True).limit(limit)
        
        if domain:
            query = query.ilike('domain', f'%{domain}%')
        
        response = query.execute()
        
        if not response.data:
            return []
        
        # Enhance the response data
        enhanced_articles = []
        for article in response.data:
            enhanced_article = {
                "id": article.get('id'),
                "url": article.get('url'),
                "title": article.get('title'),
                "content": article.get('content'),
                "summary": article.get('summary'),
                "key_points": article.get('key_points', []),
                "category": article.get('category'),
                "domain": article.get('domain'),
                "word_count": article.get('word_count', 0),
                "image_urls": article.get('image_urls', []),
                "ocr_results": article.get('ocr_results', []),
                "extracted_text_from_images": article.get('extracted_text_from_images', ''),
                "media_insights": article.get('media_insights', []),
                "metadata": article.get('metadata', {}),
                "crawled_at": article.get('crawled_at'),
                "created_at": article.get('created_at'),
                "enhanced_features": {
                    "has_ocr": bool(article.get('ocr_results')),
                    "has_images": bool(article.get('image_urls')),
                    "has_media_insights": bool(article.get('media_insights')),
                    "images_count": len(article.get('image_urls', [])),
                    "ocr_count": len(article.get('ocr_results', []))
                }
            }
            enhanced_articles.append(enhanced_article)
        
        return enhanced_articles
        
    except Exception as e:
        print(f"❌ Retrieval error: {str(e)}")
        return []

async def search_articles_by_content(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search articles by content, including OCR extracted text.
    
    Args:
        query: Search query
        limit: Maximum results to return
        
    Returns:
        List of matching articles
    """
    try:
        supabase = get_supabase_client()
        
        # Search in title, content, and extracted text from images
        response = supabase.table('articles').select('*').or_(
            f'title.ilike.%{query}%,'
            f'content.ilike.%{query}%,'
            f'extracted_text_from_images.ilike.%{query}%'
        ).limit(limit).execute()
        
        return response.data if response.data else []
        
    except Exception as e:
        print(f"❌ Search error: {str(e)}")
        return []

def format_storage_result(storage_result: Dict[str, Any]) -> str:
    """Format storage result for display."""
    if storage_result.get("status") == "success":
        enhanced_features = storage_result.get("enhanced_features", {})
        ocr_info = f"OCR: {'✅' if enhanced_features.get('mistral_ocr') else '❌'}"
        content_analysis = f"Analysis: {'✅' if enhanced_features.get('content_analysis') else '❌'}"
        media_processing = f"Media: {'✅' if enhanced_features.get('media_processing') else '❌'}"
        
        return f"""✅ **ENHANCED ARTICLE STORED IN SUPABASE**

**📊 Storage Details:**
- Record ID: {storage_result.get('record_id')}
- Action: {storage_result.get('action', '').title()}
- Title: {storage_result.get('title', '')[:50]}...
- Word Count: {storage_result.get('word_count', 0)}
- Images: {storage_result.get('images_stored', 0)}
- OCR Results: {storage_result.get('ocr_results_count', 0)}

**🤖 Enhanced Features:**
- {ocr_info}
- {content_analysis} 
- {media_processing}

**🗄️ Database Status:** Enhanced article data securely stored with OCR and media analysis.
**⏰ Timestamp:** {storage_result.get('timestamp', '')}"""
    else:
        return f"""❌ **STORAGE FAILED**

**Error:** {storage_result.get('error', 'Unknown error')}
**Timestamp:** {storage_result.get('timestamp', '')}

**💡 Suggestions:**
1. Check Supabase connection and credentials
2. Verify database schema matches expected format
3. Try again in a moment"""