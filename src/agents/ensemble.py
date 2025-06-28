"""
Ensemble Agent System for Production-Grade Code Generation
Implements multiple agent strategies with consensus mechanisms
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import asyncio
import json
from dataclasses import dataclass
from enum import Enum
# Using standard library instead of numpy for simplicity
# import numpy as np
from collections import defaultdict

import structlog
from pydantic import BaseModel, Field

from src.common.models import Task, TaskResult, AgentTier, TaskStatus
from src.agents.base_agents import Agent, T0Agent, T1Agent, T2Agent, T3Agent
from src.agents.agent_roles import AgentRole, SpecializedAgent
from src.memory.client import VectorMemoryClient
from src.validation.client import ValidationMeshClient
from src.sandbox.client import SandboxServiceClient
from src.common.config import settings
from src.agents.confidence_scorer import ConfidenceScorer
from src.agents.execution_validator import ExecutionValidator
from src.common.code_extractor import extract_code_from_markdown, clean_code_output

logger = structlog.get_logger()

# Import specialized agents when available
SPECIALIZED_AGENTS_AVAILABLE = False
try:
    from src.agents.specialized import (
        ProductionArchitectAgent,
        ProductionImplementerAgent,
        ProductionReviewerAgent,
        ProductionSecurityAgent,
        ProductionTestAgent,
        ProductionOptimizerAgent,
        ProductionDocumentorAgent,
        create_specialized_agent
    )
    SPECIALIZED_AGENTS_AVAILABLE = True
except ImportError:
    logger.warning("Specialized agents not available, using base agents")


class VotingStrategy(str, Enum):
    """Ensemble voting strategies"""
    MAJORITY = "majority"
    WEIGHTED = "weighted"
    CONFIDENCE_BASED = "confidence_based"
    QUALITY_WEIGHTED = "quality_weighted"
    ADAPTIVE = "adaptive"




@dataclass
class AgentContribution:
    """Individual agent's contribution to ensemble"""
    agent_id: str
    role: AgentRole
    output: Dict[str, Any]
    confidence: float
    execution_time: float
    validation_score: float
    metadata: Dict[str, Any]


class EnsembleConfiguration(BaseModel):
    """Configuration for ensemble execution"""
    min_agents: int = Field(default=3, ge=1)
    max_agents: int = Field(default=7, le=10)
    voting_strategy: VotingStrategy = VotingStrategy.ADAPTIVE
    consensus_threshold: float = Field(default=0.7, ge=0.5, le=1.0)
    diversity_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    parallel_execution: bool = True
    adaptive_selection: bool = True
    cross_validation: bool = True




class ArchitectAgent(SpecializedAgent):
    """Agent specialized in system architecture and design"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id, AgentRole.ARCHITECT, AgentTier.T2)
    
    async def execute(self, task: Task, context: Dict[str, Any]) -> TaskResult:
        """Design the architecture for the task"""
        logger.info(f"Architect agent designing solution", task_id=task.id)
        
        # This would use advanced prompting to create architectural designs
        # Including design patterns, component breakdown, API contracts, etc.
        # For now, simplified implementation
        
        return await super().execute(task, context)


class EnsembleOrchestrator:
    """Orchestrates ensemble agent execution"""
    
    def __init__(self, config: EnsembleConfiguration):
        self.config = config
        self.memory_client = VectorMemoryClient(settings.VECTOR_MEMORY_URL)
        self.validation_client = ValidationMeshClient(
            f"http://localhost:{settings.VALIDATION_MESH_PORT}"
        )
        self.sandbox_client = SandboxServiceClient(
            f"http://localhost:{settings.SANDBOX_PORT}"
        )
        self.performance_history = defaultdict(list)
        self.confidence_scorer = ConfidenceScorer()
        self.execution_validator = ExecutionValidator(self.sandbox_client)
    
    async def execute_ensemble(
        self, 
        task: Task, 
        context: Dict[str, Any]
    ) -> TaskResult:
        """Execute task using ensemble of agents"""
        logger.info(
            f"Starting ensemble execution",
            task_id=task.id,
            strategy=self.config.voting_strategy
        )
        
        start_time = datetime.utcnow()
        
        try:
            # 1. Select optimal agent composition
            agent_composition = await self._select_agents(task, context)
            
            # 2. Execute with all agents (parallel or sequential)
            contributions = await self._execute_agents(
                agent_composition, 
                task, 
                context
            )
            
            # 3. Cross-validate contributions
            if self.config.cross_validation:
                contributions = await self._cross_validate(contributions, task)
            
            # 4. Synthesize results using voting strategy
            final_output = await self._synthesize_results(
                contributions, 
                task,
                self.config.voting_strategy
            )
            
            # 5. Final validation
            validation_result = await self._validate_final_output(
                final_output, 
                task
            )
            
            # 6. Learn from execution
            await self._update_performance_metrics(
                contributions, 
                validation_result
            )
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                output_type="ensemble_result",
                output=final_output,
                execution_time=execution_time,
                agent_tier_used=AgentTier.T3,  # Ensemble is T3-level
                confidence_score=validation_result["confidence"],
                metadata={
                    "ensemble_size": len(contributions),
                    "voting_strategy": self.config.voting_strategy,
                    "validation_score": validation_result["score"],
                    "contributions": [
                        {
                            "agent_id": c.agent_id,
                            "role": c.role,
                            "confidence": c.confidence
                        }
                        for c in contributions
                    ]
                }
            )
            
        except Exception as e:
            logger.error(f"Ensemble execution failed", error=str(e))
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                output_type="error",
                output={"error": str(e)},
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
                agent_tier_used=AgentTier.T3,
                confidence_score=0.0,
                metadata={"ensemble_error": True}
            )
    
    async def _select_agents(
        self, 
        task: Task, 
        context: Dict[str, Any]
    ) -> List[Tuple[AgentRole, AgentTier]]:
        """Select optimal agent composition for task"""
        
        if not self.config.adaptive_selection:
            # Default composition
            return [
                (AgentRole.ARCHITECT, AgentTier.T2),
                (AgentRole.IMPLEMENTER, AgentTier.T1),
                (AgentRole.REVIEWER, AgentTier.T2),
                (AgentRole.TEST_ENGINEER, AgentTier.T1),
                (AgentRole.SECURITY_EXPERT, AgentTier.T1)
            ]
        
        # Adaptive selection based on task analysis
        composition = []
        
        # Always include architect for complex tasks
        if task.complexity in ["complex", "meta"]:
            composition.append((AgentRole.ARCHITECT, AgentTier.T2))
        
        # Always include implementer
        composition.append((AgentRole.IMPLEMENTER, AgentTier.T1))
        
        # Add reviewer for quality
        composition.append((AgentRole.REVIEWER, AgentTier.T2))
        
        # Add based on task description analysis
        task_lower = task.description.lower()
        
        if any(word in task_lower for word in ["api", "web", "security", "auth"]):
            composition.append((AgentRole.SECURITY_EXPERT, AgentTier.T1))
        
        if any(word in task_lower for word in ["test", "quality", "reliable"]):
            composition.append((AgentRole.TEST_ENGINEER, AgentTier.T1))
        
        if any(word in task_lower for word in ["performance", "optimize", "scale"]):
            composition.append((AgentRole.OPTIMIZER, AgentTier.T2))
        
        if len(composition) < self.config.min_agents:
            # Add more agents to meet minimum
            remaining_roles = [
                (AgentRole.DOCUMENTOR, AgentTier.T0),
                (AgentRole.OPTIMIZER, AgentTier.T1),
                (AgentRole.SECURITY_EXPERT, AgentTier.T1)
            ]
            for role, tier in remaining_roles:
                if len(composition) >= self.config.min_agents:
                    break
                if not any(r == role for r, _ in composition):
                    composition.append((role, tier))
        
        # Limit to max agents
        return composition[:self.config.max_agents]
    
    async def _execute_agents(
        self,
        agent_composition: List[Tuple[AgentRole, AgentTier]],
        task: Task,
        context: Dict[str, Any]
    ) -> List[AgentContribution]:
        """Execute task with multiple agents"""
        
        contributions = []
        
        if self.config.parallel_execution:
            # Execute all agents in parallel
            tasks = []
            for role, tier in agent_composition:
                agent_task = self._create_specialized_agent(role, tier)
                tasks.append(
                    self._execute_single_agent(agent_task, task, context, role)
                )
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(
                        f"Agent execution failed",
                        role=agent_composition[i][0],
                        error=str(result)
                    )
                else:
                    contributions.append(result)
        else:
            # Sequential execution with context passing
            accumulated_context = context.copy()
            
            for role, tier in agent_composition:
                agent = self._create_specialized_agent(role, tier)
                contribution = await self._execute_single_agent(
                    agent, 
                    task, 
                    accumulated_context, 
                    role
                )
                contributions.append(contribution)
                
                # Update context with previous results
                accumulated_context[f"{role}_output"] = contribution.output
        
        return contributions
    
    def _create_specialized_agent(
        self, 
        role: AgentRole, 
        tier: AgentTier
    ) -> Agent:
        """Create a specialized agent instance"""
        from uuid import uuid4
        agent_id = str(uuid4())
        
        # Use specialized agents if available
        if SPECIALIZED_AGENTS_AVAILABLE:
            try:
                return create_specialized_agent(role, agent_id)
            except ValueError:
                # Role not supported by specialized agents
                pass
        
        # Fallback to tier-based agents
        if tier == AgentTier.T0:
            return T0Agent(agent_id)
        elif tier == AgentTier.T1:
            return T1Agent(agent_id)
        elif tier == AgentTier.T2:
            return T2Agent(agent_id)
        else:
            return T3Agent(agent_id)
    
    async def _execute_single_agent(
        self,
        agent: Agent,
        task: Task,
        context: Dict[str, Any],
        role: AgentRole
    ) -> AgentContribution:
        """Execute task with a single agent"""
        start_time = datetime.utcnow()
        
        # Add role-specific context
        role_context = context.copy()
        role_context["agent_role"] = role
        role_context["specialization"] = SpecializedAgent(
            agent.agent_id, 
            role, 
            agent.tier
        ).specialization_prompts.get(role, "")
        
        # Execute
        result = await agent.execute(task, role_context)
        
        # Basic validation
        validation_score = 1.0 if result.status == TaskStatus.COMPLETED else 0.0
        
        return AgentContribution(
            agent_id=agent.agent_id,
            role=role,
            output=result.output if isinstance(result.output, dict) else {"content": result.output},
            confidence=result.confidence_score,
            execution_time=result.execution_time,
            validation_score=validation_score,
            metadata=result.metadata
        )
    
    async def _cross_validate(
        self, 
        contributions: List[AgentContribution],
        task: Task
    ) -> List[AgentContribution]:
        """Cross-validate agent contributions"""
        
        # Have each reviewer agent validate other contributions
        reviewer_contributions = [
            c for c in contributions 
            if c.role == AgentRole.REVIEWER
        ]
        
        if not reviewer_contributions:
            return contributions
        
        # For each non-reviewer contribution, get validation
        validated_contributions = []
        
        for contribution in contributions:
            if contribution.role == AgentRole.REVIEWER:
                validated_contributions.append(contribution)
                continue
            
            # Validate with reviewers
            validation_scores = []
            
            for reviewer in reviewer_contributions:
                # This would use the reviewer to validate
                # For now, simulate with confidence-based scoring
                # Simple scoring without numpy
                import random
                score = contribution.confidence * 0.8 + random.uniform(0.1, 0.2)
                validation_scores.append(min(score, 1.0))
            
            # Update validation score
            contribution.validation_score = sum(validation_scores) / len(validation_scores) if validation_scores else 0
            validated_contributions.append(contribution)
        
        return validated_contributions
    
    async def _synthesize_results(
        self,
        contributions: List[AgentContribution],
        task: Task,
        strategy: VotingStrategy
    ) -> Dict[str, Any]:
        """Synthesize results from multiple agents"""
        
        if strategy == VotingStrategy.MAJORITY:
            return self._majority_voting(contributions)
        elif strategy == VotingStrategy.WEIGHTED:
            return self._weighted_voting(contributions)
        elif strategy == VotingStrategy.CONFIDENCE_BASED:
            return self._confidence_based_synthesis(contributions)
        elif strategy == VotingStrategy.QUALITY_WEIGHTED:
            return self._quality_weighted_synthesis(contributions)
        elif strategy == VotingStrategy.ADAPTIVE:
            return await self._adaptive_synthesis(contributions, task)
        else:
            return self._majority_voting(contributions)
    
    def _majority_voting(
        self, 
        contributions: List[AgentContribution]
    ) -> Dict[str, Any]:
        """Simple majority voting on outputs"""
        # Group similar outputs and pick the most common
        # This is simplified - real implementation would use semantic similarity
        
        if not contributions:
            return {"error": "No contributions to synthesize"}
        
        # For now, pick the highest confidence contribution
        best_contribution = max(contributions, key=lambda c: c.confidence)
        
        return {
            "code": best_contribution.output.get("content", ""),
            "synthesis_method": "majority_voting",
            "selected_agent": best_contribution.agent_id,
            "confidence": best_contribution.confidence
        }
    
    def _weighted_voting(
        self, 
        contributions: List[AgentContribution]
    ) -> Dict[str, Any]:
        """Weighted voting based on agent roles"""
        role_weights = {
            AgentRole.ARCHITECT: 1.5,
            AgentRole.IMPLEMENTER: 1.3,
            AgentRole.REVIEWER: 1.2,
            AgentRole.OPTIMIZER: 1.1,
            AgentRole.SECURITY_EXPERT: 1.2,
            AgentRole.TEST_ENGINEER: 1.0,
            AgentRole.DOCUMENTOR: 0.8
        }
        
        # Calculate weighted scores
        weighted_contributions = []
        for c in contributions:
            weight = role_weights.get(c.role, 1.0)
            score = c.confidence * c.validation_score * weight
            weighted_contributions.append((score, c))
        
        # Sort by score and synthesize top contributions
        weighted_contributions.sort(key=lambda x: x[0], reverse=True)
        
        # Combine top contributions
        top_n = min(3, len(weighted_contributions))
        synthesized = {
            "code": "",
            "tests": "",
            "documentation": "",
            "synthesis_method": "weighted_voting",
            "contributors": []
        }
        
        for score, contribution in weighted_contributions[:top_n]:
            output = contribution.output
            
            if contribution.role == AgentRole.IMPLEMENTER:
                raw_code = output.get("content", output.get("code", ""))
                synthesized["code"] = extract_code_from_markdown(raw_code)
            elif contribution.role == AgentRole.TEST_ENGINEER:
                raw_tests = output.get("content", output.get("tests", ""))
                synthesized["tests"] = extract_code_from_markdown(raw_tests)
            elif contribution.role == AgentRole.DOCUMENTOR:
                synthesized["documentation"] = output.get("content", output.get("documentation", ""))
            
            synthesized["contributors"].append({
                "agent_id": contribution.agent_id,
                "role": contribution.role,
                "score": score
            })
        
        # Ensure we have at least the code
        if not synthesized["code"] and contributions:
            raw_code = contributions[0].output.get("content", "")
            synthesized["code"] = extract_code_from_markdown(raw_code)
        
        return synthesized
    
    def _confidence_based_synthesis(
        self, 
        contributions: List[AgentContribution]
    ) -> Dict[str, Any]:
        """Synthesize based on confidence scores"""
        # Sort by confidence
        sorted_contributions = sorted(
            contributions, 
            key=lambda c: c.confidence * c.validation_score,
            reverse=True
        )
        
        if not sorted_contributions:
            return {"error": "No contributions to synthesize"}
        
        # Use highest confidence as base
        base = sorted_contributions[0]
        raw_code = base.output.get("content", base.output.get("code", ""))
        synthesized = {
            "code": extract_code_from_markdown(raw_code),
            "confidence": base.confidence,
            "synthesis_method": "confidence_based",
            "base_agent": base.agent_id,
            "enhancements": []
        }
        
        # Add enhancements from other high-confidence contributions
        for contribution in sorted_contributions[1:]:
            if contribution.confidence > self.config.consensus_threshold:
                if contribution.role == AgentRole.TEST_ENGINEER:
                    synthesized["tests"] = contribution.output.get("content", "")
                elif contribution.role == AgentRole.SECURITY_EXPERT:
                    synthesized["security_notes"] = contribution.output.get("content", "")
                
                synthesized["enhancements"].append({
                    "agent_id": contribution.agent_id,
                    "role": contribution.role,
                    "confidence": contribution.confidence
                })
        
        return synthesized
    
    def _quality_weighted_synthesis(
        self, 
        contributions: List[AgentContribution]
    ) -> Dict[str, Any]:
        """Synthesize based on quality metrics"""
        # Calculate quality score for each contribution
        quality_scores = []
        
        for contribution in contributions:
            # Quality factors
            has_code = bool(contribution.output.get("code") or contribution.output.get("content"))
            has_tests = bool(contribution.output.get("tests"))
            has_docs = bool(contribution.output.get("documentation"))
            
            quality_score = (
                contribution.confidence * 0.3 +
                contribution.validation_score * 0.3 +
                (1.0 if has_code else 0.0) * 0.2 +
                (1.0 if has_tests else 0.0) * 0.1 +
                (1.0 if has_docs else 0.0) * 0.1
            )
            
            quality_scores.append((quality_score, contribution))
        
        # Sort by quality
        quality_scores.sort(key=lambda x: x[0], reverse=True)
        
        # Build synthesized result from highest quality contributions
        synthesized = {
            "synthesis_method": "quality_weighted",
            "quality_scores": []
        }
        
        for score, contribution in quality_scores:
            output = contribution.output
            
            # Take the best of each component
            if not synthesized.get("code") and (output.get("code") or output.get("content")):
                raw_code = output.get("code", output.get("content", ""))
                synthesized["code"] = extract_code_from_markdown(raw_code)
                synthesized["code_contributor"] = contribution.agent_id
            
            if not synthesized.get("tests") and output.get("tests"):
                synthesized["tests"] = output["tests"]
                synthesized["tests_contributor"] = contribution.agent_id
            
            if not synthesized.get("documentation") and output.get("documentation"):
                synthesized["documentation"] = output["documentation"]
                synthesized["docs_contributor"] = contribution.agent_id
            
            synthesized["quality_scores"].append({
                "agent_id": contribution.agent_id,
                "role": contribution.role,
                "score": score
            })
        
        return synthesized
    
    async def _adaptive_synthesis(
        self,
        contributions: List[AgentContribution],
        task: Task
    ) -> Dict[str, Any]:
        """Adaptive synthesis based on task characteristics"""
        
        # Analyze task to determine best synthesis approach
        task_lower = task.description.lower()
        
        # Choose strategy based on task
        if task.complexity == "meta":
            # For complex tasks, use quality-weighted
            return self._quality_weighted_synthesis(contributions)
        elif any(word in task_lower for word in ["critical", "security", "production"]):
            # For critical tasks, use confidence-based with high threshold
            old_threshold = self.config.consensus_threshold
            self.config.consensus_threshold = 0.8
            result = self._confidence_based_synthesis(contributions)
            self.config.consensus_threshold = old_threshold
            return result
        elif task.complexity == "trivial":
            # For simple tasks, use majority voting
            return self._majority_voting(contributions)
        else:
            # Default to weighted voting
            return self._weighted_voting(contributions)
    
    async def _validate_final_output(
        self,
        output: Dict[str, Any],
        task: Task
    ) -> Dict[str, Any]:
        """Validate the final synthesized output"""
        
        code = output.get("code", "")
        tests = output.get("tests", "")
        
        if not code:
            return {"score": 0.0, "confidence": 0.0, "issues": ["No code generated"]}
        
        # Calculate confidence using the new scorer
        confidence = self.confidence_scorer.calculate_confidence({
            "code": code,
            "tests": tests,
            "security_analysis": output.get("security_analysis", {}),
            "review": output.get("review", {})
        })
        
        # Validate with execution validator
        validation_results = await self.execution_validator.validate_code(code, tests)
        
        # Adjust confidence based on validation
        final_confidence = min(0.99, confidence + validation_results["confidence_boost"])
        
        # Determine language
        language = "python" if "def " in code or "import " in code else "javascript"
        
        try:
            # Use validation mesh for additional checks
            validation_result = await self.validation_client.validate_code(
                code=code,
                language=language
            )
            
            # Calculate overall score
            if validation_result["overall_status"] == "passed":
                score = 1.0
            elif validation_result["overall_status"] == "passed_with_warnings":
                score = 0.8
            else:
                score = 0.5
            
            # Combine all validation results
            return {
                "score": score,
                "confidence": final_confidence,
                "validation_result": validation_result,
                "execution_validation": validation_results,
                "issues": validation_results.get("issues", [])
            }
            
        except Exception as e:
            logger.error(f"Validation failed", error=str(e))
            # Still return execution validation results
            return {
                "score": 0.5,
                "confidence": final_confidence,
                "execution_validation": validation_results,
                "issues": [str(e)] + validation_results.get("issues", [])
            }
    
    async def _update_performance_metrics(
        self,
        contributions: List[AgentContribution],
        validation_result: Dict[str, Any]
    ):
        """Update performance metrics for adaptive learning"""
        
        for contribution in contributions:
            # Store performance data
            performance_data = {
                "agent_id": contribution.agent_id,
                "role": contribution.role,
                "confidence": contribution.confidence,
                "validation_score": contribution.validation_score,
                "final_score": validation_result["score"],
                "execution_time": contribution.execution_time,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Update history
            self.performance_history[contribution.role].append(performance_data)
            
            # Store in vector memory for learning
            try:
                await self.memory_client.store_execution_pattern({
                    "type": "ensemble_performance",
                    "content": performance_data,  # Send dict, not JSON string
                    "metadata": {
                        "role": contribution.role,
                        "score": validation_result["score"]
                    }
                })
            except Exception as e:
                logger.error(f"Failed to store performance metrics", error=str(e))


class ProductionCodeGenerator:
    """High-level interface for production-grade code generation"""
    
    def __init__(self):
        self.ensemble_config = EnsembleConfiguration(
            min_agents=4,
            max_agents=7,
            voting_strategy=VotingStrategy.ADAPTIVE,
            consensus_threshold=0.75,
            diversity_weight=0.3,
            parallel_execution=True,
            adaptive_selection=True,
            cross_validation=True
        )
        self.orchestrator = EnsembleOrchestrator(self.ensemble_config)
    
    async def generate_production_code(
        self,
        description: str,
        requirements: Optional[Dict[str, Any]] = None,
        constraints: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate production-grade code with ensemble agents"""
        
        # Create task from description
        task = Task(
            id=f"prod-{datetime.utcnow().timestamp()}",
            type="production_code_generation",
            description=description,
            complexity=self._assess_complexity(description),
            metadata={
                "requirements": requirements or {},
                "constraints": constraints or {},
                "production_grade": True
            }
        )
        
        # Prepare context
        context = {
            "requirements": requirements or {},
            "constraints": constraints or {},
            "quality_standards": {
                "testing": "comprehensive",
                "documentation": "detailed",
                "security": "production-grade",
                "performance": "optimized"
            }
        }
        
        # Execute with ensemble
        result = await self.orchestrator.execute_ensemble(task, context)
        
        if result.status == TaskStatus.COMPLETED:
            output = result.output
            
            # Ensure all components are present
            return {
                "status": "success",
                "code": output.get("code", ""),
                "tests": output.get("tests", ""),
                "documentation": output.get("documentation", ""),
                "security_analysis": output.get("security_notes", ""),
                "performance_notes": output.get("performance_notes", ""),
                "deployment_guide": output.get("deployment_guide", ""),
                "confidence": result.confidence_score,
                "metadata": {
                    "task_id": task.id,
                    "ensemble_size": result.metadata.get("ensemble_size", 0),
                    "voting_strategy": result.metadata.get("voting_strategy", ""),
                    "contributors": result.metadata.get("contributions", [])
                }
            }
        else:
            return {
                "status": "failed",
                "error": result.output.get("error", "Unknown error"),
                "metadata": result.metadata
            }
    
    def _assess_complexity(self, description: str) -> str:
        """Assess task complexity from description"""
        desc_lower = description.lower()
        
        # Complexity indicators
        complex_indicators = [
            "distributed", "microservice", "scale", "concurrent",
            "real-time", "machine learning", "ai", "blockchain",
            "security", "encryption", "optimization"
        ]
        
        simple_indicators = [
            "simple", "basic", "hello world", "example",
            "demo", "prototype", "test"
        ]
        
        complex_count = sum(1 for ind in complex_indicators if ind in desc_lower)
        simple_count = sum(1 for ind in simple_indicators if ind in desc_lower)
        
        if complex_count >= 3 or len(description) > 500:
            return "meta"
        elif complex_count >= 2:
            return "complex"
        elif simple_count >= 2:
            return "trivial"
        elif complex_count >= 1:
            return "medium"
        else:
            return "simple"


# Export main interface
__all__ = ["ProductionCodeGenerator", "EnsembleOrchestrator", "EnsembleConfiguration"]
