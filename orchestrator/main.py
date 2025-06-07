import asyncio
import os
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv

from langraph_workflow import run_workflow
from human_review import HumanReviewInterface

# Load environment
load_dotenv('../config/.env')

# Initialize FastAPI app
app = FastAPI(title="AI Reel Factory Orchestrator")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize human review interface
review_interface = HumanReviewInterface()

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "AI Reel Factory Orchestrator",
        "version": "0.1.0"
    }

@app.post("/workflow/start")
async def start_workflow(request: Dict[str, Any]):
    """Start a new reel generation workflow"""
    try:
        # Validate input
        input_type = request.get("input_type")
        if input_type not in ["youtube", "file", "prompt"]:
            raise HTTPException(status_code=400, detail="Invalid input_type")
        
        input_data = request.get("input_data")
        if not input_data:
            raise HTTPException(status_code=400, detail="Missing input_data")
        
        # Start workflow in background
        task = asyncio.create_task(run_workflow(input_type, input_data))
        
        # Return workflow ID immediately
        return {
            "status": "started",
            "message": "Workflow started successfully",
            "review_url": f"http://localhost:8000/"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/workflow/test")
async def test_workflow():
    """Test workflow with sample data"""
    try:
        # Run test workflow
        result = await run_workflow(
            input_type="prompt",
            input_data={
                "prompt": "5 AI productivity tips for developers",
                "style": "educational"
            }
        )
        
        return {
            "status": "completed",
            "workflow_id": result.workflow_id,
            "total_cost": result.total_cost_usd,
            "phases_completed": result.phases_completed
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def run_servers():
    """Run both the API server and review interface"""
    # Configure servers
    api_config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info"
    )
    
    # Create server instances
    api_server = uvicorn.Server(api_config)
    
    # Run both servers concurrently
    await asyncio.gather(
        api_server.serve(),
        review_interface.start_server(host="0.0.0.0", port=8000)
    )

if __name__ == "__main__":
    print("🚀 Starting AI Reel Factory Orchestrator...")
    print("📝 Human Review Interface: http://localhost:8000")
    print("🔧 API Endpoints: http://localhost:8001")
    print("📊 LangGraph Studio: https://smith.langchain.com/projects")
    
    asyncio.run(run_servers())