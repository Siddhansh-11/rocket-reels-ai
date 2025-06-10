import os
from dotenv import load_dotenv
import gradio as gr
from langchain_anthropic import ChatAnthropic
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.tools import Tool
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import AIMessage, HumanMessage
from langchain_community.tools.tavily_search import TavilySearchResults
from datetime import datetime
import requests
import json
import asyncio
from enhanced_vector_store import EnhancedNewsVectorStore

# Load environment variables
load_dotenv()

# Initialize the language model with Claude
llm = ChatAnthropic(
    model="claude-3-5-sonnet-20240620",
    max_tokens=2000,
    temperature=0,
    anthropic_api_key=os.getenv("CLAUDE_API_KEY")
)

# Initialize enhanced vector store
news_store = EnhancedNewsVectorStore()

# Define custom tools
def get_current_time() -> str:
    """Get the current date and time."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def calculator(expression: str) -> str:
    """Evaluate a mathematical expression."""
    try:
        return str(eval(expression))
    except Exception as e:
        return f"Error calculating: {str(e)}"

def get_latest_news(query: str = "", category: str = "") -> str:
    """Enhanced news function with full content extraction and media storage"""
    api_key = os.getenv("NEWSAPI_API_KEY")
    if not api_key:
        return "News API key not found. Please set NEWSAPI_API_KEY in your .env file."
    
    # Parse input if it comes as JSON string from agent
    if query.startswith('{') and query.endswith('}'):
        try:
            import json
            parsed = json.loads(query)
            category = parsed.get('category', category)
            query = parsed.get('query', '')
        except:
            pass
    
    print(f"Debug: Fetching news with query='{query}', category='{category}'")
    
    # First check cached articles
    cached_response = ""
    if query:
        cached_results = news_store.search_articles_with_media(query, n_results=3)
        if cached_results['articles']:
            cached_response = "📚 Related cached articles:\n\n"
            for i, article in enumerate(cached_results['articles'][:2], 1):
                cached_response += f"{i}. {article['content'][:100]}...\n"
                cached_response += f"   Source: {article['metadata']['source']}\n"
                cached_response += f"   Media: {len(article['media'])} items\n"
                cached_response += f"   Relevance: {article['relevance_score']:.2f}\n\n"
    
    # Get fresh news from API
    url = "https://newsapi.org/v2/top-headlines"
    params = {
        "apiKey": api_key,
        "language": "en",
        "pageSize": 5
    }
    
    if query and query.strip():
        params["q"] = query
    if category and category.lower() in ["business", "entertainment", "general", "health", "science", "sports", "technology"]:
        params["category"] = category.lower()
    elif not query or not query.strip():
        params["category"] = "general"
    
    print(f"Debug: API request params: {params}")
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"Debug: API response status: {response.status_code}")
        
        if response.status_code == 200:
            news_data = response.json()
            print(f"Debug: Found {len(news_data.get('articles', []))} articles")
            
            if not news_data.get('articles'):
                return f"No articles found for category '{category}' or query '{query}'. Try a different search term."
            
            # Process articles asynchronously to fetch full content
            async def process_articles():
                tasks = []
                for article in news_data["articles"]:
                    if article.get('url'):  # Only process if URL exists
                        article['category'] = params.get('category', 'general')
                        tasks.append(news_store.process_and_store_article(article))
                
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
            
            # Run the async processing
            try:
                asyncio.run(process_articles())
            except Exception as e:
                print(f"Error processing articles: {e}")
            
            # Format results
            result = f"📰 Latest News {f'on {query}' if query else ''} {f'in {category}' if category else ''}:\n\n"
            for i, article in enumerate(news_data["articles"], 1):
                result += f"{i}. {article['title']}\n"
                result += f"   Source: {article['source']['name']}\n"
                result += f"   Published: {article['publishedAt']}\n"
                result += f"   Summary: {article['description'] if article['description'] else 'No description available'}\n"
                result += f"   URL: {article['url']}\n"
                result += f"   📸 Full content and media being processed...\n\n"
            
            # Add cached results if available
            if cached_response:
                result += "\n" + cached_response
            
            return result
        else:
            error_detail = response.text
            return f"Error fetching news: HTTP {response.status_code}. Details: {error_detail}"
    except requests.exceptions.Timeout:
        return "Request timed out. Please try again later."
    except requests.exceptions.ConnectionError:
        return "Connection error. Please check your internet connection."
    except Exception as e:
        return f"Error processing news request: {str(e)}"

def search_cached_news_with_media(query: str) -> str:
    """Search cached articles with full content and media"""
    try:
        results = news_store.search_articles_with_media(query, n_results=5, include_media=True)
        
        if not results['articles']:
            return "No cached articles found matching your query."
        
        result = f"🔍 Found {results['total_found']} cached articles for '{query}':\n\n"
        
        for i, article in enumerate(results['articles'], 1):
            metadata = article['metadata']
            result += f"{i}. Article from {metadata['source']}\n"
            result += f"   Published: {metadata.get('published_at', 'Unknown')}\n"
            result += f"   Word Count: {metadata.get('word_count', 0)} words\n"
            result += f"   Relevance: {article['relevance_score']:.2f}\n"
            result += f"   Content Preview: {article['content'][:200]}...\n"
            
            # Add media information
            if article['media']:
                result += f"   🎨 Media ({len(article['media'])} items):\n"
                for j, media in enumerate(article['media'][:3], 1):  # Show first 3 media items
                    result += f"     {j}. {media['type'].title()}: {media['alt_text'] or 'No description'}\n"
                if len(article['media']) > 3:
                    result += f"     ... and {len(article['media']) - 3} more\n"
            
            result += f"   URL: {metadata['url']}\n\n"
        
        return result
        
    except Exception as e:
        return f"Error searching cached articles: {str(e)}"

def get_articles_by_source(source_name: str) -> str:
    """Get articles from a specific news source with media"""
    try:
        articles = news_store.get_articles_by_source(source_name, limit=5)
        
        if not articles:
            return f"No articles found from source: {source_name}"
        
        result = f"📰 Articles from {source_name}:\n\n"
        
        for i, article in enumerate(articles, 1):
            metadata = article['metadata']
            result += f"{i}. Published: {metadata.get('published_at', 'Unknown')}\n"
            result += f"   Words: {metadata.get('word_count', 0)}\n"
            result += f"   Media: {len(article['media'])} items\n"
            result += f"   Preview: {article['content'][:150]}...\n"
            result += f"   URL: {metadata['url']}\n\n"
        
        return result
        
    except Exception as e:
        return f"Error getting articles by source: {str(e)}"

# Create Tavily search tool
tavily_search = TavilySearchResults(
    api_key=os.getenv("TAVILY_API_KEY"),
    max_results=5
)

# Define the tools
tools = [
    Tool(
        name="Search",
        func=tavily_search.run,
        description="Useful for searching the web for current information."
    ),
    Tool(
        name="Calculator",
        func=calculator,
        description="Useful for performing mathematical calculations. Input should be a mathematical expression."
    ),
    Tool(
        name="CurrentTime",
        func=get_current_time,
        description="Get the current date and time. No input is needed."
    ),
    Tool(
        name="LatestNews",
        func=get_latest_news,
        description="Get latest news headlines. For technology news, use category='technology'. For other categories use: business, entertainment, health, science, sports. You can also search with a specific query."
    ),
    Tool(
        name="SearchCachedNews",
        func=search_cached_news_with_media,
        description="Search through cached news articles with full content and media. Great for finding detailed information."
    ),
    Tool(
        name="GetArticlesBySource",
        func=get_articles_by_source,
        description="Get articles from a specific news source (e.g., 'BBC News', 'CNN', 'Reuters')."
    )
]

# Create the ReAct agent prompt template
template = """You are an intelligent assistant that helps users with their questions.
You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

IMPORTANT: When using LatestNews tool:
- For technology news, use: technology
- For business news, use: business
- For health news, use: health
- For science news, use: science
- For sports news, use: sports
- For entertainment news, use: entertainment
- For general news, use: general

Examples:
- User asks for "tech news" -> Action Input: technology
- User asks for "latest technology" -> Action Input: technology
- User asks for "AI news" -> Action Input: artificial intelligence

Begin!

Question: {input}
Thought: {agent_scratchpad}"""

prompt = PromptTemplate.from_template(template)

# Create the agent
agent = create_react_agent(
    llm=llm,
    tools=tools,
    prompt=prompt
)

# Create the agent executor
agent_executor = AgentExecutor.from_agent_and_tools(
    agent=agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=5
)

# Initialize chat history
chat_history = []

# Function to process user input
def process_input(message):
    global chat_history
    try:
        # Run the agent
        response = agent_executor.invoke({
            "input": message
        })
        return response["output"]
    except Exception as e:
        return f"Sorry, I encountered an error: {str(e)}"

# Create the Gradio interface
with gr.Blocks(title="AI Agent Dashboard") as demo:
    gr.Markdown("# 🤖 AI Agent Dashboard")
    gr.Markdown("Ask me anything! I can search the web, get the latest news, perform calculations, and more.")
    
    chatbot = gr.Chatbot(height=500, type="messages")
    msg = gr.Textbox(label="Your question", placeholder="Ask me about the latest news, search the web, or do calculations...")
    clear = gr.Button("Clear conversation")
    
    def respond(message, chat_history):
        bot_message = process_input(message)
        chat_history.append({"role": "user", "content": message})
        chat_history.append({"role": "assistant", "content": bot_message})
        return "", chat_history
    
    def clear_chat():
        return []
    
    msg.submit(respond, [msg, chatbot], [msg, chatbot])
    clear.click(clear_chat, None, chatbot, queue=False)

if __name__ == "__main__":
    demo.launch(share=True)