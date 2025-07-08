"""
AITL (AI-in-the-Loop) System
Intelligent code review and decision making system that replaces HITL with AI reviewers
"""

import asyncio
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import structlog
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from src.common.config import settings
from src.common.models import TaskResult, ValidationReport

logger = structlog.get_logger()


class AITLDecision(Enum):
    APPROVED = "approved"
    APPROVED_WITH_MODIFICATIONS = "approved_with_modifications"
    REJECTED = "rejected"
    ESCALATE_TO_HUMAN = "escalate_to_human"
    REQUIRES_SENIOR_REVIEW = "requires_senior_review"


@dataclass
class AITLReviewResult:
    """Result of AITL review"""
    decision: AITLDecision
    confidence: float
    reasoning: str
    feedback: str
    modifications_required: List[str] = field(default_factory=list)
    security_issues: List[str] = field(default_factory=list)
    quality_score: float = 0.0
    estimated_fix_time: int = 0  # minutes
    reviewer_tier: str = "T1"  # T1, T2, T3 based on complexity
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AITLRequest:
    """AITL review request"""
    request_id: str
    task_id: str
    code: str
    validation_result: ValidationReport
    task_context: Dict[str, Any]
    priority: str = "normal"
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


class IntelligentAITLReviewer:
    """
    Sophisticated AI reviewer that analyzes code quality, security, and makes decisions
    """
    
    def __init__(self):
        # Initialize multiple AI models for different review aspects
        if hasattr(settings, 'AZURE_OPENAI_ENDPOINT') and settings.AZURE_OPENAI_ENDPOINT:
            from openai import AsyncAzureOpenAI
            self.openai_client = AsyncAzureOpenAI(
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
            )
        else:
            self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            
        self.anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        
        # Review history for learning
        self.review_history: List[Dict[str, Any]] = []
        self.approval_patterns: Dict[str, float] = {}
        self.rejection_patterns: Dict[str, float] = {}
        
        # Review thresholds
        self.security_threshold = 0.8
        self.quality_threshold = 0.7
        self.confidence_threshold = 0.75
        
        logger.info("AITL Intelligent Reviewer initialized")
    
    async def conduct_comprehensive_review(self, request: AITLRequest) -> AITLReviewResult:
        """
        Conduct multi-tier comprehensive review of code submission
        """
        logger.info(f"Starting comprehensive AITL review for {request.request_id}")
        
        try:
            # Parallel review analysis
            security_analysis, quality_analysis, logic_analysis = await asyncio.gather(
                self._conduct_security_review(request),
                self._conduct_quality_review(request),
                self._conduct_logic_review(request)
            )
            
            # Synthesize results into final decision
            final_result = await self._synthesize_review_results(
                request, security_analysis, quality_analysis, logic_analysis
            )
            
            # Log decision for learning
            await self._log_review_decision(request, final_result)
            
            logger.info(f"AITL review complete: {final_result.decision.value} (confidence: {final_result.confidence:.2f})")
            return final_result
            
        except Exception as e:
            logger.error(f"AITL review failed: {e}")
            # Fallback to human escalation
            return AITLReviewResult(
                decision=AITLDecision.ESCALATE_TO_HUMAN,
                confidence=0.0,
                reasoning=f"AITL system error: {str(e)}",
                feedback="System encountered an error during review. Escalating to human reviewer.",
                reviewer_tier="SYSTEM_ERROR"
            )
    
    async def _conduct_security_review(self, request: AITLRequest) -> Dict[str, Any]:
        """Specialized security-focused review"""
        prompt = f"""
        As a senior security engineer, conduct a thorough security review of this code:
        
        Code:
        ```
        {request.code}
        ```
        
        Validation Issues Found:
        {json.dumps([issue.__dict__ if hasattr(issue, '__dict__') else str(issue) for issue in request.validation_result.checks], indent=2)}
        
        Analyze for:
        1. Authentication/Authorization flaws
        2. Input validation vulnerabilities
        3. SQL injection, XSS, CSRF risks
        4. Hardcoded secrets or credentials
        5. Encryption/hashing weaknesses
        6. Rate limiting and DoS protection
        7. Error handling that leaks information
        8. Dependency vulnerabilities
        
        Return JSON:
        {{
            "security_score": 0.0-1.0,
            "critical_issues": ["issue1", "issue2"],
            "warnings": ["warning1", "warning2"],
            "recommendations": ["rec1", "rec2"],
            "compliance_status": "compliant|non_compliant|needs_review",
            "exploit_risk": "low|medium|high|critical",
            "remediation_time": "minutes_to_fix"
        }}
        """
        
        try:
            response = await self.anthropic_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return json.loads(response.content[0].text)
            
        except Exception as e:
            logger.error(f"Security review failed: {e}")
            return {
                "security_score": 0.3,
                "critical_issues": ["Security review system error"],
                "warnings": [],
                "recommendations": ["Manual security review required"],
                "compliance_status": "needs_review",
                "exploit_risk": "unknown",
                "remediation_time": 60
            }
    
    async def _conduct_quality_review(self, request: AITLRequest) -> Dict[str, Any]:
        """Code quality and best practices review"""
        prompt = f"""
        As a senior software architect, review this code for quality and best practices:
        
        Code:
        ```
        {request.code}
        ```
        
        Task Context: {json.dumps(request.task_context, indent=2)}
        
        Evaluate:
        1. Code structure and organization
        2. Naming conventions and readability
        3. Error handling and robustness
        4. Performance considerations
        5. Maintainability and extensibility
        6. Test coverage and testability
        7. Documentation quality
        8. Framework/library usage patterns
        
        Return JSON:
        {{
            "quality_score": 0.0-1.0,
            "maintainability": 0.0-1.0,
            "readability": 0.0-1.0,
            "performance": 0.0-1.0,
            "issues": ["issue1", "issue2"],
            "improvements": ["improvement1", "improvement2"],
            "code_smells": ["smell1", "smell2"],
            "technical_debt": "low|medium|high",
            "refactor_needed": true/false
        }}
        """
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a senior software architect specializing in code quality assessment."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Quality review failed: {e}")
            return {
                "quality_score": 0.5,
                "maintainability": 0.5,
                "readability": 0.5,
                "performance": 0.5,
                "issues": ["Quality review system error"],
                "improvements": [],
                "code_smells": [],
                "technical_debt": "unknown",
                "refactor_needed": False
            }
    
    async def _conduct_logic_review(self, request: AITLRequest) -> Dict[str, Any]:
        """Logic correctness and algorithmic review"""
        prompt = f"""
        As a senior software engineer, analyze the logic and correctness of this code:
        
        Code:
        ```
        {request.code}
        ```
        
        Task Requirements: {request.task_context.get('description', 'Not specified')}
        
        Analyze:
        1. Correctness of algorithms and logic
        2. Edge case handling
        3. Data flow and state management
        4. Business logic implementation
        5. Error conditions and exceptions
        6. Input/output validation
        7. Boundary conditions
        8. Requirement fulfillment
        
        Return JSON:
        {{
            "logic_score": 0.0-1.0,
            "correctness": 0.0-1.0,
            "completeness": 0.0-1.0,
            "edge_case_coverage": 0.0-1.0,
            "logic_errors": ["error1", "error2"],
            "missing_functionality": ["missing1", "missing2"],
            "algorithm_issues": ["algo1", "algo2"],
            "requirement_compliance": 0.0-1.0,
            "needs_testing": true/false
        }}
        """
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a senior software engineer specializing in algorithm correctness and logic analysis."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Logic review failed: {e}")
            return {
                "logic_score": 0.5,
                "correctness": 0.5,
                "completeness": 0.5,
                "edge_case_coverage": 0.5,
                "logic_errors": ["Logic review system error"],
                "missing_functionality": [],
                "algorithm_issues": [],
                "requirement_compliance": 0.5,
                "needs_testing": True
            }
    
    async def _synthesize_review_results(self, request: AITLRequest, 
                                       security: Dict, quality: Dict, 
                                       logic: Dict) -> AITLReviewResult:
        """Synthesize all review results into final decision"""
        
        # Calculate composite scores
        security_score = security.get("security_score", 0.0)
        quality_score = quality.get("quality_score", 0.0)
        logic_score = logic.get("logic_score", 0.0)
        
        # Weighted overall score (security is most important)
        overall_score = (security_score * 0.5 + quality_score * 0.3 + logic_score * 0.2)
        
        # Determine decision based on scores and issues
        decision = self._determine_decision(security, quality, logic, overall_score)
        
        # Calculate confidence based on consistency of analysis
        confidence = self._calculate_confidence(security, quality, logic, overall_score)
        
        # Generate comprehensive feedback
        feedback = self._generate_feedback(security, quality, logic, decision)
        
        # Collect all required modifications
        modifications = []
        modifications.extend(security.get("recommendations", []))
        modifications.extend(quality.get("improvements", []))
        modifications.extend(logic.get("missing_functionality", []))
        
        # Collect security issues
        security_issues = []
        security_issues.extend(security.get("critical_issues", []))
        security_issues.extend(security.get("warnings", []))
        
        # Estimate fix time
        fix_time = max(
            security.get("remediation_time", 30),
            30 if quality.get("refactor_needed", False) else 15,
            15 if logic.get("needs_testing", False) else 5
        )
        
        # Determine reviewer tier based on complexity
        reviewer_tier = self._determine_reviewer_tier(security, quality, logic)
        
        return AITLReviewResult(
            decision=decision,
            confidence=confidence,
            reasoning=self._generate_reasoning(security, quality, logic, decision),
            feedback=feedback,
            modifications_required=modifications[:10],  # Limit to top 10
            security_issues=security_issues[:5],  # Limit to top 5
            quality_score=overall_score,
            estimated_fix_time=fix_time,
            reviewer_tier=reviewer_tier,
            metadata={
                "security_analysis": security,
                "quality_analysis": quality,
                "logic_analysis": logic,
                "review_timestamp": datetime.utcnow().isoformat(),
                "validation_issues": len(request.validation_result.checks)
            }
        )
    
    def _determine_decision(self, security: Dict, quality: Dict, 
                          logic: Dict, overall_score: float) -> AITLDecision:
        """Determine final decision based on analysis results"""
        
        # Critical security issues = immediate rejection
        if security.get("exploit_risk") == "critical":
            return AITLDecision.REJECTED
        
        # Multiple critical issues = rejection
        critical_count = len(security.get("critical_issues", [])) + len(logic.get("logic_errors", []))
        if critical_count >= 3:
            return AITLDecision.REJECTED
        
        # Low overall score = rejection
        if overall_score < 0.4:
            return AITLDecision.REJECTED
        
        # High security risk but fixable = approved with modifications
        if security.get("exploit_risk") in ["medium", "high"] and overall_score >= 0.6:
            return AITLDecision.APPROVED_WITH_MODIFICATIONS
        
        # Quality issues but security OK = approved with modifications
        if security.get("security_score", 0) >= 0.7 and overall_score >= 0.6:
            if quality.get("technical_debt") == "high" or logic.get("needs_testing"):
                return AITLDecision.APPROVED_WITH_MODIFICATIONS
        
        # Complex issues require senior review
        if (security.get("compliance_status") == "needs_review" or 
            quality.get("refactor_needed") or 
            len(logic.get("algorithm_issues", [])) > 2):
            return AITLDecision.REQUIRES_SENIOR_REVIEW
        
        # High score = approval
        if overall_score >= 0.8:
            return AITLDecision.APPROVED
        
        # Medium score = approved with modifications
        if overall_score >= 0.6:
            return AITLDecision.APPROVED_WITH_MODIFICATIONS
        
        # Uncertain = escalate to human
        return AITLDecision.ESCALATE_TO_HUMAN
    
    def _calculate_confidence(self, security: Dict, quality: Dict, 
                            logic: Dict, overall_score: float) -> float:
        """Calculate confidence in the review decision"""
        
        # Base confidence from scores consistency
        scores = [
            security.get("security_score", 0.5),
            quality.get("quality_score", 0.5), 
            logic.get("logic_score", 0.5)
        ]
        
        # Calculate variance in scores
        mean_score = sum(scores) / len(scores)
        variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
        consistency = max(0, 1 - variance * 4)  # Lower variance = higher confidence
        
        # Boost confidence for clear decisions
        if overall_score > 0.8 or overall_score < 0.4:
            consistency += 0.1
        
        # Reduce confidence for edge cases
        if 0.5 <= overall_score <= 0.7:
            consistency -= 0.1
        
        return min(max(consistency, 0.1), 0.95)
    
    def _generate_feedback(self, security: Dict, quality: Dict, 
                         logic: Dict, decision: AITLDecision) -> str:
        """Generate comprehensive human-readable feedback"""
        
        feedback_parts = []
        
        # Decision header
        decision_emoji = {
            AITLDecision.APPROVED: "✅",
            AITLDecision.APPROVED_WITH_MODIFICATIONS: "⚠️",
            AITLDecision.REJECTED: "❌",
            AITLDecision.ESCALATE_TO_HUMAN: "🔄",
            AITLDecision.REQUIRES_SENIOR_REVIEW: "👑"
        }
        
        feedback_parts.append(f"{decision_emoji.get(decision, '❓')} **{decision.value.upper().replace('_', ' ')}**")
        
        # Security feedback
        if security.get("critical_issues"):
            feedback_parts.append("\n🔒 **Critical Security Issues:**")
            for issue in security.get("critical_issues", [])[:3]:
                feedback_parts.append(f"- {issue}")
        
        # Quality feedback
        quality_score = quality.get("quality_score", 0.5)
        if quality_score < 0.7:
            feedback_parts.append("\n📊 **Quality Concerns:**")
            for issue in quality.get("issues", [])[:3]:
                feedback_parts.append(f"- {issue}")
        
        # Logic feedback
        if logic.get("logic_errors"):
            feedback_parts.append("\n🧠 **Logic Issues:**")
            for error in logic.get("logic_errors", [])[:3]:
                feedback_parts.append(f"- {error}")
        
        # Positive feedback
        if decision in [AITLDecision.APPROVED, AITLDecision.APPROVED_WITH_MODIFICATIONS]:
            feedback_parts.append("\n✨ **Strengths:**")
            if security.get("security_score", 0) >= 0.8:
                feedback_parts.append("- Strong security implementation")
            if quality.get("readability", 0) >= 0.8:
                feedback_parts.append("- Good code readability")
            if logic.get("correctness", 0) >= 0.8:
                feedback_parts.append("- Sound logic implementation")
        
        # Recommendations
        if decision != AITLDecision.REJECTED:
            all_recommendations = []
            all_recommendations.extend(security.get("recommendations", []))
            all_recommendations.extend(quality.get("improvements", []))
            
            if all_recommendations:
                feedback_parts.append("\n🎯 **Recommendations:**")
                for rec in all_recommendations[:5]:
                    feedback_parts.append(f"- {rec}")
        
        return "\n".join(feedback_parts)
    
    def _generate_reasoning(self, security: Dict, quality: Dict, 
                          logic: Dict, decision: AITLDecision) -> str:
        """Generate technical reasoning for the decision"""
        
        reasoning_parts = []
        
        # Score summary
        sec_score = security.get("security_score", 0)
        qual_score = quality.get("quality_score", 0)
        log_score = logic.get("logic_score", 0)
        
        reasoning_parts.append(f"Analysis scores: Security={sec_score:.2f}, Quality={qual_score:.2f}, Logic={log_score:.2f}")
        
        # Key decision factors
        if decision == AITLDecision.REJECTED:
            reasoning_parts.append("Rejection due to:")
            if security.get("exploit_risk") == "critical":
                reasoning_parts.append("- Critical security vulnerabilities")
            if len(security.get("critical_issues", [])) > 2:
                reasoning_parts.append("- Multiple critical issues")
            if log_score < 0.4:
                reasoning_parts.append("- Fundamental logic errors")
        
        elif decision == AITLDecision.APPROVED_WITH_MODIFICATIONS:
            reasoning_parts.append("Approved with modifications due to:")
            if security.get("warnings"):
                reasoning_parts.append("- Security warnings that can be addressed")
            if quality.get("technical_debt") == "medium":
                reasoning_parts.append("- Manageable technical debt")
            if logic.get("needs_testing"):
                reasoning_parts.append("- Additional testing required")
        
        return " ".join(reasoning_parts)
    
    def _determine_reviewer_tier(self, security: Dict, quality: Dict, logic: Dict) -> str:
        """Determine appropriate reviewer tier based on complexity"""
        
        complexity_score = 0
        
        # Security complexity
        if security.get("exploit_risk") in ["high", "critical"]:
            complexity_score += 2
        if len(security.get("critical_issues", [])) > 1:
            complexity_score += 1
        
        # Quality complexity
        if quality.get("refactor_needed"):
            complexity_score += 1
        if quality.get("technical_debt") == "high":
            complexity_score += 1
        
        # Logic complexity
        if len(logic.get("algorithm_issues", [])) > 2:
            complexity_score += 2
        if logic.get("requirement_compliance", 1.0) < 0.6:
            complexity_score += 1
        
        if complexity_score >= 4:
            return "T3"  # Senior architect level
        elif complexity_score >= 2:
            return "T2"  # Senior engineer level
        else:
            return "T1"  # Standard engineer level
    
    async def _log_review_decision(self, request: AITLRequest, result: AITLReviewResult):
        """Log the review decision for learning and audit"""
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request.request_id,
            "task_id": request.task_id,
            "decision": result.decision.value,
            "confidence": result.confidence,
            "quality_score": result.quality_score,
            "reviewer_tier": result.reviewer_tier,
            "security_issues_count": len(result.security_issues),
            "modifications_count": len(result.modifications_required),
            "estimated_fix_time": result.estimated_fix_time,
            "validation_checks": len(request.validation_result.checks),
            "task_complexity": request.task_context.get("complexity", "unknown"),
            "code_length": len(request.code),
            "metadata": result.metadata
        }
        
        self.review_history.append(log_entry)
        
        # Update learning patterns
        if result.decision == AITLDecision.APPROVED:
            self._update_approval_patterns(log_entry)
        elif result.decision == AITLDecision.REJECTED:
            self._update_rejection_patterns(log_entry)
        
        logger.info("AITL decision logged", **log_entry)
    
    def _update_approval_patterns(self, log_entry: Dict):
        """Update patterns that lead to approvals"""
        pattern_key = f"{log_entry.get('task_complexity', 'unknown')}_{log_entry.get('reviewer_tier', 'T1')}"
        if pattern_key not in self.approval_patterns:
            self.approval_patterns[pattern_key] = 0.0
        self.approval_patterns[pattern_key] = (self.approval_patterns[pattern_key] * 0.9 + 
                                             log_entry.get('quality_score', 0.5) * 0.1)
    
    def _update_rejection_patterns(self, log_entry: Dict):
        """Update patterns that lead to rejections"""
        pattern_key = f"{log_entry.get('task_complexity', 'unknown')}_{log_entry.get('reviewer_tier', 'T1')}"
        if pattern_key not in self.rejection_patterns:
            self.rejection_patterns[pattern_key] = 0.0
        self.rejection_patterns[pattern_key] = (self.rejection_patterns[pattern_key] * 0.9 + 
                                              (1.0 - log_entry.get('quality_score', 0.5)) * 0.1)
    
    async def get_review_statistics(self) -> Dict[str, Any]:
        """Get comprehensive review statistics"""
        
        if not self.review_history:
            return {"message": "No reviews conducted yet"}
        
        recent_reviews = self.review_history[-100:]  # Last 100 reviews
        
        # Decision distribution
        decisions = [r["decision"] for r in recent_reviews]
        decision_counts = {decision.value: decisions.count(decision.value) for decision in AITLDecision}
        
        # Average metrics
        avg_confidence = sum(r["confidence"] for r in recent_reviews) / len(recent_reviews)
        avg_quality = sum(r["quality_score"] for r in recent_reviews) / len(recent_reviews)
        avg_fix_time = sum(r["estimated_fix_time"] for r in recent_reviews) / len(recent_reviews)
        
        # Tier distribution
        tiers = [r["reviewer_tier"] for r in recent_reviews]
        tier_counts = {"T1": tiers.count("T1"), "T2": tiers.count("T2"), "T3": tiers.count("T3")}
        
        return {
            "total_reviews": len(self.review_history),
            "recent_reviews": len(recent_reviews),
            "decision_distribution": decision_counts,
            "average_confidence": round(avg_confidence, 3),
            "average_quality_score": round(avg_quality, 3),
            "average_fix_time_minutes": round(avg_fix_time, 1),
            "reviewer_tier_distribution": tier_counts,
            "approval_patterns": dict(list(self.approval_patterns.items())[:5]),
            "rejection_patterns": dict(list(self.rejection_patterns.items())[:5]),
            "security_threshold": self.security_threshold,
            "quality_threshold": self.quality_threshold,
            "confidence_threshold": self.confidence_threshold
        }


class AITLOrchestrator:
    """
    Orchestrates AITL reviews and manages the workflow
    """
    
    def __init__(self):
        self.reviewer = IntelligentAITLReviewer()
        self.pending_requests: Dict[str, AITLRequest] = {}
        self.completed_reviews: Dict[str, AITLReviewResult] = {}
        self.escalation_queue: List[str] = []
        
        logger.info("AITL Orchestrator initialized")
    
    async def submit_for_aitl_review(self, request: AITLRequest) -> str:
        """Submit a request for AITL review"""
        
        # Set expiration if not provided
        if not request.expires_at:
            request.expires_at = datetime.utcnow() + timedelta(hours=2)
        
        self.pending_requests[request.request_id] = request
        
        logger.info(f"AITL request submitted: {request.request_id}")
        
        # Process immediately for high priority
        if request.priority == "high":
            return await self.process_aitl_request(request.request_id)
        
        return request.request_id
    
    async def process_aitl_request(self, request_id: str) -> str:
        """Process a specific AITL request"""
        
        if request_id not in self.pending_requests:
            raise ValueError(f"Request {request_id} not found")
        
        request = self.pending_requests[request_id]
        
        # Check expiration
        if request.expires_at and datetime.utcnow() > request.expires_at:
            logger.warning(f"AITL request {request_id} expired")
            # Move to escalation queue
            self.escalation_queue.append(request_id)
            return "expired"
        
        try:
            # Conduct review
            result = await self.reviewer.conduct_comprehensive_review(request)
            
            # Store result
            self.completed_reviews[request_id] = result
            
            # Remove from pending
            del self.pending_requests[request_id]
            
            # Handle escalations
            if result.decision in [AITLDecision.ESCALATE_TO_HUMAN, AITLDecision.REQUIRES_SENIOR_REVIEW]:
                self.escalation_queue.append(request_id)
                logger.info(f"AITL request {request_id} escalated: {result.decision.value}")
            
            logger.info(f"AITL request {request_id} processed: {result.decision.value}")
            return result.decision.value
            
        except Exception as e:
            logger.error(f"Failed to process AITL request {request_id}: {e}")
            # Escalate on error
            self.escalation_queue.append(request_id)
            return "error_escalated"
    
    async def process_all_pending(self) -> Dict[str, str]:
        """Process all pending AITL requests"""
        
        results = {}
        pending_ids = list(self.pending_requests.keys())
        
        logger.info(f"Processing {len(pending_ids)} pending AITL requests")
        
        for request_id in pending_ids:
            try:
                result = await self.process_aitl_request(request_id)
                results[request_id] = result
            except Exception as e:
                logger.error(f"Failed to process {request_id}: {e}")
                results[request_id] = "error"
        
        return results
    
    def get_aitl_status(self) -> Dict[str, Any]:
        """Get current AITL system status"""
        
        return {
            "pending_requests": len(self.pending_requests),
            "completed_reviews": len(self.completed_reviews),
            "escalation_queue": len(self.escalation_queue),
            "pending_ids": list(self.pending_requests.keys()),
            "escalated_ids": self.escalation_queue[-10:],  # Last 10 escalations
            "system_status": "operational",
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def get_aitl_result(self, request_id: str) -> Optional[AITLReviewResult]:
        """Get AITL review result for a specific request"""
        return self.completed_reviews.get(request_id)
    
    async def get_aitl_statistics(self) -> Dict[str, Any]:
        """Get comprehensive AITL statistics"""
        reviewer_stats = await self.reviewer.get_review_statistics()
        system_stats = self.get_aitl_status()
        
        return {
            "system_status": system_stats,
            "review_statistics": reviewer_stats,
            "performance_metrics": {
                "total_processed": len(self.completed_reviews),
                "escalation_rate": len(self.escalation_queue) / max(len(self.completed_reviews), 1),
                "average_processing_time": "< 2 minutes",  # Estimated
                "success_rate": (len(self.completed_reviews) - len(self.escalation_queue)) / max(len(self.completed_reviews), 1)
            }
        }


# Global AITL instance
aitl_orchestrator = AITLOrchestrator()


async def convert_hitl_to_aitl(hitl_request: Dict[str, Any]) -> AITLReviewResult:
    """
    Convert a HITL request to AITL and process it
    """
    
    # Extract validation result from HITL context
    validation_result = ValidationReport(
        id=hitl_request["context"]["validation_result"]["id"],
        execution_id=hitl_request["context"]["validation_result"].get("execution_id", ""),
        checks=hitl_request["context"]["validation_result"]["checks"],
        confidence_score=hitl_request["context"]["validation_result"]["confidence_score"],
        overall_status=hitl_request["context"]["validation_result"]["overall_status"],
        requires_human_review=hitl_request["context"]["validation_result"]["requires_human_review"]
    )
    
    # Create AITL request
    aitl_request = AITLRequest(
        request_id=hitl_request["request_id"],
        task_id=hitl_request["context"]["task"]["task_id"],
        code=hitl_request["code"],
        validation_result=validation_result,
        task_context=hitl_request["context"]["task"],
        priority=hitl_request.get("priority", "normal")
    )
    
    # Submit for AITL review
    await aitl_orchestrator.submit_for_aitl_review(aitl_request)
    
    # Process immediately
    await aitl_orchestrator.process_aitl_request(aitl_request.request_id)
    
    # Return result
    return aitl_orchestrator.get_aitl_result(aitl_request.request_id)