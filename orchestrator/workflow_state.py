from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from langchain_core.messages import BaseMessage

class ReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REVISION_REQUESTED = "revision_requested"
    REJECTED = "rejected"

class PhaseStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    AWAITING_REVIEW = "awaiting_review"
    COMPLETED = "completed"
    FAILED = "failed"

class HumanReview(BaseModel):
    """Human review decision for a phase"""
    status: ReviewStatus
    feedback: Optional[str] = None
    modifications: Optional[Dict[str, Any]] = None
    reviewer_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class PhaseOutput(BaseModel):
    """Output from a single phase"""
    phase_name: str = ""
    data: Dict[str, Any] = Field(default_factory=dict)
    status: PhaseStatus = PhaseStatus.NOT_STARTED
    error: Optional[str] = None
    duration_seconds: Optional[float] = None
    cost_usd: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class ContentState(BaseModel):
    """Main workflow state for content generation"""
    # Chat messages for LangGraph
    messages: List[BaseMessage] = Field(default_factory=list)
    
    # Workflow metadata
    workflow_id: str = Field(default_factory=lambda: f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # Input
    input_type: Literal["youtube", "file", "prompt"] = "prompt"
    input_data: Dict[str, Any] = Field(default_factory=dict)
    
    # Phase tracking
    current_phase: str = "input_processing"
    phases_completed: List[str] = Field(default_factory=list)
    
    # Phase outputs
    input_processing: Optional[PhaseOutput] = None
    search: Optional[PhaseOutput] = None  # For search agent
    search_content_ideas: Optional[PhaseOutput] = None
    research: Optional[PhaseOutput] = None
    planning: Optional[PhaseOutput] = None
    script_writing: Optional[PhaseOutput] = None
    visual_generation: Optional[PhaseOutput] = None
    assembly: Optional[PhaseOutput] = None
    export: Optional[PhaseOutput] = None
    distribution: Optional[PhaseOutput] = None
    analytics: Optional[PhaseOutput] = None
    
    # Human reviews
    reviews: Dict[str, HumanReview] = Field(default_factory=dict)
    
    # Cost tracking
    total_cost_usd: float = 0.0
    cost_breakdown: Dict[str, float] = Field(default_factory=dict)
    
    # Final outputs
    final_video_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    published_urls: Dict[str, str] = Field(default_factory=dict)
    
    # Error tracking
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    retry_count: int = 0
    
    def add_phase_output(self, phase_name: str, output: PhaseOutput):
        """Add output from a completed phase"""
        setattr(self, phase_name.replace("-", "_"), output)
        self.phases_completed.append(phase_name)
        self.updated_at = datetime.now()
        
        # Update cost tracking
        if output.cost_usd:
            self.cost_breakdown[phase_name] = output.cost_usd
            self.total_cost_usd = sum(self.cost_breakdown.values())
    
    def add_review(self, phase_name: str, review: HumanReview):
        """Add human review for a phase"""
        self.reviews[phase_name] = review
        self.updated_at = datetime.now()
    
    def get_latest_output(self) -> Optional[PhaseOutput]:
        """Get the most recent phase output"""
        for phase in reversed(self.phases_completed):
            output = getattr(self, phase.replace("-", "_"), None)
            if output:
                return output
        return None
    
    def can_proceed(self) -> bool:
        """Check if workflow can proceed to next phase"""
        if not self.reviews:
            return True
        
        latest_review = self.reviews.get(self.current_phase)
        if latest_review:
            return latest_review.status == ReviewStatus.APPROVED
        
        return True
    
    def to_checkpoint(self) -> Dict[str, Any]:
        """Convert state to checkpoint format for persistence"""
        return self.model_dump(mode='json')
    
    @classmethod
    def from_checkpoint(cls, data: Dict[str, Any]) -> "ContentState":
        """Restore state from checkpoint"""
        return cls(**data)