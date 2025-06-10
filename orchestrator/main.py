import asyncio
import os
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime
from dotenv import load_dotenv

# Import workflow
from langraph_workflow import run_workflow
from human_review import HumanReviewInterface

# Load environment
load_dotenv('../config/.env')

# Initialize FastAPI app
app = FastAPI(title="Rocket Reels AI Orchestrator", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (for human review interface)
if os.path.exists("templates/static"):
    app.mount("/static", StaticFiles(directory="templates/static"), name="static")

# Initialize human review interface
review_interface = HumanReviewInterface()

# Request models
class WorkflowRequest(BaseModel):
    input_type: str  # "youtube", "file", "prompt"
    input_data: Dict[str, Any]
    config: Optional[Dict[str, Any]] = {}

# Global workflow states storage (in production, use database)
workflow_states: Dict[str, Any] = {}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "orchestrator",
        "timestamp": datetime.now().isoformat(),
        "active_workflows": len(workflow_states)
    }

@app.get("/")
async def root():
    """Root endpoint - redirect to human review interface"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Rocket Reels AI</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; }
            .header { text-align: center; margin-bottom: 40px; }
            .status { background: #e8f5e8; padding: 20px; border-radius: 5px; margin: 20px 0; }
            .buttons { text-align: center; margin-top: 30px; }
            .btn { display: inline-block; padding: 12px 24px; margin: 10px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; }
            .btn:hover { background: #0056b3; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 Rocket Reels AI</h1>
                <p>AI-Powered Video Generation Pipeline</p>
            </div>
            
            <div class="status">
                <h3>✅ System Status</h3>
                <p>Orchestrator is running and ready to generate videos!</p>
                <p><strong>Active Workflows:</strong> 0</p>
                <p><strong>Services:</strong> 10 MCP servers available</p>
            </div>
            
            <div class="buttons">
                <a href="/docs" class="btn">📚 API Documentation</a>
                <a href="/workflow/status" class="btn">📊 Workflow Status</a>
                <a href="/start-workflow" class="btn">🎬 Start New Video</a>
            </div>
        </div>
    </body>
    </html>
    """)

@app.post("/workflow/start")
async def start_workflow(request: WorkflowRequest):
    """Start a new video generation workflow"""
    try:
        # Run the workflow
        result = await run_workflow(
            input_type=request.input_type,
            input_data=request.input_data
        )
        
        # Store the result
        workflow_states[result.workflow_id] = result
        
        return {
            "workflow_id": result.workflow_id,
            "status": result.status,
            "current_phase": result.current_phase,
            "total_cost": result.total_cost,
            "created_at": result.created_at.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow failed: {str(e)}")

@app.get("/workflow/{workflow_id}")
async def get_workflow_status(workflow_id: str):
    """Get workflow status"""
    if workflow_id not in workflow_states:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    state = workflow_states[workflow_id]
    return {
        "workflow_id": workflow_id,
        "status": state.status,
        "current_phase": state.current_phase,
        "phases_completed": len(state.phase_outputs),
        "total_cost": state.total_cost,
        "errors": state.errors,
        "created_at": state.created_at.isoformat()
    }

@app.get("/workflow/status")
async def list_workflows():
    """List all workflows"""
    return {
        "total_workflows": len(workflow_states),
        "workflows": [
            {
                "workflow_id": wid,
                "status": state.status,
                "current_phase": state.current_phase,
                "created_at": state.created_at.isoformat()
            }
            for wid, state in workflow_states.items()
        ]
    }

@app.get("/start-workflow")
async def start_workflow_form():
    """Simple form to start workflows"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Start New Video</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 600px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; }
            .form-group { margin: 20px 0; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input, select, textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
            textarea { height: 100px; }
            .btn { background: #007bff; color: white; padding: 12px 24px; border: none; border-radius: 4px; cursor: pointer; }
            .btn:hover { background: #0056b3; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎬 Start New Video Generation</h1>
            
            <form id="workflowForm">
                <div class="form-group">
                    <label for="inputType">Input Type:</label>
                    <select id="inputType" name="inputType">
                        <option value="prompt">Text Prompt</option>
                        <option value="youtube">YouTube URL</option>
                        <option value="file">File Upload</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="inputData">Input Data:</label>
                    <textarea id="inputData" name="inputData" placeholder="Enter your prompt, YouTube URL, or file path..."></textarea>
                </div>
                
                <button type="submit" class="btn">🚀 Generate Video</button>
            </form>
            
            <div id="result" style="margin-top: 20px;"></div>
            
            <script>
                document.getElementById('workflowForm').addEventListener('submit', async (e) => {
                    e.preventDefault();
                    
                    const inputType = document.getElementById('inputType').value;
                    const inputData = document.getElementById('inputData').value;
                    
                    const request = {
                        input_type: inputType,
                        input_data: inputType === 'prompt' ? {prompt: inputData} : 
                                   inputType === 'youtube' ? {url: inputData} : 
                                   {file_path: inputData}
                    };
                    
                    try {
                        const response = await fetch('/workflow/start', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify(request)
                        });
                        
                        const result = await response.json();
                        
                        if (response.ok) {
                            document.getElementById('result').innerHTML = `
                                <div style="background: #d4edda; padding: 15px; border-radius: 5px;">
                                    <h3>✅ Workflow Started!</h3>
                                    <p><strong>Workflow ID:</strong> ${result.workflow_id}</p>
                                    <p><strong>Status:</strong> ${result.status}</p>
                                    <p><strong>Current Phase:</strong> ${result.current_phase}</p>
                                    <a href="/workflow/${result.workflow_id}" style="color: #007bff;">View Status</a>
                                </div>
                            `;
                        } else {
                            throw new Error(result.detail);
                        }
                    } catch (error) {
                        document.getElementById('result').innerHTML = `
                            <div style="background: #f8d7da; padding: 15px; border-radius: 5px;">
                                <h3>❌ Error</h3>
                                <p>${error.message}</p>
                            </div>
                        `;
                    }
                });
            </script>
        </div>
    </body>
    </html>
    """)

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
    print("🚀 Starting Rocket Reels AI Orchestrator...")
    print("📝 Human Review Interface: http://localhost:8000")
    print("🔧 API Endpoints: http://localhost:8001")
    print("📊 LangGraph Studio: https://smith.langchain.com/projects")
    
    asyncio.run(run_servers())