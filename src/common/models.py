"""
Common data models used across all QLP services
"""

from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, ConfigDict
import json


# Custom JSON encoder for datetime
def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


# Base model configuration for all models
base_model_config = ConfigDict(
    json_encoders={datetime: lambda v: v.isoformat() if v else None}
)


class AgentTier(str, Enum):
    """Agent tier levels"""
    T0 = "T0"  # Simple task execution (Llama 3 8B)
    T1 = "T1"  # Context-aware generation (GPT-4/Claude)
    T2 = "T2"  # Reasoning + validation loops (GPT-4-turbo)
    T3 = "T3"  # Meta-agents creating agents (recursive)


class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ValidationStatus(str, Enum):
    """Validation result status"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


class NLPRequest(BaseModel):
    """Natural Language Processing request"""
    model_config = base_model_config
    
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    description: str
    context: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ExecutionRequest(BaseModel):
    """User's execution request"""
    model_config = base_model_config
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str
    user_id: str
    description: str
    requirements: Optional[str] = None
    constraints: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class Task(BaseModel):
    """Atomic task to be executed"""
    model_config = base_model_config
    
    id: str
    type: str  # code_generation, test_creation, documentation, etc.
    description: str
    complexity: str  # trivial, simple, medium, complex, meta
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent_tier: Optional[AgentTier] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class ExecutionResult(BaseModel):
    """Result of any execution"""
    model_config = base_model_config
    
    success: bool
    output: Optional[Union[str, Dict[str, Any]]] = None
    error: Optional[str] = None
    execution_time: float  # seconds
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentExecutionRequest(BaseModel):
    """Request for agent execution"""
    model_config = base_model_config
    
    request_id: str
    task: Task
    context: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskResult(BaseModel):
    """Result of task execution"""
    model_config = base_model_config
    
    task_id: str
    status: TaskStatus
    output_type: str  # code, tests, documentation, error
    output: Union[str, Dict[str, Any]]
    execution_time: float  # seconds
    agent_tier_used: AgentTier
    confidence_score: float  # 0.0 to 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExecutionPlan(BaseModel):
    """Execution plan for a request"""
    model_config = base_model_config
    
    id: str
    request_id: str
    tasks: List[Task]
    dependencies: Dict[str, List[str]]  # task_id -> [dependency_ids]
    execution_order: List[str]  # Topologically sorted task IDs
    task_assignments: Dict[str, AgentTier]  # task_id -> agent_tier
    estimated_duration: int  # seconds
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ValidationRequest(BaseModel):
    """Request for code validation"""
    model_config = base_model_config
    
    code: str
    language: str
    validation_type: str
    context: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ValidationCheck(BaseModel):
    """Individual validation check result"""
    model_config = base_model_config
    
    name: str
    type: str  # static_analysis, unit_test, integration_test, security, performance
    status: ValidationStatus
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    severity: str = "info"  # info, warning, error, critical


class ValidationReport(BaseModel):
    """Complete validation report"""
    model_config = base_model_config
    
    id: str
    execution_id: str
    overall_status: ValidationStatus
    checks: List[ValidationCheck]
    confidence_score: float  # 0.0 to 1.0
    requires_human_review: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class QLCapsule(BaseModel):
    """Portable execution artifact"""
    model_config = base_model_config
    
    id: str
    request_id: str
    manifest: Dict[str, Any] = Field(default_factory=dict)
    source_code: Dict[str, str] = Field(default_factory=dict)  # filename -> content
    tests: Dict[str, str] = Field(default_factory=dict)  # filename -> content
    documentation: str = Field(default="")
    validation_report: Optional[ValidationReport] = None
    deployment_config: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class AgentMetrics(BaseModel):
    """Metrics for agent performance tracking"""
    model_config = base_model_config
    
    agent_id: str
    tier: AgentTier
    task_type: str
    success_rate: float
    average_execution_time: float
    total_executions: int
    last_updated: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class MemoryEntry(BaseModel):
    """Entry in vector memory system"""
    model_config = base_model_config
    
    id: str
    type: str  # code_pattern, error_pattern, requirement_pattern
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    usage_count: int = 0
    success_rate: float = 0.0
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    last_used: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class HITLRequest(BaseModel):
    """Human-in-the-loop request"""
    model_config = base_model_config
    
    id: str
    type: str  # clarification, approval, review
    context: Dict[str, Any]
    question: str
    options: Optional[List[str]] = None
    timeout: int = 3600  # seconds
    priority: str = "normal"  # low, normal, high, critical
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class HITLResponse(BaseModel):
    """Human response to HITL request"""
    model_config = base_model_config
    
    request_id: str
    user_id: str
    response: Union[str, Dict[str, Any]]
    confidence: Optional[float] = None
    responded_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class TenantConfig(BaseModel):
    """Multi-tenant configuration"""
    model_config = base_model_config
    
    tenant_id: str
    name: str
    tier: str  # free, standard, enterprise
    limits: Dict[str, Any]  # rate limits, resource limits
    features: List[str]  # enabled features
    llm_preferences: Dict[str, Any]  # preferred models, temperature settings
    security_config: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
