import os
import asyncio
from langchain_core.tools import tool
import httpx
from dotenv import load_dotenv
from urllib.parse import urlparse, urljoin
import re
from bs4 import BeautifulSoup
from typing import List, Dict
from mistralai import Mistral
import json

# Load environment variables
load_dotenv("../.env")

# API Keys - Only what's needed for crawling
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

# Initialize Mistral client
mistral_client = Mistral(api_key=MISTRAL_API_KEY) if MISTRAL_API_KEY else None

async def enhanced_html_parsing(url: str) -> Dict:
    """Enhanced HTML parsing with site-specific selectors and better content extraction."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
        soup = BeautifulSoup(response.text, 'html.parser')
        domain = urlparse(url).netloc.lower()
        
        # Extract title with multiple fallbacks
        title = "No title found"
        title_selectors = [
            'h1[data-testid="headline"]',  # NY Times
            'h1.article-title',
            'h1.headline',
            '.headline h1',
            'article h1',
            '.post-title',
            '.entry-title',
            'h1',
            'title'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = title_elem.get_text(strip=True)
                if len(title) > 10:  # Ensure it's a meaningful title
                    break
        
        # Enhanced content extraction with site-specific selectors
        content_selectors = []
        
        # Site-specific selectors
        if 'nytimes.com' in domain:
            content_selectors = [
                '.StoryBodyCompanionColumn div[data-testid="photoviewer-wrapper"] ~ div',
                '.StoryBodyCompanionColumn div',
                'section[name="articleBody"]',
                '.css-53u6y8',  # NYT article body class
                'article section'
            ]
        elif 'techcrunch.com' in domain:
            content_selectors = [
                '.article-content',
                '.entry-content',
                '.post-content'
            ]
        elif 'theverge.com' in domain:
            content_selectors = [
                '.c-entry-content',
                '.e-content',
                'div[data-testid="BodyText"]'
            ]
        elif 'wired.com' in domain:
            content_selectors = [
                '.ArticleBodyComponent',
                '.article-body-component',
                'div[data-testid="BodyText"]'
            ]
        elif 'cnbc.com' in domain:
            content_selectors = [
                '[data-module="ArticleBody"]',
                '.ArticleBody-articleBody',
                '.InlineText-container'
            ]
        else:
            # Generic selectors
            content_selectors = [
                'article .content',
                '[role="main"] article',
                '.post-content',
                '.entry-content',
                '.article-content',
                '.content',
                'article',
                'main'
            ]
        
        article_content = ""
        content_paragraphs = []
        
        # Try site-specific selectors first
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                # Remove unwanted elements
                for unwanted in content_elem.find_all([
                    'script', 'style', 'nav', 'footer', 'aside', 
                    '.advertisement', '.ad', '.social-share',
                    '.newsletter', '.related-articles', '.sidebar'
                ]):
                    unwanted.decompose()
                
                # Extract paragraphs
                paragraphs = content_elem.find_all(['p', 'div'])
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if len(text) > 50:  # Only meaningful paragraphs
                        content_paragraphs.append(text)
                
                if content_paragraphs:
                    article_content = '\n\n'.join(content_paragraphs)
                    break
        
        # Fallback: Extract all meaningful paragraphs from the page
        if not article_content or len(article_content) < 200:
            print("🔄 Using fallback paragraph extraction...")
            all_paragraphs = soup.find_all('p')
            meaningful_paragraphs = []
            
            for p in all_paragraphs:
                text = p.get_text(strip=True)
                # Filter out short paragraphs and common non-content text
                if (len(text) > 50 and 
                    not any(skip in text.lower() for skip in [
                        'cookie', 'privacy', 'newsletter', 'subscribe', 
                        'advertisement', 'follow us', 'share this'
                    ])):
                    meaningful_paragraphs.append(text)
            
            # Take the first reasonable chunk of paragraphs
            if meaningful_paragraphs:
                article_content = '\n\n'.join(meaningful_paragraphs[:15])  # Limit to first 15 paragraphs
        
        # Final validation
        if not article_content or len(article_content) < 100:
            # Last resort: get all text content and clean it
            body = soup.find('body')
            if body:
                # Remove scripts, styles, etc.
                for unwanted in body.find_all(['script', 'style', 'nav', 'footer', 'header']):
                    unwanted.decompose()
                
                all_text = body.get_text(separator='\n', strip=True)
                lines = [line.strip() for line in all_text.split('\n') if len(line.strip()) > 30]
                article_content = '\n'.join(lines[:20])  # Take first 20 meaningful lines
        
        return {
            "title": title,
            "content": article_content,
            "summary": f"Article from {domain}",
            "key_points": [],
            "category": "Technology",
            "word_count": len(article_content.split()) if article_content else 0,
            "character_count": len(article_content) if article_content else 0,
            "domain": domain,
            "method": "enhanced_html_parsing"
        }
        
    except Exception as e:
        raise Exception(f"Enhanced HTML parsing failed: {str(e)}")

async def mistral_content_analysis(content: str, url: str) -> Dict:
    """Use Mistral to analyze HTML content and extract structured information."""
    try:
        if not mistral_client:
            raise Exception("Mistral API key not available")
        
        print(f"🤖 Analyzing content with Mistral AI...")
        
        # Use Mistral to analyze and clean the content
        analysis_response = await asyncio.to_thread(
            mistral_client.chat.complete,
            model="mistral-small-latest",
            messages=[
                {
                    "role": "user",
                    "content": f"""Analyze this webpage content and extract the main article information:

URL: {url}
CONTENT: {content[:8000]}...  

Please provide a clean, structured extraction in this format:

TITLE: [Extract the main article title]
SUMMARY: [Write a 2-sentence summary of the article]
CONTENT: [Extract and clean the main article content, removing navigation, ads, etc.]
KEY_POINTS: [List 3-4 key points from the article]
CATEGORY: [Categorize as: AI, Tech, Business, Science, etc.]

Focus on the main article content only, ignore navigation, comments, ads, and sidebars."""
                }
            ]
        )
        
        response_text = analysis_response.choices[0].message.content
        
        # Parse the response
        title = "No title found"
        summary = ""
        clean_content = ""
        key_points = []
        category = "Technology"
        
        lines = response_text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('TITLE:'):
                title = line.replace('TITLE:', '').strip()
            elif line.startswith('SUMMARY:'):
                summary = line.replace('SUMMARY:', '').strip()
            elif line.startswith('CONTENT:'):
                current_section = 'content'
                clean_content = line.replace('CONTENT:', '').strip()
            elif line.startswith('KEY_POINTS:'):
                current_section = 'key_points'
            elif line.startswith('CATEGORY:'):
                category = line.replace('CATEGORY:', '').strip()
            elif current_section == 'content' and line:
                clean_content += '\n' + line
            elif current_section == 'key_points' and line and line.startswith('-'):
                key_points.append(line.replace('-', '').strip())
        
        # Validate that we got meaningful content
        if not clean_content or len(clean_content) < 100:
            raise Exception("Mistral extracted insufficient content")
        
        return {
            "title": title,
            "content": clean_content.strip(),
            "summary": summary,
            "key_points": key_points,
            "category": category,
            "word_count": len(clean_content.split()),
            "character_count": len(clean_content),
            "domain": urlparse(url).netloc,
            "method": "mistral_analysis"
        }
        
    except Exception as e:
        raise Exception(f"Mistral content analysis failed: {str(e)}")

async def extract_media_urls_enhanced(url: str) -> Dict:
    """Enhanced media extraction with better filtering."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
        soup = BeautifulSoup(response.text, 'html.parser')
        domain = urlparse(url).netloc
        
        # Extract images with better filtering
        images = []
        img_tags = soup.find_all('img')
        
        for img in img_tags:
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or img.get('data-original')
            
            if src:
                # Convert relative URLs to absolute
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    src = urljoin(url, src)
                
                # Filter out small/icon images and data URIs
                if (src and src.startswith('http') and 
                    not src.startswith('data:') and
                    not any(skip in src.lower() for skip in ['icon', 'logo-header', 'avatar', 'thumb']) and
                    not src.endswith('.svg')):
                    
                    images.append({
                        'url': src,
                        'alt': img.get('alt', ''),
                        'width': img.get('width'),
                        'height': img.get('height')
                    })
        
        # Limit to top 10 images
        images = images[:10]
        
        print(f"📷 Found {len(images)} high-quality images from {domain}")
        
        return {
            "images": images,
            "videos": []
        }
        
    except Exception as e:
        print(f"⚠️ Media extraction error for {url}: {str(e)}")
        return {"images": [], "videos": []}

@tool
async def crawl_article_content(url: str) -> str:
    """
    Crawls article using enhanced content analysis.
    
    Args:
        url (str): The URL of the article to crawl.
    
    Returns:
        str: JSON-formatted string containing article content and media URLs.
    """
    try:
        print(f"🕷️ Starting enhanced crawl of: {url}")
        
        # Validate URL
        if not url or not url.startswith(('http://', 'https://')):
            return f"❌ Invalid URL: {url}"
        
        # Extract media URLs first
        print("📷 Extracting high-quality media URLs...")
        media_data = await extract_media_urls_enhanced(url)
        
        # Try enhanced HTML parsing first (more reliable)
        try:
            print("🔧 Trying enhanced HTML parsing...")
            article_data = await enhanced_html_parsing(url)
            
            # If we got good content, we're done
            if article_data.get('content') and len(article_data['content']) > 200:
                print(f"✅ Enhanced HTML parsing successful: {len(article_data['content'])} characters")
            else:
                raise Exception("Insufficient content from enhanced parsing")
                
        except Exception as html_error:
            print(f"⚠️ Enhanced HTML parsing failed: {html_error}")
            
            # Try Mistral as fallback
            try:
                print("🤖 Falling back to Mistral AI analysis...")
                # Get raw content for Mistral
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(url, headers={'User-Agent': 'Mozilla/5.0'})
                    soup = BeautifulSoup(response.text, 'html.parser')
                    raw_content = soup.get_text(separator='\n', strip=True)
                
                article_data = await mistral_content_analysis(raw_content, url)
                
            except Exception as mistral_error:
                print(f"⚠️ Mistral analysis also failed: {mistral_error}")
                # Use the enhanced HTML result even if content is limited
                article_data = await enhanced_html_parsing(url)
        
        # Combine article data with media data
        article_data['image_urls'] = [img['url'] for img in media_data['images']]
        article_data['video_urls'] = []
        article_data['image_metadata'] = media_data
        article_data['url'] = url  # Ensure URL is included
        
        # Validate that we have meaningful content
        if not article_data.get('content') or len(article_data.get('content', '')) < 50:
            return f"❌ Failed to extract meaningful content from {url}. Content too short or empty."
        
        # Format result
        formatted_result = f"""
✅ **ARTICLE SUCCESSFULLY CRAWLED**

**📰 Title:** {article_data['title']}
**🌐 Domain:** {article_data['domain']}
**📊 Stats:** {article_data['word_count']} words, {article_data['character_count']} characters
**🔧 Method:** {article_data.get('method', 'unknown')}
**📂 Category:** {article_data.get('category', 'Technology')}
**🖼️ Images:** {len(article_data.get('image_urls', []))}

**📋 Summary:**
{article_data.get('summary', 'No summary available')}

**🔑 Key Points:**
{chr(10).join([f"• {point}" for point in article_data.get('key_points', [])])}

**📄 FULL ARTICLE CONTENT:**
{article_data['content']}

**🖼️ Images Found:**
{chr(10).join([f"- {img_url}" for img_url in article_data['image_urls'][:5]])}

**🗄️ Ready for storage by Supabase agent!**

**📦 STRUCTURED DATA (for storage agent):**
```json
{json.dumps(article_data, indent=2, ensure_ascii=False)}
```
"""
        
        return formatted_result.strip()
        
    except Exception as e:
        return f"❌ Failed to crawl {url}: {str(e)}"

# Create crawl agent tools list - ONLY crawling functionality
crawl_tools = [crawl_article_content]