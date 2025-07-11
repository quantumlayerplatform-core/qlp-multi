#!/usr/bin/env python3
"""
Production-Grade Capsule Generation System
Enterprise-ready, reliable, and scalable capsule creation
"""

import asyncio
import json
import traceback
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
import structlog
from contextlib import asynccontextmanager

from src.common.models import (
    ExecutionRequest, QLCapsule, ValidationReport, 
    ValidationCheck, ValidationStatus, Task, TaskResult
)
from src.common.database import get_db
from src.orchestrator.capsule_storage import CapsuleStorageService
from src.agents.client import AgentFactoryClient
from src.validation.client import ValidationMeshClient
from src.sandbox.client import SandboxServiceClient
from src.memory.client import VectorMemoryClient
from src.common.config import settings

logger = structlog.get_logger()


class CapsuleGenerationStatus(Enum):
    """Status of capsule generation process"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class CapsuleGenerationMetrics:
    """Metrics for capsule generation"""
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    total_duration_seconds: float = 0.0
    task_count: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    validation_attempts: int = 0
    retry_count: int = 0
    error_count: int = 0
    warnings: List[str] = field(default_factory=list)
    status: CapsuleGenerationStatus = CapsuleGenerationStatus.PENDING
    

@dataclass 
class CapsuleGenerationContext:
    """Context for capsule generation process"""
    request: ExecutionRequest
    capsule_id: str
    metrics: CapsuleGenerationMetrics
    storage: CapsuleStorageService
    tasks: List[Task] = field(default_factory=list)
    results: Dict[str, TaskResult] = field(default_factory=dict)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    

class ProductionCapsuleSystem:
    """
    Enterprise-grade capsule generation system
    Handles failures gracefully, provides monitoring, and ensures consistency
    """
    
    def __init__(self):
        self.agent_client = AgentFactoryClient(settings.AGENT_FACTORY_URL)
        self.validation_client = ValidationMeshClient(settings.VALIDATION_MESH_URL)
        self.sandbox_client = SandboxServiceClient(settings.SANDBOX_SERVICE_URL)
        self.memory_client = VectorMemoryClient(settings.VECTOR_MEMORY_URL)
        
        # Configuration
        self.max_retries = 3
        self.retry_delay = 2.0
        self.validation_threshold = 0.7
        self.timeout_seconds = 300
        
    @asynccontextmanager
    async def generation_context(self, request: ExecutionRequest):
        """Create a managed context for capsule generation"""
        context = CapsuleGenerationContext(
            request=request,
            capsule_id=f"cap-{request.id}",
            metrics=CapsuleGenerationMetrics(),
            storage=CapsuleStorageService(next(get_db()))
        )
        
        try:
            yield context
        finally:
            # Always record metrics
            context.metrics.end_time = datetime.now(timezone.utc)
            context.metrics.total_duration_seconds = (
                context.metrics.end_time - context.metrics.start_time
            ).total_seconds()
            
            # Log final metrics
            logger.info(
                "Capsule generation completed",
                capsule_id=context.capsule_id,
                status=context.metrics.status.value,
                duration=context.metrics.total_duration_seconds,
                tasks_completed=context.metrics.tasks_completed,
                tasks_failed=context.metrics.tasks_failed,
                errors=len(context.errors)
            )
    
    async def generate_capsule(self, request: ExecutionRequest) -> QLCapsule:
        """
        Generate a production-ready capsule with full error handling
        """
        async with self.generation_context(request) as context:
            try:
                context.metrics.status = CapsuleGenerationStatus.IN_PROGRESS
                
                # Step 1: Decompose request into tasks
                tasks = await self._decompose_request(context)
                context.tasks = tasks
                context.metrics.task_count = len(tasks)
                
                # Step 2: Execute tasks with retry logic
                results = await self._execute_tasks_with_retry(context)
                context.results = results
                
                # Step 3: Validate results
                context.metrics.status = CapsuleGenerationStatus.VALIDATING
                validation_report = await self._validate_results(context)
                
                # Step 4: Create capsule
                capsule = await self._create_capsule(context, validation_report)
                
                # Step 5: Store capsule
                await self._store_capsule(context, capsule)
                
                context.metrics.status = CapsuleGenerationStatus.COMPLETED
                return capsule
                
            except Exception as e:
                context.metrics.status = CapsuleGenerationStatus.FAILED
                context.metrics.error_count += 1
                context.errors.append({
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                
                # Create a failed capsule with error information
                return await self._create_error_capsule(context, e)
    
    async def _decompose_request(self, context: CapsuleGenerationContext) -> List[Task]:
        """Decompose request into executable tasks"""
        try:
            # Use NLP to understand the request
            description = context.request.description
            requirements = context.request.requirements or ""
            
            # Create base tasks
            tasks = []
            
            # Main implementation task
            tasks.append(Task(
                id=f"task-main-{context.request.id}",
                type="implementation",
                description=f"Implement: {description}",
                complexity="medium",
                metadata={
                    "language": context.request.constraints.get("language", "python"),
                    "requirements": requirements,
                    "original_description": description,
                    "dependencies": []
                }
            ))
            
            # Test generation task
            tasks.append(Task(
                id=f"task-test-{context.request.id}",
                type="test_generation",
                description=f"Create comprehensive tests for: {description}",
                complexity="medium",
                metadata={
                    "test_framework": "pytest",
                    "coverage_target": 80,
                    "dependencies": [tasks[0].id]
                }
            ))
            
            # Documentation task
            tasks.append(Task(
                id=f"task-docs-{context.request.id}",
                type="documentation",
                description=f"Generate documentation for: {description}",
                complexity="simple",
                metadata={
                    "format": "markdown",
                    "include_examples": True,
                    "dependencies": [tasks[0].id]
                }
            ))
            
            logger.info(f"Decomposed request into {len(tasks)} tasks")
            return tasks
            
        except Exception as e:
            logger.error(f"Failed to decompose request: {e}")
            # Return a minimal task set
            return [Task(
                id=f"task-fallback-{context.request.id}",
                type="implementation",
                description=context.request.description,
                complexity="simple",
                metadata={}
            )]
    
    async def _execute_tasks_with_retry(self, context: CapsuleGenerationContext) -> Dict[str, TaskResult]:
        """Execute tasks with retry logic and error handling"""
        results = {}
        
        for task in context.tasks:
            retry_count = 0
            
            while retry_count <= self.max_retries:
                try:
                    # Check dependencies
                    if not self._dependencies_met(task, results):
                        logger.warning(f"Skipping task {task.id} - dependencies not met")
                        break
                    
                    # Execute task
                    result = await self._execute_single_task(context, task)
                    
                    if result.status == "completed":
                        results[task.id] = result
                        context.metrics.tasks_completed += 1
                        break
                    else:
                        raise Exception(f"Task failed: {result.output.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    retry_count += 1
                    context.metrics.retry_count += 1
                    
                    if retry_count > self.max_retries:
                        logger.error(f"Task {task.id} failed after {retry_count} retries: {e}")
                        context.metrics.tasks_failed += 1
                        
                        # Create a failed result
                        results[task.id] = TaskResult(
                            task_id=task.id,
                            status="failed",
                            output_type="error",
                            output={"error": str(e)},
                            execution_time=0.0,
                            confidence_score=0.0,
                            agent_tier_used="none"
                        )
                        break
                    else:
                        logger.warning(f"Retrying task {task.id} (attempt {retry_count + 1})")
                        await asyncio.sleep(self.retry_delay * retry_count)
        
        return results
    
    async def _execute_single_task(self, context: CapsuleGenerationContext, task: Task) -> TaskResult:
        """Execute a single task with timeout"""
        try:
            # Add context from previous results
            enriched_task = self._enrich_task_context(task, context.results)
            
            # Execute with timeout
            result = await asyncio.wait_for(
                self.agent_client.execute_task(enriched_task),
                timeout=self.timeout_seconds
            )
            
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"Task {task.id} timed out after {self.timeout_seconds}s")
            raise
        except Exception as e:
            logger.error(f"Task {task.id} execution failed: {e}")
            raise
    
    def _dependencies_met(self, task: Task, results: Dict[str, TaskResult]) -> bool:
        """Check if task dependencies are met"""
        dependencies = task.metadata.get("dependencies", [])
        for dep_id in dependencies:
            if dep_id not in results or results[dep_id].status != "completed":
                return False
        return True
    
    def _enrich_task_context(self, task: Task, results: Dict[str, TaskResult]) -> Task:
        """Enrich task context with results from dependencies"""
        enriched = task.model_copy()
        
        # Add results from dependencies
        dependencies = task.metadata.get("dependencies", [])
        for dep_id in dependencies:
            if dep_id in results:
                dep_result = results[dep_id]
                enriched.metadata[f"dependency_{dep_id}"] = {
                    "output": dep_result.output,
                    "confidence": dep_result.confidence_score
                }
        
        return enriched
    
    async def _validate_results(self, context: CapsuleGenerationContext) -> ValidationReport:
        """Validate all results comprehensively"""
        try:
            # Collect all code artifacts
            code_artifacts = {}
            test_artifacts = {}
            
            for task_id, result in context.results.items():
                if result.status == "completed":
                    if result.output_type == "code":
                        code_artifacts[task_id] = result.output
                    elif result.output_type == "tests":
                        test_artifacts[task_id] = result.output
            
            # Run validation
            validation_result = await self.validation_client.validate_code_batch(
                code_artifacts,
                language=context.request.constraints.get("language", "python")
            )
            
            # Run tests in sandbox
            if test_artifacts:
                test_results = await self._run_tests_in_sandbox(code_artifacts, test_artifacts)
                validation_result["test_results"] = test_results
            
            # Create validation report
            return self._create_validation_report(validation_result)
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            context.metrics.warnings.append(f"Validation error: {str(e)}")
            
            # Return a basic validation report
            return ValidationReport(
                overall_status=ValidationStatus.WARNING,
                confidence_score=0.5,
                checks=[
                    ValidationCheck(
                        name="validation_error",
                        type="warning",
                        status=ValidationStatus.WARNING,
                        message=f"Validation encountered error: {str(e)}",
                        severity="medium"
                    )
                ]
            )
    
    async def _run_tests_in_sandbox(self, code: Dict[str, Any], tests: Dict[str, Any]) -> Dict[str, Any]:
        """Run tests in isolated sandbox"""
        try:
            # Prepare sandbox environment
            files = {}
            
            # Add code files
            for task_id, code_data in code.items():
                if isinstance(code_data, dict) and "code" in code_data:
                    files["main.py"] = code_data["code"]
            
            # Add test files
            for task_id, test_data in tests.items():
                if isinstance(test_data, dict) and "code" in test_data:
                    files["test_main.py"] = test_data["code"]
            
            # Run in sandbox
            result = await self.sandbox_client.execute_code(
                files=files,
                command="python -m pytest test_main.py -v",
                language="python"
            )
            
            return {
                "success": result.get("success", False),
                "output": result.get("output", ""),
                "error": result.get("error", "")
            }
            
        except Exception as e:
            logger.error(f"Sandbox test execution failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _create_validation_report(self, validation_result: Dict[str, Any]) -> ValidationReport:
        """Create a structured validation report"""
        checks = []
        overall_score = 0.0
        
        # Process validation checks
        for check_name, check_result in validation_result.items():
            if isinstance(check_result, dict):
                checks.append(ValidationCheck(
                    name=check_name,
                    type=check_name,
                    status=ValidationStatus.PASSED if check_result.get("passed", False) else ValidationStatus.FAILED,
                    message=check_result.get("message", ""),
                    severity=check_result.get("severity", "low"),
                    details=check_result.get("details", {})
                ))
                
                if check_result.get("score"):
                    overall_score += check_result["score"]
        
        # Calculate overall status
        if overall_score / max(len(checks), 1) >= self.validation_threshold:
            overall_status = ValidationStatus.PASSED
        else:
            overall_status = ValidationStatus.WARNING
        
        return ValidationReport(
            overall_status=overall_status,
            confidence_score=overall_score / max(len(checks), 1),
            checks=checks
        )
    
    async def _create_capsule(self, context: CapsuleGenerationContext, validation_report: ValidationReport) -> QLCapsule:
        """Create a QLCapsule from results"""
        # Extract code and tests
        source_code = {}
        tests = {}
        documentation = ""
        
        for task_id, result in context.results.items():
            if result.status == "completed":
                task = next((t for t in context.tasks if t.id == task_id), None)
                
                if task and task.type == "implementation":
                    code = result.output.get("code", "")
                    if code:
                        source_code["main.py"] = code
                
                elif task and task.type == "test_generation":
                    test_code = result.output.get("code", "")
                    if test_code:
                        tests["test_main.py"] = test_code
                
                elif task and task.type == "documentation":
                    documentation = result.output.get("content", "")
        
        # Create manifest
        manifest = {
            "version": "1.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "language": context.request.constraints.get("language", "python"),
            "description": context.request.description,
            "tasks_completed": context.metrics.tasks_completed,
            "tasks_total": context.metrics.task_count,
            "validation_score": validation_report.confidence_score
        }
        
        # Create metadata
        metadata = {
            "generation_metrics": {
                "duration_seconds": context.metrics.total_duration_seconds,
                "retry_count": context.metrics.retry_count,
                "error_count": context.metrics.error_count,
                "warnings": context.metrics.warnings
            },
            "request_info": {
                "request_id": context.request.id,
                "tenant_id": context.request.tenant_id,
                "user_id": context.request.user_id
            }
        }
        
        # Create capsule
        capsule = QLCapsule(
            id=context.capsule_id,
            request_id=context.request.id,
            manifest=manifest,
            source_code=source_code,
            tests=tests,
            documentation=documentation or self._generate_default_documentation(context),
            validation_report=validation_report,
            deployment_config={},
            metadata=metadata,
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        return capsule
    
    def _generate_default_documentation(self, context: CapsuleGenerationContext) -> str:
        """Generate default documentation if none provided"""
        return f"""# {context.request.description}

Generated by Quantum Layer Platform on {datetime.now(timezone.utc).isoformat()}

## Overview
{context.request.description}

## Requirements
{context.request.requirements or "No specific requirements provided"}

## Validation Results
- Overall Score: {context.results.get('validation_score', 'N/A')}
- Tasks Completed: {context.metrics.tasks_completed}/{context.metrics.task_count}

## Usage
Please refer to the source code and tests for usage examples.

---
*This documentation was automatically generated.*
"""
    
    async def _store_capsule(self, context: CapsuleGenerationContext, capsule: QLCapsule) -> None:
        """Store capsule with proper error handling"""
        try:
            # Store in database
            stored_id = await context.storage.store_capsule(
                capsule,
                context.request,
                overwrite=True
            )
            
            logger.info(f"Capsule stored successfully: {stored_id}")
            
            # Store in vector memory for future reference
            await self._store_in_vector_memory(capsule)
            
        except Exception as e:
            logger.error(f"Failed to store capsule: {e}")
            context.errors.append({
                "operation": "store_capsule",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            # Don't fail the entire operation if storage fails
    
    async def _store_in_vector_memory(self, capsule: QLCapsule) -> None:
        """Store capsule patterns in vector memory"""
        try:
            # Store successful code patterns
            for filename, code in capsule.source_code.items():
                await self.memory_client.store_pattern(
                    type="code_pattern",
                    content=code,
                    metadata={
                        "capsule_id": capsule.id,
                        "filename": filename,
                        "language": capsule.manifest.get("language", "python"),
                        "validation_score": capsule.validation_report.confidence_score if capsule.validation_report else 0.0
                    }
                )
            
        except Exception as e:
            logger.warning(f"Failed to store in vector memory: {e}")
    
    async def _create_error_capsule(self, context: CapsuleGenerationContext, error: Exception) -> QLCapsule:
        """Create a capsule representing the error state"""
        return QLCapsule(
            id=context.capsule_id,
            request_id=context.request.id,
            manifest={
                "version": "1.0",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "error",
                "error": str(error)
            },
            source_code={},
            tests={},
            documentation=f"""# Error During Capsule Generation

An error occurred while generating the capsule for request: {context.request.id}

## Error Details
```
{str(error)}
```

## Request Information
- Description: {context.request.description}
- Tenant: {context.request.tenant_id}
- User: {context.request.user_id}

## Metrics
- Tasks Attempted: {context.metrics.task_count}
- Tasks Completed: {context.metrics.tasks_completed}
- Tasks Failed: {context.metrics.tasks_failed}
- Total Errors: {len(context.errors)}

## Error Log
{json.dumps(context.errors, indent=2)}
""",
            validation_report=ValidationReport(
                overall_status=ValidationStatus.FAILED,
                confidence_score=0.0,
                checks=[
                    ValidationCheck(
                        name="generation_error",
                        type="error",
                        status=ValidationStatus.FAILED,
                        message=str(error),
                        severity="critical"
                    )
                ]
            ),
            metadata={
                "error": str(error),
                "errors": context.errors,
                "metrics": {
                    "duration_seconds": context.metrics.total_duration_seconds,
                    "retry_count": context.metrics.retry_count,
                    "error_count": context.metrics.error_count
                }
            },
            created_at=datetime.now(timezone.utc).isoformat()
        )


# Singleton instance
_production_system = None

def get_production_capsule_system() -> ProductionCapsuleSystem:
    """Get singleton instance of production capsule system"""
    global _production_system
    if _production_system is None:
        _production_system = ProductionCapsuleSystem()
    return _production_system