"""
AITL (AI-in-the-Loop) Refinement System
Advanced code refinement with meta-cognitive strategies and reviewer ensembles.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from uuid import uuid4

from openai import AsyncOpenAI, AsyncAzureOpenAI
from anthropic import AsyncAnthropic
import structlog

from src.common.config import settings
from src.common.models import TaskResult, ValidationReport

logger = structlog.get_logger()

# Helper function to get model name based on client type
def get_model_name(llm_client):
    """Get appropriate model name based on LLM client type"""
    if isinstance(llm_client, AsyncAzureOpenAI):
        # For Azure, use the deployment name
        return settings.AZURE_OPENAI_DEPLOYMENT_NAME
    elif isinstance(llm_client, AsyncOpenAI):
        return "gpt-4"
    else:
        # Anthropic
        return "claude-3-sonnet-20240229"

class RefinementPattern(Enum):
    """Available refinement patterns"""
    INTENT_DIFFING = "intent_diffing"
    FAILURE_SYNTHESIS = "failure_synthesis"
    REVIEWER_ENSEMBLE = "reviewer_ensemble"
    CONTEXT_CONSTRAINED = "context_constrained"
    REGRESSION_AWARE = "regression_aware"
    PROGRESSIVE_BUCKETING = "progressive_bucketing"

class ReviewerPersona(Enum):
    """Reviewer personas for ensemble review"""
    SECURITY_ANALYST = "security_analyst"
    PERFORMANCE_AUDITOR = "performance_auditor"
    ARCHITECTURAL_PURIST = "architectural_purist"
    USER_EXPERIENCE_ADVOCATE = "user_experience_advocate"
    MAINTAINABILITY_GUARDIAN = "maintainability_guardian"

@dataclass
class RefinementContext:
    """Context for refinement operations"""
    original_code: str
    original_request: str
    execution_results: Optional[Dict] = None
    validation_failures: List[str] = field(default_factory=list)
    previous_iterations: List[Dict] = field(default_factory=list)
    complexity_score: float = 0.0
    risk_factors: List[str] = field(default_factory=list)

@dataclass
class RefinementResult:
    """Result of a refinement operation"""
    refined_code: str
    confidence_score: float
    pattern_used: RefinementPattern
    improvements: List[str]
    reasoning: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AITLDecision:
    """AITL decision result"""
    decision: str  # "approve", "refine", "escalate_to_human"
    confidence: float
    reasoning: str
    suggested_improvements: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class IntentDiffingRefiner:
    """Refines code by analyzing intent vs implementation gaps"""
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
    
    async def refine(self, context: RefinementContext) -> RefinementResult:
        """Refine code using intent diffing analysis"""
        
        prompt = f"""
        Analyze the gap between intended functionality and actual implementation:

        ORIGINAL REQUEST: {context.original_request}
        CURRENT CODE: {context.original_code}
        
        VALIDATION FAILURES: {context.validation_failures}
        EXECUTION RESULTS: {context.execution_results}

        Perform intent diffing analysis:
        1. Extract the core intent from the original request
        2. Analyze what the current code actually does
        3. Identify specific gaps between intent and implementation
        4. Provide refined code that better aligns with the original intent
        5. Explain your reasoning for each change

        Return your analysis in this JSON format:
        {{
            "intent_analysis": {{
                "extracted_intent": "...",
                "current_behavior": "...",
                "identified_gaps": ["..."]
            }},
            "refined_code": "...",
            "improvements": ["..."],
            "confidence_score": 0.0-1.0,
            "reasoning": "..."
        }}
        """
        
        try:
            if hasattr(self.llm_client, 'chat'):
                # OpenAI client
                response = await self.llm_client.chat.completions.create(
                    model=get_model_name(self.llm_client),
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3
                )
                content = response.choices[0].message.content
            else:
                # Anthropic client
                response = await self.llm_client.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=2000,
                    temperature=0.3,
                    messages=[{"role": "user", "content": prompt}]
                )
                content = response.content[0].text
            
            # Try to extract JSON from the content
            # Sometimes LLMs add extra text before/after JSON
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
            else:
                result = json.loads(content)
            
            return RefinementResult(
                refined_code=result["refined_code"],
                confidence_score=result["confidence_score"],
                pattern_used=RefinementPattern.INTENT_DIFFING,
                improvements=result["improvements"],
                reasoning=result["reasoning"],
                metadata=result.get("intent_analysis", {})
            )
            
        except Exception as e:
            logger.error(f"Intent diffing refinement failed: {e}")
            logger.debug(f"Raw LLM response: {content[:500] if 'content' in locals() else 'No content'}")
            return RefinementResult(
                refined_code=context.original_code,
                confidence_score=0.1,
                pattern_used=RefinementPattern.INTENT_DIFFING,
                improvements=[],
                reasoning=f"Refinement failed: {str(e)}",
                metadata={"error": str(e)}
            )

class FailureSynthesisRefiner:
    """Synthesizes failures into systematic improvements"""
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
    
    async def refine(self, context: RefinementContext) -> RefinementResult:
        """Refine code by synthesizing failure patterns"""
        
        failure_analysis = self._analyze_failures(context)
        
        prompt = f"""
        Synthesize systematic improvements from failure patterns:

        ORIGINAL CODE: {context.original_code}
        FAILURE ANALYSIS: {failure_analysis}
        PREVIOUS ITERATIONS: {context.previous_iterations}

        Perform failure synthesis:
        1. Identify common failure patterns across iterations
        2. Determine root causes vs symptoms
        3. Design systematic fixes that address root causes
        4. Ensure fixes don't introduce new failure modes
        5. Provide comprehensive testing strategies

        Return your synthesis in this JSON format:
        {{
            "failure_synthesis": {{
                "common_patterns": ["..."],
                "root_causes": ["..."],
                "systematic_fixes": ["..."]
            }},
            "refined_code": "...",
            "improvements": ["..."],
            "confidence_score": 0.0-1.0,
            "reasoning": "..."
        }}
        """
        
        try:
            if hasattr(self.llm_client, 'chat'):
                response = await self.llm_client.chat.completions.create(
                    model=get_model_name(self.llm_client),
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2
                )
                content = response.choices[0].message.content
            else:
                response = await self.llm_client.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=2000,
                    temperature=0.2,
                    messages=[{"role": "user", "content": prompt}]
                )
                content = response.content[0].text
            
            # Try to extract JSON from the content
            # Sometimes LLMs add extra text before/after JSON
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
            else:
                result = json.loads(content)
            
            return RefinementResult(
                refined_code=result["refined_code"],
                confidence_score=result["confidence_score"],
                pattern_used=RefinementPattern.FAILURE_SYNTHESIS,
                improvements=result["improvements"],
                reasoning=result["reasoning"],
                metadata=result.get("failure_synthesis", {})
            )
            
        except Exception as e:
            logger.error(f"Failure synthesis refinement failed: {e}")
            logger.debug(f"Raw LLM response: {content[:500] if 'content' in locals() else 'No content'}")
            return RefinementResult(
                refined_code=context.original_code,
                confidence_score=0.1,
                pattern_used=RefinementPattern.FAILURE_SYNTHESIS,
                improvements=[],
                reasoning=f"Refinement failed: {str(e)}",
                metadata={"error": str(e)}
            )
    
    def _analyze_failures(self, context: RefinementContext) -> Dict:
        """Analyze failure patterns from context"""
        return {
            "validation_failures": context.validation_failures,
            "execution_results": context.execution_results,
            "iteration_count": len(context.previous_iterations),
            "complexity_score": context.complexity_score,
            "risk_factors": context.risk_factors
        }

class ReviewerEnsembleRefiner:
    """Uses multiple reviewer personas for comprehensive review"""
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.reviewer_prompts = {
            ReviewerPersona.SECURITY_ANALYST: """
            You are a security analyst reviewing code for vulnerabilities.
            Focus on: SQL injection, XSS, authentication flaws, data exposure, input validation.
            """,
            ReviewerPersona.PERFORMANCE_AUDITOR: """
            You are a performance auditor reviewing code for efficiency.
            Focus on: Algorithm complexity, memory usage, database queries, caching, scalability.
            """,
            ReviewerPersona.ARCHITECTURAL_PURIST: """
            You are an architectural purist reviewing code structure.
            Focus on: Design patterns, SOLID principles, modularity, separation of concerns.
            """,
            ReviewerPersona.USER_EXPERIENCE_ADVOCATE: """
            You are a UX advocate reviewing code for user impact.
            Focus on: Error handling, user feedback, accessibility, response times.
            """,
            ReviewerPersona.MAINTAINABILITY_GUARDIAN: """
            You are a maintainability guardian reviewing code for long-term health.
            Focus on: Code clarity, documentation, testability, technical debt.
            """
        }
    
    async def refine(self, context: RefinementContext) -> RefinementResult:
        """Refine code using reviewer ensemble"""
        
        # Get reviews from all personas
        reviews = await self._get_ensemble_reviews(context)
        
        # Synthesize consensus
        synthesis = await self._synthesize_consensus(context, reviews)
        
        return RefinementResult(
            refined_code=synthesis["refined_code"],
            confidence_score=synthesis["confidence_score"],
            pattern_used=RefinementPattern.REVIEWER_ENSEMBLE,
            improvements=synthesis["improvements"],
            reasoning=synthesis["reasoning"],
            metadata={"ensemble_reviews": reviews}
        )
    
    async def _get_ensemble_reviews(self, context: RefinementContext) -> Dict:
        """Get reviews from all reviewer personas"""
        reviews = {}
        
        for persona in ReviewerPersona:
            try:
                review = await self._get_persona_review(persona, context)
                reviews[persona.value] = review
            except Exception as e:
                logger.warning(f"Review from {persona.value} failed: {e}")
                reviews[persona.value] = {"error": str(e)}
        
        return reviews
    
    async def _get_persona_review(self, persona: ReviewerPersona, context: RefinementContext) -> Dict:
        """Get review from specific persona"""
        
        prompt = f"""
        {self.reviewer_prompts[persona]}

        Review this code from your specialized perspective:

        ORIGINAL REQUEST: {context.original_request}
        CODE TO REVIEW: {context.original_code}
        VALIDATION FAILURES: {context.validation_failures}

        Provide your specialized review in this JSON format:
        {{
            "issues_found": ["..."],
            "suggested_fixes": ["..."],
            "confidence": 0.0-1.0,
            "priority": "high|medium|low",
            "reasoning": "..."
        }}
        """
        
        try:
            if hasattr(self.llm_client, 'chat'):
                response = await self.llm_client.chat.completions.create(
                    model=get_model_name(self.llm_client),
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3
                )
                content = response.choices[0].message.content
            else:
                response = await self.llm_client.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=1500,
                    temperature=0.3,
                    messages=[{"role": "user", "content": prompt}]
                )
                content = response.content[0].text
            
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"Persona review failed for {persona.value}: {e}")
            return {"error": str(e)}
    
    async def _synthesize_consensus(self, context: RefinementContext, reviews: Dict) -> Dict:
        """Synthesize consensus from ensemble reviews"""
        
        prompt = f"""
        Synthesize a consensus from multiple expert reviews:

        ORIGINAL CODE: {context.original_code}
        EXPERT REVIEWS: {json.dumps(reviews, indent=2)}

        Create a consensus that:
        1. Prioritizes high-confidence, high-priority issues
        2. Resolves conflicts between reviewers
        3. Provides comprehensive refined code
        4. Explains the synthesis reasoning

        Return consensus in this JSON format:
        {{
            "consensus_issues": ["..."],
            "refined_code": "...",
            "improvements": ["..."],
            "confidence_score": 0.0-1.0,
            "reasoning": "..."
        }}
        """
        
        try:
            if hasattr(self.llm_client, 'chat'):
                response = await self.llm_client.chat.completions.create(
                    model=get_model_name(self.llm_client),
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3
                )
                content = response.choices[0].message.content
            else:
                response = await self.llm_client.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=2000,
                    temperature=0.3,
                    messages=[{"role": "user", "content": prompt}]
                )
                content = response.content[0].text
            
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"Consensus synthesis failed: {e}")
            return {
                "refined_code": context.original_code,
                "improvements": [],
                "confidence_score": 0.1,
                "reasoning": f"Synthesis failed: {str(e)}"
            }

class MetaCognitiveStrategySelector:
    """Selects optimal refinement strategy based on context"""
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.strategy_map = {
            RefinementPattern.INTENT_DIFFING: IntentDiffingRefiner,
            RefinementPattern.FAILURE_SYNTHESIS: FailureSynthesisRefiner,
            RefinementPattern.REVIEWER_ENSEMBLE: ReviewerEnsembleRefiner,
        }
    
    async def select_strategy(self, context: RefinementContext) -> RefinementPattern:
        """Select optimal refinement strategy"""
        
        # Simple heuristic-based selection for now
        # In production, this could use ML models
        
        if len(context.validation_failures) > 2:
            return RefinementPattern.FAILURE_SYNTHESIS
        
        if context.complexity_score > 0.7:
            return RefinementPattern.REVIEWER_ENSEMBLE
        
        if len(context.previous_iterations) == 0:
            return RefinementPattern.INTENT_DIFFING
        
        return RefinementPattern.REVIEWER_ENSEMBLE

class AITLRefinementOrchestrator:
    """Orchestrates the entire AITL refinement process"""
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.meta_selector = MetaCognitiveStrategySelector(llm_client)
        self.max_iterations = 5
        self.target_confidence = 0.9
    
    async def process_refinement(self, context: RefinementContext) -> AITLDecision:
        """Process code refinement using optimal strategy"""
        
        iteration = 0
        current_context = context
        refinement_history = []
        
        while iteration < self.max_iterations:
            # Select refinement strategy
            strategy = await self.meta_selector.select_strategy(current_context)
            
            # Get refiner for strategy
            refiner_class = self.meta_selector.strategy_map.get(strategy)
            if not refiner_class:
                logger.warning(f"No refiner found for strategy: {strategy}")
                break
            
            refiner = refiner_class(self.llm_client)
            
            # Perform refinement
            try:
                refinement_result = await refiner.refine(current_context)
                refinement_history.append(refinement_result)
                
                # Check if we've reached target confidence
                if refinement_result.confidence_score >= self.target_confidence:
                    return AITLDecision(
                        decision="approve",
                        confidence=refinement_result.confidence_score,
                        reasoning=f"Code refined to target confidence using {strategy.value}",
                        suggested_improvements=refinement_result.improvements,
                        metadata={
                            "refinement_history": refinement_history,
                            "final_strategy": strategy.value,
                            "iterations": iteration + 1
                        }
                    )
                
                # Update context for next iteration
                current_context.original_code = refinement_result.refined_code
                current_context.previous_iterations.append({
                    "iteration": iteration,
                    "strategy": strategy.value,
                    "confidence": refinement_result.confidence_score,
                    "improvements": refinement_result.improvements
                })
                
                iteration += 1
                
            except Exception as e:
                logger.error(f"Refinement iteration {iteration} failed: {e}")
                break
        
        # If we haven't reached target confidence after max iterations
        if refinement_history:
            best_result = max(refinement_history, key=lambda x: x.confidence_score)
            
            if best_result.confidence_score > 0.5:
                return AITLDecision(
                    decision="refine",
                    confidence=best_result.confidence_score,
                    reasoning=f"Partial refinement achieved using {best_result.pattern_used.value}",
                    suggested_improvements=best_result.improvements,
                    metadata={
                        "refinement_history": refinement_history,
                        "best_strategy": best_result.pattern_used.value,
                        "iterations": len(refinement_history)
                    }
                )
        
        # Escalate to human if refinement unsuccessful
        return AITLDecision(
            decision="escalate_to_human",
            confidence=0.0,
            reasoning="Automated refinement unsuccessful after maximum iterations",
            suggested_improvements=[],
            metadata={
                "refinement_history": refinement_history,
                "iterations": iteration,
                "reason": "max_iterations_reached"
            }
        )

# Legacy compatibility functions for existing system
async def convert_hitl_to_aitl(hitl_data: Dict) -> AITLDecision:
    """Convert HITL data to AITL decision format"""
    
    try:
        # Initialize with LLM client
        if settings.OPENAI_API_KEY:
            llm_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        elif settings.ANTHROPIC_API_KEY:
            llm_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        else:
            # Fallback to basic approval
            return AITLDecision(
                decision="approve",
                confidence=0.8,
                reasoning="No LLM client available - using fallback approval",
                suggested_improvements=[]
            )
        
        # Extract data from HITL format
        context = hitl_data.get("context", {})
        task = context.get("task", {})
        validation_result = context.get("validation_result", {})
        
        # Create refinement context
        refinement_context = RefinementContext(
            original_code=hitl_data.get("code", ""),
            original_request=task.get("description", ""),
            validation_failures=validation_result.get("checks", []),
            execution_results=context.get("execution_results", {}),
            complexity_score=task.get("complexity", 0.5),
            risk_factors=task.get("risk_factors", [])
        )
        
        # Initialize orchestrator
        orchestrator = AITLRefinementOrchestrator(llm_client)
        
        # Process refinement
        decision = await orchestrator.process_refinement(refinement_context)
        
        return decision
        
    except Exception as e:
        logger.error(f"AITL conversion failed: {e}")
        return AITLDecision(
            decision="escalate_to_human",
            confidence=0.0,
            reasoning=f"AITL processing failed: {str(e)}",
            suggested_improvements=[],
            metadata={"error": str(e)}
        )

# Initialize global orchestrator (will be created when needed)
_global_orchestrator = None

async def get_aitl_orchestrator():
    """Get global AITL orchestrator instance"""
    global _global_orchestrator
    
    if _global_orchestrator is None:
        # Initialize LLM client - prefer Azure OpenAI
        if settings.AZURE_OPENAI_API_KEY and settings.AZURE_OPENAI_ENDPOINT:
            logger.info("Using Azure OpenAI for AITL refinement")
            llm_client = AsyncAzureOpenAI(
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
            )
        elif settings.ANTHROPIC_API_KEY:
            logger.info("Using Anthropic Claude for AITL refinement")
            llm_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        elif settings.OPENAI_API_KEY:
            logger.warning("Using OpenAI for AITL refinement (may have quota issues)")
            llm_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        else:
            raise ValueError("No LLM client available for AITL orchestrator")
        
        _global_orchestrator = AITLRefinementOrchestrator(llm_client)
    
    return _global_orchestrator

# Legacy AITLDecision Enum for backward compatibility
class AITLDecisionEnum(Enum):
    APPROVED = "approved"
    APPROVED_WITH_MODIFICATIONS = "approved_with_modifications"
    REJECTED = "rejected"
    ESCALATE_TO_HUMAN = "escalate_to_human"
    REQUIRES_SENIOR_REVIEW = "requires_senior_review"

# Legacy compatibility - maintain existing interfaces
@dataclass
class AITLReviewResult:
    """Result of AITL review - legacy compatibility"""
    decision: AITLDecisionEnum
    confidence: float
    reasoning: str
    feedback: str
    modifications_required: List[str] = field(default_factory=list)
    security_issues: List[str] = field(default_factory=list)
    quality_score: float = 0.0
    estimated_fix_time: int = 0
    reviewer_tier: str = "T1"
    metadata: Dict[str, Any] = field(default_factory=dict)