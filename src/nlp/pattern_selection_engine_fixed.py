"""
Fixed Pattern Selection Engine - Rule-based pattern selection as fallback
"""

from typing import Dict, List, Any
from dataclasses import dataclass
import structlog
from src.nlp.pattern_selection_engine import (
    PatternType, PatternRecommendation, RequestCharacteristics,
    PatternSelectionEngine as BaseEngine
)

logger = structlog.get_logger()


class FixedPatternSelectionEngine(BaseEngine):
    """Pattern selection engine with rule-based fallback"""
    
    async def analyze_request_characteristics(self, request: str, context: Dict[str, Any]) -> RequestCharacteristics:
        """Analyze request using rules when LLM fails"""
        try:
            # Try the original LLM-based analysis first
            return await super().analyze_request_characteristics(request, context)
        except Exception as e:
            logger.warning(f"LLM analysis failed, using rule-based analysis: {e}")
            return self._rule_based_analysis(request, context)
    
    def _rule_based_analysis(self, request: str, context: Dict[str, Any]) -> RequestCharacteristics:
        """Rule-based request analysis"""
        text = request.lower()
        
        # Complexity detection
        complexity = "medium"  # default
        if any(word in text for word in ["simple", "basic", "hello", "trivial"]):
            complexity = "simple"
        elif any(word in text for word in ["complex", "distributed", "microservice", "enterprise"]):
            complexity = "complex"
        elif any(word in text for word in ["advanced", "sophisticated", "ai", "ml"]):
            complexity = "critical"
        
        # Domain detection
        domain = "technical"  # default
        if any(word in text for word in ["business", "finance", "marketing", "sales"]):
            domain = "business"
        elif any(word in text for word in ["ui", "ux", "design", "frontend", "css"]):
            domain = "creative"
        elif any(word in text for word in ["analysis", "data", "metrics", "report"]):
            domain = "analytical"
        
        # Ambiguity detection
        ambiguity = 0.3  # default low
        if any(word in text for word in ["maybe", "possibly", "could", "might", "perhaps"]):
            ambiguity = 0.7
        elif len(text.split()) < 10:  # Very short descriptions are often ambiguous
            ambiguity = 0.6
        
        # Constraint detection
        constraints = 0.3  # default low
        if any(word in text for word in ["must", "require", "need", "constraint", "limit"]):
            constraints = 0.7
        elif any(word in text for word in ["should", "prefer", "ideally"]):
            constraints = 0.5
        
        # Conflict detection
        conflicts = False
        if any(phrase in text for phrase in ["but also", "however", "on the other hand", "conflicting"]):
            conflicts = True
        
        # Learning opportunity
        learning = False
        if any(word in text for word in ["learn", "improve", "optimize", "adapt", "ml", "ai"]):
            learning = True
        
        # Uncertainty factors
        uncertainty_factors = []
        if "api" in text:
            uncertainty_factors.append("api_design")
        if "performance" in text:
            uncertainty_factors.append("performance_requirements")
        if "scale" in text:
            uncertainty_factors.append("scalability")
        if not uncertainty_factors:
            uncertainty_factors = ["general_requirements"]
        
        return RequestCharacteristics(
            complexity_level=complexity,
            domain=domain,
            ambiguity_level=ambiguity,
            constraint_density=constraints,
            conceptual_depth=0.5 if complexity in ["simple", "medium"] else 0.8,
            uncertainty_factors=uncertainty_factors,
            conflicting_requirements=conflicts,
            multi_perspective_needed=complexity in ["complex", "critical"],
            learning_opportunity=learning,
            time_sensitivity="high" if "urgent" in text or "asap" in text else "medium"
        )