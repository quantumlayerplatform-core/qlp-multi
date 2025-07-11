#!/usr/bin/env python3
"""
Capsule Critic Agent
An intelligent agent that critically evaluates capsule quality and usefulness
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import json
import asyncio
import structlog

from src.common.models import QLCapsule, ExecutionRequest
from src.agents.base_agents import Agent
from src.common.models import AgentTier
from src.agents.azure_llm_client import llm_client, LLMProvider

logger = structlog.get_logger()


class CriticDimension(str, Enum):
    """Dimensions for capsule criticism"""
    TASK_ALIGNMENT = "task_alignment"
    CORRECTNESS = "correctness"
    COMPLETENESS = "completeness"
    REUSABILITY = "reusability"
    MAINTAINABILITY = "maintainability"
    PERFORMANCE = "performance"
    SECURITY = "security"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    DELIVERY_READINESS = "delivery_readiness"


@dataclass
class CriticScore:
    """Individual dimension score"""
    dimension: CriticDimension
    score: float  # 0-100
    reasoning: str
    issues: List[str]
    suggestions: List[str]


@dataclass
class CapsuleCritique:
    """Complete capsule critique"""
    capsule_id: str
    overall_usefulness: float  # 0-100
    is_useful: bool
    confidence: float
    dimension_scores: List[CriticScore]
    overall_reasoning: str
    key_strengths: List[str]
    key_weaknesses: List[str]
    improvement_priorities: List[Dict[str, Any]]
    recommendation: str  # "use_as_is", "use_with_modifications", "regenerate", "human_review"
    metadata: Dict[str, Any]


class CapsuleCriticAgent(Agent):
    """Agent that critically evaluates capsule quality"""
    
    def __init__(self, agent_id: str = "capsule-critic", llm_client_instance=None):
        super().__init__(
            agent_id=agent_id,
            tier=AgentTier.T2
        )
        self.name = "CapsuleCritic"
        self.capabilities = ["critique", "evaluation", "quality_assessment"]
        self.llm_client_instance = llm_client_instance or llm_client
        
        # Scoring weights for overall usefulness
        self.dimension_weights = {
            CriticDimension.TASK_ALIGNMENT: 0.25,      # Most important
            CriticDimension.CORRECTNESS: 0.20,         # Critical
            CriticDimension.COMPLETENESS: 0.15,        # Important
            CriticDimension.TESTING: 0.10,             # Important
            CriticDimension.DELIVERY_READINESS: 0.10,  # Important
            CriticDimension.REUSABILITY: 0.05,         # Nice to have
            CriticDimension.MAINTAINABILITY: 0.05,     # Nice to have
            CriticDimension.PERFORMANCE: 0.05,         # Context dependent
            CriticDimension.SECURITY: 0.03,            # Context dependent
            CriticDimension.DOCUMENTATION: 0.02        # Nice to have
        }
    
    async def _query_llm(self, prompt: str) -> str:
        """Query the LLM for analysis"""
        try:
            # Use the azure_llm_client's query method
            response = await self.llm_client_instance.query(
                prompt=prompt,
                model="gpt-4",  # Use GPT-4 for better critique quality
                max_tokens=1000,
                temperature=0.3  # Lower temperature for more consistent analysis
            )
            return response
        except Exception as e:
            logger.error(f"Error querying LLM: {str(e)}")
            return "Unable to generate analysis due to LLM error."
    
    async def critique_capsule(
        self,
        capsule: QLCapsule,
        request: ExecutionRequest,
        context: Optional[Dict[str, Any]] = None
    ) -> CapsuleCritique:
        """Perform comprehensive critique of capsule"""
        
        logger.info(
            "Starting capsule critique",
            capsule_id=capsule.id,
            request_id=request.id
        )
        
        # Evaluate each dimension
        dimension_scores = []
        
        # 1. Task Alignment
        task_score = await self._evaluate_task_alignment(capsule, request)
        dimension_scores.append(task_score)
        
        # 2. Correctness
        correctness_score = await self._evaluate_correctness(capsule)
        dimension_scores.append(correctness_score)
        
        # 3. Completeness
        completeness_score = await self._evaluate_completeness(capsule, request)
        dimension_scores.append(completeness_score)
        
        # 4. Testing
        testing_score = await self._evaluate_testing(capsule)
        dimension_scores.append(testing_score)
        
        # 5. Delivery Readiness
        delivery_score = await self._evaluate_delivery_readiness(capsule)
        dimension_scores.append(delivery_score)
        
        # 6. Other dimensions
        for dimension in [
            CriticDimension.REUSABILITY,
            CriticDimension.MAINTAINABILITY,
            CriticDimension.PERFORMANCE,
            CriticDimension.SECURITY,
            CriticDimension.DOCUMENTATION
        ]:
            score = await self._evaluate_dimension(capsule, dimension)
            dimension_scores.append(score)
        
        # Calculate overall usefulness
        overall_usefulness = self._calculate_overall_usefulness(dimension_scores)
        
        # Generate overall assessment
        overall_assessment = await self._generate_overall_assessment(
            capsule, request, dimension_scores, overall_usefulness
        )
        
        # Determine recommendation
        recommendation = self._determine_recommendation(
            overall_usefulness, dimension_scores
        )
        
        # Extract key insights
        key_strengths = self._extract_strengths(dimension_scores)
        key_weaknesses = self._extract_weaknesses(dimension_scores)
        improvement_priorities = self._prioritize_improvements(dimension_scores)
        
        critique = CapsuleCritique(
            capsule_id=capsule.id,
            overall_usefulness=overall_usefulness,
            is_useful=overall_usefulness >= 70,  # 70% threshold for usefulness
            confidence=self._calculate_confidence(dimension_scores),
            dimension_scores=dimension_scores,
            overall_reasoning=overall_assessment,
            key_strengths=key_strengths,
            key_weaknesses=key_weaknesses,
            improvement_priorities=improvement_priorities,
            recommendation=recommendation,
            metadata={
                "critique_timestamp": datetime.utcnow().isoformat(),
                "critic_version": "1.0",
                "request_description": request.description[:200],
                "capsule_file_count": len(capsule.source_code) + len(capsule.tests or {}),
                "has_tests": bool(capsule.tests),
                "has_documentation": bool(capsule.documentation)
            }
        )
        
        logger.info(
            "Capsule critique complete",
            capsule_id=capsule.id,
            overall_usefulness=overall_usefulness,
            is_useful=critique.is_useful,
            recommendation=recommendation
        )
        
        return critique
    
    async def _evaluate_task_alignment(
        self, 
        capsule: QLCapsule, 
        request: ExecutionRequest
    ) -> CriticScore:
        """Evaluate how well the capsule aligns with the requested task"""
        
        prompt = f"""
        Evaluate how well this generated code aligns with the user's request.
        
        User Request:
        {request.description}
        
        Requirements:
        {json.dumps(request.requirements, indent=2) if request.requirements else "None specified"}
        
        Generated Code Summary:
        - Files: {list(capsule.source_code.keys())}
        - Has Tests: {bool(capsule.tests)}
        - Language: {capsule.manifest.get('language', 'unknown')}
        
        Code Sample (first file):
        ```
        {list(capsule.source_code.values())[0][:500] if capsule.source_code else "No code"}
        ```
        
        Evaluate:
        1. Does the code solve the requested problem?
        2. Are all requirements addressed?
        3. Are there unnecessary features added?
        4. Is the solution approach appropriate?
        
        Provide a score 0-100 and detailed analysis.
        """
        
        response = await self._query_llm(prompt)
        
        # Parse LLM response to extract score and analysis
        score, reasoning, issues, suggestions = self._parse_evaluation_response(response)
        
        return CriticScore(
            dimension=CriticDimension.TASK_ALIGNMENT,
            score=score,
            reasoning=reasoning,
            issues=issues,
            suggestions=suggestions
        )
    
    async def _evaluate_correctness(self, capsule: QLCapsule) -> CriticScore:
        """Evaluate code correctness"""
        
        prompt = f"""
        Evaluate the correctness of this code:
        
        Language: {capsule.manifest.get('language', 'unknown')}
        
        Code Files:
        {self._format_code_for_review(capsule.source_code)}
        
        Check for:
        1. Syntax errors
        2. Logic errors
        3. Runtime errors
        4. Edge case handling
        5. Error handling
        
        Provide a score 0-100 and identify any correctness issues.
        """
        
        response = await self._query_llm(prompt)
        score, reasoning, issues, suggestions = self._parse_evaluation_response(response)
        
        return CriticScore(
            dimension=CriticDimension.CORRECTNESS,
            score=score,
            reasoning=reasoning,
            issues=issues,
            suggestions=suggestions
        )
    
    async def _evaluate_completeness(
        self, 
        capsule: QLCapsule, 
        request: ExecutionRequest
    ) -> CriticScore:
        """Evaluate if the capsule is complete"""
        
        checklist = {
            "has_main_functionality": bool(capsule.source_code),
            "has_tests": bool(capsule.tests),
            "has_documentation": bool(capsule.documentation),
            "has_error_handling": False,  # Will check in code
            "has_configuration": any("config" in f.lower() for f in capsule.source_code.keys()),
            "has_dependencies": any(f in capsule.source_code for f in ["requirements.txt", "package.json", "go.mod"]),
            "has_deployment": any("docker" in f.lower() or "deploy" in f.lower() for f in capsule.source_code.keys())
        }
        
        # Check for error handling in code
        code_content = " ".join(capsule.source_code.values())
        checklist["has_error_handling"] = any(
            keyword in code_content.lower() 
            for keyword in ["try", "catch", "except", "error", "exception"]
        )
        
        completeness_ratio = sum(checklist.values()) / len(checklist)
        base_score = completeness_ratio * 100
        
        issues = []
        suggestions = []
        
        if not checklist["has_tests"]:
            issues.append("No tests provided")
            suggestions.append("Add comprehensive unit tests")
        
        if not checklist["has_documentation"]:
            issues.append("No documentation provided")
            suggestions.append("Add README with usage instructions")
        
        if not checklist["has_error_handling"]:
            issues.append("Limited error handling detected")
            suggestions.append("Add proper error handling and validation")
        
        reasoning = f"Completeness score based on {sum(checklist.values())}/{len(checklist)} components present"
        
        return CriticScore(
            dimension=CriticDimension.COMPLETENESS,
            score=base_score,
            reasoning=reasoning,
            issues=issues,
            suggestions=suggestions
        )
    
    async def _evaluate_testing(self, capsule: QLCapsule) -> CriticScore:
        """Evaluate test quality and coverage"""
        
        if not capsule.tests:
            return CriticScore(
                dimension=CriticDimension.TESTING,
                score=0,
                reasoning="No tests provided",
                issues=["No test files found"],
                suggestions=["Add comprehensive test suite with unit and integration tests"]
            )
        
        # Analyze test quality
        test_content = " ".join(capsule.tests.values())
        test_count = test_content.lower().count("def test_") + test_content.lower().count("it(") + test_content.lower().count("test(")
        
        # Estimate coverage based on test/code ratio
        code_size = sum(len(content) for content in capsule.source_code.values())
        test_size = sum(len(content) for content in capsule.tests.values())
        test_ratio = test_size / max(code_size, 1)
        
        # Calculate score
        base_score = min(100, test_count * 10)  # 10 points per test, max 100
        ratio_bonus = min(30, test_ratio * 100)  # Bonus for test/code ratio
        score = min(100, base_score + ratio_bonus)
        
        issues = []
        suggestions = []
        
        if test_count < 5:
            issues.append(f"Only {test_count} tests found")
            suggestions.append("Add more test cases to improve coverage")
        
        if test_ratio < 0.3:
            issues.append("Low test-to-code ratio")
            suggestions.append("Increase test coverage to at least 80%")
        
        reasoning = f"Found {test_count} tests with {test_ratio:.1%} test-to-code ratio"
        
        return CriticScore(
            dimension=CriticDimension.TESTING,
            score=score,
            reasoning=reasoning,
            issues=issues,
            suggestions=suggestions
        )
    
    async def _evaluate_delivery_readiness(self, capsule: QLCapsule) -> CriticScore:
        """Evaluate if capsule is ready for delivery"""
        
        readiness_checklist = {
            "has_entrypoint": any("main" in f for f in capsule.source_code.keys()),
            "has_dependencies": any(f in capsule.source_code for f in ["requirements.txt", "package.json", "go.mod", "pom.xml"]),
            "has_dockerfile": any("dockerfile" in f.lower() for f in capsule.source_code.keys()),
            "has_ci_cd": any("github" in f or "gitlab" in f or "jenkins" in f for f in capsule.source_code.keys()),
            "has_readme": any("readme" in f.lower() for f in capsule.source_code.keys()),
            "validation_passed": capsule.validation_report and capsule.validation_report.overall_status == "passed" if capsule.validation_report else False
        }
        
        ready_count = sum(readiness_checklist.values())
        score = (ready_count / len(readiness_checklist)) * 100
        
        issues = []
        suggestions = []
        
        if not readiness_checklist["has_entrypoint"]:
            issues.append("No clear entry point found")
            suggestions.append("Add a main file or entry point")
        
        if not readiness_checklist["has_dockerfile"]:
            issues.append("No Dockerfile for containerization")
            suggestions.append("Add Dockerfile for easy deployment")
        
        if not readiness_checklist["has_ci_cd"]:
            issues.append("No CI/CD configuration")
            suggestions.append("Add GitHub Actions or similar CI/CD pipeline")
        
        reasoning = f"{ready_count}/{len(readiness_checklist)} delivery requirements met"
        
        return CriticScore(
            dimension=CriticDimension.DELIVERY_READINESS,
            score=score,
            reasoning=reasoning,
            issues=issues,
            suggestions=suggestions
        )
    
    async def _evaluate_dimension(
        self, 
        capsule: QLCapsule, 
        dimension: CriticDimension
    ) -> CriticScore:
        """Generic dimension evaluation"""
        
        dimension_prompts = {
            CriticDimension.REUSABILITY: "Evaluate code modularity, coupling, and reusability",
            CriticDimension.MAINTAINABILITY: "Evaluate code readability, structure, and maintainability",
            CriticDimension.PERFORMANCE: "Evaluate potential performance issues and optimizations",
            CriticDimension.SECURITY: "Evaluate security practices and potential vulnerabilities",
            CriticDimension.DOCUMENTATION: "Evaluate code comments and documentation quality"
        }
        
        prompt = f"""
        {dimension_prompts.get(dimension, f"Evaluate {dimension.value}")}
        
        Code to review:
        {self._format_code_for_review(capsule.source_code, max_chars=2000)}
        
        Provide a score 0-100 and analysis.
        """
        
        response = await self._query_llm(prompt)
        score, reasoning, issues, suggestions = self._parse_evaluation_response(response)
        
        return CriticScore(
            dimension=dimension,
            score=score,
            reasoning=reasoning,
            issues=issues,
            suggestions=suggestions
        )
    
    def _calculate_overall_usefulness(self, dimension_scores: List[CriticScore]) -> float:
        """Calculate weighted overall usefulness score"""
        
        total_score = 0
        total_weight = 0
        
        for score in dimension_scores:
            weight = self.dimension_weights.get(score.dimension, 0)
            total_score += score.score * weight
            total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0
    
    async def _generate_overall_assessment(
        self,
        capsule: QLCapsule,
        request: ExecutionRequest,
        dimension_scores: List[CriticScore],
        overall_usefulness: float
    ) -> str:
        """Generate natural language overall assessment"""
        
        prompt = f"""
        Provide an overall assessment of this code capsule:
        
        Request: {request.description[:200]}
        
        Dimension Scores:
        {self._format_dimension_scores(dimension_scores)}
        
        Overall Usefulness Score: {overall_usefulness:.1f}/100
        
        Write a 2-3 sentence summary explaining:
        1. Whether this capsule successfully addresses the user's request
        2. The main strengths and weaknesses
        3. Whether it's ready for use or needs improvements
        """
        
        response = await self._query_llm(prompt)
        return response.strip()
    
    def _determine_recommendation(
        self, 
        overall_score: float, 
        dimension_scores: List[CriticScore]
    ) -> str:
        """Determine recommendation based on scores"""
        
        # Check critical dimensions
        task_alignment = next((s for s in dimension_scores if s.dimension == CriticDimension.TASK_ALIGNMENT), None)
        correctness = next((s for s in dimension_scores if s.dimension == CriticDimension.CORRECTNESS), None)
        
        # Critical failures
        if task_alignment and task_alignment.score < 50:
            return "regenerate"  # Doesn't solve the problem
        
        if correctness and correctness.score < 60:
            return "human_review"  # Has correctness issues
        
        # Based on overall score
        if overall_score >= 85:
            return "use_as_is"
        elif overall_score >= 70:
            return "use_with_modifications"
        elif overall_score >= 50:
            return "human_review"
        else:
            return "regenerate"
    
    def _extract_strengths(self, dimension_scores: List[CriticScore]) -> List[str]:
        """Extract key strengths from dimension scores"""
        
        strengths = []
        for score in dimension_scores:
            if score.score >= 80:
                strengths.append(f"Strong {score.dimension.value.replace('_', ' ')}: {score.reasoning}")
        
        return strengths[:3]  # Top 3 strengths
    
    def _extract_weaknesses(self, dimension_scores: List[CriticScore]) -> List[str]:
        """Extract key weaknesses from dimension scores"""
        
        weaknesses = []
        for score in dimension_scores:
            if score.score < 60:
                weaknesses.append(f"Weak {score.dimension.value.replace('_', ' ')}: {score.issues[0] if score.issues else score.reasoning}")
        
        return weaknesses[:3]  # Top 3 weaknesses
    
    def _prioritize_improvements(self, dimension_scores: List[CriticScore]) -> List[Dict[str, Any]]:
        """Prioritize improvements based on impact"""
        
        improvements = []
        
        for score in dimension_scores:
            if score.score < 80 and score.suggestions:
                priority = "high" if score.score < 50 else "medium" if score.score < 70 else "low"
                impact = self.dimension_weights.get(score.dimension, 0) * (100 - score.score)
                
                improvements.append({
                    "dimension": score.dimension.value,
                    "current_score": score.score,
                    "suggestion": score.suggestions[0],
                    "priority": priority,
                    "impact_score": impact
                })
        
        # Sort by impact score
        improvements.sort(key=lambda x: x["impact_score"], reverse=True)
        
        return improvements[:5]  # Top 5 improvements
    
    def _calculate_confidence(self, dimension_scores: List[CriticScore]) -> float:
        """Calculate confidence in the critique"""
        
        # Higher confidence if scores are consistent
        scores = [s.score for s in dimension_scores]
        avg_score = sum(scores) / len(scores)
        variance = sum((s - avg_score) ** 2 for s in scores) / len(scores)
        
        # Lower variance = higher confidence
        confidence = max(0.5, 1 - (variance / 1000))
        
        return min(0.95, confidence)
    
    def _format_code_for_review(self, source_code: Dict[str, str], max_chars: int = 3000) -> str:
        """Format code for LLM review"""
        
        formatted = []
        char_count = 0
        
        for filename, content in source_code.items():
            if char_count >= max_chars:
                formatted.append("... (truncated)")
                break
            
            remaining = max_chars - char_count
            truncated_content = content[:remaining] if len(content) > remaining else content
            
            formatted.append(f"\n--- {filename} ---\n{truncated_content}")
            char_count += len(truncated_content)
        
        return "\n".join(formatted)
    
    def _format_dimension_scores(self, dimension_scores: List[CriticScore]) -> str:
        """Format dimension scores for display"""
        
        formatted = []
        for score in dimension_scores:
            formatted.append(f"- {score.dimension.value}: {score.score:.1f}/100 - {score.reasoning}")
        
        return "\n".join(formatted)
    
    def _parse_evaluation_response(self, response: str) -> Tuple[float, str, List[str], List[str]]:
        """Parse LLM evaluation response"""
        
        # This is a simplified parser - in production, use structured output
        lines = response.strip().split('\n')
        
        # Extract score (look for number 0-100)
        score = 75  # Default
        for line in lines:
            if "score:" in line.lower():
                try:
                    score = float(line.split(":")[-1].strip().rstrip('/100'))
                    break
                except:
                    pass
        
        # Extract reasoning (first substantial paragraph)
        reasoning = "Evaluation complete"
        for line in lines:
            if len(line) > 50 and not line.startswith('-'):
                reasoning = line.strip()
                break
        
        # Extract issues and suggestions (bullet points)
        issues = []
        suggestions = []
        
        current_section = None
        for line in lines:
            if "issues:" in line.lower() or "problems:" in line.lower():
                current_section = "issues"
            elif "suggestions:" in line.lower() or "recommendations:" in line.lower():
                current_section = "suggestions"
            elif line.strip().startswith('-') or line.strip().startswith('•'):
                content = line.strip().lstrip('-•').strip()
                if current_section == "issues":
                    issues.append(content)
                elif current_section == "suggestions":
                    suggestions.append(content)
        
        return score, reasoning, issues, suggestions


async def example_usage():
    """Example of using the Capsule Critic Agent"""
    
    # Create a sample capsule
    capsule = QLCapsule(
        id="test-capsule-001",
        title="User Management API",
        description="FastAPI user management system",
        source_code={
            "main.py": """
from fastapi import FastAPI
app = FastAPI()

@app.get("/users")
def get_users():
    return [{"id": 1, "name": "Test User"}]
""",
            "requirements.txt": "fastapi==0.104.1\nuvicorn==0.24.0"
        },
        tests={},  # No tests - will be criticized
        documentation="Basic user API",
        manifest={"language": "python"}
    )
    
    # Create request
    request = ExecutionRequest(
        id="req-001",
        tenant_id="test",
        user_id="user1",
        description="Create a REST API for user management with CRUD operations, authentication, and proper error handling"
    )
    
    # Create critic agent
    critic = CapsuleCriticAgent()
    
    # Perform critique
    critique = await critic.critique_capsule(capsule, request)
    
    # Display results
    print(f"\n🔍 CAPSULE CRITIQUE REPORT")
    print(f"{'='*50}")
    print(f"Capsule ID: {critique.capsule_id}")
    print(f"Overall Usefulness: {critique.overall_usefulness:.1f}/100")
    print(f"Is Useful: {'✅ Yes' if critique.is_useful else '❌ No'}")
    print(f"Recommendation: {critique.recommendation.upper()}")
    print(f"\n📊 Dimension Scores:")
    for score in critique.dimension_scores:
        print(f"  - {score.dimension.value}: {score.score:.1f}/100")
    print(f"\n💪 Key Strengths:")
    for strength in critique.key_strengths:
        print(f"  - {strength}")
    print(f"\n⚠️  Key Weaknesses:")
    for weakness in critique.key_weaknesses:
        print(f"  - {weakness}")
    print(f"\n🎯 Improvement Priorities:")
    for priority in critique.improvement_priorities[:3]:
        print(f"  - [{priority['priority'].upper()}] {priority['suggestion']}")
    print(f"\n📝 Overall Assessment:")
    print(f"{critique.overall_reasoning}")


if __name__ == "__main__":
    asyncio.run(example_usage())