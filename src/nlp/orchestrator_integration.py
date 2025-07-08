"""
Integration layer for Universal NLP Decomposer with existing orchestrator
Provides seamless integration while maintaining backward compatibility
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import structlog

from src.nlp.universal_decomposer import UniversalDecomposer, DecompositionResult
from src.common.models import (
    ExecutionRequest, 
    ExecutionPlan, 
    Task, 
    TaskResult,
    TaskStatus,
    TaskType
)
from src.memory.client import VectorMemoryClient
from src.common.config import settings

logger = structlog.get_logger()


class NLPOrchestrator:
    """
    NLP-enhanced orchestrator that uses universal decomposition
    Maintains compatibility with existing system while adding universal capabilities
    """
    
    def __init__(self, memory_client: VectorMemoryClient):
        self.universal_decomposer = UniversalDecomposer(memory_client)
        self.memory_client = memory_client
        self.execution_history: List[Dict[str, Any]] = []
        
        logger.info("NLP Orchestrator initialized with universal decomposer")
    
    async def enhanced_decompose_request(self, request: ExecutionRequest) -> ExecutionPlan:
        """
        Enhanced decomposition using universal NLP foundation
        Provides better understanding and adaptive decomposition
        """
        logger.info(f"Enhanced decomposition for request: {request.request_id}")
        
        try:
            # Use universal decomposer for intelligent decomposition
            decomposition_result = await self.universal_decomposer.decompose_request(
                request.description
            )
            
            # Convert to ExecutionPlan format for compatibility
            execution_plan = self.convert_to_execution_plan(
                request, decomposition_result
            )
            
            # Store decomposition for learning
            await self.store_decomposition(request, decomposition_result)
            
            logger.info(f"Enhanced decomposition complete: {len(execution_plan.tasks)} tasks")
            return execution_plan
            
        except Exception as e:
            logger.error(f"Enhanced decomposition failed: {e}")
            
            # Fallback to basic decomposition
            return await self.fallback_decompose_request(request)
    
    def convert_to_execution_plan(self, request: ExecutionRequest, 
                                 decomposition_result: DecompositionResult) -> ExecutionPlan:
        """Convert universal decomposition result to ExecutionPlan"""
        
        # Enrich tasks with NLP insights
        enriched_tasks = []
        for task in decomposition_result.tasks:
            # Add NLP context to task
            enhanced_context = {
                **task.context,
                "nlp_intent": {
                    "primary_goal": decomposition_result.intent.primary_goal,
                    "expected_output": decomposition_result.intent.expected_output,
                    "complexity_level": decomposition_result.intent.complexity_level,
                    "confidence": decomposition_result.intent.confidence
                },
                "nlp_requirements": {
                    "functional": decomposition_result.requirements.functional,
                    "non_functional": decomposition_result.requirements.non_functional,
                    "constraints": decomposition_result.requirements.constraints,
                    "success_criteria": decomposition_result.requirements.success_criteria
                },
                "nlp_patterns": [
                    {
                        "confidence": pattern.pattern_confidence,
                        "success_rate": pattern.success_rate,
                        "abstraction_level": pattern.abstraction_level,
                        "complexity_indicators": pattern.complexity_indicators[:3]
                    }
                    for pattern in decomposition_result.patterns_used[:3]
                ],
                "nlp_metadata": {
                    "decomposition_confidence": decomposition_result.confidence,
                    "reasoning": decomposition_result.reasoning,
                    "patterns_used": len(decomposition_result.patterns_used)
                }
            }
            
            # Create enhanced task
            enhanced_task = Task(
                id=task.id,
                title=task.title,
                description=task.description,
                type=task.type,
                complexity=task.complexity,
                estimated_time=task.estimated_time,
                dependencies=task.dependencies,
                status=task.status,
                context=enhanced_context,
                agent_requirements=task.agent_requirements,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            enriched_tasks.append(enhanced_task)
        
        # Create execution plan with NLP insights
        execution_plan = ExecutionPlan(
            plan_id=f"nlp_plan_{request.request_id}",
            request_id=request.request_id,
            tasks=enriched_tasks,
            dependencies=self.extract_dependencies(enriched_tasks),
            metadata={
                "nlp_enhanced": True,
                "intent_analysis": {
                    "primary_goal": decomposition_result.intent.primary_goal,
                    "expected_output": decomposition_result.intent.expected_output,
                    "complexity_level": decomposition_result.intent.complexity_level,
                    "scope": decomposition_result.intent.scope,
                    "confidence": decomposition_result.intent.confidence
                },
                "requirements_analysis": {
                    "functional_count": len(decomposition_result.requirements.functional),
                    "non_functional_count": len(decomposition_result.requirements.non_functional),
                    "constraints_count": len(decomposition_result.requirements.constraints),
                    "risks_count": len(decomposition_result.requirements.risks)
                },
                "decomposition_confidence": decomposition_result.confidence,
                "patterns_used": len(decomposition_result.patterns_used),
                "reasoning": decomposition_result.reasoning
            },
            estimated_duration=sum(task.estimated_time for task in enriched_tasks),
            created_at=datetime.utcnow()
        )
        
        return execution_plan
    
    def extract_dependencies(self, tasks: List[Task]) -> Dict[str, List[str]]:
        """Extract task dependencies for execution plan"""
        dependencies = {}
        for task in tasks:
            dependencies[task.id] = task.dependencies or []
        return dependencies
    
    async def store_decomposition(self, request: ExecutionRequest, 
                                 decomposition_result: DecompositionResult):
        """Store decomposition result for learning"""
        try:
            decomposition_record = {
                "request_id": request.request_id,
                "request_description": request.description,
                "decomposition_result": {
                    "task_count": len(decomposition_result.tasks),
                    "intent": decomposition_result.intent.__dict__,
                    "requirements": decomposition_result.requirements.__dict__,
                    "confidence": decomposition_result.confidence,
                    "patterns_used": len(decomposition_result.patterns_used),
                    "reasoning": decomposition_result.reasoning
                },
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": decomposition_result.metadata
            }
            
            # Store in memory for learning
            await self.memory_client.store_decomposition(decomposition_record)
            
        except Exception as e:
            logger.error(f"Failed to store decomposition: {e}")
    
    async def fallback_decompose_request(self, request: ExecutionRequest) -> ExecutionPlan:
        """Fallback decomposition if universal decomposition fails"""
        logger.info("Using fallback decomposition")
        
        # Create simple fallback task
        fallback_task = Task(
            id="fallback_task",
            title="Complete the requested task",
            description=request.description,
            type=TaskType.CODE_GENERATION,
            complexity="medium",
            estimated_time=60,
            dependencies=[],
            status=TaskStatus.PENDING,
            context={
                "fallback": True,
                "original_request": request.description,
                "success_criteria": ["Works correctly", "Passes basic tests"]
            },
            agent_requirements=["General coding ability"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        return ExecutionPlan(
            plan_id=f"fallback_plan_{request.request_id}",
            request_id=request.request_id,
            tasks=[fallback_task],
            dependencies={"fallback_task": []},
            metadata={
                "fallback": True,
                "reason": "Universal decomposition failed"
            },
            estimated_duration=60,
            created_at=datetime.utcnow()
        )
    
    async def learn_from_execution(self, request: ExecutionRequest, 
                                 execution_plan: ExecutionPlan,
                                 task_results: List[TaskResult]):
        """Learn from execution results to improve future decompositions"""
        logger.info(f"Learning from execution results for request: {request.request_id}")
        
        try:
            # Calculate execution success
            successful_tasks = sum(1 for result in task_results if result.status == TaskStatus.COMPLETED)
            success_rate = successful_tasks / len(task_results) if task_results else 0
            
            # Build execution result for learning
            execution_result = {
                "success": success_rate > 0.8,  # Consider success if >80% tasks completed
                "success_rate": success_rate,
                "task_results": [
                    {
                        "task_id": result.task_id,
                        "status": result.status.value,
                        "success": result.status == TaskStatus.COMPLETED,
                        "execution_time": result.execution_time,
                        "confidence_score": result.confidence_score,
                        "errors": result.output.get("errors", []) if result.output else []
                    }
                    for result in task_results
                ],
                "total_execution_time": sum(result.execution_time for result in task_results),
                "average_confidence": sum(result.confidence_score for result in task_results) / len(task_results) if task_results else 0,
                "metadata": {
                    "nlp_enhanced": execution_plan.metadata.get("nlp_enhanced", False),
                    "decomposition_confidence": execution_plan.metadata.get("decomposition_confidence", 0),
                    "patterns_used": execution_plan.metadata.get("patterns_used", 0)
                }
            }
            
            # Learn from execution using universal decomposer
            if execution_plan.metadata.get("nlp_enhanced", False):
                # Extract original decomposition result from plan metadata
                decomposition_result = self.reconstruct_decomposition_result(execution_plan)
                
                await self.universal_decomposer.learn_from_execution(
                    request.description, decomposition_result, execution_result
                )
            
            # Store execution history
            self.execution_history.append({
                "request_id": request.request_id,
                "request_description": request.description,
                "execution_result": execution_result,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Learning complete: success_rate={success_rate:.2f}")
            
        except Exception as e:
            logger.error(f"Failed to learn from execution: {e}")
    
    def reconstruct_decomposition_result(self, execution_plan: ExecutionPlan) -> DecompositionResult:
        """Reconstruct decomposition result from execution plan metadata"""
        from src.nlp.universal_decomposer import Intent, Requirements
        
        # Reconstruct intent
        intent_data = execution_plan.metadata.get("intent_analysis", {})
        intent = Intent(
            primary_goal=intent_data.get("primary_goal", ""),
            expected_output=intent_data.get("expected_output", ""),
            complexity_level=intent_data.get("complexity_level", "medium"),
            scope=intent_data.get("scope", "single"),
            confidence=intent_data.get("confidence", 0.5)
        )
        
        # Reconstruct requirements
        requirements = Requirements(
            functional=["Extracted from task context"],
            non_functional=["Extracted from task context"],
            constraints=["Extracted from task context"],
            success_criteria=["Extracted from task context"]
        )
        
        # Create basic decomposition result
        decomposition_result = DecompositionResult(
            tasks=execution_plan.tasks,
            intent=intent,
            requirements=requirements,
            patterns_used=[],
            confidence=execution_plan.metadata.get("decomposition_confidence", 0.5),
            reasoning=execution_plan.metadata.get("reasoning", ""),
            metadata=execution_plan.metadata
        )
        
        return decomposition_result
    
    async def get_nlp_insights(self, request: ExecutionRequest) -> Dict[str, Any]:
        """Get NLP insights for a request without full decomposition"""
        logger.info(f"Getting NLP insights for request: {request.request_id}")
        
        try:
            # Get intent analysis
            intent = await self.universal_decomposer.intent_learner.learn_intent(
                request.description, []
            )
            
            # Get requirements analysis
            requirements = await self.universal_decomposer.requirement_extractor.extract(
                request.description, intent
            )
            
            # Find similar patterns
            similar_patterns = await self.universal_decomposer.pattern_memory.find_similar(
                request.description, intent
            )
            
            insights = {
                "intent_analysis": {
                    "primary_goal": intent.primary_goal,
                    "expected_output": intent.expected_output,
                    "complexity_level": intent.complexity_level,
                    "scope": intent.scope,
                    "confidence": intent.confidence
                },
                "requirements_summary": {
                    "functional_count": len(requirements.functional),
                    "non_functional_count": len(requirements.non_functional),
                    "constraints_count": len(requirements.constraints),
                    "risks_count": len(requirements.risks)
                },
                "similar_patterns": [
                    {
                        "confidence": pattern.pattern_confidence,
                        "success_rate": pattern.success_rate,
                        "abstraction_level": pattern.abstraction_level,
                        "usage_count": pattern.usage_count
                    }
                    for pattern in similar_patterns[:3]
                ],
                "complexity_assessment": {
                    "level": intent.complexity_level,
                    "estimated_tasks": self.estimate_task_count(intent, requirements),
                    "estimated_time": self.estimate_total_time(intent, requirements)
                },
                "recommendations": self.generate_recommendations(intent, requirements, similar_patterns)
            }
            
            return insights
            
        except Exception as e:
            logger.error(f"Failed to get NLP insights: {e}")
            return {
                "error": str(e),
                "fallback_insights": {
                    "intent_analysis": {"primary_goal": "Complete the requested task"},
                    "complexity_assessment": {"level": "unknown"}
                }
            }
    
    def estimate_task_count(self, intent: Intent, requirements: Requirements) -> int:
        """Estimate number of tasks based on intent and requirements"""
        base_count = 1
        
        # Add tasks based on complexity
        if intent.complexity_level == "trivial":
            base_count = 1
        elif intent.complexity_level == "simple":
            base_count = 2
        elif intent.complexity_level == "medium":
            base_count = 4
        elif intent.complexity_level == "complex":
            base_count = 8
        elif intent.complexity_level == "meta":
            base_count = 15
        
        # Add tasks based on requirements
        base_count += len(requirements.functional) // 2
        base_count += len(requirements.non_functional) // 3
        base_count += len(requirements.constraints) // 4
        
        return max(1, base_count)
    
    def estimate_total_time(self, intent: Intent, requirements: Requirements) -> int:
        """Estimate total execution time in minutes"""
        task_count = self.estimate_task_count(intent, requirements)
        
        # Base time per task based on complexity
        time_per_task = {
            "trivial": 15,
            "simple": 30,
            "medium": 60,
            "complex": 120,
            "meta": 240
        }
        
        base_time = time_per_task.get(intent.complexity_level, 60)
        return task_count * base_time
    
    def generate_recommendations(self, intent: Intent, requirements: Requirements, 
                               patterns: List) -> List[str]:
        """Generate recommendations based on NLP analysis"""
        recommendations = []
        
        # Complexity-based recommendations
        if intent.complexity_level == "complex" or intent.complexity_level == "meta":
            recommendations.append("Consider breaking this into smaller, more manageable requests")
            recommendations.append("Ensure thorough testing due to high complexity")
        
        # Confidence-based recommendations
        if intent.confidence < 0.6:
            recommendations.append("Request may benefit from more specific requirements")
            recommendations.append("Consider providing examples or clarifying expectations")
        
        # Pattern-based recommendations
        if not patterns:
            recommendations.append("This appears to be a novel request - extra validation recommended")
        elif all(p.success_rate < 0.7 for p in patterns):
            recommendations.append("Similar patterns have lower success rates - proceed with caution")
        
        # Requirements-based recommendations
        if len(requirements.risks) > 3:
            recommendations.append("High number of identified risks - consider risk mitigation strategies")
        
        if len(requirements.constraints) > 5:
            recommendations.append("Many constraints identified - ensure all are clearly communicated")
        
        return recommendations
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """Get statistics about the NLP system performance"""
        decomposer_stats = await self.universal_decomposer.get_decomposition_stats()
        
        return {
            "nlp_system": {
                "decomposer_stats": decomposer_stats,
                "execution_history": len(self.execution_history),
                "recent_success_rate": self.calculate_recent_success_rate(),
                "learning_status": "active"
            }
        }
    
    def calculate_recent_success_rate(self) -> float:
        """Calculate recent success rate from execution history"""
        if not self.execution_history:
            return 0.0
        
        # Look at last 20 executions
        recent_executions = self.execution_history[-20:]
        successful = sum(1 for exec in recent_executions if exec["execution_result"]["success"])
        
        return successful / len(recent_executions)


# Factory function for easy integration
def create_nlp_orchestrator(memory_client: VectorMemoryClient) -> NLPOrchestrator:
    """Create NLP orchestrator instance"""
    return NLPOrchestrator(memory_client)