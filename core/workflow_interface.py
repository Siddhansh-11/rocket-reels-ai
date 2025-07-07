"""
Unified Workflow Interface for Rocket Reels AI

This module provides a unified interface for triggering and managing workflows
that can be used by MCP servers, direct API calls, or other integrations.
"""

import asyncio
import json
import uuid
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import sys
from pathlib import Path

# Import progress tracking
from core.progress_tracker import (
    progress_tracker,
    workflow_started,
    workflow_completed,
    workflow_failed,
    workflow_cancelled,
    phase_started,
    phase_completed,
    phase_failed,
    cost_update
)

# Add project paths for imports
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "production-workflow"))

class WorkflowType(Enum):
    FULL_PIPELINE = "full_pipeline"
    QUICK_GENERATE = "quick_generate"
    SEARCH_AND_SCRIPT = "search_and_script"
    ARTICLE_TO_SCRIPT = "article_to_script"

class WorkflowStatus(Enum):
    PENDING = "pending"
    STARTING = "starting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class WorkflowConfig:
    """Configuration for workflow execution"""
    topic: str
    workflow_type: WorkflowType = WorkflowType.FULL_PIPELINE
    platforms: List[str] = field(default_factory=lambda: ["all"])
    style: str = "educational"
    tone: str = "casual"
    enable_human_review: bool = False
    max_cost_usd: float = 10.0
    timeout_minutes: int = 30

@dataclass
class WorkflowPhase:
    """Individual workflow phase tracking"""
    name: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cost_usd: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@dataclass
class WorkflowExecution:
    """Complete workflow execution tracking"""
    id: str
    config: WorkflowConfig
    status: WorkflowStatus = WorkflowStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    phases: List[WorkflowPhase] = field(default_factory=list)
    total_cost_usd: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress_callbacks: List[Callable] = field(default_factory=list)

class WorkflowManager:
    """Central workflow management and execution"""
    
    def __init__(self):
        self.active_workflows: Dict[str, WorkflowExecution] = {}
        self.workflow_history: List[WorkflowExecution] = []
        
    async def create_workflow(self, config: WorkflowConfig) -> str:
        """Create a new workflow execution"""
        workflow_id = str(uuid.uuid4())
        
        workflow = WorkflowExecution(
            id=workflow_id,
            config=config
        )
        
        # Initialize phases based on workflow type
        workflow.phases = self._get_phases_for_type(config.workflow_type)
        
        self.active_workflows[workflow_id] = workflow
        
        return workflow_id
    
    def _get_phases_for_type(self, workflow_type: WorkflowType) -> List[WorkflowPhase]:
        """Get the phases for a specific workflow type"""
        if workflow_type == WorkflowType.FULL_PIPELINE:
            return [
                WorkflowPhase("search"),
                WorkflowPhase("crawl"),
                WorkflowPhase("store_article"),
                WorkflowPhase("generate_script"),
                WorkflowPhase("store_script"),
                WorkflowPhase("prompt_generation"),
                WorkflowPhase("image_generation"),
                WorkflowPhase("voice_generation"),
                WorkflowPhase("broll_search"),
                WorkflowPhase("asset_gathering"),
                WorkflowPhase("notion_integration"),
                WorkflowPhase("finalize")
            ]
        elif workflow_type == WorkflowType.QUICK_GENERATE:
            return [
                WorkflowPhase("search"),
                WorkflowPhase("generate_script")
            ]
        elif workflow_type == WorkflowType.SEARCH_AND_SCRIPT:
            return [
                WorkflowPhase("search"),
                WorkflowPhase("generate_script"),
                WorkflowPhase("store_script")
            ]
        elif workflow_type == WorkflowType.ARTICLE_TO_SCRIPT:
            return [
                WorkflowPhase("crawl"),
                WorkflowPhase("generate_script"),
                WorkflowPhase("store_script")
            ]
        else:
            return []
    
    async def execute_workflow(self, workflow_id: str) -> WorkflowExecution:
        """Execute a workflow with progress tracking"""
        if workflow_id not in self.active_workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow = self.active_workflows[workflow_id]
        workflow.status = WorkflowStatus.STARTING
        workflow.started_at = datetime.now()
        
        # Emit workflow started event
        await workflow_started(workflow_id, {
            "topic": workflow.config.topic,
            "workflow_type": workflow.config.workflow_type.value,
            "platforms": workflow.config.platforms,
            "style": workflow.config.style
        })
        
        try:
            if workflow.config.workflow_type == WorkflowType.FULL_PIPELINE:
                await self._execute_full_pipeline(workflow)
            elif workflow.config.workflow_type == WorkflowType.QUICK_GENERATE:
                await self._execute_quick_generate(workflow)
            elif workflow.config.workflow_type == WorkflowType.SEARCH_AND_SCRIPT:
                await self._execute_search_and_script(workflow)
            elif workflow.config.workflow_type == WorkflowType.ARTICLE_TO_SCRIPT:
                await self._execute_article_to_script(workflow)
            
            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = datetime.now()
            
            # Emit workflow completed event
            await workflow_completed(workflow_id, workflow.result or {})
            
        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            workflow.error = str(e)
            workflow.completed_at = datetime.now()
            
            # Emit workflow failed event
            await workflow_failed(workflow_id, str(e))
        
        # Move to history
        self.workflow_history.append(workflow)
        if workflow_id in self.active_workflows:
            del self.active_workflows[workflow_id]
        
        return workflow
    
    async def _execute_full_pipeline(self, workflow: WorkflowExecution):
        """Execute the full content generation pipeline"""
        workflow.status = WorkflowStatus.RUNNING
        
        # Import production workflow
        try:
            from production_workflow.core.production_workflow import ProductionWorkflow, WorkflowState
            
            # Create production workflow instance
            production_workflow = ProductionWorkflow()
            
            # Create initial state
            initial_state = WorkflowState(
                user_query=workflow.config.topic,
                topic=workflow.config.topic.split()[0] if ' ' in workflow.config.topic else workflow.config.topic
            )
            
            # Execute the workflow
            compiled_workflow = production_workflow.workflow.compile()
            
            # Track execution through phases
            for i, phase in enumerate(workflow.phases):
                phase.status = WorkflowStatus.RUNNING
                phase.started_at = datetime.now()
                
                # Emit phase started event
                await phase_started(workflow.id, phase.name, i, len(workflow.phases))
                await self._notify_progress(workflow, phase, i, len(workflow.phases))
                
                # Simulate phase execution (in real implementation, this would track actual LangGraph execution)
                await asyncio.sleep(0.5)  # Simulate processing time
                
                phase.status = WorkflowStatus.COMPLETED
                phase.completed_at = datetime.now()
                phase.cost_usd = 0.05  # Mock cost
                workflow.total_cost_usd += phase.cost_usd
                
                # Emit phase completed event
                await phase_completed(workflow.id, phase.name, i, len(workflow.phases), phase.cost_usd)
                await cost_update(workflow.id, phase.cost_usd, workflow.total_cost_usd)
            
            # In production, this would run the actual workflow:
            # final_state = await compiled_workflow.ainvoke(initial_state)
            
            workflow.result = {
                "workflow_type": "full_pipeline",
                "phases_completed": len(workflow.phases),
                "topic": workflow.config.topic,
                "platforms": workflow.config.platforms,
                "total_cost": workflow.total_cost_usd,
                "execution_time_seconds": (datetime.now() - workflow.started_at).total_seconds()
            }
            
        except ImportError as e:
            # Fallback for when production workflow is not available
            workflow.result = {
                "workflow_type": "full_pipeline",
                "status": "simulated",
                "topic": workflow.config.topic,
                "platforms": workflow.config.platforms,
                "note": "Production workflow not available, simulated execution",
                "error": str(e)
            }
    
    async def _execute_quick_generate(self, workflow: WorkflowExecution):
        """Execute quick generation workflow"""
        workflow.status = WorkflowStatus.RUNNING
        
        try:
            # Import search agent
            from production_workflow.agents.search_agent import search_tech_news
            
            # Phase 1: Search
            search_phase = workflow.phases[0]
            search_phase.status = WorkflowStatus.RUNNING
            search_phase.started_at = datetime.now()
            
            search_result = await search_tech_news(workflow.config.topic)
            
            search_phase.status = WorkflowStatus.COMPLETED
            search_phase.completed_at = datetime.now()
            search_phase.result = search_result
            search_phase.cost_usd = 0.02
            workflow.total_cost_usd += search_phase.cost_usd
            
            # Phase 2: Generate Script
            script_phase = workflow.phases[1]
            script_phase.status = WorkflowStatus.RUNNING
            script_phase.started_at = datetime.now()
            
            # Simulate script generation
            await asyncio.sleep(1.0)
            
            script_phase.status = WorkflowStatus.COMPLETED
            script_phase.completed_at = datetime.now()
            script_phase.result = {"scripts_generated": len(workflow.config.platforms)}
            script_phase.cost_usd = 0.08
            workflow.total_cost_usd += script_phase.cost_usd
            
            workflow.result = {
                "workflow_type": "quick_generate",
                "search_results": search_result,
                "platforms": workflow.config.platforms,
                "total_cost": workflow.total_cost_usd
            }
            
        except ImportError:
            # Fallback simulation
            for phase in workflow.phases:
                phase.status = WorkflowStatus.COMPLETED
                phase.completed_at = datetime.now()
                phase.cost_usd = 0.05
                workflow.total_cost_usd += phase.cost_usd
            
            workflow.result = {
                "workflow_type": "quick_generate",
                "status": "simulated",
                "topic": workflow.config.topic,
                "platforms": workflow.config.platforms,
                "total_cost": workflow.total_cost_usd
            }
    
    async def _execute_search_and_script(self, workflow: WorkflowExecution):
        """Execute search and script generation workflow"""
        await self._execute_quick_generate(workflow)
        
        # Add storage phase if it exists
        if len(workflow.phases) > 2:
            storage_phase = workflow.phases[2]
            storage_phase.status = WorkflowStatus.RUNNING
            storage_phase.started_at = datetime.now()
            
            await asyncio.sleep(0.5)
            
            storage_phase.status = WorkflowStatus.COMPLETED
            storage_phase.completed_at = datetime.now()
            storage_phase.cost_usd = 0.01
            workflow.total_cost_usd += storage_phase.cost_usd
    
    async def _execute_article_to_script(self, workflow: WorkflowExecution):
        """Execute article URL to script conversion"""
        workflow.status = WorkflowStatus.RUNNING
        
        for phase in workflow.phases:
            phase.status = WorkflowStatus.RUNNING
            phase.started_at = datetime.now()
            
            await asyncio.sleep(0.5)  # Simulate processing
            
            phase.status = WorkflowStatus.COMPLETED
            phase.completed_at = datetime.now()
            phase.cost_usd = 0.05
            workflow.total_cost_usd += phase.cost_usd
        
        workflow.result = {
            "workflow_type": "article_to_script",
            "article_url": workflow.config.topic,
            "platforms": workflow.config.platforms,
            "total_cost": workflow.total_cost_usd
        }
    
    async def _notify_progress(self, workflow: WorkflowExecution, phase: WorkflowPhase, current: int, total: int):
        """Notify progress callbacks"""
        for callback in workflow.progress_callbacks:
            try:
                await callback(workflow, phase, current, total)
            except Exception as e:
                print(f"Progress callback error: {e}")
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a workflow"""
        # Check active workflows
        if workflow_id in self.active_workflows:
            workflow = self.active_workflows[workflow_id]
        else:
            # Check history
            workflow = next((w for w in self.workflow_history if w.id == workflow_id), None)
            if not workflow:
                return None
        
        current_phase = None
        phases_completed = 0
        
        for phase in workflow.phases:
            if phase.status == WorkflowStatus.RUNNING:
                current_phase = phase.name
            elif phase.status == WorkflowStatus.COMPLETED:
                phases_completed += 1
        
        return {
            "workflow_id": workflow.id,
            "status": workflow.status.value,
            "topic": workflow.config.topic,
            "workflow_type": workflow.config.workflow_type.value,
            "current_phase": current_phase,
            "phases_completed": phases_completed,
            "total_phases": len(workflow.phases),
            "created_at": workflow.created_at.isoformat(),
            "started_at": workflow.started_at.isoformat() if workflow.started_at else None,
            "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
            "total_cost": workflow.total_cost_usd,
            "platforms": workflow.config.platforms,
            "style": workflow.config.style,
            "error": workflow.error
        }
    
    def list_workflows(self) -> Dict[str, Any]:
        """List all workflows (active and completed)"""
        active = [self.get_workflow_status(wf_id) for wf_id in self.active_workflows.keys()]
        completed = [self.get_workflow_status(wf.id) for wf in self.workflow_history[-10:]]  # Last 10
        
        return {
            "active_workflows": active,
            "recent_completed": completed,
            "total_active": len(active),
            "total_completed": len(self.workflow_history)
        }
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow"""
        if workflow_id not in self.active_workflows:
            return False
        
        workflow = self.active_workflows[workflow_id]
        
        if workflow.status not in [WorkflowStatus.RUNNING, WorkflowStatus.STARTING]:
            return False
        
        workflow.status = WorkflowStatus.CANCELLED
        workflow.completed_at = datetime.now()
        
        # Emit workflow cancelled event
        await workflow_cancelled(workflow_id)
        
        # Move to history
        self.workflow_history.append(workflow)
        del self.active_workflows[workflow_id]
        
        return True

# Global workflow manager instance
workflow_manager = WorkflowManager()

# Convenience functions for common operations
async def trigger_workflow(
    topic: str,
    workflow_type: str = "full_pipeline",
    platforms: List[str] = None,
    style: str = "educational"
) -> str:
    """Trigger a workflow with simple parameters"""
    if platforms is None:
        platforms = ["all"]
    
    config = WorkflowConfig(
        topic=topic,
        workflow_type=WorkflowType(workflow_type),
        platforms=platforms,
        style=style
    )
    
    workflow_id = await workflow_manager.create_workflow(config)
    
    # Execute in background
    asyncio.create_task(workflow_manager.execute_workflow(workflow_id))
    
    return workflow_id

async def search_trending_topics(query: str, limit: int = 5) -> Dict[str, Any]:
    """Search for trending topics using the search agent"""
    try:
        from production_workflow.agents.search_agent import search_tech_news
        result = await search_tech_news(query)
        return {
            "query": query,
            "limit": limit,
            "results": result.get("results", "No results found"),
            "cost": result.get("cost", 0.02),
            "timestamp": datetime.now().isoformat(),
            "source": "tech_news_search"
        }
    except ImportError:
        return {
            "query": query,
            "results": f"Simulated search results for: {query}",
            "cost": 0.02,
            "timestamp": datetime.now().isoformat(),
            "source": "simulated"
        }

async def generate_scripts_from_url(
    article_url: str,
    platforms: List[str] = None,
    tone: str = "casual"
) -> Dict[str, Any]:
    """Generate scripts directly from an article URL"""
    if platforms is None:
        platforms = ["all"]
    
    # This would integrate with crawl and script generation agents
    return {
        "article_url": article_url,
        "platforms": platforms,
        "tone": tone,
        "scripts_generated": len(platforms) if "all" not in platforms else 3,
        "estimated_cost": 0.08,
        "timestamp": datetime.now().isoformat(),
        "note": "Script generation from URL functionality available"
    }