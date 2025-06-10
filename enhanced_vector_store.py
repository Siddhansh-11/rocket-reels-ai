import os
import chromadb
from chromadb.utils import embedding_functions
import hashlib
from datetime import datetime
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import aiohttp
import asyncio
from typing import List, Dict, Any, Optional
import base64
from PIL import Image
import io

class EnhancedNewsVectorStore:
    def __init__(self):
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path="./news_db")
        
        # Create embedding function
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
        
        # Get or create collections
        self.articles_collection = self.client.get_or_create_collection(
            name="news_articles",
            embedding_function=self.embedding_function
        )
        
        self.media_collection = self.client.get_or_create_collection(
            name="article_media",
            embedding_function=self.embedding_function
        )
        
        # Headers for web scraping
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    async def fetch_article_content(self, url: str) -> Dict[str, Any]:
        """Fetch full article content from URL"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, timeout=10) as response:
                    if response.status == 200:
                        html_content = await response.text()
                        return self._parse_article_content(html_content, url)
                    else:
                        return {"error": f"HTTP {response.status}", "url": url}
        except Exception as e:
            return {"error": str(e), "url": url}
    
    def _parse_article_content(self, html_content: str, url: str) -> Dict[str, Any]:
        """Parse article content and extract media"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Extract article content
        article_content = self._extract_article_text(soup)
        
        # Extract media
        media_items = self._extract_media(soup, url)
        
        # Extract metadata
        metadata = self._extract_metadata(soup)
        
        return {
            "url": url,
            "content": article_content,
            "media": media_items,
            "metadata": metadata,
            "word_count": len(article_content.split()),
            "scraped_at": datetime.now().isoformat()
        }
    
    def _extract_article_text(self, soup: BeautifulSoup) -> str:
        """Extract main article text using multiple strategies"""
        # Strategy 1: Look for common article containers
        article_selectors = [
            'article',
            '[role="main"]',
            '.article-content',
            '.post-content',
            '.entry-content',
            '.content',
            'main',
            '.story-body',
            '.article-body'
        ]
        
        for selector in article_selectors:
            elements = soup.select(selector)
            if elements:
                # Get the largest text block
                texts = [elem.get_text(strip=True) for elem in elements]
                if texts:
                    return max(texts, key=len)
        
        # Strategy 2: Find paragraphs in likely containers
        content_areas = soup.find_all(['div', 'section'], class_=lambda x: x and any(
            keyword in x.lower() for keyword in ['content', 'article', 'story', 'post']
        ))
        
        if content_areas:
            for area in content_areas:
                paragraphs = area.find_all('p')
                if len(paragraphs) >= 3:  # At least 3 paragraphs
                    return '\n'.join([p.get_text(strip=True) for p in paragraphs])
        
        # Strategy 3: All paragraphs (fallback)
        paragraphs = soup.find_all('p')
        if paragraphs:
            return '\n'.join([p.get_text(strip=True) for p in paragraphs])
        
        # Last resort: body text
        return soup.get_text(strip=True)
    
    def _extract_media(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """Extract images, videos, and other media"""
        media_items = []
        
        # Extract images
        images = soup.find_all('img')
        for img in images:
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            if src:
                full_url = urljoin(base_url, src)
                media_items.append({
                    "type": "image",
                    "url": full_url,
                    "alt": img.get('alt', ''),
                    "caption": self._find_image_caption(img),
                    "dimensions": {
                        "width": img.get('width'),
                        "height": img.get('height')
                    }
                })
        
        # Extract videos
        videos = soup.find_all(['video', 'iframe'])
        for video in videos:
            if video.name == 'video':
                src = video.get('src')
                if src:
                    media_items.append({
                        "type": "video",
                        "url": urljoin(base_url, src),
                        "poster": video.get('poster', ''),
                        "duration": video.get('duration', '')
                    })
            elif 'youtube' in str(video.get('src', '')):
                media_items.append({
                    "type": "youtube_embed",
                    "url": video.get('src'),
                    "embed_code": str(video)
                })
        
        return media_items
    
    def _find_image_caption(self, img_element) -> str:
        """Find caption for an image"""
        # Look for caption in nearby elements
        parent = img_element.parent
        if parent:
            # Check for figcaption
            figcaption = parent.find('figcaption')
            if figcaption:
                return figcaption.get_text(strip=True)
            
            # Check for caption class
            caption = parent.find(class_=lambda x: x and 'caption' in x.lower())
            if caption:
                return caption.get_text(strip=True)
        
        return ""
    
    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract article metadata"""
        metadata = {}
        
        # Author
        author_selectors = [
            'meta[name="author"]',
            '.author',
            '.byline',
            '[rel="author"]'
        ]
        for selector in author_selectors:
            element = soup.select_one(selector)
            if element:
                metadata['author'] = element.get('content') or element.get_text(strip=True)
                break
        
        # Published date
        date_selectors = [
            'meta[property="article:published_time"]',
            'meta[name="publishdate"]',
            'time[datetime]',
            '.publish-date',
            '.date'
        ]
        for selector in date_selectors:
            element = soup.select_one(selector)
            if element:
                metadata['published_date'] = element.get('content') or element.get('datetime') or element.get_text(strip=True)
                break
        
        # Keywords/Tags
        keywords = soup.find('meta', attrs={'name': 'keywords'})
        if keywords:
            metadata['keywords'] = keywords.get('content', '').split(',')
        
        # Description
        description = soup.find('meta', attrs={'name': 'description'})
        if description:
            metadata['meta_description'] = description.get('content', '')
        
        return metadata
    
    async def process_and_store_article(self, article_data: Dict[str, Any]) -> str:
        """Process a news article and store full content + media"""
        try:
            # Create unique ID for article
            article_id = hashlib.md5(article_data['url'].encode()).hexdigest()
            
            print(f"🔄 Processing article: {article_id}")
            
            # Check if already processed
            try:
                existing = self.articles_collection.get(ids=[article_id])
                if existing['ids']:
                    print(f"✅ Article {article_id} already exists")
                    return article_id
            except:
                pass
            
            # Fetch full article content
            print(f"📝 Fetching content for: {article_data['url']}")
            full_content = await self.fetch_article_content(article_data['url'])
            
            if 'error' in full_content:
                print(f"⚠️ Error fetching full content: {full_content['error']}")
                # Use basic info if scraping fails
                text_content = f"{article_data['title']} {article_data.get('description', '')}"
                scraped_metadata = {}
                content = article_data.get('description', '')
                word_count = len(content.split()) if content else 0
            else:
                # Use scraped content
                text_content = f"{article_data['title']} {article_data.get('description', '')} {full_content.get('content', '')[:2000]}"
                scraped_metadata = full_content.get('metadata', {})
                content = full_content.get('content', '')
                word_count = full_content.get('word_count', 0)
            
            # Flatten metadata - ChromaDB only accepts str, int, float, bool, None
            metadata = {
                "source": article_data.get('source', {}).get('name', ''),
                "published_at": article_data.get('publishedAt', ''),
                "url": article_data['url'],
                "category": article_data.get('category', 'general'),
                "stored_at": datetime.now().isoformat(),
                "title": article_data.get('title', ''),
                "description": article_data.get('description', ''),
                "word_count": word_count,
                "has_full_content": 'error' not in full_content,
                # Flatten scraped metadata
                "scraped_author": scraped_metadata.get('author', ''),
                "scraped_published_date": scraped_metadata.get('published_date', ''),
                "scraped_meta_description": scraped_metadata.get('meta_description', ''),
                "scraped_keywords": ', '.join(scraped_metadata.get('keywords', [])) if scraped_metadata.get('keywords') else ''
            }
            
            print(f"💾 Storing in ChromaDB with metadata keys: {list(metadata.keys())}")
            
            # Store article in vector database
            self.articles_collection.add(
                documents=[text_content],
                metadatas=[metadata],
                ids=[article_id]
            )
            
            # Store media separately if available
            if full_content.get('media'):
                await self._store_media_items(article_id, full_content['media'])
            
            print(f"✅ Successfully stored article {article_id}")
            return article_id
            
        except Exception as e:
            print(f"❌ Error processing article: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def _store_media_items(self, article_id: str, media_items: List[Dict[str, Any]]):
        """Store media items separately"""
        for i, media in enumerate(media_items):
            media_id = f"{article_id}_media_{i}"
            
            # Create embedding text for media
            media_text = f"{media.get('type', '')} {media.get('alt', '')} {media.get('caption', '')}"
            
            # Flatten media metadata
            media_metadata = {
                "article_id": article_id,
                "media_type": media.get('type', ''),
                "url": media.get('url', ''),
                "alt_text": media.get('alt', ''),
                "caption": media.get('caption', ''),
                "stored_at": datetime.now().isoformat(),
                # Flatten dimensions if they exist
                "width": str(media.get('dimensions', {}).get('width', '')) if media.get('dimensions', {}).get('width') else '',
                "height": str(media.get('dimensions', {}).get('height', '')) if media.get('dimensions', {}).get('height') else ''
            }
            
            try:
                self.media_collection.add(
                    documents=[media_text],
                    metadatas=[media_metadata],
                    ids=[media_id]
                )
                print(f"📸 Stored media: {media_id}")
            except Exception as e:
                print(f"⚠️ Error storing media {media_id}: {e}")
    
    def search_articles_with_media(self, query: str, n_results: int = 5, include_media: bool = True) -> Dict[str, Any]:
        """Search articles and optionally include their media"""
        try:
            # Search articles
            article_results = self.articles_collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            results = {
                "articles": [],
                "total_found": len(article_results['documents'][0]) if article_results['documents'] else 0
            }
            
            if not article_results['documents'] or not article_results['documents'][0]:
                return results
            
            # Process each article
            for i, (doc, metadata, distance) in enumerate(zip(
                article_results['documents'][0],
                article_results['metadatas'][0],
                article_results['distances'][0]
            )):
                article_data = {
                    "content": doc,
                    "metadata": metadata,
                    "relevance_score": 1 - distance,
                    "media": []
                }
                
                # Get associated media if requested
                if include_media:
                    article_id = article_results['ids'][0][i]
                    media_items = self._get_article_media(article_id)
                    article_data["media"] = media_items
                
                results["articles"].append(article_data)
            
            return results
            
        except Exception as e:
            print(f"Error searching articles: {e}")
            return {"articles": [], "total_found": 0, "error": str(e)}
    
    def _get_article_media(self, article_id: str) -> List[Dict[str, Any]]:
        """Get all media items for an article"""
        try:
            # Query media collection for this article
            all_media = self.media_collection.get()
            
            article_media = []
            for i, metadata in enumerate(all_media['metadatas']):
                if metadata.get('article_id') == article_id:
                    article_media.append({
                        "type": metadata.get('media_type', ''),
                        "url": metadata.get('url', ''),
                        "alt_text": metadata.get('alt_text', ''),
                        "caption": metadata.get('caption', ''),
                        "width": metadata.get('width', ''),
                        "height": metadata.get('height', ''),
                        "description": all_media['documents'][i]
                    })
            
            return article_media
            
        except Exception as e:
            print(f"Error getting media for article {article_id}: {e}")
            return []
    
    def get_articles_by_source(self, source_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get articles from a specific news source"""
        try:
            all_articles = self.articles_collection.get()
            
            source_articles = []
            for i, metadata in enumerate(all_articles['metadatas']):
                if metadata.get('source', '').lower() == source_name.lower():
                    source_articles.append({
                        "content": all_articles['documents'][i],
                        "metadata": metadata,
                        "media": self._get_article_media(all_articles['ids'][i])
                    })
                    
                    if len(source_articles) >= limit:
                        break
            
            return source_articles
            
        except Exception as e:
            print(f"Error getting articles by source: {e}")
            return []