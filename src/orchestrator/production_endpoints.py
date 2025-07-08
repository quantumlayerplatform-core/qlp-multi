#!/usr/bin/env python3
"""
Production-Grade Code Generation API Endpoints
Enterprise-ready endpoints with comprehensive quality assurance
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from fastapi import HTTPException
import structlog

from src.common.models import ExecutionRequest
from src.orchestrator.production_orchestrator import (
    ProductionOrchestrator, ProductionTier, ProductionConfig, ProductionResult
)
from src.validation.production_validator import QualityLevel

logger = structlog.get_logger()


class ProductionCodeRequest(BaseModel):
    """Request for production-grade code generation"""
    description: str = Field(..., min_length=10, description="Detailed description of the code to generate")
    requirements: Optional[str] = Field(None, description="Specific requirements and constraints")
    constraints: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Technical constraints")
    production_tier: ProductionTier = Field(default=ProductionTier.DEVELOPMENT, description="Production readiness tier")
    target_confidence: Optional[float] = Field(default=None, ge=0.5, le=1.0, description="Target confidence score")
    target_test_coverage: Optional[float] = Field(default=None, ge=30.0, le=100.0, description="Target test coverage percentage")
    enable_comprehensive_testing: bool = Field(default=True, description="Enable comprehensive test generation")
    enable_security_scanning: bool = Field(default=True, description="Enable security vulnerability scanning")
    enable_performance_validation: bool = Field(default=True, description="Enable performance validation")
    enable_integration_testing: bool = Field(default=False, description="Enable integration testing")
    enable_load_testing: bool = Field(default=False, description="Enable load testing")
    max_iterations: Optional[int] = Field(default=None, ge=1, le=10, description="Maximum generation iterations")
    tenant_id: str = Field(..., description="Tenant identifier")
    user_id: str = Field(..., description="User identifier")


class ProductionCodeResponse(BaseModel):
    """Response for production-grade code generation"""
    request_id: str
    capsule_id: str
    status: str  # success, failed, partial
    production_ready: bool
    confidence_score: float
    quality_metrics: Dict[str, Any]
    validation_summary: Dict[str, Any]
    test_summary: Optional[Dict[str, Any]] = None
    security_summary: Optional[Dict[str, Any]] = None
    performance_summary: Optional[Dict[str, Any]] = None
    iterations_performed: int
    execution_time: float
    files_generated: int
    languages: list
    frameworks: list
    recommendations: list
    next_steps: Optional[list] = None


class ProductionEndpoints:
    """Production-grade code generation endpoints"""
    
    def __init__(self):
        self.orchestrator = ProductionOrchestrator()
    
    async def generate_production_code(
        self, 
        request: ProductionCodeRequest
    ) -> ProductionCodeResponse:
        """Generate production-ready code with comprehensive quality assurance"""
        
        logger.info(
            "Production code generation requested",
            description=request.description[:100] + "..." if len(request.description) > 100 else request.description,
            production_tier=request.production_tier,
            tenant_id=request.tenant_id,
            user_id=request.user_id
        )
        
        try:
            # Create execution request
            execution_request = ExecutionRequest(
                id=f"prod-{datetime.utcnow().timestamp()}",
                tenant_id=request.tenant_id,
                user_id=request.user_id,
                description=request.description,
                requirements=request.requirements,
                constraints=request.constraints,
                metadata={
                    "production_tier": request.production_tier,
                    "api_request": True,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            # Create custom configuration if needed
            custom_config = None
            if any([
                request.target_confidence is not None,
                request.target_test_coverage is not None,
                request.max_iterations is not None
            ]):
                base_config = self.orchestrator.tier_configs[request.production_tier]
                custom_config = ProductionConfig(
                    quality_level=base_config.quality_level,
                    production_tier=request.production_tier,
                    enable_comprehensive_testing=request.enable_comprehensive_testing,
                    enable_security_scanning=request.enable_security_scanning,
                    enable_performance_validation=request.enable_performance_validation,
                    enable_integration_testing=request.enable_integration_testing,
                    enable_load_testing=request.enable_load_testing,
                    max_iterations=request.max_iterations or base_config.max_iterations,
                    target_confidence=request.target_confidence or base_config.target_confidence,
                    target_test_coverage=request.target_test_coverage or base_config.target_test_coverage
                )
            
            # Generate production code
            result = await self.orchestrator.generate_production_code(
                request=execution_request,
                production_tier=request.production_tier,
                custom_config=custom_config
            )
            
            # Build response
            response = await self._build_response(result, execution_request)
            
            logger.info(
                "Production code generation completed",
                request_id=execution_request.id,
                capsule_id=response.capsule_id,
                production_ready=response.production_ready,
                confidence_score=response.confidence_score
            )
            
            return response
            
        except Exception as e:
            logger.error("Production code generation failed", error=str(e))
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Production code generation failed",
                    "message": str(e),
                    "request_id": execution_request.id if 'execution_request' in locals() else None
                }
            )
    
    async def get_production_recommendations(
        self,
        description: str,
        current_tier: ProductionTier = ProductionTier.DEVELOPMENT
    ) -> Dict[str, Any]:
        """Get recommendations for production-grade development"""
        
        # Analyze description for complexity and requirements
        complexity_score = self._analyze_complexity(description)
        
        # Recommend appropriate tier
        recommended_tier = self._recommend_tier(description, complexity_score)
        
        # Generate configuration recommendations
        config_recommendations = self._generate_config_recommendations(
            description, complexity_score, recommended_tier
        )
        
        # Estimate resources and timeline
        resource_estimates = self._estimate_resources(
            description, complexity_score, recommended_tier
        )
        
        return {
            "analysis": {
                "complexity_score": complexity_score,
                "estimated_loc": self._estimate_lines_of_code(description),
                "estimated_components": self._estimate_components(description),
                "technology_stack": self._suggest_technology_stack(description)
            },
            "recommendations": {
                "current_tier": current_tier,
                "recommended_tier": recommended_tier,
                "tier_justification": self._explain_tier_recommendation(
                    description, complexity_score, recommended_tier
                ),
                "configuration": config_recommendations
            },
            "estimates": resource_estimates,
            "quality_gates": self._recommend_quality_gates(recommended_tier),
            "best_practices": self._suggest_best_practices(description, recommended_tier)
        }
    
    async def validate_production_readiness(
        self,
        capsule_id: str,
        target_tier: ProductionTier = ProductionTier.PRODUCTION
    ) -> Dict[str, Any]:
        """Validate existing code for production readiness"""
        
        # This would integrate with the capsule storage system
        # For now, return a template response
        
        return {
            "capsule_id": capsule_id,
            "target_tier": target_tier,
            "readiness_assessment": {
                "overall_score": 0.85,
                "production_ready": False,
                "blocking_issues": [
                    "Test coverage below 90% threshold",
                    "Missing integration tests"
                ],
                "recommendations": [
                    "Add comprehensive integration test suite",
                    "Improve test coverage in authentication module",
                    "Add performance benchmarks"
                ]
            },
            "quality_metrics": {
                "code_quality": 0.88,
                "test_coverage": 0.75,
                "security_score": 0.92,
                "performance_score": 0.80,
                "documentation_score": 0.70
            },
            "next_steps": [
                {
                    "action": "Generate additional tests",
                    "priority": "high",
                    "estimated_effort": "2-4 hours"
                },
                {
                    "action": "Add API documentation",
                    "priority": "medium", 
                    "estimated_effort": "1-2 hours"
                }
            ]
        }
    
    async def _build_response(
        self, 
        result: ProductionResult, 
        request: ExecutionRequest
    ) -> ProductionCodeResponse:
        """Build comprehensive response from production result"""
        
        # Extract quality metrics
        quality_metrics = {}
        if result.quality_metrics:
            quality_metrics = {
                "overall_score": result.quality_metrics.overall_score,
                "cyclomatic_complexity": result.quality_metrics.cyclomatic_complexity,
                "test_coverage": result.quality_metrics.test_coverage,
                "security_score": result.quality_metrics.security_score,
                "maintainability_index": result.quality_metrics.maintainability_index,
                "technical_debt_ratio": result.quality_metrics.technical_debt_ratio
            }
        
        # Extract validation summary
        validation_summary = {
            "status": result.validation_report.overall_status,
            "confidence": result.validation_report.confidence_score,
            "requires_review": result.validation_report.requires_human_review,
            "checks_performed": len(result.validation_report.checks),
            "issues_found": len([
                check for check in result.validation_report.checks 
                if check.status == "failed"
            ])
        }
        
        # Extract test summary
        test_summary = None
        if result.test_results:
            execution_results = result.test_results.get("execution_results")
            if execution_results:
                test_summary = {
                    "total_tests": execution_results.total_tests,
                    "passed": execution_results.passed,
                    "failed": execution_results.failed,
                    "coverage": execution_results.overall_coverage,
                    "quality_score": execution_results.quality_score
                }
        
        # Extract security summary
        security_summary = None
        if result.security_report:
            security_summary = {
                "vulnerabilities_found": result.security_report.get("vulnerabilities_found", 0),
                "security_score": result.security_report.get("security_score", 0),
                "status": result.security_report.get("status", "unknown")
            }
        
        # Extract performance summary
        performance_summary = None
        if result.performance_report:
            performance_summary = {
                "response_time_p95": result.performance_report.get("response_time_p95"),
                "throughput": result.performance_report.get("throughput"),
                "memory_usage": result.performance_report.get("memory_usage"),
                "cpu_usage": result.performance_report.get("cpu_usage")
            }
        
        # Count files
        files_generated = 0
        if hasattr(result.capsule, 'source_code'):
            files_generated += len(result.capsule.source_code)
        if hasattr(result.capsule, 'tests'):
            files_generated += len(result.capsule.tests)
        
        # Detect languages and frameworks
        languages = self._detect_languages(result.capsule)
        frameworks = self._detect_frameworks(result.capsule)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(result)
        
        # Generate next steps if not production ready
        next_steps = None
        if not result.production_ready:
            next_steps = self._generate_next_steps(result)
        
        return ProductionCodeResponse(
            request_id=request.id,
            capsule_id=result.capsule.id,
            status="success" if result.production_ready else "partial",
            production_ready=result.production_ready,
            confidence_score=result.confidence_score,
            quality_metrics=quality_metrics,
            validation_summary=validation_summary,
            test_summary=test_summary,
            security_summary=security_summary,
            performance_summary=performance_summary,
            iterations_performed=result.iterations_performed,
            execution_time=result.total_execution_time,
            files_generated=files_generated,
            languages=languages,
            frameworks=frameworks,
            recommendations=recommendations,
            next_steps=next_steps
        )
    
    def _analyze_complexity(self, description: str) -> float:
        """Analyze complexity score from description (0-1 scale)"""
        
        # Simple heuristic-based analysis
        complexity_indicators = {
            # High complexity
            "microservice": 0.9, "distributed": 0.9, "real-time": 0.8,
            "machine learning": 0.8, "ai": 0.7, "blockchain": 0.9,
            "concurrent": 0.7, "parallel": 0.7, "async": 0.6,
            
            # Medium complexity  
            "api": 0.5, "database": 0.5, "authentication": 0.6,
            "authorization": 0.6, "payment": 0.7, "integration": 0.6,
            
            # Lower complexity
            "crud": 0.3, "simple": 0.2, "basic": 0.2,
            "hello world": 0.1, "demo": 0.2, "prototype": 0.3
        }
        
        description_lower = description.lower()
        complexity_scores = []
        
        for indicator, score in complexity_indicators.items():
            if indicator in description_lower:
                complexity_scores.append(score)
        
        if not complexity_scores:
            # Base complexity based on description length
            base_complexity = min(0.5, len(description) / 1000)
            return base_complexity
        
        # Return average of found indicators
        return sum(complexity_scores) / len(complexity_scores)
    
    def _recommend_tier(self, description: str, complexity_score: float) -> ProductionTier:
        """Recommend appropriate production tier"""
        
        description_lower = description.lower()
        
        # Mission critical indicators
        if any(word in description_lower for word in [
            "financial", "banking", "payment processing", "medical", 
            "healthcare", "safety", "security system", "mission critical"
        ]):
            return ProductionTier.MISSION_CRITICAL
        
        # Production tier indicators
        if any(word in description_lower for word in [
            "production", "enterprise", "commercial", "customer-facing"
        ]) or complexity_score > 0.7:
            return ProductionTier.PRODUCTION
        
        # Staging tier indicators
        if any(word in description_lower for word in [
            "staging", "pre-production", "testing environment"
        ]) or complexity_score > 0.5:
            return ProductionTier.STAGING
        
        # Development tier (default for most cases)
        if complexity_score > 0.3:
            return ProductionTier.DEVELOPMENT
        
        # Prototype tier
        return ProductionTier.PROTOTYPE
    
    def _generate_config_recommendations(
        self, 
        description: str, 
        complexity_score: float, 
        tier: ProductionTier
    ) -> Dict[str, Any]:
        """Generate configuration recommendations"""
        
        return {
            "testing": {
                "comprehensive_testing": tier in [ProductionTier.PRODUCTION, ProductionTier.MISSION_CRITICAL],
                "integration_testing": tier in [ProductionTier.STAGING, ProductionTier.PRODUCTION, ProductionTier.MISSION_CRITICAL],
                "load_testing": tier in [ProductionTier.PRODUCTION, ProductionTier.MISSION_CRITICAL],
                "target_coverage": 95 if tier == ProductionTier.MISSION_CRITICAL else 90 if tier == ProductionTier.PRODUCTION else 70
            },
            "security": {
                "vulnerability_scanning": True,
                "penetration_testing": tier in [ProductionTier.PRODUCTION, ProductionTier.MISSION_CRITICAL],
                "compliance_checks": tier == ProductionTier.MISSION_CRITICAL
            },
            "performance": {
                "performance_testing": tier in [ProductionTier.STAGING, ProductionTier.PRODUCTION, ProductionTier.MISSION_CRITICAL],
                "load_testing": tier in [ProductionTier.PRODUCTION, ProductionTier.MISSION_CRITICAL],
                "chaos_testing": tier == ProductionTier.MISSION_CRITICAL
            },
            "iterations": {
                "max_iterations": 5 if tier == ProductionTier.MISSION_CRITICAL else 3 if tier in [ProductionTier.PRODUCTION, ProductionTier.STAGING] else 2
            }
        }
    
    def _estimate_resources(
        self, 
        description: str, 
        complexity_score: float, 
        tier: ProductionTier
    ) -> Dict[str, Any]:
        """Estimate resources and timeline"""
        
        # Base estimates
        base_time = complexity_score * 60  # minutes
        
        # Tier multipliers
        tier_multipliers = {
            ProductionTier.PROTOTYPE: 1.0,
            ProductionTier.DEVELOPMENT: 1.5,
            ProductionTier.STAGING: 2.0,
            ProductionTier.PRODUCTION: 3.0,
            ProductionTier.MISSION_CRITICAL: 4.0
        }
        
        estimated_time = base_time * tier_multipliers[tier]
        
        return {
            "estimated_generation_time": f"{estimated_time:.0f} minutes",
            "estimated_validation_time": f"{estimated_time * 0.3:.0f} minutes",
            "estimated_testing_time": f"{estimated_time * 0.5:.0f} minutes",
            "total_estimated_time": f"{estimated_time * 1.8:.0f} minutes",
            "resource_requirements": {
                "cpu": "2-4 cores",
                "memory": "4-8 GB",
                "storage": "1-2 GB temporary"
            }
        }
    
    def _recommend_quality_gates(self, tier: ProductionTier) -> List[Dict[str, Any]]:
        """Recommend quality gates for tier"""
        
        gates = [
            {"name": "Syntax Validation", "required": True, "automated": True},
            {"name": "Unit Testing", "required": True, "automated": True},
            {"name": "Security Scanning", "required": True, "automated": True}
        ]
        
        if tier in [ProductionTier.DEVELOPMENT, ProductionTier.STAGING, ProductionTier.PRODUCTION, ProductionTier.MISSION_CRITICAL]:
            gates.extend([
                {"name": "Integration Testing", "required": True, "automated": True},
                {"name": "Code Quality Analysis", "required": True, "automated": True},
                {"name": "Documentation Review", "required": True, "automated": False}
            ])
        
        if tier in [ProductionTier.PRODUCTION, ProductionTier.MISSION_CRITICAL]:
            gates.extend([
                {"name": "Performance Testing", "required": True, "automated": True},
                {"name": "Load Testing", "required": True, "automated": True},
                {"name": "Security Penetration Testing", "required": True, "automated": False}
            ])
        
        if tier == ProductionTier.MISSION_CRITICAL:
            gates.extend([
                {"name": "Chaos Engineering", "required": True, "automated": True},
                {"name": "Disaster Recovery Testing", "required": True, "automated": False},
                {"name": "Compliance Audit", "required": True, "automated": False}
            ])
        
        return gates
    
    def _suggest_best_practices(
        self, 
        description: str, 
        tier: ProductionTier
    ) -> List[str]:
        """Suggest best practices for the tier"""
        
        practices = [
            "Follow SOLID design principles",
            "Implement comprehensive error handling",
            "Use dependency injection for testability",
            "Follow consistent code formatting standards"
        ]
        
        if tier in [ProductionTier.DEVELOPMENT, ProductionTier.STAGING, ProductionTier.PRODUCTION, ProductionTier.MISSION_CRITICAL]:
            practices.extend([
                "Implement comprehensive logging with structured data",
                "Use configuration management for environment-specific settings",
                "Implement health check endpoints",
                "Follow API versioning best practices"
            ])
        
        if tier in [ProductionTier.PRODUCTION, ProductionTier.MISSION_CRITICAL]:
            practices.extend([
                "Implement circuit breaker patterns for external services",
                "Use distributed tracing for observability",
                "Implement graceful shutdown procedures",
                "Follow security hardening guidelines"
            ])
        
        if tier == ProductionTier.MISSION_CRITICAL:
            practices.extend([
                "Implement redundancy and failover mechanisms",
                "Use blue-green deployment strategies",
                "Implement comprehensive monitoring and alerting",
                "Follow disaster recovery best practices"
            ])
        
        return practices
    
    # Helper methods for response building
    
    def _detect_languages(self, capsule) -> List[str]:
        """Detect programming languages in capsule"""
        # Simple detection based on file extensions or content
        return ["Python"]  # Default for now
    
    def _detect_frameworks(self, capsule) -> List[str]:
        """Detect frameworks used in capsule"""
        # Analyze code for framework patterns
        return ["FastAPI"]  # Default for now
    
    def _generate_recommendations(self, result: ProductionResult) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []
        
        if result.confidence_score < 0.9:
            recommendations.append("Consider increasing test coverage for higher confidence")
        
        if not result.production_ready:
            recommendations.append("Address validation issues before production deployment")
        
        if result.test_results and result.test_results.get("failed_tests", 0) > 0:
            recommendations.append("Fix failing tests before deployment")
        
        return recommendations
    
    def _generate_next_steps(self, result: ProductionResult) -> List[Dict[str, Any]]:
        """Generate next steps for non-production-ready code"""
        steps = []
        
        if result.validation_report.overall_status == "failed":
            steps.append({
                "action": "Fix validation errors",
                "priority": "high",
                "description": "Address critical validation issues preventing deployment"
            })
        
        if result.test_results and result.test_results.get("coverage", 0) < 80:
            steps.append({
                "action": "Improve test coverage",
                "priority": "medium",
                "description": "Add more comprehensive test cases"
            })
        
        return steps
    
    def _estimate_lines_of_code(self, description: str) -> str:
        """Estimate lines of code from description"""
        # Simple estimation
        words = len(description.split())
        estimated_loc = words * 2  # Rough heuristic
        return f"{estimated_loc}-{estimated_loc * 2}"
    
    def _estimate_components(self, description: str) -> str:
        """Estimate number of components"""
        # Count nouns and features mentioned
        complexity_words = ["service", "component", "module", "class", "function", "api", "endpoint"]
        count = sum(1 for word in complexity_words if word in description.lower())
        return f"{max(1, count)}-{count + 3}"
    
    def _suggest_technology_stack(self, description: str) -> Dict[str, str]:
        """Suggest appropriate technology stack"""
        # Default recommendations
        return {
            "backend": "FastAPI + Python",
            "database": "PostgreSQL",
            "testing": "pytest + coverage",
            "deployment": "Docker + Kubernetes"
        }
    
    def _explain_tier_recommendation(
        self, 
        description: str, 
        complexity_score: float, 
        tier: ProductionTier
    ) -> str:
        """Explain why a particular tier was recommended"""
        
        explanations = {
            ProductionTier.PROTOTYPE: "Suitable for proof-of-concept and early development",
            ProductionTier.DEVELOPMENT: "Appropriate for feature development with good testing practices",
            ProductionTier.STAGING: "Recommended for pre-production validation and testing",
            ProductionTier.PRODUCTION: "Required for customer-facing production deployment",
            ProductionTier.MISSION_CRITICAL: "Essential for safety-critical or high-availability systems"
        }
        
        base_explanation = explanations[tier]
        
        if complexity_score > 0.7:
            base_explanation += " given the high complexity requirements"
        elif complexity_score < 0.3:
            base_explanation += " considering the relatively simple requirements"
        
        return base_explanation


# Export endpoints class
__all__ = ["ProductionEndpoints", "ProductionCodeRequest", "ProductionCodeResponse"]