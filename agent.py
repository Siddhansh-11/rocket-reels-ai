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

# Load environment variables
load_dotenv()

# Initialize the language model with Claude
llm = ChatAnthropic(
    model="claude-3-5-sonnet-20240620",
    max_tokens=2000,
    temperature=0,
    anthropic_api_key=os.getenv("CLAUDE_API_KEY")
)

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
    """
    Get the latest news headlines.
    Parameters:
    - query: Search term for specific news (optional)
    - category: News category like business, entertainment, health, science, sports, technology (optional)
    """
    api_key = os.getenv("NEWSAPI_API_KEY")
    if not api_key:
        return "News API key not found. Please set NEWSAPI_API_KEY in your .env file."
    
    # Construct the API request
    url = "https://newsapi.org/v2/top-headlines"
    params = {
        "apiKey": api_key,
        "language": "en",
        "pageSize": 5  # Limit to 5 articles for readability
    }
    
    # Add optional parameters if provided
    if query:
        params["q"] = query
    if category and category.lower() in ["business", "entertainment", "general", "health", "science", "sports", "technology"]:
        params["category"] = category.lower()
    elif not query:  # Default to general news if no query or category
        params["category"] = "general"
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            news_data = response.json()
            if news_data["totalResults"] == 0:
                # Try an alternative approach with everything endpoint for location-based searches
                return get_location_news(query)
            
            # Format the results
            result = f"Latest News {f'on {query}' if query else ''} {f'in {category}' if category else ''}:\n\n"
            for i, article in enumerate(news_data["articles"], 1):
                result += f"{i}. {article['title']}\n"
                result += f"   Source: {article['source']['name']}\n"
                result += f"   Published: {article['publishedAt']}\n"
                result += f"   Summary: {article['description'] if article['description'] else 'No description available'}\n"
                result += f"   URL: {article['url']}\n\n"
            
            return result
        else:
            return f"Error fetching news: {response.status_code}"
    except Exception as e:
        return f"Error processing news request: {str(e)}"

def get_location_news(location: str) -> str:
    """
    Get news for a specific location using the everything endpoint.
    This is better for location-based searches.
    """
    api_key = os.getenv("NEWSAPI_API_KEY")
    if not api_key:
        return "News API key not found. Please set NEWSAPI_API_KEY in your .env file."
    
    # Use the everything endpoint which is better for location searches
    url = "https://newsapi.org/v2/everything"
    params = {
        "apiKey": api_key,
        "q": location,  # Search for the location name
        "sortBy": "publishedAt",  # Sort by most recent
        "language": "en",
        "pageSize": 5
    }
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            news_data = response.json()
            
            if news_data["totalResults"] == 0:
                return f"No news found for location: {location}. Try a different search term or check back later."
            
            # Format the results
            result = f"Latest News related to {location}:\n\n"
            for i, article in enumerate(news_data["articles"], 1):
                result += f"{i}. {article['title']}\n"
                result += f"   Source: {article['source']['name']}\n"
                result += f"   Published: {article['publishedAt']}\n"
                result += f"   Summary: {article['description'] if article['description'] else 'No description available'}\n"
                result += f"   URL: {article['url']}\n\n"
            
            return result
        else:
            return f"Error fetching location news: {response.status_code}"
    except Exception as e:
        return f"Error processing location news request: {str(e)}"

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
        description="Get the latest news headlines. You can specify a search query and/or category (business, entertainment, health, science, sports, technology)."
    ),
    Tool(
        name="LocationNews",
        func=get_location_news,
        description="Get news for a specific location or city. Input should be the name of the location (e.g., 'Mumbai', 'New York')."
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

When asked about general news or news categories, use the LatestNews tool.
When asked about news in a specific location or city, use the LocationNews tool.

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