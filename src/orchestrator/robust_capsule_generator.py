#!/usr/bin/env python3
"""
Robust QLCapsule Generator with Iterative Refinement
Ensures high-quality, production-ready code generation
"""

from typing import List, Dict, Optional, Any
import asyncio
from dataclasses import dataclass
from datetime import datetime
import structlog
import json

from src.common.models import ExecutionRequest, QLCapsule, ValidationReport, ValidationCheck, ValidationStatus
from src.orchestrator.enhanced_capsule import EnhancedCapsuleGenerator
from src.validation.capsule_validator import CapsuleValidator, ValidationResult, ValidationLevel
from src.agents.advanced_generation import EnhancedCodeGenerator, GenerationStrategy
from src.sandbox.client import SandboxServiceClient

logger = structlog.get_logger()


@dataclass
class RefinementFeedback:
    category: str  # "syntax", "logic", "performance", "security", "structure"
    severity: str  # "critical", "major", "minor"
    description: str
    suggested_fix: str
    code_section: Optional[str] = None


class RobustCapsuleGenerator:
    """
    Generates high-quality QLCapsules through iterative refinement
    Ensures capsules meet production standards
    """
    
    def __init__(self, 
                 max_iterations: int = 5,
                 target_score: float = 0.85,
                 target_metrics: Optional[Dict[str, Any]] = None):
        self.base_generator = EnhancedCapsuleGenerator()
        self.validator = CapsuleValidator()
        self.code_generator = EnhancedCodeGenerator()
        self.max_iterations = max_iterations
        self.target_score = target_score
        self.target_metrics = target_metrics or {
            "functional_score": 0.8,      # Most tests should pass
            "quality_score": 0.7,         # Good code quality
            "security_score": 0.8,        # Secure code
            "overall_score": self.target_score  # Use the provided target
        }
        self.refinement_history = []
    
    async def generate_robust_capsule(self, request: ExecutionRequest) -> QLCapsule:
        """
        Generate a capsule that meets all quality criteria through iterative refinement
        """
        
        logger.info(
            "Starting robust capsule generation",
            request_id=request.id,
            max_iterations=self.max_iterations,
            target_score=self.target_score
        )
        
        iteration = 0
        capsule = None
        validation_history = []
        
        while iteration < self.max_iterations:
            try:
                # Generate or refine capsule
                if iteration == 0:
                    logger.info("Generating initial capsule")
                    capsule = await self._generate_initial_capsule(request)
                else:
                    logger.info(f"Refining capsule (iteration {iteration + 1})")
                    capsule = await self._refine_capsule(
                        capsule,
                        validation_history[-1],
                        request
                    )
                
                # Comprehensive validation
                logger.info("Validating capsule")
                validation_results = await self.validator.validate_capsule(capsule)
                validation_history.append(validation_results)
                
                # Check if meets all targets
                if self._meets_targets(validation_results):
                    logger.info(
                        f"✅ Robust capsule achieved in {iteration + 1} iterations",
                        final_score=validation_results['overall'].score
                    )
                    
                    # Update metadata
                    capsule.metadata.update({
                        "refinement_iterations": iteration + 1,
                        "final_scores": {
                            level: result.score 
                            for level, result in validation_results.items()
                        },
                        "validation_passed": True,
                        "generation_strategy": "iterative_refinement"
                    })
                    
                    # Set validation report
                    capsule.validation_report = self._create_validation_report(validation_results)
                    
                    break
                
                # Log progress
                logger.info(
                    f"Iteration {iteration + 1} results",
                    overall_score=validation_results['overall'].score,
                    issues_count=len(validation_results['overall'].issues),
                    passed=validation_results['overall'].passed
                )
                
                # Check for improvement
                if iteration > 0 and not self._has_improved(validation_history):
                    logger.warning("No improvement detected, applying advanced strategies")
                    # Switch to more advanced generation strategy
                    request.metadata['force_strategy'] = GenerationStrategy.TEST_DRIVEN
                
                # Early termination if critical issues persist
                if iteration >= 2 and self._has_critical_issues(validation_results):
                    logger.error("Critical issues persist after multiple iterations")
                    break
                    
            except Exception as e:
                logger.error(f"Refinement iteration {iteration} failed: {e}", exc_info=True)
                if iteration == 0:
                    raise
                # Continue with best effort
                break
                
            iteration += 1
        
        # Final validation report
        if validation_history:
            final_validation = validation_history[-1]
            capsule.metadata['final_validation'] = {
                'passed': final_validation['overall'].passed,
                'score': final_validation['overall'].score,
                'iterations': len(validation_history)
            }
        
        logger.info(
            "Robust generation complete",
            iterations_used=iteration + 1,
            final_score=validation_history[-1]['overall'].score if validation_history else 0
        )
        
        return capsule
    
    async def _generate_initial_capsule(self, request: ExecutionRequest) -> QLCapsule:
        """Generate the initial capsule with high-quality settings"""
        
        # Force high-quality generation strategies
        enhanced_request = ExecutionRequest(
            id=request.id,
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            description=request.description,
            requirements=request.requirements,
            constraints={
                **(request.constraints or {}),
                "quality": "production",
                "testing": "comprehensive",
                "security": "strict",
                "documentation": "detailed"
            },
            metadata={
                **(request.metadata or {}),
                "generation_mode": "robust",
                "use_advanced": True
            }
        )
        
        # Generate with TEST_DRIVEN strategy for best quality
        return await self.base_generator.generate_capsule(enhanced_request, use_advanced=True)
    
    async def _refine_capsule(self, 
                             capsule: QLCapsule, 
                             validation_results: Dict[str, ValidationResult],
                             original_request: ExecutionRequest) -> QLCapsule:
        """Refine capsule based on validation feedback"""
        
        # Analyze validation results to create targeted feedback
        feedback = self._analyze_validation_results(validation_results)
        
        if not feedback:
            logger.warning("No specific feedback generated, returning original capsule")
            return capsule
        
        # Sort feedback by severity
        critical_feedback = [f for f in feedback if f.severity == "critical"]
        major_feedback = [f for f in feedback if f.severity == "major"]
        minor_feedback = [f for f in feedback if f.severity == "minor"]
        
        # Create refinement prompt
        refinement_prompt = self._create_refinement_prompt(
            original_request,
            capsule,
            critical_feedback,
            major_feedback,
            minor_feedback
        )
        
        # Generate refined code using the most reliable strategy
        logger.info(f"Applying {len(feedback)} refinements")
        
        refined_result = await self.code_generator.generate_enhanced(
            prompt=refinement_prompt,
            strategy=GenerationStrategy.TEST_DRIVEN,
            requirements={} if isinstance(original_request.requirements, str) else original_request.requirements,
            constraints=original_request.constraints
        )
        
        # Update capsule with refined code
        # refined_result.code is a string, so we need to handle it properly
        capsule.source_code = self._merge_code_improvements(
            capsule.source_code,
            refined_result.code
        )
        
        if refined_result.tests:
            capsule.tests = self._merge_test_improvements(
                capsule.tests,
                refined_result.tests
            )
        
        # Update metadata
        capsule.metadata['refinement_count'] = capsule.metadata.get('refinement_count', 0) + 1
        capsule.metadata['last_refinement'] = datetime.utcnow().isoformat()
        
        return capsule
    
    def _analyze_validation_results(self, results: Dict[str, ValidationResult]) -> List[RefinementFeedback]:
        """Convert validation results into actionable feedback"""
        
        feedback = []
        
        # Analyze each validation level
        for level, result in results.items():
            if level == 'overall':
                continue
                
            if not result.passed:
                # Convert issues to feedback
                for issue in result.issues[:5]:  # Top 5 issues
                    severity = "critical" if level == ValidationLevel.FUNCTIONAL else "major"
                    
                    feedback.append(RefinementFeedback(
                        category=level,
                        severity=severity,
                        description=issue,
                        suggested_fix=self._get_fix_suggestion(issue, result)
                    ))
        
        # Add specific feedback based on metrics
        if 'functional' in results:
            metrics = results['functional'].metrics
            
            if not metrics.get('all_tests_pass', True):
                feedback.append(RefinementFeedback(
                    category="testing",
                    severity="critical",
                    description="Tests are failing",
                    suggested_fix="Fix the implementation to pass all tests"
                ))
            
            if not metrics.get('has_tests', True):
                feedback.append(RefinementFeedback(
                    category="testing",
                    severity="major",
                    description="Missing test coverage",
                    suggested_fix="Add comprehensive unit tests with edge cases"
                ))
        
        if 'quality' in results:
            metrics = results['quality'].metrics
            
            if metrics.get('security_score', 1.0) < 0.9:
                feedback.append(RefinementFeedback(
                    category="security",
                    severity="critical",
                    description="Security vulnerabilities detected",
                    suggested_fix="Fix security issues: use parameterized queries, environment variables for secrets"
                ))
        
        return feedback
    
    def _create_refinement_prompt(self,
                                 request: ExecutionRequest,
                                 capsule: QLCapsule,
                                 critical: List[RefinementFeedback],
                                 major: List[RefinementFeedback],
                                 minor: List[RefinementFeedback]) -> str:
        """Create a detailed prompt for refinement"""
        
        prompt = f"""
You are refining code to meet production quality standards. The original request was:

"{request.description}"

The current implementation has issues that need to be fixed while maintaining all working functionality.

CRITICAL ISSUES (MUST fix all):
"""
        
        for feedback in critical:
            prompt += f"\n- {feedback.description}\n  Fix: {feedback.suggested_fix}\n"
        
        if major:
            prompt += "\n\nMAJOR ISSUES (fix as many as possible):\n"
            for feedback in major[:3]:  # Top 3 major issues
                prompt += f"- {feedback.description}\n  Fix: {feedback.suggested_fix}\n"
        
        prompt += f"""

Current Implementation:
```python
{self._get_main_code(capsule.source_code)}
```

Requirements:
1. Fix ALL critical issues
2. Maintain all working functionality
3. Ensure all tests pass
4. Follow security best practices
5. Add proper error handling and logging
6. Include comprehensive tests

Generate the corrected implementation with all issues resolved.
"""
        
        return prompt
    
    def _meets_targets(self, validation_results: Dict[str, ValidationResult]) -> bool:
        """Check if validation results meet all target metrics"""
        
        overall = validation_results.get('overall')
        if not overall:
            return False
        
        # Check overall score (primary criterion)
        if overall.score < self.target_score:
            logger.debug(f"Overall score {overall.score:.3f} < target {self.target_score}")
            return False
        
        # Check specific metrics
        for metric, target_value in self.target_metrics.items():
            if metric == "functional_score":
                actual = validation_results.get('functional', ValidationResult(ValidationLevel.FUNCTIONAL, False, 0, {}, [], [])).score
            elif metric == "quality_score":
                actual = validation_results.get('quality', ValidationResult(ValidationLevel.QUALITY, False, 0, {}, [], [])).score
            elif metric == "security_score":
                actual = validation_results.get('quality', ValidationResult(ValidationLevel.QUALITY, False, 0, {}, [], [])).metrics.get('security_score', 0)
            elif metric == "overall_score":
                actual = overall.score
            else:
                continue
            
            if actual < target_value:
                logger.debug(f"Metric {metric} below target: {actual} < {target_value}")
                return False
        
        # All targets met!
        return True
    
    def _has_improved(self, validation_history: List[Dict[str, ValidationResult]]) -> bool:
        """Check if there's improvement between iterations"""
        
        if len(validation_history) < 2:
            return True
        
        prev_score = validation_history[-2]['overall'].score
        curr_score = validation_history[-1]['overall'].score
        
        # Consider it improved if score increased by at least 0.05
        return curr_score > prev_score + 0.05
    
    def _has_critical_issues(self, validation_results: Dict[str, ValidationResult]) -> bool:
        """Check if there are persistent critical issues"""
        
        # Functional validation must pass
        functional = validation_results.get('functional')
        if functional and not functional.passed:
            return True
        
        # Security score must be acceptable
        quality = validation_results.get('quality')
        if quality and quality.metrics.get('security_score', 1.0) < 0.7:
            return True
        
        return False
    
    def _get_fix_suggestion(self, issue: str, result: ValidationResult) -> str:
        """Generate specific fix suggestions based on issue type"""
        
        issue_lower = issue.lower()
        
        if "syntax" in issue_lower:
            return "Fix syntax errors - check for missing colons, parentheses, or indentation"
        elif "import" in issue_lower:
            return "Add missing imports or install required packages"
        elif "test" in issue_lower and "fail" in issue_lower:
            return "Debug failing tests and fix the implementation logic"
        elif "security" in issue_lower:
            return "Remove hardcoded secrets, use environment variables, sanitize inputs"
        elif "error handling" in issue_lower:
            return "Add try-except blocks with specific error handling"
        elif "documentation" in issue_lower:
            return "Add docstrings to all functions and classes"
        elif "logging" in issue_lower:
            return "Add structured logging using the logging module"
        else:
            # Check recommendations
            if result.recommendations:
                return result.recommendations[0]
            return "Review and fix the identified issue"
    
    def _merge_code_improvements(self, original: Dict[str, str], refined: Any) -> Dict[str, str]:
        """Merge refined code with original structure"""
        
        # Make a copy to avoid modifying original
        result = original.copy()
        
        if isinstance(refined, str):
            # If refined is a single string, update the main file
            main_file = self._get_main_file(result)
            if main_file:
                result[main_file] = refined
            else:
                result['main.py'] = refined
        elif isinstance(refined, dict):
            # If refined is a dict, update each file
            result.update(refined)
        
        return result
    
    def _merge_test_improvements(self, original: Dict[str, str], refined: str) -> Dict[str, str]:
        """Merge refined tests with original"""
        
        # Make a copy to avoid modifying original
        result = original.copy()
        
        if isinstance(refined, str):
            # Update or add test file
            if result:
                test_file = list(result.keys())[0]
                result[test_file] = refined
            else:
                result = {'test_main.py': refined}
        
        return result
    
    def _get_main_file(self, source_code: Dict[str, str]) -> Optional[str]:
        """Find the main file in source code"""
        
        for name in ['main.py', 'app.py', '__main__.py']:
            if name in source_code:
                return name
        
        # Return first Python file
        for name in source_code:
            if name.endswith('.py'):
                return name
        
        return None
    
    def _get_main_code(self, source_code: Dict[str, str]) -> str:
        """Extract main code for prompt"""
        
        main_file = self._get_main_file(source_code)
        if main_file:
            return source_code[main_file]
        
        # Return first file
        if source_code:
            return list(source_code.values())[0]
        
        return ""
    
    def _create_validation_report(self, validation_results: Dict[str, ValidationResult]) -> ValidationReport:
        """Create a ValidationReport from results"""
        
        from uuid import uuid4
        
        checks = []
        
        # Convert each validation level to checks
        for level, result in validation_results.items():
            if level == 'overall':
                continue
                
            status = ValidationStatus.PASSED if result.passed else ValidationStatus.FAILED
            
            check = ValidationCheck(
                name=f"{level.title()} Validation",
                type=level,
                status=status,
                message=f"Score: {result.score:.2f}",
                details={
                    "metrics": result.metrics,
                    "issues": result.issues[:3]  # Top 3 issues
                },
                severity="error" if not result.passed else "info"
            )
            checks.append(check)
        
        overall = validation_results['overall']
        
        return ValidationReport(
            id=str(uuid4()),
            execution_id=str(uuid4()),
            overall_status=ValidationStatus.PASSED if overall.passed else ValidationStatus.FAILED,
            checks=checks,
            confidence_score=overall.score,
            requires_human_review=overall.score < 0.9,
            metadata={
                "iterations": len(self.refinement_history),
                "final_score": overall.score,
                "timestamp": datetime.utcnow().isoformat()
            }
        )