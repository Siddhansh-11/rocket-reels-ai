# Supabase Operations Summary

This document summarizes all files in the orchestrator directory and related locations that handle Supabase operations, particularly those related to retrieving scripts.

## Key Files Handling Supabase Operations

### 1. **orchestrator/enhanced_storage_agent.py**
- **Purpose**: Handles enhanced article storage with OCR results and media processing
- **Key Functions**:
  - `get_supabase_client()` - Initializes Supabase client
  - `store_enhanced_article()` - Stores articles with OCR and media data
  - `retrieve_enhanced_articles()` - Retrieves articles with filters
  - `search_articles_by_content()` - Searches articles including OCR text
  - `format_storage_result()` - Formats storage results for display

### 2. **orchestrator/scripting_agent.py**
- **Purpose**: Manages script generation and storage
- **Key Functions**:
  - `get_supabase_client()` - Initializes Supabase client
  - `store_script_content()` - Stores generated scripts linked to articles
  - `retrieve_scripts()` - Retrieves scripts with optional filters
  - `update_script()` - Updates existing scripts
  - `delete_script()` - Deletes scripts
  - `check_scripts_table_access()` - Verifies script table accessibility
  - `generate_and_store_script()` - Generates and stores scripts from articles

### 3. **orchestrator/chat_agent_fixed.py** (NEW)
- **Purpose**: Intelligent chat agent for routing and database operations
- **Key Functions**:
  - `retrieve_stored_articles()` - Tool to retrieve articles from database
  - `check_script_table()` - Tool to check script table access
  - `route_to_search()` - Routes users to search functionality
  - `route_to_crawl()` - Routes users to crawl functionality
  - `route_to_script_generation()` - Routes users to script generation
  - `run_chat_agent_sync()` - Synchronous wrapper for chat agent

### 4. **orchestrator/langraph_workflow.py**
- **Purpose**: Main workflow orchestration
- **Key Agents/Functions**:
  - `retrieve_articles_agent()` - Retrieves and displays stored articles
  - `check_script_table_access()` - Checks script table accessibility
  - `intelligent_chat_agent()` - Routes user queries intelligently
  - `crawl_and_store_agent()` - Crawls articles and stores in Supabase
  - `write_script()` - Generates and stores scripts

### 5. **langgraph/supabase_agent.py**
- **Purpose**: Original Supabase agent with core storage functions
- **Key Functions**:
  - `store_article_content_sync_wrapped()` - Stores articles synchronously
  - `store_multiple_articles()` - Batch article storage
  - `retrieve_stored_articles()` - Retrieves articles with domain filter
  - `get_article_by_url()` - Retrieves specific article by URL
  - `get_stored_article_by_keyword()` - Searches articles by keyword
  - `get_article_id_by_url()` - Gets article ID for script linking
  - `store_script_content()` - Stores generated scripts
  - `approve_script()` - Approves scripts for use

## Common Issues and Solutions

### 1. "Chat agent not available" Error
- **Cause**: Import error with `langgraph.prebuilt.create_react_agent`
- **Solution**: Created `chat_agent_fixed.py` using `langchain.agents.create_structured_chat_agent` instead
- **Files Fixed**: 
  - `orchestrator/chat_agent_fixed.py` (new)
  - `orchestrator/orchestration_agent_fixed.py` (new)
  - Updated imports in `langraph_workflow.py`

### 2. Script Table Access
- **Function**: `check_scripts_table_access()` in `scripting_agent.py`
- **Usage**: Verifies if scripts table is accessible and returns count
- **Integration**: Available as both standalone function and chat agent tool

### 3. Article Retrieval
- **Multiple Implementations**:
  - `retrieve_enhanced_articles()` - Enhanced version with OCR data
  - `retrieve_stored_articles()` - Basic version with filters
  - `get_stored_article_by_keyword()` - Keyword search functionality

## Environment Variables Required
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_ANON_KEY` or `SUPABASE_KEY` - Supabase API key
- `DEEPSEEK_API_KEY` - For chat agents

## Database Tables Used
1. **articles** - Stores crawled article content
   - Fields: id, url, url_hash, title, content, domain, word_count, image_urls, ocr_results, etc.
   
2. **scripts** - Stores generated scripts
   - Fields: id, article_id, platform, content, style, template, metadata, created_at, etc.

## Workflow Integration
1. User searches for content → `search_agent`
2. User selects article to crawl → `crawl_and_store_agent`
3. Article stored in Supabase → `enhanced_storage_agent`
4. User requests script generation → `scripting_agent`
5. Scripts stored and linked to articles → Database

## Key Features
- Enhanced OCR processing with Mistral AI
- Media insights extraction
- Script generation for multiple platforms (YouTube, TikTok, Instagram)
- Intelligent routing based on user intent
- Database status checking and reporting