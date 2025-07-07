"""
WebSocket Server for Real-time Workflow Progress Updates

This module provides a WebSocket server that streams real-time progress
updates for Rocket Reels AI workflows.
"""

import asyncio
import json
import logging
import websockets
from websockets.server import WebSocketServerProtocol
from typing import Set, Dict
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from core.progress_tracker import progress_tracker, ProgressEvent

class WebSocketProgressServer:
    """WebSocket server for streaming workflow progress"""
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.connections: Set[WebSocketServerProtocol] = set()
        self.workflow_connections: Dict[str, Set[WebSocketServerProtocol]] = {}
        self.server = None
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Subscribe to all progress events
        progress_tracker.subscribe_globally(self._broadcast_event)
    
    async def start_server(self):
        """Start the WebSocket server"""
        self.logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        
        self.server = await websockets.serve(
            self.handle_connection,
            self.host,
            self.port,
            ping_interval=30,
            ping_timeout=10
        )
        
        self.logger.info(f"WebSocket server started on ws://{self.host}:{self.port}")
        
        # Keep server running
        await self.server.wait_closed()
    
    async def stop_server(self):
        """Stop the WebSocket server"""
        if self.server:
            self.logger.info("Stopping WebSocket server")
            self.server.close()
            await self.server.wait_closed()
            self.logger.info("WebSocket server stopped")
    
    async def handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Handle new WebSocket connection"""
        self.logger.info(f"New WebSocket connection: {path}")
        
        try:
            # Parse the path to determine subscription type
            if path == "/all":
                # Subscribe to all workflows
                await self._handle_global_connection(websocket)
            elif path.startswith("/workflow/"):
                # Subscribe to specific workflow
                workflow_id = path.split("/")[-1]
                await self._handle_workflow_connection(websocket, workflow_id)
            else:
                # Invalid path
                await websocket.close(code=4000, reason="Invalid path")
                return
        
        except websockets.exceptions.ConnectionClosed:
            self.logger.info("WebSocket connection closed")
        except Exception as e:
            self.logger.error(f"WebSocket connection error: {e}")
        finally:
            # Clean up connection
            self.connections.discard(websocket)
            for workflow_connections in self.workflow_connections.values():
                workflow_connections.discard(websocket)
    
    async def _handle_global_connection(self, websocket: WebSocketServerProtocol):
        """Handle connection that wants all workflow updates"""
        self.connections.add(websocket)
        
        # Send welcome message
        welcome = {
            "type": "connection",
            "message": "Connected to Rocket Reels AI progress stream",
            "scope": "all_workflows"
        }
        await websocket.send(json.dumps(welcome))
        
        # Send recent events from all workflows
        active_workflows = progress_tracker.get_all_active_workflows()
        for workflow_id in active_workflows:
            history = progress_tracker.get_workflow_history(workflow_id, 5)
            for event_data in history:
                await websocket.send(json.dumps(event_data))
        
        # Keep connection alive
        async for message in websocket:
            # Handle client messages
            try:
                data = json.loads(message)
                await self._handle_client_message(websocket, data)
            except json.JSONDecodeError:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON message"
                }))
    
    async def _handle_workflow_connection(self, websocket: WebSocketServerProtocol, workflow_id: str):
        """Handle connection for specific workflow"""
        if workflow_id not in self.workflow_connections:
            self.workflow_connections[workflow_id] = set()
        
        self.workflow_connections[workflow_id].add(websocket)
        
        # Send welcome message
        welcome = {
            "type": "connection",
            "message": f"Connected to workflow {workflow_id}",
            "scope": "single_workflow",
            "workflow_id": workflow_id
        }
        await websocket.send(json.dumps(welcome))
        
        # Send recent events for this workflow
        history = progress_tracker.get_workflow_history(workflow_id, 10)
        for event_data in history:
            await websocket.send(json.dumps(event_data))
        
        # Keep connection alive
        async for message in websocket:
            # Handle client messages
            try:
                data = json.loads(message)
                await self._handle_client_message(websocket, data, workflow_id)
            except json.JSONDecodeError:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON message"
                }))
    
    async def _handle_client_message(self, websocket: WebSocketServerProtocol, data: dict, workflow_id: str = None):
        """Handle messages from client"""
        message_type = data.get("type")
        
        if message_type == "ping":
            # Respond to ping
            await websocket.send(json.dumps({"type": "pong"}))
        
        elif message_type == "get_status":
            # Send current status
            if workflow_id:
                from core.workflow_interface import workflow_manager
                status = workflow_manager.get_workflow_status(workflow_id)
                await websocket.send(json.dumps({
                    "type": "status",
                    "workflow_id": workflow_id,
                    "data": status
                }))
            else:
                from core.workflow_interface import workflow_manager
                workflows = workflow_manager.list_workflows()
                await websocket.send(json.dumps({
                    "type": "status",
                    "data": workflows
                }))
        
        elif message_type == "get_history":
            # Send history
            limit = data.get("limit", 20)
            if workflow_id:
                history = progress_tracker.get_workflow_history(workflow_id, limit)
            else:
                # Get history for all workflows
                active_workflows = progress_tracker.get_all_active_workflows()
                history = []
                for wf_id in active_workflows:
                    history.extend(progress_tracker.get_workflow_history(wf_id, 5))
                history = sorted(history, key=lambda x: x["timestamp"])[-limit:]
            
            await websocket.send(json.dumps({
                "type": "history",
                "data": history
            }))
    
    async def _broadcast_event(self, event: ProgressEvent):
        """Broadcast event to relevant connections"""
        event_data = progress_tracker._event_to_dict(event)
        message = json.dumps(event_data)
        
        # Send to global connections
        for websocket in list(self.connections):
            try:
                await websocket.send(message)
            except websockets.exceptions.ConnectionClosed:
                self.connections.discard(websocket)
            except Exception as e:
                self.logger.error(f"Error broadcasting to global connection: {e}")
                self.connections.discard(websocket)
        
        # Send to workflow-specific connections
        workflow_connections = self.workflow_connections.get(event.workflow_id, set())
        for websocket in list(workflow_connections):
            try:
                await websocket.send(message)
            except websockets.exceptions.ConnectionClosed:
                workflow_connections.discard(websocket)
            except Exception as e:
                self.logger.error(f"Error broadcasting to workflow connection: {e}")
                workflow_connections.discard(websocket)
    
    def get_connection_stats(self) -> dict:
        """Get statistics about current connections"""
        workflow_stats = {}
        for workflow_id, connections in self.workflow_connections.items():
            workflow_stats[workflow_id] = len(connections)
        
        return {
            "total_connections": len(self.connections),
            "global_connections": len(self.connections),
            "workflow_connections": workflow_stats,
            "active_workflows": len(self.workflow_connections)
        }

async def run_websocket_server(host: str = "localhost", port: int = 8765):
    """Run the WebSocket server"""
    server = WebSocketProgressServer(host, port)
    
    try:
        await server.start_server()
    except KeyboardInterrupt:
        print("Shutting down WebSocket server...")
    except Exception as e:
        print(f"WebSocket server error: {e}")
    finally:
        await server.stop_server()

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the server
    asyncio.run(run_websocket_server())