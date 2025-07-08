"""
Pattern Selection Engine - Intelligent Selection of Reasoning Patterns
Automatically selects optimal reasoning patterns based on request characteristics
"""

from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import json
import structlog
from openai import AsyncOpenAI
from datetime import datetime

from src.common.config import settings

logger = structlog.get_logger()


class PatternType(Enum):
    """Types of reasoning patterns"""
    ABSTRACTION = "abstraction"
    EMERGENT_PATTERNS = "emergent_patterns"
    META_LEARNING = "meta_learning"
    UNCERTAINTY = "uncertainty"
    CONSTRAINT = "constraint"
    SEMANTIC = "semantic"
    DIALECTICAL = "dialectical"
    QUANTUM = "quantum"


@dataclass
class PatternRecommendation:
    """Recommendation for using a specific pattern"""
    pattern: PatternType
    confidence: float
    reasoning: str
    priority: int  # 1-5, 1 being highest
    computational_cost: float  # 0.1-1.0
    expected_value: float  # 0.1-1.0


@dataclass
class RequestCharacteristics:
    """Characteristics extracted from a request"""
    complexity_level: str  # trivial, simple, medium, complex, critical
    domain: str  # technical, business, creative, analytical
    ambiguity_level: float  # 0.0-1.0
    constraint_density: float  # 0.0-1.0
    conceptual_depth: float  # 0.0-1.0
    uncertainty_factors: List[str]
    conflicting_requirements: bool
    multi_perspective_needed: bool
    learning_opportunity: bool
    time_sensitivity: str  # low, medium, high, critical


class PatternSelectionEngine:
    """
    Intelligent engine for selecting optimal reasoning patterns based on request analysis
    """
    
    def __init__(self):
        # Initialize OpenAI client
        if hasattr(settings, 'AZURE_OPENAI_ENDPOINT') and settings.AZURE_OPENAI_ENDPOINT:
            from openai import AsyncAzureOpenAI
            self.openai_client = AsyncAzureOpenAI(
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
            )
        else:
            self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Pattern performance tracking
        self.pattern_performance = {}
        self.selection_history = []
        
        # Pattern characteristics matrix
        self.pattern_matrix = self._initialize_pattern_matrix()
    
    def _initialize_pattern_matrix(self) -> Dict[PatternType, Dict[str, Any]]:
        """Initialize the pattern characteristics matrix"""
        return {
            PatternType.ABSTRACTION: {
                "best_for": ["complex_hierarchies", "multi_level_thinking", "system_design"],
                "computational_cost": 0.7,
                "domains": ["technical", "business", "analytical"],
                "complexity_threshold": "medium",
                "characteristics": {
                    "handles_complexity": 0.9,
                    "handles_ambiguity": 0.7,
                    "handles_constraints": 0.6,
                    "handles_uncertainty": 0.5,
                    "handles_conflicts": 0.4
                }
            },
            PatternType.EMERGENT_PATTERNS: {
                "best_for": ["learning_scenarios", "pattern_discovery", "optimization"],
                "computational_cost": 0.8,
                "domains": ["analytical", "technical", "creative"],
                "complexity_threshold": "medium",
                "characteristics": {
                    "handles_complexity": 0.6,
                    "handles_ambiguity": 0.5,
                    "handles_constraints": 0.4,
                    "handles_uncertainty": 0.6,
                    "handles_conflicts": 0.3
                }
            },
            PatternType.META_LEARNING: {
                "best_for": ["learning_optimization", "strategy_adaptation", "performance_tuning"],
                "computational_cost": 0.6,
                "domains": ["analytical", "technical"],
                "complexity_threshold": "simple",
                "characteristics": {
                    "handles_complexity": 0.5,
                    "handles_ambiguity": 0.4,
                    "handles_constraints": 0.3,
                    "handles_uncertainty": 0.7,
                    "handles_conflicts": 0.2
                }
            },
            PatternType.UNCERTAINTY: {
                "best_for": ["risk_assessment", "confidence_evaluation", "decision_making"],
                "computational_cost": 0.5,
                "domains": ["business", "analytical", "technical"],
                "complexity_threshold": "simple",
                "characteristics": {
                    "handles_complexity": 0.4,
                    "handles_ambiguity": 0.9,
                    "handles_constraints": 0.3,
                    "handles_uncertainty": 0.9,
                    "handles_conflicts": 0.5
                }
            },
            PatternType.CONSTRAINT: {
                "best_for": ["optimization_problems", "requirement_satisfaction", "trade_offs"],
                "computational_cost": 0.8,
                "domains": ["technical", "business", "analytical"],
                "complexity_threshold": "complex",
                "characteristics": {
                    "handles_complexity": 0.7,
                    "handles_ambiguity": 0.4,
                    "handles_constraints": 0.9,
                    "handles_uncertainty": 0.3,
                    "handles_conflicts": 0.8
                }
            },
            PatternType.SEMANTIC: {
                "best_for": ["language_understanding", "concept_mapping", "knowledge_graphs"],
                "computational_cost": 0.6,
                "domains": ["creative", "analytical", "technical"],
                "complexity_threshold": "medium",
                "characteristics": {
                    "handles_complexity": 0.6,
                    "handles_ambiguity": 0.8,
                    "handles_constraints": 0.4,
                    "handles_uncertainty": 0.5,
                    "handles_conflicts": 0.3
                }
            },
            PatternType.DIALECTICAL: {
                "best_for": ["conflict_resolution", "synthesis", "opposing_viewpoints"],
                "computational_cost": 0.9,
                "domains": ["business", "creative", "analytical"],
                "complexity_threshold": "complex",
                "characteristics": {
                    "handles_complexity": 0.8,
                    "handles_ambiguity": 0.6,
                    "handles_constraints": 0.5,
                    "handles_uncertainty": 0.4,
                    "handles_conflicts": 0.9
                }
            },
            PatternType.QUANTUM: {
                "best_for": ["parallel_exploration", "superposition_analysis", "novel_insights"],
                "computational_cost": 0.9,
                "domains": ["creative", "analytical", "technical"],
                "complexity_threshold": "critical",
                "characteristics": {
                    "handles_complexity": 0.9,
                    "handles_ambiguity": 0.8,
                    "handles_constraints": 0.6,
                    "handles_uncertainty": 0.8,
                    "handles_conflicts": 0.7
                }
            }
        }
    
    async def analyze_request_characteristics(self, request: str, context: Dict[str, Any]) -> RequestCharacteristics:
        """Analyze request to extract characteristics for pattern selection"""
        logger.info("Analyzing request characteristics for pattern selection")
        
        analysis_prompt = f"""
        Analyze this request to extract characteristics for intelligent pattern selection:
        
        REQUEST: {request}
        CONTEXT: {json.dumps(context, indent=2)}
        
        Extract these characteristics:
        
        1. COMPLEXITY LEVEL: trivial, simple, medium, complex, critical
        2. DOMAIN: technical, business, creative, analytical, mixed
        3. AMBIGUITY LEVEL: 0.0-1.0 (how ambiguous/unclear is the request?)
        4. CONSTRAINT DENSITY: 0.0-1.0 (how many constraints/requirements?)
        5. CONCEPTUAL DEPTH: 0.0-1.0 (how deep is the conceptual thinking needed?)
        6. UNCERTAINTY FACTORS: List specific uncertainty sources
        7. CONFLICTING REQUIREMENTS: Are there conflicting requirements?
        8. MULTI-PERSPECTIVE NEEDED: Does this need multiple viewpoints?
        9. LEARNING OPPORTUNITY: Is this a learning/optimization scenario?
        10. TIME SENSITIVITY: low, medium, high, critical
        
        Return as JSON:
        {{
            "complexity_level": "medium",
            "domain": "technical",
            "ambiguity_level": 0.3,
            "constraint_density": 0.6,
            "conceptual_depth": 0.7,
            "uncertainty_factors": ["technical_feasibility", "resource_constraints"],
            "conflicting_requirements": false,
            "multi_perspective_needed": true,
            "learning_opportunity": false,
            "time_sensitivity": "medium"
        }}
        """
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing request characteristics for pattern selection."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.2,
                max_tokens=1000
            )
            
            analysis_data = json.loads(response.choices[0].message.content)
            
            characteristics = RequestCharacteristics(
                complexity_level=analysis_data.get("complexity_level", "medium"),
                domain=analysis_data.get("domain", "technical"),
                ambiguity_level=analysis_data.get("ambiguity_level", 0.5),
                constraint_density=analysis_data.get("constraint_density", 0.5),
                conceptual_depth=analysis_data.get("conceptual_depth", 0.5),
                uncertainty_factors=analysis_data.get("uncertainty_factors", []),
                conflicting_requirements=analysis_data.get("conflicting_requirements", False),
                multi_perspective_needed=analysis_data.get("multi_perspective_needed", False),
                learning_opportunity=analysis_data.get("learning_opportunity", False),
                time_sensitivity=analysis_data.get("time_sensitivity", "medium")
            )
            
            return characteristics
            
        except Exception as e:
            logger.error(f"Failed to analyze request characteristics: {e}")
            return self._fallback_characteristics()
    
    async def recommend_patterns(self, characteristics: RequestCharacteristics, 
                               max_patterns: int = 5, 
                               budget_constraint: float = 3.0) -> List[PatternRecommendation]:
        """Recommend optimal patterns based on request characteristics"""
        logger.info("Recommending optimal patterns", 
                   complexity=characteristics.complexity_level,
                   domain=characteristics.domain)
        
        recommendations = []
        
        # Score each pattern
        for pattern_type, pattern_info in self.pattern_matrix.items():
            score = self._calculate_pattern_score(pattern_type, pattern_info, characteristics)
            
            if score > 0.3:  # Minimum threshold
                recommendation = PatternRecommendation(
                    pattern=pattern_type,
                    confidence=score,
                    reasoning=self._generate_reasoning(pattern_type, pattern_info, characteristics),
                    priority=self._calculate_priority(score, pattern_info),
                    computational_cost=pattern_info["computational_cost"],
                    expected_value=score * (1 - pattern_info["computational_cost"])
                )
                recommendations.append(recommendation)
        
        # Sort by expected value (confidence * efficiency)
        recommendations.sort(key=lambda x: x.expected_value, reverse=True)
        
        # Apply budget constraint
        selected_recommendations = self._apply_budget_constraint(recommendations, budget_constraint)
        
        # Limit to max_patterns
        final_recommendations = selected_recommendations[:max_patterns]
        
        # Log selection reasoning
        self._log_selection_reasoning(characteristics, final_recommendations)
        
        return final_recommendations
    
    def _calculate_pattern_score(self, pattern_type: PatternType, 
                               pattern_info: Dict[str, Any], 
                               characteristics: RequestCharacteristics) -> float:
        """Calculate fitness score for a pattern given request characteristics"""
        score = 0.0
        
        # Domain match
        if characteristics.domain in pattern_info["domains"]:
            score += 0.3
        elif "mixed" in characteristics.domain:
            score += 0.2
        
        # Complexity match
        complexity_mapping = {"trivial": 1, "simple": 2, "medium": 3, "complex": 4, "critical": 5}
        req_complexity = complexity_mapping.get(characteristics.complexity_level, 3)
        pattern_threshold = complexity_mapping.get(pattern_info["complexity_threshold"], 3)
        
        if req_complexity >= pattern_threshold:
            score += 0.2
        
        # Characteristic-specific scoring
        pattern_chars = pattern_info["characteristics"]
        
        # Ambiguity handling
        if characteristics.ambiguity_level > 0.5:
            score += pattern_chars["handles_ambiguity"] * 0.15
        
        # Constraint handling
        if characteristics.constraint_density > 0.5:
            score += pattern_chars["handles_constraints"] * 0.15
        
        # Uncertainty handling
        if len(characteristics.uncertainty_factors) > 2:
            score += pattern_chars["handles_uncertainty"] * 0.15
        
        # Conflict handling
        if characteristics.conflicting_requirements:
            score += pattern_chars["handles_conflicts"] * 0.2
        
        # Special case bonuses
        if pattern_type == PatternType.META_LEARNING and characteristics.learning_opportunity:
            score += 0.25
        
        if pattern_type == PatternType.DIALECTICAL and characteristics.multi_perspective_needed:
            score += 0.25
        
        if pattern_type == PatternType.QUANTUM and characteristics.complexity_level == "critical":
            score += 0.2
        
        return min(score, 1.0)
    
    def _generate_reasoning(self, pattern_type: PatternType, 
                          pattern_info: Dict[str, Any], 
                          characteristics: RequestCharacteristics) -> str:
        """Generate human-readable reasoning for pattern selection"""
        reasons = []
        
        if characteristics.domain in pattern_info["domains"]:
            reasons.append(f"Strong domain match ({characteristics.domain})")
        
        if characteristics.complexity_level in ["complex", "critical"] and pattern_type in [PatternType.QUANTUM, PatternType.DIALECTICAL]:
            reasons.append("High complexity requires advanced reasoning")
        
        if characteristics.ambiguity_level > 0.7 and pattern_type in [PatternType.UNCERTAINTY, PatternType.SEMANTIC]:
            reasons.append("High ambiguity benefits from uncertainty/semantic analysis")
        
        if characteristics.conflicting_requirements and pattern_type == PatternType.DIALECTICAL:
            reasons.append("Conflicting requirements need dialectical synthesis")
        
        if characteristics.constraint_density > 0.6 and pattern_type == PatternType.CONSTRAINT:
            reasons.append("High constraint density requires constraint satisfaction")
        
        if characteristics.learning_opportunity and pattern_type == PatternType.META_LEARNING:
            reasons.append("Learning opportunity detected")
        
        if not reasons:
            reasons.append("General applicability for this request type")
        
        return "; ".join(reasons)
    
    def _calculate_priority(self, score: float, pattern_info: Dict[str, Any]) -> int:
        """Calculate priority based on score and computational cost"""
        efficiency = score / pattern_info["computational_cost"]
        
        if efficiency > 0.8:
            return 1  # Highest priority
        elif efficiency > 0.6:
            return 2
        elif efficiency > 0.4:
            return 3
        elif efficiency > 0.2:
            return 4
        else:
            return 5  # Lowest priority
    
    def _apply_budget_constraint(self, recommendations: List[PatternRecommendation], 
                                budget: float) -> List[PatternRecommendation]:
        """Apply computational budget constraint"""
        selected = []
        total_cost = 0.0
        
        for rec in recommendations:
            if total_cost + rec.computational_cost <= budget:
                selected.append(rec)
                total_cost += rec.computational_cost
            else:
                break
        
        return selected
    
    def _log_selection_reasoning(self, characteristics: RequestCharacteristics, 
                               recommendations: List[PatternRecommendation]):
        """Log the selection reasoning for analysis"""
        selection_log = {
            "timestamp": datetime.utcnow().isoformat(),
            "characteristics": {
                "complexity": characteristics.complexity_level,
                "domain": characteristics.domain,
                "ambiguity": characteristics.ambiguity_level,
                "constraints": characteristics.constraint_density,
                "conflicts": characteristics.conflicting_requirements
            },
            "selected_patterns": [
                {
                    "pattern": rec.pattern.value,
                    "confidence": rec.confidence,
                    "priority": rec.priority,
                    "reasoning": rec.reasoning
                }
                for rec in recommendations
            ]
        }
        
        self.selection_history.append(selection_log)
        
        logger.info("Pattern selection completed",
                   selected_count=len(recommendations),
                   top_pattern=recommendations[0].pattern.value if recommendations else "none",
                   total_cost=sum(r.computational_cost for r in recommendations))
    
    def _fallback_characteristics(self) -> RequestCharacteristics:
        """Fallback characteristics when analysis fails"""
        return RequestCharacteristics(
            complexity_level="medium",
            domain="technical",
            ambiguity_level=0.5,
            constraint_density=0.5,
            conceptual_depth=0.5,
            uncertainty_factors=["unknown"],
            conflicting_requirements=False,
            multi_perspective_needed=False,
            learning_opportunity=False,
            time_sensitivity="medium"
        )
    
    async def get_selection_explanation(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed explanation of pattern selection for a request"""
        characteristics = await self.analyze_request_characteristics(request, context)
        recommendations = await self.recommend_patterns(characteristics)
        
        return {
            "request": request,
            "characteristics": {
                "complexity_level": characteristics.complexity_level,
                "domain": characteristics.domain,
                "ambiguity_level": characteristics.ambiguity_level,
                "constraint_density": characteristics.constraint_density,
                "conceptual_depth": characteristics.conceptual_depth,
                "uncertainty_factors": characteristics.uncertainty_factors,
                "conflicting_requirements": characteristics.conflicting_requirements,
                "multi_perspective_needed": characteristics.multi_perspective_needed,
                "learning_opportunity": characteristics.learning_opportunity,
                "time_sensitivity": characteristics.time_sensitivity
            },
            "recommendations": [
                {
                    "pattern": rec.pattern.value,
                    "confidence": rec.confidence,
                    "reasoning": rec.reasoning,
                    "priority": rec.priority,
                    "computational_cost": rec.computational_cost,
                    "expected_value": rec.expected_value
                }
                for rec in recommendations
            ],
            "selection_summary": {
                "total_patterns": len(recommendations),
                "total_cost": sum(r.computational_cost for r in recommendations),
                "avg_confidence": sum(r.confidence for r in recommendations) / len(recommendations) if recommendations else 0,
                "recommended_approach": self._generate_approach_summary(characteristics, recommendations)
            }
        }
    
    def _generate_approach_summary(self, characteristics: RequestCharacteristics, 
                                 recommendations: List[PatternRecommendation]) -> str:
        """Generate a summary of the recommended approach"""
        if not recommendations:
            return "No specific patterns recommended - use standard analysis"
        
        primary_pattern = recommendations[0].pattern.value
        pattern_count = len(recommendations)
        
        if pattern_count == 1:
            return f"Single-pattern approach using {primary_pattern}"
        elif pattern_count <= 3:
            return f"Focused multi-pattern approach led by {primary_pattern}"
        else:
            return f"Comprehensive multi-pattern approach with {primary_pattern} as primary"


# Usage guidance dictionary
PATTERN_USAGE_GUIDE = {
    "abstraction": {
        "when_to_use": "Complex hierarchical problems, system design, multi-level analysis",
        "avoid_when": "Simple linear tasks, time-critical situations",
        "best_domains": ["technical", "business", "analytical"],
        "examples": ["Design microservices architecture", "Organize complex requirements", "Create abstraction layers"]
    },
    "emergent_patterns": {
        "when_to_use": "Learning scenarios, optimization, pattern discovery",
        "avoid_when": "Well-understood problems, no historical data",
        "best_domains": ["analytical", "technical", "creative"],
        "examples": ["Optimize performance based on usage patterns", "Discover user behavior patterns", "Learn from failures"]
    },
    "meta_learning": {
        "when_to_use": "Strategy adaptation, learning optimization, performance tuning",
        "avoid_when": "First-time problems, no learning history",
        "best_domains": ["analytical", "technical"],
        "examples": ["Improve development processes", "Optimize AI model performance", "Adapt to new domains"]
    },
    "uncertainty": {
        "when_to_use": "Risk assessment, confidence evaluation, ambiguous requirements",
        "avoid_when": "Clear, well-defined problems",
        "best_domains": ["business", "analytical", "technical"],
        "examples": ["Assess project risks", "Evaluate technical feasibility", "Handle ambiguous requirements"]
    },
    "constraint": {
        "when_to_use": "Optimization problems, requirement satisfaction, trade-offs",
        "avoid_when": "Unconstrained creative problems",
        "best_domains": ["technical", "business", "analytical"],
        "examples": ["Resource allocation", "Meeting multiple requirements", "Optimization under constraints"]
    },
    "semantic": {
        "when_to_use": "Language understanding, concept mapping, knowledge representation",
        "avoid_when": "Purely numerical problems",
        "best_domains": ["creative", "analytical", "technical"],
        "examples": ["Natural language processing", "Knowledge graph creation", "Concept relationship mapping"]
    },
    "dialectical": {
        "when_to_use": "Conflict resolution, opposing viewpoints, synthesis needed",
        "avoid_when": "Consensus exists, no contradictions",
        "best_domains": ["business", "creative", "analytical"],
        "examples": ["Resolve conflicting requirements", "Merge opposing designs", "Synthesize different approaches"]
    },
    "quantum": {
        "when_to_use": "Parallel exploration, superposition analysis, novel insights",
        "avoid_when": "Simple problems, computational constraints",
        "best_domains": ["creative", "analytical", "technical"],
        "examples": ["Explore multiple solutions simultaneously", "Complex possibility spaces", "Novel insight generation"]
    }
}