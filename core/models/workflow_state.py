from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

class PhaseStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PENDING_REVIEW = "pending_review"

class ReviewStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"

@dataclass
class PhaseOutput:
    phase_name: str
    data: Dict[str, Any]
    status: PhaseStatus
    cost_usd: float = 0.0
    error: str = ""
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class ContentState:
    workflow_id: str
    input_type: str  # "youtube", "file", "prompt"
    input_data: Dict[str, Any]
    current_phase: str
    status: str = "running"
    created_at: datetime = field(default_factory=datetime.now)
    
    # Phase outputs
    phase_outputs: Dict[str, PhaseOutput] = field(default_factory=dict)
    
    # Human review
    pending_reviews: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Error tracking
    errors: List[Dict[str, str]] = field(default_factory=list)
    
    def add_phase_output(self, phase_name: str, output: PhaseOutput):
        """Add output for a phase"""
        self.phase_outputs[phase_name] = output
    
    @property
    def input_processing(self) -> Optional[PhaseOutput]:
        return self.phase_outputs.get("input_processing")
    
    @property
    def research(self) -> Optional[PhaseOutput]:
        return self.phase_outputs.get("research")
    
    @property
    def planning(self) -> Optional[PhaseOutput]:
        return self.phase_outputs.get("planning")
    
    @property
    def script_writing(self) -> Optional[PhaseOutput]:
        return self.phase_outputs.get("script_writing")
    
    @property
    def visual_generation(self) -> Optional[PhaseOutput]:
        return self.phase_outputs.get("visual_generation")
    
    @property
    def assembly(self) -> Optional[PhaseOutput]:
        return self.phase_outputs.get("assembly")
    
    @property
    def export(self) -> Optional[PhaseOutput]:
        return self.phase_outputs.get("export")
    
    @property
    def distribution(self) -> Optional[PhaseOutput]:
        return self.phase_outputs.get("distribution")
    
    @property
    def analytics(self) -> Optional[PhaseOutput]:
        return self.phase_outputs.get("analytics")
    
    @property
    def total_cost(self) -> float:
        """Calculate total cost across all phases"""
        return sum(output.cost_usd for output in self.phase_outputs.values())