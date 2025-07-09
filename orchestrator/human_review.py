import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn

from workflow_state import ContentState, HumanReview, ReviewStatus

class HumanReviewInterface:
    """Interface for human review of workflow phases"""
    
    def __init__(self):
        self.pending_reviews: Dict[str, ContentState] = {}
        self.review_decisions: Dict[str, HumanReview] = {}
        self.app = self._create_app()
        
    def _create_app(self) -> FastAPI:
        """Create FastAPI app for review interface"""
        app = FastAPI(title="Rocket Reels AI - Human Review")
        
        @app.get("/")
        async def get_review_interface():
            """Serve the review interface"""
            return HTMLResponse(content=self._get_html_interface())
        
        @app.websocket("/ws/{workflow_id}")
        async def websocket_endpoint(websocket: WebSocket, workflow_id: str):
            await websocket.accept()
            
            try:
                # Send current state to reviewer
                if workflow_id in self.pending_reviews:
                    state = self.pending_reviews[workflow_id]
                    await websocket.send_json({
                        "type": "state_update",
                        "data": self._prepare_review_data(state)
                    })
                
                # Wait for review decision
                while True:
                    data = await websocket.receive_json()
                    
                    if data["type"] == "review_decision":
                        review = HumanReview(
                            status=ReviewStatus(data["status"]),
                            feedback=data.get("feedback"),
                            modifications=data.get("modifications"),
                            reviewer_id=data.get("reviewer_id", "anonymous")
                        )
                        
                        self.review_decisions[workflow_id] = review
                        await websocket.send_json({
                            "type": "decision_received",
                            "status": "success"
                        })
                        break
                        
            except WebSocketDisconnect:
                pass
            finally:
                await websocket.close()
        
        return app
    
    async def get_review(self, state: ContentState) -> HumanReview:
        """Get human review for current workflow state"""
        # Store state for review
        self.pending_reviews[state.workflow_id] = state
        
        # In production, would notify reviewers via multiple channels
        print(f"\n🔔 Human review needed for: {state.current_phase}")
        print(f"Workflow ID: {state.workflow_id}")
        print(f"Review URL: http://localhost:8000/?workflow_id={state.workflow_id}")
        
        # Wait for review decision (with timeout)
        timeout = 300  # 5 minutes
        start_time = asyncio.get_event_loop().time()
        
        while state.workflow_id not in self.review_decisions:
            if asyncio.get_event_loop().time() - start_time > timeout:
                # Auto-approve after timeout (configurable behavior)
                return HumanReview(
                    status=ReviewStatus.APPROVED,
                    feedback="Auto-approved due to timeout",
                    reviewer_id="system"
                )
            
            await asyncio.sleep(1)
        
        # Get and remove the decision
        review = self.review_decisions.pop(state.workflow_id)
        self.pending_reviews.pop(state.workflow_id, None)
        
        return review
    
    def _prepare_review_data(self, state: ContentState) -> Dict[str, Any]:
        """Prepare state data for review interface"""
        latest_output = state.get_latest_output()
        
        return {
            "workflow_id": state.workflow_id,
            "current_phase": state.current_phase,
            "phases_completed": state.phases_completed,
            "latest_output": latest_output.model_dump() if latest_output else None,
            "total_cost": state.total_cost_usd,
            "input_type": state.input_type,
            "preview": self._generate_preview(state)
        }
    
    def _generate_preview(self, state: ContentState) -> Dict[str, Any]:
        """Generate preview content for current phase"""
        preview = {
            "phase": state.current_phase,
            "content": {}
        }
        
        if state.current_phase == "script_writing" and state.script_writing:
            preview["content"] = {
                "script_preview": state.script_writing.data.get("script", "")[:200] + "...",
                "duration": state.script_writing.data.get("estimated_duration"),
                "quality_score": state.script_writing.data.get("quality_score")
            }
        elif state.current_phase == "research" and state.research:
            preview["content"] = {
                "facts": state.research.data.get("research", {}).get("facts", [])[:3],
                "suggested_angle": state.research.data.get("research", {}).get("suggested_angle")
            }
        elif state.current_phase == "planning" and state.planning:
            preview["content"] = {
                "hook": state.planning.data.get("content_plan", {}).get("hook"),
                "main_points": state.planning.data.get("content_plan", {}).get("main_points", [])
            }
        
        return preview
    
    def _get_html_interface(self) -> str:
        """Get HTML for review interface"""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>Rocket Reels AI - Review Interface</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 { color: #333; }
        .phase-info {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            margin: 20px 0;
        }
        .preview {
            background: #fff;
            border: 1px solid #ddd;
            padding: 20px;
            border-radius: 4px;
            margin: 20px 0;
            max-height: 400px;
            overflow-y: auto;
        }
        .actions {
            display: flex;
            gap: 10px;
            margin-top: 30px;
        }
        button {
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .approve { background: #28a745; color: white; }
        .approve:hover { background: #218838; }
        .revise { background: #ffc107; color: #333; }
        .revise:hover { background: #e0a800; }
        .reject { background: #dc3545; color: white; }
        .reject:hover { background: #c82333; }
        textarea {
            width: 100%;
            min-height: 100px;
            margin: 10px 0;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-family: inherit;
        }
        .cost {
            float: right;
            font-size: 18px;
            color: #666;
        }
        pre {
            background: #f4f4f4;
            padding: 10px;
            border-radius: 4px;
            overflow-x: auto;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Rocket Reels AI - Human Review <span class="cost">Cost: $<span id="cost">0.00</span></span></h1>
        
        <div class="phase-info">
            <h2>Current Phase: <span id="phase">Loading...</span></h2>
            <p>Workflow ID: <span id="workflow-id">Loading...</span></p>
            <p>Completed Phases: <span id="completed">Loading...</span></p>
        </div>
        
        <div class="preview">
            <h3>Preview</h3>
            <div id="preview-content">Loading preview...</div>
        </div>
        
        <div>
            <h3>Feedback</h3>
            <textarea id="feedback" placeholder="Enter your feedback here..."></textarea>
        </div>
        
        <div class="actions">
            <button class="approve" onclick="submitReview('approved')">✅ Approve</button>
            <button class="revise" onclick="submitReview('revision_requested')">🔄 Request Revision</button>
            <button class="reject" onclick="submitReview('rejected')">❌ Reject</button>
        </div>
    </div>
    
    <script>
        const params = new URLSearchParams(window.location.search);
        const workflowId = params.get('workflow_id') || 'test';
        let ws;
        
        function connect() {
            ws = new WebSocket(`ws://localhost:8000/ws/${workflowId}`);
            
            ws.onopen = () => {
                console.log('Connected to review server');
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                
                if (data.type === 'state_update') {
                    updateUI(data.data);
                } else if (data.type === 'decision_received') {
                    alert('Review submitted successfully!');
                    window.close();
                }
            };
            
            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
            
            ws.onclose = () => {
                console.log('Disconnected from review server');
                setTimeout(connect, 3000);
            };
        }
        
        function updateUI(data) {
            document.getElementById('workflow-id').textContent = data.workflow_id;
            document.getElementById('phase').textContent = data.current_phase;
            document.getElementById('completed').textContent = data.phases_completed.join(' → ');
            document.getElementById('cost').textContent = data.total_cost.toFixed(2);
            
            const previewContent = document.getElementById('preview-content');
            previewContent.innerHTML = '<pre>' + JSON.stringify(data.preview, null, 2) + '</pre>';
        }
        
        function submitReview(status) {
            const feedback = document.getElementById('feedback').value;
            
            const decision = {
                type: 'review_decision',
                status: status,
                feedback: feedback || null,
                reviewer_id: 'human_reviewer'
            };
            
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify(decision));
            } else {
                alert('Not connected to server. Please refresh and try again.');
            }
        }
        
        // Connect on load
        connect();
    </script>
</body>
</html>
        """
    
    async def start_server(self, host: str = "0.0.0.0", port: int = 8000):
        """Start the review interface server"""
        config = uvicorn.Config(self.app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()