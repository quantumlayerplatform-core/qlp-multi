"""
HAP-filtered agent wrapper for content safety
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from src.agents.base_agents import BaseAgent
from src.common.models import Task, TaskResult, AgentType
from src.moderation import (
    check_content, CheckContext, Severity, Category
)

logger = logging.getLogger(__name__)


class HAPFilteredAgent(BaseAgent):
    """
    Agent wrapper that adds HAP filtering to inputs and outputs
    """
    
    def __init__(self, base_agent: BaseAgent, strict_mode: bool = True):
        """
        Initialize HAP-filtered agent
        
        Args:
            base_agent: The underlying agent to wrap
            strict_mode: If True, block on medium severity; if False, only high/critical
        """
        super().__init__(
            agent_id=f"hap-{base_agent.agent_id}",
            agent_type=base_agent.agent_type,
            tier=base_agent.tier,
            config=base_agent.config
        )
        self.base_agent = base_agent
        self.strict_mode = strict_mode
        self.blocked_count = 0
        self.filtered_count = 0
    
    async def validate_input(self, task: Task) -> tuple[bool, Optional[str]]:
        """
        Validate task input for HAP violations
        
        Returns:
            Tuple of (is_valid, rejection_reason)
        """
        try:
            # Check task description
            result = await check_content(
                content=task.description,
                context=CheckContext.USER_REQUEST,
                user_id=task.metadata.get("user_id"),
                tenant_id=task.metadata.get("tenant_id")
            )
            
            # Determine if we should block
            if self.strict_mode and result.severity >= Severity.MEDIUM:
                self.blocked_count += 1
                return False, f"Input rejected: {result.explanation}"
            elif result.severity >= Severity.HIGH:
                self.blocked_count += 1
                return False, f"Input blocked: {result.explanation}"
            
            return True, None
            
        except Exception as e:
            logger.error(f"HAP input validation error: {e}")
            # Fail open - don't block on HAP errors
            return True, None
    
    async def filter_output(self, output: str, task: Task) -> str:
        """
        Filter agent output for HAP violations
        
        Args:
            output: Raw agent output
            task: Original task for context
            
        Returns:
            Filtered output or regenerated content
        """
        try:
            # Check output content
            result = await check_content(
                content=output,
                context=CheckContext.AGENT_OUTPUT,
                user_id=task.metadata.get("user_id"),
                tenant_id=task.metadata.get("tenant_id")
            )
            
            # Handle violations
            if result.severity >= Severity.MEDIUM:
                self.filtered_count += 1
                logger.warning(
                    f"Agent {self.agent_id} generated {result.severity} content: "
                    f"{result.categories}"
                )
                
                # For high severity, regenerate with safety prompt
                if result.severity >= Severity.HIGH:
                    return await self._regenerate_safe_output(task, result)
                
                # For medium severity, attempt to clean
                return self._clean_output(output, result)
            
            return output
            
        except Exception as e:
            logger.error(f"HAP output filtering error: {e}")
            # Fail open - return original output
            return output
    
    async def _regenerate_safe_output(self, task: Task, hap_result) -> str:
        """
        Regenerate output with enhanced safety guidelines
        """
        # Create safety-enhanced task
        safe_task = Task(
            task_id=f"{task.task_id}-safe",
            description=task.description,
            agent_type=task.agent_type,
            context=task.context,
            metadata={
                **task.metadata,
                "safety_prompt": f"""
                IMPORTANT: Generate professional, respectful content only.
                Avoid: {', '.join([cat.value for cat in hap_result.categories])}
                
                Original request: {task.description}
                
                Provide a helpful response while maintaining appropriate language.
                """
            }
        )
        
        # Try regeneration up to 3 times
        for attempt in range(3):
            try:
                result = await self.base_agent.execute(safe_task)
                
                # Verify the regenerated content
                check_result = await check_content(
                    content=result.output,
                    context=CheckContext.AGENT_OUTPUT
                )
                
                if check_result.severity < Severity.MEDIUM:
                    return result.output
                    
            except Exception as e:
                logger.error(f"Regeneration attempt {attempt + 1} failed: {e}")
        
        # If all attempts fail, return generic safe response
        return self._get_safe_fallback_response(task)
    
    def _clean_output(self, output: str, hap_result) -> str:
        """
        Attempt to clean medium severity content
        """
        cleaned = output
        
        # Basic profanity masking
        if Category.PROFANITY in hap_result.categories:
            # In production, use more sophisticated cleaning
            profanity_patterns = [
                # Add patterns as needed
            ]
            for pattern in profanity_patterns:
                cleaned = cleaned.replace(pattern, "[removed]")
        
        return cleaned
    
    def _get_safe_fallback_response(self, task: Task) -> str:
        """
        Generate a safe fallback response
        """
        return f"""
I apologize, but I'm unable to provide a response that meets both your request 
and our content guidelines. 

Task type: {task.agent_type}

Please rephrase your request or contact support if you believe this is an error.
"""
    
    async def execute(self, task: Task) -> TaskResult:
        """
        Execute task with HAP filtering
        """
        start_time = datetime.utcnow()
        
        # Validate input
        is_valid, rejection_reason = await self.validate_input(task)
        if not is_valid:
            return TaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                output=f"Task rejected: {rejection_reason}",
                status="failed",
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
                metadata={
                    "hap_blocked": True,
                    "reason": rejection_reason
                }
            )
        
        # Execute with base agent
        result = await self.base_agent.execute(task)
        
        # Filter output
        if result.status == "completed":
            filtered_output = await self.filter_output(result.output, task)
            result.output = filtered_output
            
            # Add HAP metadata
            result.metadata["hap_filtered"] = filtered_output != result.output
            result.metadata["hap_stats"] = {
                "blocked_total": self.blocked_count,
                "filtered_total": self.filtered_count
            }
        
        return result
    
    async def get_agent_info(self) -> Dict[str, Any]:
        """Get information about this agent"""
        base_info = await self.base_agent.get_agent_info()
        return {
            **base_info,
            "hap_enabled": True,
            "strict_mode": self.strict_mode,
            "blocked_count": self.blocked_count,
            "filtered_count": self.filtered_count
        }


def create_hap_filtered_agent(
    base_agent: BaseAgent,
    strict_mode: bool = True
) -> HAPFilteredAgent:
    """
    Factory function to create HAP-filtered agents
    
    Args:
        base_agent: The agent to wrap
        strict_mode: Whether to use strict filtering
        
    Returns:
        HAP-filtered agent
    """
    return HAPFilteredAgent(base_agent, strict_mode)