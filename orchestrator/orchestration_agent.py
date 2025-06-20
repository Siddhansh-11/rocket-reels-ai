from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.chat_models import ChatLiteLLM
import os
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv

# Import agent tools
from search_agent import search_tools

# Load environment variables
load_dotenv('../.env')

# Get today's date for context
today = datetime.now().strftime("%Y-%m-%d")

model = ChatLiteLLM(
    model="deepseek/deepseek-chat",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    max_tokens=4000,
    temperature=0.1
)

# System prompt for the orchestration agent
SYSTEM_PROMPT = f"""
You are Rocket Reels AI Orchestration Assistant - a specialized agent that understands and manages the content creation workflow.

📅 **Today's date:** {today}

🎬 **YOUR ROLE:**
You are the intelligent orchestration layer that understands what's happening in our content creation workflow and can help with search functionality.

🔧 **AVAILABLE TOOLS:**

🔍 **SEARCH CAPABILITIES:**
- search_content_ideas: Search for trending content ideas and topics for video creation
- extract_trending_topics: Extract trending topics from search results

🎯 **WORKFLOW UNDERSTANDING:**
You understand our content creation workflow which includes these phases:
1. **Input Processing** - Processing YouTube URLs, files, or prompts
2. **Research** - Researching content using MCP research server  
3. **Planning** - Creating content plans with MCP planner server
4. **Script Writing** - Generating scripts with MCP script server
5. **Visual Generation** - Creating visuals with MCP visual server

Each phase has human review checkpoints where users can approve, request revisions, or reject outputs.

🎯 **YOUR CURRENT FOCUS:**
Right now, you're focused on providing **search functionality** to help users find trending content ideas that can feed into our orchestration workflow.

**SEARCH WORKFLOW:**
1. When users ask for content ideas or trending topics, use search_content_ideas
2. Present the search results in a clear, organized format
3. Help users understand how these search results can be used in our content creation pipeline
4. Extract trending topics when relevant using extract_trending_topics

⚠️ **IMPORTANT:**
- You are part of a larger orchestration system with MCP servers
- Your current scope is limited to search functionality
- Always relate search results back to how they can be used in content creation
- Be clear about what phase of the workflow the search results would be most useful for

🚀 **YOUR MISSION:**
Help users discover trending content ideas through search, and explain how these ideas can be integrated into our content creation workflow.

Ready to help you find the next viral content idea?
"""

# Combine all available tools (currently just search tools)
all_tools = search_tools

# Create the agent with search tools
agent = create_react_agent(
    model, 
    all_tools, 
    prompt=SYSTEM_PROMPT
)

async def run_orchestration_agent(message: str):
    """Run the orchestration agent with a user message"""
    try:
        # Create the message
        messages = [HumanMessage(content=message)]
        
        # Run the agent
        response = await agent.ainvoke({"messages": messages})
        
        # Extract the last AI message
        if response and "messages" in response:
            last_message = response["messages"][-1]
            if hasattr(last_message, 'content'):
                return last_message.content
            else:
                return str(last_message)
        else:
            return str(response)
            
    except Exception as e:
        return f"❌ Error running orchestration agent: {str(e)}"

# Example usage for testing
if __name__ == "__main__":
    async def test_agent():
        result = await run_orchestration_agent("Find trending AI content ideas")
        print(result)
    
    asyncio.run(test_agent())