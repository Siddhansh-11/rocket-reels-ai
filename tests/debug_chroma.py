import chromadb
from enhanced_vector_store import EnhancedNewsVectorStore
import os

def debug_chroma():
    """Debug ChromaDB to see what's stored"""
    print("🔍 Debugging ChromaDB...")
    
    # Check if database exists
    db_path = "./news_db"
    if os.path.exists(db_path):
        print(f"✅ Database directory exists: {db_path}")
        files = os.listdir(db_path)
        print(f"📁 Files in database: {files}")
    else:
        print(f"❌ Database directory doesn't exist: {db_path}")
    
    # Initialize vector store
    try:
        news_store = EnhancedNewsVectorStore()
        print("✅ Vector store initialized")
        
        # Check articles collection
        articles = news_store.articles_collection.get()
        print(f"📰 Articles in database: {len(articles['ids'])}")
        
        if articles['ids']:
            print("📋 Sample articles:")
            for i, (id, metadata) in enumerate(zip(articles['ids'][:3], articles['metadatas'][:3])):
                print(f"  {i+1}. {id}: {metadata.get('source', 'Unknown')} - {metadata.get('url', 'No URL')}")
        
        # Check media collection
        media = news_store.media_collection.get()
        print(f"🎨 Media items in database: {len(media['ids'])}")
        
        return len(articles['ids']), len(media['ids'])
        
    except Exception as e:
        print(f"❌ Error accessing vector store: {e}")
        return 0, 0

def test_news_api():
    """Test NewsAPI directly"""
    import requests
    from dotenv import load_dotenv
    
    load_dotenv()
    
    api_key = os.getenv("NEWSAPI_API_KEY")
    print(f"\n🔑 NewsAPI Key: {api_key[:10]}...{api_key[-5:]}")
    
    url = "https://newsapi.org/v2/top-headlines"
    params = {
        "apiKey": api_key,
        "category": "technology",
        "language": "en",
        "pageSize": 3
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"🌐 API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"📊 Total articles available: {data.get('totalResults', 0)}")
            print(f"📝 Articles returned: {len(data.get('articles', []))}")
            
            if data.get('articles'):
                print("\n📰 Sample articles:")
                for i, article in enumerate(data['articles'][:2]):
                    print(f"  {i+1}. {article['title']}")
                    print(f"     Source: {article['source']['name']}")
                    print(f"     URL: {article['url']}")
        else:
            print(f"❌ API Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Request Error: {e}")

if __name__ == "__main__":
    articles_count, media_count = debug_chroma()
    print(f"\n📊 Summary: {articles_count} articles, {media_count} media items")
    
    test_news_api()