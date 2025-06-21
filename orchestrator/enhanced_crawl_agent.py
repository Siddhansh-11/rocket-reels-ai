import os
import asyncio
import httpx
import json
import re
from typing import Dict, Any, List
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from datetime import datetime
import base64
from io import BytesIO
from PIL import Image
import requests

# Import Mistral for OCR and content analysis
try:
    from mistralai import Mistral
    MISTRAL_AVAILABLE = True
except ImportError:
    MISTRAL_AVAILABLE = False
    print("⚠️ Mistral AI not available. Install with: pip install mistralai")

# Initialize Mistral client
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
mistral_client = Mistral(api_key=MISTRAL_API_KEY) if MISTRAL_API_KEY and MISTRAL_AVAILABLE else None

async def enhanced_crawl_with_media_ocr(url: str) -> Dict[str, Any]:
    """
    Enhanced web crawling with Mistral OCR for media processing.
    Extracts text content, images, and performs OCR on images.
    """
    try:
        print(f"🕷️ Starting enhanced crawl with media OCR: {url}")
        
        # Step 1: Basic HTML crawling
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
        soup = BeautifulSoup(response.text, 'html.parser')
        domain = urlparse(url).netloc.lower()
        
        # Step 2: Extract basic article content
        article_data = await extract_article_content(soup, url, domain)
        
        # Step 3: Extract and process images with OCR
        image_data = await extract_and_process_images(soup, url, domain)
        
        # Step 4: Combine and enhance with Mistral analysis
        if mistral_client:
            enhanced_data = await enhance_with_mistral_analysis(article_data, image_data, url)
        else:
            enhanced_data = article_data
            enhanced_data.update(image_data)
        
        # Step 5: Prepare final structured data
        final_data = {
            "url": url,
            "domain": domain,
            "title": enhanced_data.get("title", "No title"),
            "content": enhanced_data.get("content", ""),
            "summary": enhanced_data.get("summary", ""),
            "key_points": enhanced_data.get("key_points", []),
            "category": enhanced_data.get("category", "Technology"),
            "word_count": len(enhanced_data.get("content", "").split()),
            "character_count": len(enhanced_data.get("content", "")),
            "image_urls": enhanced_data.get("image_urls", []),
            "image_metadata": enhanced_data.get("image_metadata", {}),
            "ocr_results": enhanced_data.get("ocr_results", []),
            "media_insights": enhanced_data.get("media_insights", []),
            "extracted_text_from_images": enhanced_data.get("extracted_text_from_images", ""),
            "crawled_at": datetime.now().isoformat(),
            "method": "enhanced_crawl_with_mistral_ocr"
        }
        
        return final_data
        
    except Exception as e:
        raise Exception(f"Enhanced crawl with OCR failed: {str(e)}")

async def extract_article_content(soup: BeautifulSoup, url: str, domain: str) -> Dict[str, Any]:
    """Extract main article content using site-specific selectors."""
    
    # Extract title
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
            if len(title) > 10:
                break
    
    # Extract content with site-specific selectors
    content_selectors = []
    
    if 'techcrunch.com' in domain:
        content_selectors = ['.article-content', '.entry-content', '.post-content']
    elif 'theverge.com' in domain:
        content_selectors = ['.c-entry-content', '.e-content', 'div[data-testid="BodyText"]']
    elif 'wired.com' in domain:
        content_selectors = ['.ArticleBodyComponent', '.article-body-component']
    elif 'nytimes.com' in domain:
        content_selectors = ['.StoryBodyCompanionColumn div', 'section[name="articleBody"]']
    else:
        content_selectors = [
            'article .content', '[role="main"] article', '.post-content',
            '.entry-content', '.article-content', '.content', 'article', 'main'
        ]
    
    article_content = ""
    for selector in content_selectors:
        content_elem = soup.select_one(selector)
        if content_elem:
            # Remove unwanted elements
            for unwanted in content_elem.find_all([
                'script', 'style', 'nav', 'footer', 'aside', 
                '.advertisement', '.ad', '.social-share'
            ]):
                unwanted.decompose()
            
            paragraphs = content_elem.find_all(['p', 'div'])
            content_paragraphs = []
            for p in paragraphs:
                text = p.get_text(strip=True)
                if len(text) > 50:
                    content_paragraphs.append(text)
            
            if content_paragraphs:
                article_content = '\n\n'.join(content_paragraphs)
                break
    
    # Fallback content extraction
    if not article_content or len(article_content) < 200:
        all_paragraphs = soup.find_all('p')
        meaningful_paragraphs = []
        
        for p in all_paragraphs:
            text = p.get_text(strip=True)
            if (len(text) > 50 and 
                not any(skip in text.lower() for skip in [
                    'cookie', 'privacy', 'newsletter', 'subscribe', 
                    'advertisement', 'follow us', 'share this'
                ])):
                meaningful_paragraphs.append(text)
        
        if meaningful_paragraphs:
            article_content = '\n\n'.join(meaningful_paragraphs[:15])
    
    return {
        "title": title,
        "content": article_content,
        "summary": f"Article from {domain}",
        "key_points": [],
        "category": "Technology"
    }

async def extract_and_process_images(soup: BeautifulSoup, url: str, domain: str) -> Dict[str, Any]:
    """Extract images and process them with OCR if Mistral is available."""
    
    images = []
    img_tags = soup.find_all('img')
    
    print(f"📷 Found {len(img_tags)} image tags on {domain}")
    
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
    
    # Limit to top 5 images for OCR processing
    images = images[:5]
    
    ocr_results = []
    extracted_text_from_images = ""
    
    # Process images with Mistral OCR if available
    if mistral_client and images:
        print(f"🔍 Processing {len(images)} images with Mistral OCR...")
        
        for i, img_data in enumerate(images):
            try:
                ocr_result = await process_image_with_mistral_ocr(img_data['url'], img_data.get('alt', ''))
                if ocr_result:
                    ocr_results.append(ocr_result)
                    if ocr_result.get('extracted_text'):
                        extracted_text_from_images += f"\n[Image {i+1}]: {ocr_result['extracted_text']}"
            except Exception as e:
                print(f"⚠️ OCR failed for image {i+1}: {str(e)}")
                continue
    
    return {
        "image_urls": [img['url'] for img in images],
        "image_metadata": {"images": images},
        "ocr_results": ocr_results,
        "extracted_text_from_images": extracted_text_from_images.strip()
    }

async def process_image_with_mistral_ocr(image_url: str, alt_text: str = "") -> Dict[str, Any]:
    """Process a single image with Mistral OCR."""
    try:
        # Download image
        async with httpx.AsyncClient(timeout=20.0) as client:
            img_response = await client.get(image_url)
            img_response.raise_for_status()
        
        # Convert to base64
        image_data = base64.b64encode(img_response.content).decode('utf-8')
        
        # Use Mistral vision model for OCR
        response = await asyncio.to_thread(
            mistral_client.chat.complete,
            model="pixtral-12b-2409",  # Mistral's vision model
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"""Analyze this image and extract any text content you can see. Also describe what's in the image.

Image context (alt text): {alt_text}

Please provide:
1. Any text visible in the image (OCR)
2. Brief description of the image content
3. Key visual elements that might be relevant to the article

Format your response as:
TEXT_FOUND: [any text you can read]
DESCRIPTION: [brief description]
KEY_ELEMENTS: [important visual elements]"""
                        },
                        {
                            "type": "image_url",
                            "image_url": f"data:image/jpeg;base64,{image_data}"
                        }
                    ]
                }
            ]
        )
        
        response_text = response.choices[0].message.content
        
        # Parse the response
        extracted_text = ""
        description = ""
        key_elements = ""
        
        lines = response_text.split('\n')
        for line in lines:
            if line.startswith('TEXT_FOUND:'):
                extracted_text = line.replace('TEXT_FOUND:', '').strip()
            elif line.startswith('DESCRIPTION:'):
                description = line.replace('DESCRIPTION:', '').strip()
            elif line.startswith('KEY_ELEMENTS:'):
                key_elements = line.replace('KEY_ELEMENTS:', '').strip()
        
        return {
            "image_url": image_url,
            "extracted_text": extracted_text,
            "description": description,
            "key_elements": key_elements,
            "alt_text": alt_text,
            "ocr_method": "mistral_pixtral"
        }
        
    except Exception as e:
        print(f"⚠️ Mistral OCR failed for {image_url}: {str(e)}")
        return None

async def enhance_with_mistral_analysis(article_data: Dict, image_data: Dict, url: str) -> Dict[str, Any]:
    """Use Mistral to enhance and analyze the combined content."""
    try:
        combined_content = f"""
ARTICLE CONTENT:
{article_data.get('content', '')}

EXTRACTED TEXT FROM IMAGES:
{image_data.get('extracted_text_from_images', '')}

IMAGE DESCRIPTIONS:
{json.dumps([ocr.get('description', '') for ocr in image_data.get('ocr_results', [])], indent=2)}
"""
        
        analysis_response = await asyncio.to_thread(
            mistral_client.chat.complete,
            model="mistral-small-latest",
            messages=[
                {
                    "role": "user",
                    "content": f"""Analyze this webpage content (including text extracted from images) and provide a comprehensive analysis:

URL: {url}
CONTENT: {combined_content[:8000]}...  

Please provide:
1. A clean, well-structured version of the main article content
2. A 2-sentence summary
3. 3-5 key points from the article
4. Category classification (AI, Tech, Business, Science, etc.)
5. Any insights gained from the images/visual content
6. Overall content quality assessment

Format as:
TITLE: [main title]
SUMMARY: [2-sentence summary]
CONTENT: [cleaned main content]
KEY_POINTS: 
- [point 1]
- [point 2]
- [point 3]
CATEGORY: [category]
MEDIA_INSIGHTS: [insights from images/visuals]
QUALITY: [assessment of content quality and completeness]"""
                }
            ]
        )
        
        response_text = analysis_response.choices[0].message.content
        
        # Parse the enhanced analysis
        title = article_data.get('title', 'No title')
        summary = ""
        content = article_data.get('content', '')
        key_points = []
        category = "Technology"
        media_insights = []
        
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
                content = line.replace('CONTENT:', '').strip()
            elif line.startswith('KEY_POINTS:'):
                current_section = 'key_points'
            elif line.startswith('CATEGORY:'):
                category = line.replace('CATEGORY:', '').strip()
            elif line.startswith('MEDIA_INSIGHTS:'):
                current_section = 'media_insights'
                insight = line.replace('MEDIA_INSIGHTS:', '').strip()
                if insight:
                    media_insights.append(insight)
            elif current_section == 'content' and line:
                content += '\n' + line
            elif current_section == 'key_points' and line.startswith('-'):
                key_points.append(line.replace('-', '').strip())
            elif current_section == 'media_insights' and line:
                media_insights.append(line)
        
        # Combine all data
        enhanced_data = {
            "title": title,
            "content": content.strip(),
            "summary": summary,
            "key_points": key_points,
            "category": category,
            "media_insights": media_insights
        }
        
        # Add image data
        enhanced_data.update(image_data)
        
        return enhanced_data
        
    except Exception as e:
        print(f"⚠️ Mistral analysis failed: {str(e)}")
        # Return basic data with image info
        result = article_data.copy()
        result.update(image_data)
        return result