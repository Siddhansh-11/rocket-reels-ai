import os
import asyncio
import json
from typing import Dict, Any, List, Optional
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

async def store_script_content(script_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Store generated script in Supabase database linked to article.
    
    Args:
        script_data: Dictionary containing:
            - article_id: UUID of the related article
            - platform: Target platform (youtube, tiktok, etc.)
            - content: The generated script content
            - style: Script style
            - template: Script template used
            - duration: Expected duration in seconds
            - metadata: Additional script metadata
    
    Returns:
        Dictionary with storage result details
    """
    try:
        print(f"📝 Storing script content in Supabase...")
        
        # Validate required fields
        required_fields = ['article_id', 'content', 'platform']
        for field in required_fields:
            if not script_data.get(field):
                raise Exception(f"Missing required '{field}' field")
        
        # Initialize Supabase client
        supabase = get_supabase_client()
        
        # Prepare storage data
        storage_data = {
            'article_id': script_data['article_id'],
            'content': script_data['content'],
            'style': script_data.get('style', 'standard'),
            'template': script_data.get('template', 'default'),
            'platform': script_data['platform'].lower(),
            'duration': script_data.get('duration'),
            'metadata': script_data.get('metadata', {}),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        # Store script in database
        result = supabase.table('scripts').insert(storage_data).execute()
        
        if result.data:
            script_id = result.data[0]['id']
            print(f"✅ Script stored successfully with ID: {script_id}")
            
            return {
                'success': True,
                'script_id': script_id,
                'article_id': storage_data['article_id'],
                'platform': storage_data['platform'],
                'content_length': len(storage_data['content']),
                'created_at': storage_data['created_at'],
                'message': f"Script successfully stored with ID: {script_id}"
            }
        else:
            raise Exception("No data returned from script insertion")
        
    except Exception as e:
        error_msg = f"Error storing script: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            'success': False,
            'error': error_msg,
            'message': error_msg
        }

async def retrieve_scripts(article_id: Optional[str] = None, platform: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
    """
    Retrieve scripts from Supabase database with optional filters.
    
    Args:
        article_id: Optional article ID filter
        platform: Optional platform filter
        limit: Maximum number of scripts to retrieve
        
    Returns:
        Dictionary with retrieved scripts
    """
    try:
        print(f"🔍 Retrieving scripts from Supabase...")
        
        # Initialize Supabase client
        supabase = get_supabase_client()
        
        # Build query
        query = supabase.table('scripts').select('*')
        
        # Apply filters
        if article_id:
            query = query.eq('article_id', article_id)
        if platform:
            query = query.eq('platform', platform.lower())
        
        # Execute query with limit
        result = query.limit(limit).order('created_at', desc=True).execute()
        
        scripts = result.data if result.data else []
        
        print(f"✅ Retrieved {len(scripts)} scripts")
        
        return {
            'success': True,
            'scripts': scripts,
            'count': len(scripts),
            'message': f"Retrieved {len(scripts)} scripts"
        }
        
    except Exception as e:
        error_msg = f"Error retrieving scripts: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            'success': False,
            'error': error_msg,
            'scripts': [],
            'count': 0,
            'message': error_msg
        }

async def update_script(script_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update script in Supabase database.
    
    Args:
        script_id: ID of the script to update
        updates: Dictionary of fields to update
        
    Returns:
        Dictionary with update result
    """
    try:
        print(f"📝 Updating script {script_id} in Supabase...")
        
        # Initialize Supabase client
        supabase = get_supabase_client()
        
        # Add updated timestamp
        updates['updated_at'] = datetime.now().isoformat()
        
        # Update script
        result = supabase.table('scripts').update(updates).eq('id', script_id).execute()
        
        if result.data:
            print(f"✅ Script {script_id} updated successfully")
            
            return {
                'success': True,
                'script_id': script_id,
                'updated_fields': list(updates.keys()),
                'message': f"Script {script_id} updated successfully"
            }
        else:
            raise Exception("Script not found or update failed")
        
    except Exception as e:
        error_msg = f"Error updating script: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            'success': False,
            'error': error_msg,
            'message': error_msg
        }

async def delete_script(script_id: str) -> Dict[str, Any]:
    """
    Delete script from Supabase database.
    
    Args:
        script_id: ID of the script to delete
        
    Returns:
        Dictionary with deletion result
    """
    try:
        print(f"🗑️ Deleting script {script_id} from Supabase...")
        
        # Initialize Supabase client
        supabase = get_supabase_client()
        
        # Delete script
        result = supabase.table('scripts').delete().eq('id', script_id).execute()
        
        if result.data:
            print(f"✅ Script {script_id} deleted successfully")
            
            return {
                'success': True,
                'script_id': script_id,
                'message': f"Script {script_id} deleted successfully"
            }
        else:
            raise Exception("Script not found or deletion failed")
        
    except Exception as e:
        error_msg = f"Error deleting script: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            'success': False,
            'error': error_msg,
            'message': error_msg
        }

async def check_scripts_table_access() -> Dict[str, Any]:
    """
    Check if scripts table is accessible and return basic info.
    
    Returns:
        Dictionary with table access status
    """
    try:
        print(f"🔍 Checking scripts table accessibility...")
        
        # Initialize Supabase client
        supabase = get_supabase_client()
        
        # Try to query the scripts table
        result = supabase.table('scripts').select('id,created_at').limit(1).execute()
        
        # Check if table exists and is accessible
        table_accessible = True
        script_count_result = supabase.table('scripts').select('id', count='exact').execute()
        total_scripts = script_count_result.count if script_count_result.count is not None else 0
        
        print(f"✅ Scripts table is accessible with {total_scripts} records")
        
        return {
            'success': True,
            'table_accessible': table_accessible,
            'total_scripts': total_scripts,
            'message': f"Scripts table accessible with {total_scripts} records"
        }
        
    except Exception as e:
        error_msg = f"Error accessing scripts table: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            'success': False,
            'table_accessible': False,
            'error': error_msg,
            'message': error_msg
        }

# Main functions for orchestrator workflow
async def generate_and_store_script(article_data: Dict[str, Any], script_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate and store script based on article data and configuration.
    
    Args:
        article_data: Article data containing content to generate script from
        script_config: Configuration for script generation (platform, style, etc.)
        
    Returns:
        Dictionary with generation and storage result
    """
    try:
        print(f"🎬 Generating and storing script for article...")
        
        # Extract article ID
        article_id = article_data.get('id') or article_data.get('article_id')
        if not article_id:
            raise Exception("Missing article ID in article data")
        
        # Generate script content (placeholder - replace with actual generation logic)
        platform = script_config.get('platform', 'youtube')
        style = script_config.get('style', 'engaging')
        
        # TODO: Replace this with actual script generation logic
        script_content = f"Generated {platform} script for article: {article_data.get('title', 'Untitled')}"
        
        # Prepare script data
        script_data = {
            'article_id': article_id,
            'content': script_content,
            'platform': platform,
            'style': style,
            'template': script_config.get('template', 'default'),
            'duration': script_config.get('duration'),
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'article_title': article_data.get('title'),
                'article_url': article_data.get('url'),
                'generation_config': script_config
            }
        }
        
        # Store script
        storage_result = await store_script_content(script_data)
        
        return storage_result
        
    except Exception as e:
        error_msg = f"Error generating and storing script: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            'success': False,
            'error': error_msg,
            'message': error_msg
        }