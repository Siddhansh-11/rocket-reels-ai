# Enhanced Crawl & Storage Setup

## ✅ What's Been Fixed

### 1. Enhanced Web Crawling
- **Real-time web scraping** with site-specific content extraction
- **Mistral AI OCR integration** for image text extraction
- **Content analysis** using Mistral for better structured data
- **Media processing** with image metadata and insights

### 2. Advanced Storage System
- **Supabase integration** with enhanced schema support
- **OCR results storage** for searchable image text
- **Media metadata storage** including image insights
- **Comprehensive article data** with enhanced features

### 3. Workflow Integration
- **Smart routing** - detects crawl commands automatically
- **Chat interface** - works seamlessly in LangGraph Studio
- **Error handling** - robust fallbacks and error reporting
- **Cost tracking** - monitors API usage

## 🚀 How to Use

### Basic Crawling
In LangGraph Studio chat, type:
```
crawl https://techcrunch.com/some-article
```

### Advanced Commands
```
scrape https://www.theverge.com/article-with-images
extract https://arstechnica.com/tech-policy/article/
```

## 🔧 Required Setup

### 1. Environment Variables (.env)
```bash
# Required for OCR and analysis
MISTRAL_API_KEY=your_mistral_api_key

# Required for storage
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key

# Optional for enhanced search (already working)
TAVILY_API_KEY=your_tavily_api_key
```

### 2. Supabase Database Schema
Create table with enhanced fields:

```sql
CREATE TABLE articles (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  url TEXT NOT NULL,
  url_hash TEXT UNIQUE NOT NULL,
  title TEXT,
  content TEXT,
  summary TEXT,
  key_points JSONB DEFAULT '[]'::jsonb,
  category TEXT DEFAULT 'Technology',
  domain TEXT,
  word_count INTEGER DEFAULT 0,
  character_count INTEGER DEFAULT 0,
  
  -- Media and OCR fields
  image_urls JSONB DEFAULT '[]'::jsonb,
  stored_image_urls JSONB DEFAULT '[]'::jsonb,
  image_metadata JSONB DEFAULT '{}'::jsonb,
  image_storage_metadata JSONB DEFAULT '{}'::jsonb,
  ocr_results JSONB DEFAULT '[]'::jsonb,
  extracted_text_from_images TEXT,
  media_insights JSONB DEFAULT '[]'::jsonb,
  
  -- Enhanced metadata
  metadata JSONB DEFAULT '{}'::jsonb,
  
  -- Timestamps
  crawled_at TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  status TEXT DEFAULT 'stored'
);

-- Indexes for performance
CREATE INDEX idx_articles_url_hash ON articles(url_hash);
CREATE INDEX idx_articles_domain ON articles(domain);
CREATE INDEX idx_articles_created_at ON articles(created_at DESC);
CREATE INDEX idx_articles_content_search ON articles USING gin(to_tsvector('english', content));
```

## 🎯 Features Overview

### Enhanced Crawling (`enhanced_crawl_agent.py`)
- **Site-specific extraction** for TechCrunch, The Verge, Wired, NYTimes
- **Mistral OCR processing** extracts text from images
- **Content analysis** generates summaries and key points
- **Media insights** analyzes visual content relevance

### Smart Storage (`enhanced_storage_agent.py`)
- **Duplicate detection** using URL hashing
- **Enhanced metadata** tracking OCR and analysis results
- **Searchable content** including image-extracted text
- **Performance optimized** with proper indexing

### Workflow Integration
- **Auto-detection** of crawl commands in chat
- **Real-time feedback** shows progress and results
- **Error recovery** with fallback mechanisms
- **Cost tracking** for API usage monitoring

## 📊 What You Get

### Article Data Structure
```json
{
  "url": "https://example.com/article",
  "title": "Article Title",
  "content": "Full article content...",
  "summary": "AI-generated summary",
  "key_points": ["Point 1", "Point 2", "Point 3"],
  "category": "Technology",
  "image_urls": ["image1.jpg", "image2.jpg"],
  "ocr_results": [
    {
      "image_url": "image1.jpg",
      "extracted_text": "Text found in image",
      "description": "Image description",
      "key_elements": "Visual elements"
    }
  ],
  "extracted_text_from_images": "Combined text from all images",
  "media_insights": ["Insight 1", "Insight 2"],
  "word_count": 1500,
  "method": "enhanced_crawl_with_mistral_ocr"
}
```

### Storage Result
```
✅ ENHANCED CRAWL AND STORAGE WITH MISTRAL OCR COMPLETED

📰 Article Details:
- Title: Breaking: New AI Development Revolutionizes Tech...
- Domain: techcrunch.com
- Word Count: 1,247
- Method: enhanced_crawl_with_mistral_ocr

📄 Content Preview:
A groundbreaking artificial intelligence system has been developed...

🎯 Key Points:
• Revolutionary AI breakthrough in natural language processing
• 40% improvement in accuracy over previous models
• Commercial applications expected within 6 months

📷 Media Processing:
- Images Found: 3
🔍 OCR Results: Processed 3 images with text extraction
👁️ Media Insights: Technical diagrams showing architecture; Performance charts indicating improvements

📝 Extracted Text from Images:
Figure 1: AI Model Architecture - Input Layer: 512 nodes, Hidden Layers: 2048 nodes each...

✅ ENHANCED ARTICLE STORED IN SUPABASE
🤖 Enhanced Features: OCR: ✅, Analysis: ✅, Media: ✅
🔗 Article URL: https://techcrunch.com/article
📊 Ready for script generation and content creation!
```

## 🧪 Testing

### Test Commands
```
# Basic crawl test
crawl https://techcrunch.com/2024/01/15/openai-gpt-4-update/

# Test with images
scrape https://www.theverge.com/2024/1/10/apple-vision-pro-review

# Test content analysis
extract https://arstechnica.com/gadgets/quantum-computing-breakthrough/
```

### Expected Results
1. **Article extracted** with clean content
2. **Images processed** with OCR text extraction
3. **Stored in Supabase** with enhanced metadata
4. **Chat feedback** showing comprehensive results
5. **Database record** with all enhanced features

## 🎯 Next Steps

The crawl and storage system is now fully operational with:
- ✅ Real-time web crawling
- ✅ Mistral OCR integration  
- ✅ Enhanced Supabase storage
- ✅ LangGraph workflow integration
- ✅ Error handling and fallbacks

**Ready for use!** Just add your API keys and start crawling articles with enhanced media processing and intelligent storage.