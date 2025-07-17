"""
Unified Optimization Engine - Integrates Meta-Prompts with Pattern Selection
Provides unified optimization strategy for both reasoning patterns and prompt evolution
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import json
import structlog
from datetime import datetime

from src.agents.meta_prompts.meta_engineer import MetaPromptEngineer, PromptEvolutionStrategy
from src.nlp.pattern_selection_engine_fixed import FixedPatternSelectionEngine as PatternSelectionEngine
from src.nlp.pattern_selection_engine import PatternType, RequestCharacteristics
from src.common.models import ExecutionRequest, Task, TaskResult
from src.common.config import settings

logger = structlog.get_logger()


@dataclass
class UnifiedOptimizationResult:
    """Result of unified pattern selection and meta-prompt optimization"""
    selected_patterns: List[PatternType]
    pattern_confidence: float
    evolved_meta_prompt: str
    evolution_strategy: PromptEvolutionStrategy
    optimization_reasoning: str
    computational_cost: float
    expected_performance: float
    optimization_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OptimizationContext:
    """Context for optimization decisions"""
    request_characteristics: RequestCharacteristics
    task_complexity: str
    agent_tier: str
    previous_performance: Optional[Dict[str, Any]] = None
    budget_constraints: Optional[Dict[str, float]] = None
    time_constraints: Optional[Dict[str, Any]] = None


class UnifiedOptimizationEngine:
    """
    Unified engine that combines pattern selection with meta-prompt evolution
    for optimal task decomposition and agent performance
    """
    
    def __init__(self):
        self.pattern_selector = PatternSelectionEngine()
        self.meta_prompt_engineer = MetaPromptEngineer()
        self.optimization_history = []
        self.performance_metrics = {}
        self.learning_feedback = {}
        
        # Optimization strategy mapping
        self.strategy_mapping = self._initialize_strategy_mapping()
        
        logger.info("Unified Optimization Engine initialized")
    
    def _initialize_strategy_mapping(self) -> Dict[PatternType, PromptEvolutionStrategy]:
        """Map reasoning patterns to optimal prompt evolution strategies"""
        return {
            PatternType.ABSTRACTION: PromptEvolutionStrategy.EXPLANATION_DEPTH,
            PatternType.EMERGENT_PATTERNS: PromptEvolutionStrategy.PRINCIPLE_EXTRACTION,
            PatternType.META_LEARNING: PromptEvolutionStrategy.CREATIVE_DESTRUCTION,
            PatternType.UNCERTAINTY: PromptEvolutionStrategy.ERROR_CORRECTION,
            PatternType.CONSTRAINT: PromptEvolutionStrategy.CONTRARIAN,
            PatternType.SEMANTIC: PromptEvolutionStrategy.SYNTHESIS,
            PatternType.DIALECTICAL: PromptEvolutionStrategy.CONJECTURE_REFUTATION,
            PatternType.QUANTUM: PromptEvolutionStrategy.CREATIVE_DESTRUCTION
        }
    
    async def optimize_for_task(
        self,
        request: ExecutionRequest,
        task: Task,
        context: OptimizationContext
    ) -> UnifiedOptimizationResult:
        """
        Perform unified optimization for a specific task
        Combines pattern selection with meta-prompt evolution
        """
        logger.info(f"Optimizing task: {task.id} with unified approach")
        
        # Step 1: Analyze request characteristics
        characteristics = await self.pattern_selector.analyze_request_characteristics(
            request.description,
            {"task_type": task.type, "complexity": task.complexity, **context.request_characteristics.__dict__}
        )
        
        # Step 2: Get pattern recommendations
        pattern_recommendations = await self.pattern_selector.recommend_patterns(
            characteristics,
            max_patterns=3,  # Limit for efficiency
            budget_constraint=context.budget_constraints.get("computational", 2.5) if context.budget_constraints else 2.5
        )
        
        # Step 3: Select optimal patterns
        selected_patterns = [rec.pattern for rec in pattern_recommendations[:3]]
        # Avoid division by zero if no patterns recommended
        if pattern_recommendations:
            pattern_confidence = sum(rec.confidence for rec in pattern_recommendations[:3]) / min(len(pattern_recommendations), 3)
        else:
            pattern_confidence = 0.0
        
        # Step 4: Determine optimal evolution strategy
        evolution_strategy = self._select_evolution_strategy(selected_patterns, characteristics)
        
        # Step 5: Generate evolved meta-prompt
        evolved_meta_prompt = await self.meta_prompt_engineer.generate_meta_prompt(
            task_description=f"{request.description} -> {task.description}",
            agent_role=f"{context.agent_tier}_agent",
            context={
                "selected_patterns": [p.value for p in selected_patterns],
                "task_complexity": task.complexity,
                "request_characteristics": characteristics.__dict__,
                "optimization_context": context.__dict__
            },
            evolution_strategy=evolution_strategy
        )
        
        # Step 6: Calculate optimization metrics
        computational_cost = sum(rec.computational_cost for rec in pattern_recommendations[:3]) if pattern_recommendations else 1.0
        expected_performance = self._calculate_expected_performance(
            selected_patterns, evolution_strategy, characteristics
        )
        
        # Step 7: Generate optimization reasoning
        optimization_reasoning = self._generate_optimization_reasoning(
            selected_patterns, evolution_strategy, pattern_recommendations, characteristics
        )
        
        # Step 8: Create unified result
        result = UnifiedOptimizationResult(
            selected_patterns=selected_patterns,
            pattern_confidence=pattern_confidence,
            evolved_meta_prompt=evolved_meta_prompt,
            evolution_strategy=evolution_strategy,
            optimization_reasoning=optimization_reasoning,
            computational_cost=computational_cost,
            expected_performance=expected_performance,
            optimization_metadata={
                "pattern_recommendations": [
                    {
                        "pattern": rec.pattern.value,
                        "confidence": rec.confidence,
                        "reasoning": rec.reasoning,
                        "priority": rec.priority
                    }
                    for rec in pattern_recommendations
                ],
                "characteristics": characteristics.__dict__,
                "optimization_timestamp": datetime.utcnow().isoformat(),
                "task_id": task.id,
                "request_id": request.id
            }
        )
        
        # Step 9: Store optimization decision
        self._record_optimization_decision(result, context)
        
        return result
    
    def _select_evolution_strategy(
        self,
        selected_patterns: List[PatternType],
        characteristics: RequestCharacteristics
    ) -> PromptEvolutionStrategy:
        """Select optimal evolution strategy based on patterns and characteristics"""
        
        # Get base strategy from primary pattern
        primary_pattern = selected_patterns[0] if selected_patterns else PatternType.ABSTRACTION
        base_strategy = self.strategy_mapping.get(primary_pattern, PromptEvolutionStrategy.EXPLANATION_DEPTH)
        
        # Adjust based on characteristics
        if characteristics.ambiguity_level > 0.7:
            return PromptEvolutionStrategy.ERROR_CORRECTION
        elif characteristics.conflicting_requirements:
            return PromptEvolutionStrategy.DIALECTICAL
        elif characteristics.learning_opportunity:
            return PromptEvolutionStrategy.PRINCIPLE_EXTRACTION
        elif characteristics.complexity_level in ["complex", "critical"]:
            return PromptEvolutionStrategy.EXPLANATION_DEPTH
        else:
            return base_strategy
    
    def _calculate_expected_performance(
        self,
        selected_patterns: List[PatternType],
        evolution_strategy: PromptEvolutionStrategy,
        characteristics: RequestCharacteristics
    ) -> float:
        """Calculate expected performance based on optimization decisions"""
        
        # Base performance from pattern selection
        pattern_performance = 0.7  # Base score
        
        # Adjust for pattern fitness
        if len(selected_patterns) <= 3:  # Optimal number
            pattern_performance += 0.1
        
        # Adjust for evolution strategy alignment
        strategy_bonus = 0.05 if evolution_strategy in [
            PromptEvolutionStrategy.EXPLANATION_DEPTH,
            PromptEvolutionStrategy.PRINCIPLE_EXTRACTION
        ] else 0.0
        
        # Adjust for characteristics
        complexity_factor = {
            "trivial": 0.9,
            "simple": 0.85,
            "medium": 0.8,
            "complex": 0.75,
            "critical": 0.7
        }.get(characteristics.complexity_level, 0.8)
        
        return min(1.0, (pattern_performance + strategy_bonus) * complexity_factor)
    
    def _generate_optimization_reasoning(
        self,
        selected_patterns: List[PatternType],
        evolution_strategy: PromptEvolutionStrategy,
        pattern_recommendations: List,
        characteristics: RequestCharacteristics
    ) -> str:
        """Generate human-readable reasoning for optimization decisions"""
        
        pattern_names = [p.value for p in selected_patterns]
        
        # Handle empty patterns case
        if not selected_patterns or not pattern_recommendations:
            reasoning = f"""
Unified Optimization Decision:

Selected Patterns: Default (Abstraction)
- No specific patterns matched, using default abstraction pattern
- Pattern selection based on: {characteristics.complexity_level} complexity, {characteristics.domain} domain
- Computational cost: 1.0 units

Evolution Strategy: {evolution_strategy.value}
- Chosen for {characteristics.complexity_level} complexity tasks
- Optimized for {"high" if characteristics.ambiguity_level > 0.7 else "low"} ambiguity
- {"Conflict resolution" if characteristics.conflicting_requirements else "Standard approach"} mode

Expected Benefits:
- Improved task decomposition quality
- Optimized prompt evolution for agent tier
- Reduced computational overhead through targeted pattern usage
- Enhanced learning from execution feedback"""
        else:
            reasoning = f"""
Unified Optimization Decision:

Selected Patterns: {', '.join(pattern_names)}
- Primary pattern: {selected_patterns[0].value} (confidence: {pattern_recommendations[0].confidence:.2f})
- Pattern selection based on: {characteristics.complexity_level} complexity, {characteristics.domain} domain
- Computational cost: {sum(rec.computational_cost for rec in pattern_recommendations[:3]):.2f} units

Evolution Strategy: {evolution_strategy.value}
- Chosen for {characteristics.complexity_level} complexity tasks
- Optimized for {"high" if characteristics.ambiguity_level > 0.7 else "low"} ambiguity
- {"Conflict resolution" if characteristics.conflicting_requirements else "Standard approach"} mode

Expected Benefits:
- Improved task decomposition quality
- Optimized prompt evolution for agent tier
- Reduced computational overhead through targeted pattern usage
- Enhanced learning from execution feedback
"""
        
        return reasoning.strip()
    
    def _record_optimization_decision(
        self,
        result: UnifiedOptimizationResult,
        context: OptimizationContext
    ):
        """Record optimization decision for learning and analysis"""
        
        decision_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "selected_patterns": [p.value for p in result.selected_patterns],
            "evolution_strategy": result.evolution_strategy.value,
            "pattern_confidence": result.pattern_confidence,
            "computational_cost": result.computational_cost,
            "expected_performance": result.expected_performance,
            "context": {
                "complexity": context.task_complexity,
                "agent_tier": context.agent_tier,
                "characteristics": context.request_characteristics.__dict__
            }
        }
        
        self.optimization_history.append(decision_record)
        
        # Keep only last 1000 decisions
        if len(self.optimization_history) > 1000:
            self.optimization_history = self.optimization_history[-1000:]
    
    async def learn_from_execution(
        self,
        optimization_result: UnifiedOptimizationResult,
        execution_result: TaskResult
    ):
        """Learn from execution results to improve future optimization"""
        
        # Update pattern performance metrics
        for pattern in optimization_result.selected_patterns:
            if pattern.value not in self.performance_metrics:
                self.performance_metrics[pattern.value] = {"successes": 0, "failures": 0, "total": 0}
            
            self.performance_metrics[pattern.value]["total"] += 1
            if execution_result.status.value == "completed" and execution_result.confidence_score > 0.7:
                self.performance_metrics[pattern.value]["successes"] += 1
            else:
                self.performance_metrics[pattern.value]["failures"] += 1
        
        # Update evolution strategy performance
        strategy_key = optimization_result.evolution_strategy.value
        if strategy_key not in self.performance_metrics:
            self.performance_metrics[strategy_key] = {"successes": 0, "failures": 0, "total": 0}
        
        self.performance_metrics[strategy_key]["total"] += 1
        if execution_result.status.value == "completed" and execution_result.confidence_score > 0.7:
            self.performance_metrics[strategy_key]["successes"] += 1
        else:
            self.performance_metrics[strategy_key]["failures"] += 1
        
        # Store learning feedback
        if optimization_result.selected_patterns:
            feedback_key = f"{optimization_result.selected_patterns[0].value}_{optimization_result.evolution_strategy.value}"
        else:
            feedback_key = f"default_{optimization_result.evolution_strategy.value}"
        
        if feedback_key not in self.learning_feedback:
            self.learning_feedback[feedback_key] = []
        
        self.learning_feedback[feedback_key].append({
            "timestamp": datetime.utcnow().isoformat(),
            "execution_time": execution_result.execution_time,
            "confidence_score": execution_result.confidence_score,
            "success": execution_result.status.value == "completed",
            "computational_cost": optimization_result.computational_cost,
            "expected_performance": optimization_result.expected_performance,
            "actual_performance": execution_result.confidence_score
        })
        
        logger.info(f"Learning feedback recorded for {feedback_key}")
    
    async def get_optimization_insights(self) -> Dict[str, Any]:
        """Get insights about optimization performance and patterns"""
        
        insights = {
            "total_optimizations": len(self.optimization_history),
            "pattern_performance": {},
            "evolution_strategy_performance": {},
            "optimization_trends": {},
            "recommendations": []
        }
        
        # Calculate pattern success rates
        for pattern, metrics in self.performance_metrics.items():
            if metrics["total"] > 0:
                success_rate = metrics["successes"] / metrics["total"]
                insights["pattern_performance"][pattern] = {
                    "success_rate": success_rate,
                    "total_usage": metrics["total"],
                    "performance_grade": "A" if success_rate > 0.8 else "B" if success_rate > 0.6 else "C"
                }
        
        # Generate recommendations
        if insights["pattern_performance"]:
            best_pattern = max(insights["pattern_performance"].items(), key=lambda x: x[1]["success_rate"])
            insights["recommendations"].append(f"Consider using {best_pattern[0]} more often (success rate: {best_pattern[1]['success_rate']:.2f})")
        
        return insights
    
    def reset_learning_data(self):
        """Reset learning data for fresh start"""
        self.optimization_history = []
        self.performance_metrics = {}
        self.learning_feedback = {}
        logger.info("Unified optimization learning data reset")