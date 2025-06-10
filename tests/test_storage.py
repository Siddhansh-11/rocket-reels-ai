import asyncio
import os
from dotenv import load_dotenv
from enhanced_vector_store import EnhancedNewsVectorStore
import requests

load_dotenv()

async def test_direct_storage():
    """Test storing articles directly"""
    print("🧪 Testing direct article storage...")
    
    # Initialize vector store
    news_store = EnhancedNewsVectorStore()
    
    # Get a real article from NewsAPI
    api_key = os.getenv("NEWSAPI_API_KEY")
    response = requests.get(
        "https://newsapi.org/v2/top-headlines",
        params={
            "apiKey": api_key,
            "category": "technology",
            "language": "en",
            "pageSize": 1
        }
    )
    
    if response.status_code == 200:
        articles = response.json().get('articles', [])
        if articles:
            article = articles[0]
            article['category'] = 'technology'
            
            print(f"📰 Testing with article: {article['title']}")
            print(f"🔗 URL: {article['url']}")
            
            # Test async storage
            try:
                article_id = await news_store.process_and_store_article(article)
                print(f"✅ Stored article with ID: {article_id}")
                
                # Check if it's really stored
                stored_articles = news_store.articles_collection.get()
                print(f"📊 Articles now in DB: {len(stored_articles['ids'])}")
                
                if stored_articles['ids']:
                    print(f"✅ Success! First stored article: {stored_articles['metadatas'][0]}")
                else:
                    print("❌ Article not found in database after storage")
                    
            except Exception as e:
                print(f"❌ Storage failed: {e}")
                import traceback
                traceback.print_exc()
    else:
        print(f"❌ API request failed: {response.status_code}")

if __name__ == "__main__":
    asyncio.run(test_direct_storage())