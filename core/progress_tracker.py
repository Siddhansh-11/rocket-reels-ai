"""
Real-time Progress Tracking for Rocket Reels AI Workflows

This module provides WebSocket-based real-time progress updates
and event streaming for workflow execution.
"""

import asyncio
import json
import logging
from typing import Dict, List, Set, Callable, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import weakref

class EventType(Enum):
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    WORKFLOW_CANCELLED = "workflow_cancelled"
    PHASE_STARTED = "phase_started"
    PHASE_COMPLETED = "phase_completed"
    PHASE_FAILED = "phase_failed"
    PROGRESS_UPDATE = "progress_update"
    COST_UPDATE = "cost_update"
    LOG_MESSAGE = "log_message"

@dataclass
class ProgressEvent:
    """Event for progress tracking"""
    event_type: EventType
    workflow_id: str
    timestamp: datetime
    data: Dict[str, Any]
    phase_name: Optional[str] = None
    progress_percentage: Optional[float] = None
    cost_delta: Optional[float] = None
    message: Optional[str] = None

class ProgressTracker:
    """Central progress tracking and event emission"""
    
    def __init__(self):
        self.subscribers: Dict[str, Set[Callable]] = {}  # workflow_id -> set of callbacks
        self.global_subscribers: Set[Callable] = set()   # callbacks for all workflows
        self.event_history: Dict[str, List[ProgressEvent]] = {}  # workflow_id -> events
        self.max_history_per_workflow = 100
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
    def subscribe_to_workflow(self, workflow_id: str, callback: Callable[[ProgressEvent], None]):
        """Subscribe to progress updates for a specific workflow"""
        if workflow_id not in self.subscribers:
            self.subscribers[workflow_id] = set()
        
        self.subscribers[workflow_id].add(callback)
        
        # Send recent events to new subscriber
        if workflow_id in self.event_history:
            for event in self.event_history[workflow_id][-10:]:  # Last 10 events
                try:
                    asyncio.create_task(self._safe_callback(callback, event))
                except Exception as e:
                    self.logger.error(f"Error sending history to subscriber: {e}")
    
    def subscribe_globally(self, callback: Callable[[ProgressEvent], None]):
        """Subscribe to progress updates for all workflows"""
        self.global_subscribers.add(callback)
    
    def unsubscribe_from_workflow(self, workflow_id: str, callback: Callable):
        """Unsubscribe from workflow updates"""
        if workflow_id in self.subscribers:
            self.subscribers[workflow_id].discard(callback)
            if not self.subscribers[workflow_id]:
                del self.subscribers[workflow_id]
    
    def unsubscribe_globally(self, callback: Callable):
        """Unsubscribe from global updates"""
        self.global_subscribers.discard(callback)
    
    async def emit_event(self, event: ProgressEvent):
        """Emit a progress event to all relevant subscribers"""
        # Store in history
        if event.workflow_id not in self.event_history:
            self.event_history[event.workflow_id] = []
        
        self.event_history[event.workflow_id].append(event)
        
        # Trim history if too long
        if len(self.event_history[event.workflow_id]) > self.max_history_per_workflow:
            self.event_history[event.workflow_id] = self.event_history[event.workflow_id][-self.max_history_per_workflow:]
        
        # Notify workflow-specific subscribers
        workflow_callbacks = self.subscribers.get(event.workflow_id, set())
        for callback in list(workflow_callbacks):  # Use list() to avoid modification during iteration
            await self._safe_callback(callback, event)
        
        # Notify global subscribers
        for callback in list(self.global_subscribers):
            await self._safe_callback(callback, event)
        
        # Log the event
        self.logger.info(f"Event: {event.event_type.value} for workflow {event.workflow_id}")
    
    async def _safe_callback(self, callback: Callable, event: ProgressEvent):
        """Safely execute a callback, handling errors"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(event)
            else:
                callback(event)
        except Exception as e:
            self.logger.error(f"Error in progress callback: {e}")
    
    def get_workflow_history(self, workflow_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get event history for a workflow"""
        if workflow_id not in self.event_history:
            return []
        
        events = self.event_history[workflow_id][-limit:]
        return [self._event_to_dict(event) for event in events]
    
    def get_all_active_workflows(self) -> List[str]:
        """Get list of workflow IDs that have subscribers"""
        return list(self.subscribers.keys())
    
    def _event_to_dict(self, event: ProgressEvent) -> Dict[str, Any]:
        """Convert event to dictionary for JSON serialization"""
        return {
            "event_type": event.event_type.value,
            "workflow_id": event.workflow_id,
            "timestamp": event.timestamp.isoformat(),
            "data": event.data,
            "phase_name": event.phase_name,
            "progress_percentage": event.progress_percentage,
            "cost_delta": event.cost_delta,
            "message": event.message
        }

# Global progress tracker instance
progress_tracker = ProgressTracker()

# Convenience functions for emitting common events
async def workflow_started(workflow_id: str, config: Dict[str, Any]):
    """Emit workflow started event"""
    event = ProgressEvent(
        event_type=EventType.WORKFLOW_STARTED,
        workflow_id=workflow_id,
        timestamp=datetime.now(),
        data=config,
        message=f"Started workflow: {config.get('topic', 'Unknown topic')}"
    )
    await progress_tracker.emit_event(event)

async def workflow_completed(workflow_id: str, result: Dict[str, Any]):
    """Emit workflow completed event"""
    event = ProgressEvent(
        event_type=EventType.WORKFLOW_COMPLETED,
        workflow_id=workflow_id,
        timestamp=datetime.now(),
        data=result,
        progress_percentage=100.0,
        message="Workflow completed successfully"
    )
    await progress_tracker.emit_event(event)

async def workflow_failed(workflow_id: str, error: str, data: Dict[str, Any] = None):
    """Emit workflow failed event"""
    event = ProgressEvent(
        event_type=EventType.WORKFLOW_FAILED,
        workflow_id=workflow_id,
        timestamp=datetime.now(),
        data=data or {},
        message=f"Workflow failed: {error}"
    )
    await progress_tracker.emit_event(event)

async def workflow_cancelled(workflow_id: str):
    """Emit workflow cancelled event"""
    event = ProgressEvent(
        event_type=EventType.WORKFLOW_CANCELLED,
        workflow_id=workflow_id,
        timestamp=datetime.now(),
        data={},
        message="Workflow cancelled by user"
    )
    await progress_tracker.emit_event(event)

async def phase_started(workflow_id: str, phase_name: str, current_phase: int, total_phases: int):
    """Emit phase started event"""
    progress = (current_phase / total_phases) * 100 if total_phases > 0 else 0
    
    event = ProgressEvent(
        event_type=EventType.PHASE_STARTED,
        workflow_id=workflow_id,
        timestamp=datetime.now(),
        data={"current_phase": current_phase, "total_phases": total_phases},
        phase_name=phase_name,
        progress_percentage=progress,
        message=f"Started phase: {phase_name}"
    )
    await progress_tracker.emit_event(event)

async def phase_completed(workflow_id: str, phase_name: str, current_phase: int, total_phases: int, cost: float = 0.0, result: Dict[str, Any] = None):
    """Emit phase completed event"""
    progress = ((current_phase + 1) / total_phases) * 100 if total_phases > 0 else 0
    
    event = ProgressEvent(
        event_type=EventType.PHASE_COMPLETED,
        workflow_id=workflow_id,
        timestamp=datetime.now(),
        data=result or {},
        phase_name=phase_name,
        progress_percentage=progress,
        cost_delta=cost,
        message=f"Completed phase: {phase_name}"
    )
    await progress_tracker.emit_event(event)

async def phase_failed(workflow_id: str, phase_name: str, error: str):
    """Emit phase failed event"""
    event = ProgressEvent(
        event_type=EventType.PHASE_FAILED,
        workflow_id=workflow_id,
        timestamp=datetime.now(),
        data={"error": error},
        phase_name=phase_name,
        message=f"Phase {phase_name} failed: {error}"
    )
    await progress_tracker.emit_event(event)

async def cost_update(workflow_id: str, cost_delta: float, total_cost: float):
    """Emit cost update event"""
    event = ProgressEvent(
        event_type=EventType.COST_UPDATE,
        workflow_id=workflow_id,
        timestamp=datetime.now(),
        data={"total_cost": total_cost},
        cost_delta=cost_delta,
        message=f"Cost update: +${cost_delta:.3f} (total: ${total_cost:.3f})"
    )
    await progress_tracker.emit_event(event)

async def log_message(workflow_id: str, level: str, message: str, data: Dict[str, Any] = None):
    """Emit log message event"""
    event = ProgressEvent(
        event_type=EventType.LOG_MESSAGE,
        workflow_id=workflow_id,
        timestamp=datetime.now(),
        data={"level": level, **(data or {})},
        message=message
    )
    await progress_tracker.emit_event(event)

class WebSocketProgressHandler:
    """WebSocket handler for streaming progress updates"""
    
    def __init__(self):
        self.connections: Dict[str, Set] = {}  # workflow_id -> websocket connections
        self.global_connections: Set = set()   # connections for all workflows
    
    async def handle_connection(self, websocket, path: str):
        """Handle new WebSocket connection"""
        try:
            # Parse path to determine subscription type
            if path.startswith('/workflow/'):
                workflow_id = path.split('/')[-1]
                await self._handle_workflow_connection(websocket, workflow_id)
            elif path == '/all':
                await self._handle_global_connection(websocket)
            else:
                await websocket.close(code=4000, reason="Invalid path")
                return
        except Exception as e:
            logging.error(f"WebSocket connection error: {e}")
            try:
                await websocket.close()
            except:
                pass
    
    async def _handle_workflow_connection(self, websocket, workflow_id: str):
        """Handle connection for specific workflow"""
        if workflow_id not in self.connections:
            self.connections[workflow_id] = set()
        
        self.connections[workflow_id].add(websocket)
        
        # Create callback for this connection
        async def websocket_callback(event: ProgressEvent):
            if event.workflow_id == workflow_id:
                try:
                    await websocket.send(json.dumps(progress_tracker._event_to_dict(event)))
                except Exception as e:
                    logging.error(f"Error sending to websocket: {e}")
                    self.connections[workflow_id].discard(websocket)
        
        # Subscribe to progress updates
        progress_tracker.subscribe_to_workflow(workflow_id, websocket_callback)
        
        try:
            # Send initial history
            history = progress_tracker.get_workflow_history(workflow_id, 10)
            for event_data in history:
                await websocket.send(json.dumps(event_data))
            
            # Keep connection alive
            async for message in websocket:
                # Handle any client messages if needed
                pass
        except Exception as e:
            logging.error(f"WebSocket error: {e}")
        finally:
            # Cleanup
            self.connections[workflow_id].discard(websocket)
            progress_tracker.unsubscribe_from_workflow(workflow_id, websocket_callback)
    
    async def _handle_global_connection(self, websocket):
        """Handle connection for all workflows"""
        self.global_connections.add(websocket)
        
        # Create callback for this connection
        async def websocket_callback(event: ProgressEvent):
            try:
                await websocket.send(json.dumps(progress_tracker._event_to_dict(event)))
            except Exception as e:
                logging.error(f"Error sending to global websocket: {e}")
                self.global_connections.discard(websocket)
        
        # Subscribe to all progress updates
        progress_tracker.subscribe_globally(websocket_callback)
        
        try:
            # Keep connection alive
            async for message in websocket:
                # Handle any client messages if needed
                pass
        except Exception as e:
            logging.error(f"Global WebSocket error: {e}")
        finally:
            # Cleanup
            self.global_connections.discard(websocket)
            progress_tracker.unsubscribe_globally(websocket_callback)

# Global WebSocket handler
websocket_handler = WebSocketProgressHandler()

# Example usage for testing
async def example_progress_simulation():
    """Example function showing how to emit progress events"""
    workflow_id = "test-workflow-123"
    
    # Start workflow
    await workflow_started(workflow_id, {"topic": "AI trends", "type": "full_pipeline"})
    
    phases = ["search", "crawl", "script_generation", "image_generation", "finalize"]
    
    for i, phase in enumerate(phases):
        await phase_started(workflow_id, phase, i, len(phases))
        await asyncio.sleep(1)  # Simulate work
        await phase_completed(workflow_id, phase, i, len(phases), cost=0.05)
    
    await workflow_completed(workflow_id, {"status": "success", "cost": 0.25})

if __name__ == "__main__":
    # Test the progress tracking
    async def test_subscriber(event: ProgressEvent):
        print(f"Event: {event.event_type.value} - {event.message}")
    
    progress_tracker.subscribe_globally(test_subscriber)
    
    asyncio.run(example_progress_simulation())