"""
Base agent classes for the Quantum Layer Platform
These are the core agent implementations used by both the factory and ensemble
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime
import asyncio
import json
from uuid import uuid4

import structlog
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from src.common.models import (
    Task,
    TaskResult,
    AgentTier,
    TaskStatus
)
from src.common.config import settings
from src.common.error_handling import (
    error_handler,
    RetryableError,
    NonRetryableError,
    ErrorSeverity,
    with_retry,
    with_circuit_breaker
)
from src.memory.client import VectorMemoryClient
from src.sandbox.client import SandboxServiceClient
from src.agents.azure_llm_client import llm_client, get_model_for_tier, LLMProvider

logger = structlog.get_logger()

# Initialize clients
# Keep legacy clients for backward compatibility
openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY) if settings.ANTHROPIC_API_KEY else None
memory_client = VectorMemoryClient(settings.VECTOR_MEMORY_URL)
sandbox_client = SandboxServiceClient(f"http://localhost:{settings.SANDBOX_PORT}")


class Agent:
    """Base agent class"""
    
    def __init__(self, agent_id: str, tier: AgentTier):
        self.agent_id = agent_id
        self.tier = tier
        self.created_at = datetime.utcnow()
        
    async def execute(self, task: Task, context: Dict[str, Any]) -> TaskResult:
        """Execute a task - to be implemented by subclasses"""
        raise NotImplementedError


class T0Agent(Agent):
    """Tier 0: Simple task execution using Llama or small models"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id, AgentTier.T0)
        
    @with_circuit_breaker("llm_service", failure_threshold=3, recovery_timeout=30)
    @with_retry(max_attempts=3, service="t0_agent", exceptions=(RetryableError, ConnectionError, TimeoutError))
    async def execute(self, task: Task, context: Dict[str, Any]) -> TaskResult:
        logger.info(f"T0 Agent executing task", task_id=task.id, agent_id=self.agent_id)
        
        start_time = datetime.utcnow()
        
        try:
            # For T0, we use simple prompts with minimal context
            prompt = self._build_prompt(task, context)
            
            # Get appropriate model for T0 tier
            model, provider = get_model_for_tier("T0")
            
            # Use unified LLM client with enhanced error handling
            try:
                response = await llm_client.chat_completion(
                    messages=[
                        {"role": "system", "content": "You are a code generation assistant. Be concise and direct."},
                        {"role": "user", "content": prompt}
                    ],
                    model=model,
                    provider=provider,
                    temperature=0.3,
                    max_tokens=2000,
                    timeout=30.0
                )
            except (ConnectionError, TimeoutError) as e:
                # These are retryable errors
                logger.warning(f"Retryable error in T0 agent", error=str(e), task_id=task.id)
                raise RetryableError(f"LLM service temporarily unavailable: {str(e)}", 
                                   severity=ErrorSeverity.MEDIUM,
                                   service="llm_client",
                                   details={"model": model, "provider": provider.value})
            except Exception as e:
                # Non-retryable errors
                if "rate_limit" in str(e).lower():
                    raise RetryableError(f"Rate limit hit: {str(e)}", 
                                       severity=ErrorSeverity.MEDIUM,
                                       service="llm_client")
                else:
                    raise NonRetryableError(f"LLM error: {str(e)}", 
                                          severity=ErrorSeverity.HIGH,
                                          service="llm_client",
                                          details={"model": model, "provider": provider.value})
            
            output = response["content"]
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(f"T0 Agent completed task", 
                       task_id=task.id, 
                       execution_time=execution_time,
                       model=model,
                       provider=provider.value)
            
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                output_type="code",
                output={"content": output},
                execution_time=execution_time,
                agent_tier_used=self.tier,
                confidence_score=0.7,  # T0 agents have lower confidence
                metadata={
                    "agent_id": self.agent_id,
                    "model": model,
                    "provider": provider.value
                }
            )
            
        except (RetryableError, NonRetryableError):
            # Re-raise our custom errors
            raise
        except Exception as e:
            # Catch any unexpected errors
            error_details = error_handler.handle_error(
                e,
                service="t0_agent",
                context={"task_id": task.id, "agent_id": self.agent_id},
                raise_after=False
            )
            
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                output_type="error",
                output={"error": str(e), "details": error_details},
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
                agent_tier_used=self.tier,
                confidence_score=0.0,
                metadata={"agent_id": self.agent_id, "error": error_details}
            )
    
    def _build_prompt(self, task: Task, context: Dict[str, Any]) -> str:
        """Build a simple prompt for T0 tasks"""
        prompt = f"Task: {task.description}\n\n"
        
        if context:
            prompt += "Context:\n"
            for key, value in context.items():
                prompt += f"- {key}: {value}\n"
            prompt += "\n"
        
        prompt += """IMPORTANT: Generate ACTUAL EXECUTABLE CODE, not directory structures or project layouts.

Requirements:
- Provide complete, working Python code
- Include proper imports, functions, and classes
- Do NOT provide directory listings, file structures, or project layouts
- Do NOT use placeholder comments like "# implement this"
- Generate real, functional implementation

Example of what NOT to do:
```
src/
├── main.py
├── __init__.py
└── tests/
```

Example of what TO do:
```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}
```

Generate the complete, executable code now:"""
        
        return prompt


class T1Agent(Agent):
    """Tier 1: Context-aware generation using GPT-4/Claude"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id, AgentTier.T1)
        
    async def execute(self, task: Task, context: Dict[str, Any]) -> TaskResult:
        logger.info(f"T1 Agent executing task", task_id=task.id, agent_id=self.agent_id)
        
        start_time = datetime.utcnow()
        
        try:
            # Search for similar code patterns
            similar_patterns = await memory_client.search_code_patterns(
                task.description,
                limit=3
            )
            
            # Build enhanced prompt with context
            prompt = self._build_enhanced_prompt(task, context, similar_patterns)
            
            # Get appropriate model for T1 tier
            model, provider = get_model_for_tier("T1")
            
            # Use unified LLM client
            response = await llm_client.chat_completion(
                messages=[
                    {
                        "role": "system", 
                        "content": """You are an expert software engineer. Generate high-quality, 
                        production-ready code with proper error handling, documentation, and best practices."""
                    },
                    {"role": "user", "content": prompt}
                ],
                model=model,
                provider=provider,
                temperature=0.3,
                max_tokens=4000,
                timeout=30.0
            )
            
            output = response["content"]
            
            # Parse structured output
            parsed_output = self._parse_output(output)
            
            # If we generated code, optionally test it in sandbox
            if parsed_output["type"] == "code" and "code" in parsed_output["content"]:
                try:
                    # Detect language (simplified - would be more robust)
                    code = parsed_output["content"]["code"]
                    language = "python" if "def " in code or "import " in code else "javascript"
                    
                    # Execute in sandbox for validation
                    sandbox_result = await sandbox_client.execute(
                        code=code,
                        language=language,
                        inputs={}
                    )
                    
                    parsed_output["content"]["execution_result"] = {
                        "status": sandbox_result["status"],
                        "output": sandbox_result.get("output", ""),
                        "error": sandbox_result.get("error", "")
                    }
                except Exception as e:
                    logger.warning(f"Sandbox execution failed: {e}")
                    # Continue without sandbox results
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                output_type=parsed_output["type"],
                output=parsed_output["content"],
                execution_time=execution_time,
                agent_tier_used=self.tier,
                confidence_score=0.85,
                metadata={
                    "agent_id": self.agent_id,
                    "patterns_used": len(similar_patterns)
                }
            )
            
        except Exception as e:
            logger.error(f"T1 Agent execution failed", error=str(e))
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                output_type="error",
                output={"error": str(e)},
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
                agent_tier_used=self.tier,
                confidence_score=0.0,
                metadata={"agent_id": self.agent_id}
            )
    
    def _build_enhanced_prompt(self, task: Task, context: Dict[str, Any], patterns: List[Dict]) -> str:
        """Build an enhanced prompt with context and patterns"""
        prompt = f"Task: {task.description}\n\n"
        
        if context:
            prompt += "Context from previous tasks:\n"
            for key, value in context.items():
                prompt += f"- {key}: {json.dumps(value, indent=2)}\n"
            prompt += "\n"
        
        if patterns:
            prompt += "Similar successful patterns:\n"
            for pattern in patterns:
                prompt += f"- Pattern: {pattern['description']}\n"
                prompt += f"  Code: {pattern['code'][:200]}...\n\n"
        
        prompt += """
CRITICAL: Generate ACTUAL EXECUTABLE CODE, NOT directory structures or file layouts.

Requirements:
- Provide complete, working Python code with real implementations
- Include all necessary imports and proper error handling
- Do NOT provide directory listings, project structures, or placeholders
- Do NOT use comments like "# implement this" or "# add code here"
- Generate functional, production-ready code

Generate a complete solution including:
1. Main implementation code (ACTUAL CODE, not structure)
2. Error handling and validation
3. Brief documentation
4. All necessary imports and dependencies

Format your response as JSON:
{
    "code": "complete executable Python code with imports, classes, functions",
    "tests": "actual test code with assertions and test cases",
    "documentation": "brief explanation of the implementation",
    "dependencies": ["list", "of", "required", "packages"]
}

EXAMPLE OF GOOD RESPONSE:
{
    "code": "from fastapi import FastAPI, HTTPException\\nfrom pydantic import BaseModel\\n\\napp = FastAPI()\\n\\nclass User(BaseModel):\\n    name: str\\n    email: str\\n\\n@app.post('/users')\\ndef create_user(user: User):\\n    return {'message': 'User created', 'user': user}",
    "tests": "import pytest\\nfrom fastapi.testclient import TestClient\\nfrom main import app\\n\\nclient = TestClient(app)\\n\\ndef test_create_user():\\n    response = client.post('/users', json={'name': 'John', 'email': 'john@example.com'})\\n    assert response.status_code == 200",
    "documentation": "FastAPI application with user creation endpoint",
    "dependencies": ["fastapi", "pydantic"]
}
"""
        
        return prompt
    
    def _parse_output(self, output: str) -> Dict[str, Any]:
        """Parse structured output from LLM"""
        try:
            # Try to parse as JSON first
            parsed = json.loads(output)
            return {
                "type": "code",
                "content": parsed
            }
        except:
            # Extract code from markdown or plain text
            code, tests, docs = self._extract_code_from_response(output)
            
            return {
                "type": "code",
                "content": {
                    "code": code,
                    "tests": tests,
                    "documentation": docs,
                    "raw_response": output  # Keep original for debugging
                }
            }
    
    def _extract_code_from_response(self, response: str) -> Tuple[str, str, str]:
        """Extract code, tests, and documentation from LLM response"""
        import re
        
        # Look for code blocks
        code_pattern = r'```(?:python)?\n(.*?)```'
        code_blocks = re.findall(code_pattern, response, re.DOTALL)
        
        code = ""
        tests = ""
        docs = ""
        
        if code_blocks:
            # First block is usually the main code
            code = code_blocks[0].strip()
            
            # Look for test code
            for block in code_blocks[1:]:
                if 'test' in block.lower() or 'assert' in block:
                    tests = block.strip()
                    break
            
            # Extract documentation
            docs_before_code = response.split('```')[0].strip()
            if docs_before_code and len(docs_before_code) < 1000:
                docs = docs_before_code
        else:
            # No code blocks, assume pure code
            code = response.strip()
        
        return code, tests, docs


class T2Agent(Agent):
    """Tier 2: Reasoning + validation loops"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id, AgentTier.T2)
        
    async def execute(self, task: Task, context: Dict[str, Any]) -> TaskResult:
        logger.info(f"T2 Agent executing task", task_id=task.id, agent_id=self.agent_id)
        
        start_time = datetime.utcnow()
        max_iterations = 3
        
        try:
            for iteration in range(max_iterations):
                # Generate solution
                solution = await self._generate_solution(task, context, iteration)
                
                # Validate solution
                validation_result = await self._validate_solution(solution, task)
                
                if validation_result["valid"]:
                    execution_time = (datetime.utcnow() - start_time).total_seconds()
                    
                    return TaskResult(
                        task_id=task.id,
                        status=TaskStatus.COMPLETED,
                        output_type="code",
                        output=solution,
                        execution_time=execution_time,
                        agent_tier_used=self.tier,
                        confidence_score=0.95,
                        metadata={
                            "agent_id": self.agent_id,
                            "iterations": iteration + 1,
                            "validation_passed": True
                        }
                    )
                
                # Use validation feedback for next iteration
                context["validation_feedback"] = validation_result["feedback"]
            
            # Max iterations reached without valid solution
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                output_type="code",
                output=solution,
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
                agent_tier_used=self.tier,
                confidence_score=0.6,  # Lower confidence due to validation issues
                metadata={
                    "agent_id": self.agent_id,
                    "iterations": max_iterations,
                    "validation_passed": False
                }
            )
            
        except Exception as e:
            logger.error(f"T2 Agent execution failed", error=str(e))
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                output_type="error",
                output={"error": str(e)},
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
                agent_tier_used=self.tier,
                confidence_score=0.0,
                metadata={"agent_id": self.agent_id}
            )
    
    async def _generate_solution(self, task: Task, context: Dict[str, Any], iteration: int) -> Dict[str, Any]:
        """Generate a solution with reasoning"""
        system_prompt = """You are an expert software architect. Think step-by-step:
1. Understand the requirements
2. Design the solution architecture
3. Implement with best practices
4. Consider edge cases and error handling
5. Validate your approach

If this is a retry, use the validation feedback to improve."""
        
        user_prompt = f"Task: {task.description}\n\n"
        
        if context:
            user_prompt += f"Context: {json.dumps(context, indent=2)}\n\n"
        
        if iteration > 0:
            user_prompt += f"This is iteration {iteration + 1}. Previous attempts had issues.\n\n"
        
        # Get appropriate model for T2 tier (reasoning)
        model, provider = get_model_for_tier("T2")
        
        # Use unified LLM client
        response = await llm_client.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model=model,
            provider=provider,
            temperature=0.4,
            max_tokens=4000
        )
        
        # Parse and structure the response
        return self._parse_solution(response["content"])
    
    async def _validate_solution(self, solution: Dict[str, Any], task: Task) -> Dict[str, Any]:
        """Validate the generated solution"""
        # This would normally call the validation service
        # For now, we do a simple LLM-based validation
        
        validation_prompt = f"""
Review this solution for the task: {task.description}

Solution:
{json.dumps(solution, indent=2)}

Check for:
1. Correctness - Does it solve the problem?
2. Completeness - Are all requirements met?
3. Quality - Is it production-ready?
4. Security - Any vulnerabilities?

Respond with JSON:
{{
    "valid": true/false,
    "feedback": "specific issues to fix if any"
}}
"""
        
        # Use GPT-4 for validation (can be from Azure or OpenAI)
        response = await llm_client.chat_completion(
            messages=[
                {"role": "system", "content": "You are a code reviewer. Be strict but fair."},
                {"role": "user", "content": validation_prompt}
            ],
            model="gpt-4-turbo-preview",  # Will auto-select Azure if available
            temperature=0.1,
            response_format={"type": "json_object"}  # Note: response_format support varies by provider
        )
        
        return json.loads(response["content"])
    
    def _parse_solution(self, content: str) -> Dict[str, Any]:
        """Parse solution from LLM response"""
        # Extract code blocks and structure
        # This is simplified - real implementation would be more robust
        return {
            "code": content,
            "language": "python",  # Would be detected
            "dependencies": []
        }


class T3Agent(Agent):
    """Tier 3: Meta-agents that can create other agents"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id, AgentTier.T3)
        
    async def execute(self, task: Task, context: Dict[str, Any]) -> TaskResult:
        logger.info(f"T3 Meta-Agent executing task", task_id=task.id, agent_id=self.agent_id)
        
        # T3 agents can spawn other agents dynamically
        # This is a simplified implementation
        
        start_time = datetime.utcnow()
        
        try:
            # Analyze task to determine agent composition
            agent_plan = await self._plan_agent_composition(task, context)
            
            # Create and orchestrate sub-agents
            results = await self._execute_with_sub_agents(agent_plan, task, context)
            
            # Synthesize results
            final_output = await self._synthesize_results(results, task)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                output_type="meta_execution",
                output=final_output,
                execution_time=execution_time,
                agent_tier_used=self.tier,
                confidence_score=0.9,
                metadata={
                    "agent_id": self.agent_id,
                    "sub_agents_used": len(agent_plan["agents"]),
                    "agent_plan": agent_plan
                }
            )
            
        except Exception as e:
            logger.error(f"T3 Meta-Agent execution failed", error=str(e))
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                output_type="error",
                output={"error": str(e)},
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
                agent_tier_used=self.tier,
                confidence_score=0.0,
                metadata={"agent_id": self.agent_id}
            )
    
    async def _plan_agent_composition(self, task: Task, context: Dict[str, Any]) -> Dict[str, Any]:
        """Plan which agents to create for this task"""
        # This would use an LLM to analyze the task and determine optimal agent composition
        # Simplified for now
        return {
            "agents": [
                {"type": "T1", "subtask": "Generate initial solution"},
                {"type": "T2", "subtask": "Validate and refine"},
                {"type": "T0", "subtask": "Generate tests"}
            ]
        }
    
    async def _execute_with_sub_agents(self, plan: Dict[str, Any], task: Task, context: Dict[str, Any]) -> List[TaskResult]:
        """Execute task using sub-agents"""
        results = []
        
        for agent_spec in plan["agents"]:
            # Create appropriate agent
            if agent_spec["type"] == "T0":
                agent = T0Agent(str(uuid4()))
            elif agent_spec["type"] == "T1":
                agent = T1Agent(str(uuid4()))
            elif agent_spec["type"] == "T2":
                agent = T2Agent(str(uuid4()))
            else:
                continue
            
            # Create subtask
            subtask = Task(
                id=str(uuid4()),
                type=task.type,
                description=agent_spec["subtask"],
                complexity="medium"
            )
            
            # Execute with accumulated context
            result = await agent.execute(subtask, context)
            results.append(result)
            
            # Update context with result
            if result.status == TaskStatus.COMPLETED:
                context[f"result_{agent_spec['type']}"] = result.output
        
        return results
    
    async def _synthesize_results(self, results: List[TaskResult], task: Task) -> Dict[str, Any]:
        """Synthesize results from multiple agents"""
        successful_results = [r for r in results if r.status == TaskStatus.COMPLETED]
        
        return {
            "synthesized_output": {
                "code": successful_results[0].output if successful_results else "",
                "validation": successful_results[1].output if len(successful_results) > 1 else {},
                "tests": successful_results[2].output if len(successful_results) > 2 else ""
            },
            "sub_agent_results": [r.dict() for r in results]
        }


# Export all base agents
__all__ = ["Agent", "T0Agent", "T1Agent", "T2Agent", "T3Agent"]
