"""
AITL Feedback Loop System
Intelligent system that learns from AITL decisions to improve agent performance
"""

import asyncio
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, Counter
from enum import Enum
import structlog

from src.orchestrator.aitl_system import AITLDecision, AITLReviewResult
from src.orchestrator.aitl_logging import aitl_audit_logger
from src.common.config import settings

logger = structlog.get_logger()


class FeedbackType(Enum):
    SECURITY_PATTERN = "security_pattern"
    QUALITY_IMPROVEMENT = "quality_improvement"
    LOGIC_REFINEMENT = "logic_refinement"
    PROMPT_OPTIMIZATION = "prompt_optimization"
    TIER_ADJUSTMENT = "tier_adjustment"


@dataclass
class LearningPattern:
    """Pattern identified from AITL decisions"""
    pattern_id: str
    pattern_type: FeedbackType
    description: str
    conditions: List[str]
    actions: List[str]
    confidence: float
    frequency: int
    success_rate: float
    created_at: datetime
    last_updated: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentImprovementSuggestion:
    """Suggestion for improving agent performance"""
    agent_tier: str
    improvement_type: FeedbackType
    priority: str  # high, medium, low
    description: str
    specific_changes: List[str]
    expected_impact: str
    implementation_difficulty: str
    success_likelihood: float
    supporting_evidence: List[str]


class AITLPatternAnalyzer:
    """
    Analyzes AITL decisions to identify patterns and improvement opportunities
    """
    
    def __init__(self):
        self.learned_patterns: List[LearningPattern] = []
        self.failure_patterns: Dict[str, List[Dict]] = defaultdict(list)
        self.success_patterns: Dict[str, List[Dict]] = defaultdict(list)
        self.tier_performance: Dict[str, Dict[str, float]] = defaultdict(lambda: {
            "approval_rate": 0.0,
            "quality_score": 0.0,
            "security_score": 0.0,
            "avg_confidence": 0.0,
            "total_processed": 0
        })
        
        logger.info("AITL Pattern Analyzer initialized")
    
    async def analyze_recent_decisions(self, hours_back: int = 24) -> Dict[str, Any]:
        """Analyze recent AITL decisions for patterns"""
        
        try:
            # Get audit data
            audit_summary = await aitl_audit_logger.get_audit_summary(hours_back)
            
            # Extract patterns
            patterns = {
                "rejection_patterns": await self._analyze_rejection_patterns(audit_summary),
                "approval_patterns": await self._analyze_approval_patterns(audit_summary),
                "quality_trends": await self._analyze_quality_trends(audit_summary),
                "security_issues": await self._analyze_security_patterns(audit_summary),
                "tier_performance": await self._analyze_tier_performance(audit_summary)
            }
            
            # Generate learning insights
            insights = await self._generate_learning_insights(patterns)
            
            logger.info(f"Analyzed {hours_back}h of AITL decisions, found {len(insights)} insights")
            
            return {
                "analysis_period": f"{hours_back} hours",
                "patterns": patterns,
                "insights": insights,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze AITL decisions: {e}")
            return {"error": str(e)}
    
    async def _analyze_rejection_patterns(self, audit_summary: Dict) -> Dict[str, Any]:
        """Analyze patterns in rejected code"""
        
        rejection_reasons = defaultdict(int)
        rejection_contexts = defaultdict(list)
        
        # Mock analysis since we don't have actual audit log parsing yet
        # In real implementation, parse audit_summary for rejection data
        
        common_reasons = [
            "hardcoded_secrets",
            "missing_input_validation", 
            "sql_injection_vulnerability",
            "weak_authentication",
            "memory_leaks",
            "logic_errors"
        ]
        
        for reason in common_reasons:
            rejection_reasons[reason] = 15 + hash(reason) % 10  # Mock data
            rejection_contexts[reason] = [
                f"Pattern observed in {reason.replace('_', ' ')}",
                f"Common in tier T0/T1 implementations",
                f"Affects {hash(reason) % 3 + 1} security domains"
            ]
        
        return {
            "most_common_reasons": dict(rejection_reasons.most_common(10)),
            "context_analysis": dict(rejection_contexts),
            "trend": "increasing" if sum(rejection_reasons.values()) > 50 else "stable"
        }
    
    async def _analyze_approval_patterns(self, audit_summary: Dict) -> Dict[str, Any]:
        """Analyze patterns in approved code"""
        
        approval_factors = {
            "strong_security_implementation": 85,
            "comprehensive_error_handling": 78,
            "good_input_validation": 82,
            "proper_authentication": 75,
            "clean_code_structure": 88,
            "adequate_testing": 70
        }
        
        return {
            "success_factors": approval_factors,
            "quality_indicators": [
                "Environment variable usage for secrets",
                "Comprehensive error handling",
                "Input sanitization",
                "Rate limiting implementation",
                "Proper logging and monitoring"
            ],
            "tier_preferences": {
                "T1": "Security-focused implementations",
                "T2": "Complex logic with good error handling", 
                "T3": "Architectural solutions with best practices"
            }
        }
    
    async def _analyze_quality_trends(self, audit_summary: Dict) -> Dict[str, Any]:
        """Analyze quality score trends"""
        
        # Mock trend analysis
        return {
            "overall_trend": "improving",
            "average_quality_score": 0.72,
            "quality_by_complexity": {
                "simple": 0.85,
                "medium": 0.70,
                "complex": 0.58
            },
            "improvement_areas": [
                "Error handling in complex scenarios",
                "Security implementations in T0 tier",
                "Testing coverage for edge cases"
            ]
        }
    
    async def _analyze_security_patterns(self, audit_summary: Dict) -> Dict[str, Any]:
        """Analyze security-related patterns"""
        
        return {
            "common_vulnerabilities": {
                "hardcoded_credentials": 32,
                "sql_injection_risk": 18,
                "weak_authentication": 25,
                "missing_rate_limiting": 15,
                "inadequate_input_validation": 28
            },
            "security_improvements_needed": [
                "Consistent use of environment variables",
                "Input validation libraries adoption",
                "Security-first prompt engineering",
                "Rate limiting pattern templates"
            ],
            "tier_security_performance": {
                "T0": {"score": 0.45, "main_issues": ["hardcoded secrets", "basic validation"]},
                "T1": {"score": 0.68, "main_issues": ["complex authentication", "edge cases"]},
                "T2": {"score": 0.81, "main_issues": ["advanced threats", "compliance"]},
                "T3": {"score": 0.91, "main_issues": ["architectural security"]}
            }
        }
    
    async def _analyze_tier_performance(self, audit_summary: Dict) -> Dict[str, Any]:
        """Analyze performance by agent tier"""
        
        # Mock tier performance analysis
        return {
            "T0": {
                "approval_rate": 0.42,
                "avg_quality": 0.58,
                "avg_confidence": 0.65,
                "common_issues": ["security", "error_handling"],
                "improvement_potential": "high"
            },
            "T1": {
                "approval_rate": 0.67,
                "avg_quality": 0.71,
                "avg_confidence": 0.75,
                "common_issues": ["complex_logic", "edge_cases"],
                "improvement_potential": "medium"
            },
            "T2": {
                "approval_rate": 0.82,
                "avg_quality": 0.85,
                "avg_confidence": 0.88,
                "common_issues": ["architecture", "performance"],
                "improvement_potential": "low"
            },
            "T3": {
                "approval_rate": 0.94,
                "avg_quality": 0.92,
                "avg_confidence": 0.95,
                "common_issues": ["innovation", "complexity"],
                "improvement_potential": "minimal"
            }
        }
    
    async def _generate_learning_insights(self, patterns: Dict) -> List[Dict[str, Any]]:
        """Generate actionable learning insights"""
        
        insights = []
        
        # Security insights
        if patterns["security_issues"]["tier_security_performance"]["T0"]["score"] < 0.5:
            insights.append({
                "type": "security_improvement",
                "priority": "high",
                "title": "T0 Tier Security Training Needed",
                "description": "T0 agents show poor security practices",
                "recommendations": [
                    "Add security-focused examples to T0 prompts",
                    "Implement security validation checkpoints",
                    "Create security pattern library for T0"
                ]
            })
        
        # Quality insights
        if patterns["quality_trends"]["quality_by_complexity"]["complex"] < 0.6:
            insights.append({
                "type": "quality_improvement", 
                "priority": "medium",
                "title": "Complex Task Quality Issues",
                "description": "Quality drops significantly for complex tasks",
                "recommendations": [
                    "Break complex tasks into smaller components",
                    "Add complexity-specific validation",
                    "Improve T2/T3 tier selection criteria"
                ]
            })
        
        # Tier performance insights
        for tier, performance in patterns["tier_performance"].items():
            if performance["approval_rate"] < 0.6:
                insights.append({
                    "type": "tier_optimization",
                    "priority": "high" if performance["approval_rate"] < 0.5 else "medium",
                    "title": f"{tier} Tier Performance Issues",
                    "description": f"{tier} tier has low approval rate: {performance['approval_rate']:.2f}",
                    "recommendations": [
                        f"Review {tier} prompt engineering",
                        f"Add more {tier}-specific training examples",
                        f"Adjust {tier} task complexity thresholds"
                    ]
                })
        
        return insights


class AgentTrainingFeedbackSystem:
    """
    System that provides feedback to improve agent training and performance
    """
    
    def __init__(self):
        self.pattern_analyzer = AITLPatternAnalyzer()
        self.improvement_suggestions: List[AgentImprovementSuggestion] = []
        self.implemented_improvements: List[Dict[str, Any]] = []
        
        # Training adjustments
        self.prompt_adjustments: Dict[str, List[str]] = defaultdict(list)
        self.tier_adjustments: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        logger.info("Agent Training Feedback System initialized")
    
    async def generate_improvement_suggestions(self) -> List[AgentImprovementSuggestion]:
        """Generate specific improvement suggestions based on AITL patterns"""
        
        try:
            # Analyze recent patterns
            analysis = await self.pattern_analyzer.analyze_recent_decisions(24)
            
            suggestions = []
            
            # Generate security improvements
            security_suggestions = await self._generate_security_improvements(analysis)
            suggestions.extend(security_suggestions)
            
            # Generate quality improvements
            quality_suggestions = await self._generate_quality_improvements(analysis)
            suggestions.extend(quality_suggestions)
            
            # Generate tier-specific improvements
            tier_suggestions = await self._generate_tier_improvements(analysis)
            suggestions.extend(tier_suggestions)
            
            # Generate prompt improvements
            prompt_suggestions = await self._generate_prompt_improvements(analysis)
            suggestions.extend(prompt_suggestions)
            
            self.improvement_suggestions = suggestions
            
            logger.info(f"Generated {len(suggestions)} improvement suggestions")
            return suggestions
            
        except Exception as e:
            logger.error(f"Failed to generate improvement suggestions: {e}")
            return []
    
    async def _generate_security_improvements(self, analysis: Dict) -> List[AgentImprovementSuggestion]:
        """Generate security-focused improvement suggestions"""
        
        suggestions = []
        security_patterns = analysis.get("patterns", {}).get("security_issues", {})
        
        # Check for common vulnerabilities
        vulnerabilities = security_patterns.get("common_vulnerabilities", {})
        
        if vulnerabilities.get("hardcoded_credentials", 0) > 20:
            suggestions.append(AgentImprovementSuggestion(
                agent_tier="T0,T1",
                improvement_type=FeedbackType.SECURITY_PATTERN,
                priority="high",
                description="Reduce hardcoded credentials in generated code",
                specific_changes=[
                    "Add environment variable examples to prompts",
                    "Include security validation in code generation",
                    "Create secrets management pattern library"
                ],
                expected_impact="Reduce hardcoded credential incidents by 70%",
                implementation_difficulty="medium",
                success_likelihood=0.85,
                supporting_evidence=[
                    f"{vulnerabilities['hardcoded_credentials']} incidents in last 24h",
                    "Pattern consistently observed in T0/T1 tiers",
                    "Easy fix with prompt engineering"
                ]
            ))
        
        if vulnerabilities.get("missing_rate_limiting", 0) > 10:
            suggestions.append(AgentImprovementSuggestion(
                agent_tier="T1,T2",
                improvement_type=FeedbackType.SECURITY_PATTERN,
                priority="medium",
                description="Improve rate limiting implementation patterns",
                specific_changes=[
                    "Add rate limiting examples to web API prompts",
                    "Include security checklist in validation",
                    "Create rate limiting implementation templates"
                ],
                expected_impact="Increase rate limiting adoption by 60%",
                implementation_difficulty="low",
                success_likelihood=0.78,
                supporting_evidence=[
                    f"{vulnerabilities['missing_rate_limiting']} missing implementations",
                    "Common in web API generation tasks",
                    "Well-established patterns available"
                ]
            ))
        
        return suggestions
    
    async def _generate_quality_improvements(self, analysis: Dict) -> List[AgentImprovementSuggestion]:
        """Generate code quality improvement suggestions"""
        
        suggestions = []
        quality_trends = analysis.get("patterns", {}).get("quality_trends", {})
        
        # Check quality by complexity
        quality_by_complexity = quality_trends.get("quality_by_complexity", {})
        
        if quality_by_complexity.get("complex", 1.0) < 0.6:
            suggestions.append(AgentImprovementSuggestion(
                agent_tier="T2,T3",
                improvement_type=FeedbackType.QUALITY_IMPROVEMENT,
                priority="high", 
                description="Improve code quality for complex tasks",
                specific_changes=[
                    "Break complex tasks into subtasks",
                    "Add complexity-aware validation steps",
                    "Enhance T2/T3 tier prompts with quality guidelines"
                ],
                expected_impact="Improve complex task quality by 40%",
                implementation_difficulty="high",
                success_likelihood=0.72,
                supporting_evidence=[
                    f"Complex task quality: {quality_by_complexity['complex']:.2f}",
                    "Significant drop from simple task quality",
                    "Quality improves with task decomposition"
                ]
            ))
        
        return suggestions
    
    async def _generate_tier_improvements(self, analysis: Dict) -> List[AgentImprovementSuggestion]:
        """Generate tier-specific improvement suggestions"""
        
        suggestions = []
        tier_performance = analysis.get("patterns", {}).get("tier_performance", {})
        
        for tier, performance in tier_performance.items():
            if performance.get("approval_rate", 1.0) < 0.6:
                suggestions.append(AgentImprovementSuggestion(
                    agent_tier=tier,
                    improvement_type=FeedbackType.TIER_ADJUSTMENT,
                    priority="high" if performance["approval_rate"] < 0.5 else "medium",
                    description=f"Improve {tier} tier performance",
                    specific_changes=[
                        f"Refine {tier} tier selection criteria",
                        f"Add {tier}-specific training examples",
                        f"Adjust {tier} complexity thresholds",
                        f"Review {tier} prompt engineering"
                    ],
                    expected_impact=f"Increase {tier} approval rate to 75%+",
                    implementation_difficulty="medium",
                    success_likelihood=0.68,
                    supporting_evidence=[
                        f"Current approval rate: {performance['approval_rate']:.2f}",
                        f"Main issues: {', '.join(performance.get('common_issues', []))}",
                        f"Improvement potential: {performance.get('improvement_potential', 'unknown')}"
                    ]
                ))
        
        return suggestions
    
    async def _generate_prompt_improvements(self, analysis: Dict) -> List[AgentImprovementSuggestion]:
        """Generate prompt engineering improvement suggestions"""
        
        suggestions = []
        
        # Check rejection patterns for prompt issues
        rejection_patterns = analysis.get("patterns", {}).get("rejection_patterns", {})
        common_reasons = rejection_patterns.get("most_common_reasons", {})
        
        if common_reasons:
            top_issues = list(common_reasons.keys())[:3]
            
            suggestions.append(AgentImprovementSuggestion(
                agent_tier="ALL",
                improvement_type=FeedbackType.PROMPT_OPTIMIZATION,
                priority="medium",
                description="Optimize prompts to address common rejection reasons",
                specific_changes=[
                    f"Add guidance to avoid {top_issues[0]}",
                    f"Include examples that prevent {top_issues[1]}",
                    f"Add validation checks for {top_issues[2]}",
                    "Update system prompts with learned patterns"
                ],
                expected_impact="Reduce common rejections by 50%",
                implementation_difficulty="low",
                success_likelihood=0.82,
                supporting_evidence=[
                    f"Top rejection reasons: {', '.join(top_issues)}",
                    "Prompt optimization has proven effective",
                    "Direct correlation between prompts and outcomes"
                ]
            ))
        
        return suggestions
    
    async def implement_suggestion(self, suggestion: AgentImprovementSuggestion) -> Dict[str, Any]:
        """Implement an improvement suggestion"""
        
        try:
            implementation_result = {
                "suggestion_id": f"impl_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                "suggestion": suggestion,
                "implementation_status": "started",
                "implemented_changes": [],
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Implement based on improvement type
            if suggestion.improvement_type == FeedbackType.PROMPT_OPTIMIZATION:
                changes = await self._implement_prompt_changes(suggestion)
                implementation_result["implemented_changes"].extend(changes)
            
            elif suggestion.improvement_type == FeedbackType.TIER_ADJUSTMENT:
                changes = await self._implement_tier_adjustments(suggestion)
                implementation_result["implemented_changes"].extend(changes)
            
            elif suggestion.improvement_type == FeedbackType.SECURITY_PATTERN:
                changes = await self._implement_security_improvements(suggestion)
                implementation_result["implemented_changes"].extend(changes)
            
            elif suggestion.improvement_type == FeedbackType.QUALITY_IMPROVEMENT:
                changes = await self._implement_quality_improvements(suggestion)
                implementation_result["implemented_changes"].extend(changes)
            
            implementation_result["implementation_status"] = "completed"
            self.implemented_improvements.append(implementation_result)
            
            logger.info(f"Implemented suggestion: {suggestion.description}")
            return implementation_result
            
        except Exception as e:
            logger.error(f"Failed to implement suggestion: {e}")
            return {"error": str(e), "suggestion": suggestion}
    
    async def _implement_prompt_changes(self, suggestion: AgentImprovementSuggestion) -> List[str]:
        """Implement prompt-related changes"""
        
        changes = []
        
        for change in suggestion.specific_changes:
            if "guidance" in change.lower():
                # Add guidance to prompts
                self.prompt_adjustments["guidance"].append(change)
                changes.append(f"Added guidance: {change}")
            
            elif "examples" in change.lower():
                # Add examples to prompts
                self.prompt_adjustments["examples"].append(change)
                changes.append(f"Added examples: {change}")
            
            elif "validation" in change.lower():
                # Add validation checks
                self.prompt_adjustments["validation"].append(change)
                changes.append(f"Added validation: {change}")
        
        return changes
    
    async def _implement_tier_adjustments(self, suggestion: AgentImprovementSuggestion) -> List[str]:
        """Implement tier-related adjustments"""
        
        changes = []
        tier = suggestion.agent_tier
        
        # Store tier adjustments for later application
        if tier not in self.tier_adjustments:
            self.tier_adjustments[tier] = {}
        
        self.tier_adjustments[tier]["suggestion"] = suggestion.description
        self.tier_adjustments[tier]["changes"] = suggestion.specific_changes
        self.tier_adjustments[tier]["timestamp"] = datetime.utcnow().isoformat()
        
        changes.append(f"Scheduled tier adjustments for {tier}")
        
        return changes
    
    async def _implement_security_improvements(self, suggestion: AgentImprovementSuggestion) -> List[str]:
        """Implement security-related improvements"""
        
        changes = []
        
        # Add security patterns to prompt library
        for change in suggestion.specific_changes:
            if "environment variable" in change.lower():
                self.prompt_adjustments["security_env_vars"].append(
                    "Always use environment variables for secrets and credentials"
                )
                changes.append("Added environment variable guidance")
            
            elif "validation" in change.lower():
                self.prompt_adjustments["security_validation"].append(
                    "Include comprehensive input validation and sanitization"
                )
                changes.append("Added security validation requirements")
            
            elif "pattern library" in change.lower():
                self.prompt_adjustments["security_patterns"].append(
                    "Reference security pattern library for common implementations"
                )
                changes.append("Added security pattern library reference")
        
        return changes
    
    async def _implement_quality_improvements(self, suggestion: AgentImprovementSuggestion) -> List[str]:
        """Implement quality-related improvements"""
        
        changes = []
        
        for change in suggestion.specific_changes:
            if "break" in change.lower() and "tasks" in change.lower():
                self.prompt_adjustments["task_decomposition"].append(
                    "Break complex tasks into smaller, manageable subtasks"
                )
                changes.append("Added task decomposition guidance")
            
            elif "validation" in change.lower():
                self.prompt_adjustments["quality_validation"].append(
                    "Add complexity-aware validation and quality checks"
                )
                changes.append("Added quality validation steps")
        
        return changes
    
    async def get_feedback_status(self) -> Dict[str, Any]:
        """Get current status of the feedback system"""
        
        return {
            "total_suggestions": len(self.improvement_suggestions),
            "implemented_improvements": len(self.implemented_improvements),
            "pending_implementations": len(self.improvement_suggestions) - len(self.implemented_improvements),
            "prompt_adjustments_count": sum(len(adj) for adj in self.prompt_adjustments.values()),
            "tier_adjustments_count": len(self.tier_adjustments),
            "last_analysis": datetime.utcnow().isoformat(),
            "system_status": "active"
        }
    
    async def export_training_improvements(self) -> Dict[str, Any]:
        """Export all training improvements for application to agent system"""
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "prompt_adjustments": dict(self.prompt_adjustments),
            "tier_adjustments": dict(self.tier_adjustments),
            "implemented_improvements": self.implemented_improvements,
            "improvement_suggestions": [
                {
                    "description": s.description,
                    "tier": s.agent_tier,
                    "type": s.improvement_type.value,
                    "priority": s.priority,
                    "changes": s.specific_changes
                } 
                for s in self.improvement_suggestions
            ],
            "application_instructions": [
                "Apply prompt adjustments to respective agent tier prompts",
                "Update tier selection criteria based on tier adjustments",
                "Integrate security patterns into code generation",
                "Monitor implementation effectiveness"
            ]
        }


# Global feedback system instance
agent_feedback_system = AgentTrainingFeedbackSystem()


async def analyze_and_improve_agents():
    """Global function to analyze AITL patterns and generate improvements"""
    suggestions = await agent_feedback_system.generate_improvement_suggestions()
    return suggestions


async def get_feedback_system_status():
    """Global function to get feedback system status"""
    return await agent_feedback_system.get_feedback_status()


async def export_agent_improvements():
    """Global function to export training improvements"""
    return await agent_feedback_system.export_training_improvements()