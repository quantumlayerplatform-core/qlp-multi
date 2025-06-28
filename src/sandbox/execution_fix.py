"""Fix for sandbox execution validation errors"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class ExecutionResult(BaseModel):
    """Fixed execution result model"""
    execution_id: str
    success: bool = Field(default=True)
    execution_time: float = Field(default=0.0)
    output: Optional[str] = None
    error: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Monkey patch if needed
def patch_execution_result():
    """Apply the fix to the sandbox module"""
    try:
        import src.sandbox.models
        src.sandbox.models.ExecutionResult = ExecutionResult
        return True
    except:
        return False