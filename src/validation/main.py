"""
Validation Mesh Service
Multi-stage validation with ensemble consensus
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
import json
import subprocess
import tempfile
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import structlog
import ast
import black
import pylint.lint
from pylint.reporters.text import TextReporter
import mypy.api
try:
    import bandit
    from bandit.core import manager as bandit_manager
    BANDIT_AVAILABLE = True
except ImportError:
    BANDIT_AVAILABLE = False
import docker

from src.common.models import (
    TaskResult,
    ValidationReport,
    ValidationCheck,
    ValidationStatus
)
from src.common.config import settings

logger = structlog.get_logger()

app = FastAPI(title="Quantum Layer Platform Validation Mesh", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Docker client initialization
docker_client = None

def get_docker_client():
    """Get Docker client with proper error handling"""
    global docker_client
    if docker_client is None:
        try:
            # Clear problematic DOCKER_HOST environment variable
            import os
            old_docker_host = os.environ.pop('DOCKER_HOST', None)
            
            # Try direct socket connection first
            docker_client = docker.DockerClient(base_url='unix://var/run/docker.sock')
            # Test the connection
            docker_client.ping()
            logger.info("Docker client initialized successfully")
        except Exception as e:
            logger.warning(f"Docker client initialization failed: {e}")
            # Try fallback method
            try:
                docker_client = docker.from_env()
                docker_client.ping()
                logger.info("Docker client initialized via from_env")
            except Exception as e2:
                logger.warning(f"Docker fallback initialization failed: {e2}")
                # Return None to allow service to run without Docker
                return None
    return docker_client


class Validator:
    """Base validator class"""
    
    def __init__(self, name: str, validator_type: str):
        self.name = name
        self.type = validator_type
        
    async def validate(self, code: str, language: str = "python") -> ValidationCheck:
        """Validate code - to be implemented by subclasses"""
        raise NotImplementedError


class LLMValidator(Validator):
    """Universal LLM-powered validator for any programming language"""
    
    def __init__(self, name: str, validator_type: str, validation_focus: str):
        super().__init__(name, validator_type)
        self.validation_focus = validation_focus
        self.llm_client = self._get_llm_client()
    
    def _get_llm_client(self):
        """Initialize LLM client (Azure OpenAI or OpenAI)"""
        try:
            from src.common.config import settings
            if settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_API_KEY:
                from openai import AsyncAzureOpenAI
                return AsyncAzureOpenAI(
                    api_key=settings.AZURE_OPENAI_API_KEY,
                    api_version=settings.AZURE_OPENAI_API_VERSION,
                    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
                )
            else:
                from openai import AsyncOpenAI
                return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        except Exception as e:
            logger.warning(f"Failed to initialize LLM client: {e}")
            return None
    
    async def validate(self, code: str, language: str = "unknown") -> ValidationCheck:
        """Universal validation using LLM analysis"""
        if not self.llm_client:
            return ValidationCheck(
                name=self.name,
                type=self.type,
                status=ValidationStatus.SKIPPED,
                message="LLM client not available for validation"
            )
        
        if not code.strip():
            return ValidationCheck(
                name=self.name,
                type=self.type,
                status=ValidationStatus.FAILED,
                message="Empty code provided",
                severity="error"
            )
        
        try:
            # Create validation prompt
            prompt = self._create_validation_prompt(code, language)
            
            # Use deployment name for Azure OpenAI, model name for OpenAI
            model = getattr(settings, 'AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-3.5-turbo')
            
            response = await self.llm_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert code validator. Analyze code and respond in JSON format."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                timeout=30.0
            )
            
            # Parse LLM response
            result = json.loads(response.choices[0].message.content)
            
            # Convert to ValidationCheck
            return ValidationCheck(
                name=self.name,
                type=self.type,
                status=ValidationStatus(result.get("status", "warning")),
                message=result.get("message", "Validation completed"),
                details=result.get("details", {}),
                severity=result.get("severity", "info")
            )
            
        except Exception as e:
            return ValidationCheck(
                name=self.name,
                type=self.type,
                status=ValidationStatus.WARNING,
                message=f"LLM validation error: {str(e)}",
                severity="warning"
            )
    
    def _create_validation_prompt(self, code: str, language: str) -> str:
        """Create language-agnostic validation prompt"""
        return f"""
Analyze this {language} code for {self.validation_focus}:

```{language}
{code}
```

Respond in JSON format:
{{
    "status": "passed|warning|failed",
    "message": "Brief description of findings",
    "severity": "info|warning|error|critical",
    "details": {{
        "issues": ["list of specific issues if any"],
        "suggestions": ["improvement suggestions"],
        "confidence": 0.8
    }}
}}

Focus on {self.validation_focus}. Consider:
- Language-specific best practices for {language}
- Common patterns and anti-patterns
- Security implications if applicable
- Code structure and readability
- Potential runtime issues

Be pragmatic - small style issues should be warnings, not failures.
"""


class SyntaxValidator(LLMValidator):
    """Universal syntax validator using LLM"""
    
    def __init__(self):
        super().__init__("syntax_validator", "static_analysis", "syntax correctness and basic structure")


class StyleValidator(LLMValidator):
    """Universal style validator using LLM"""
    
    def __init__(self):
        super().__init__("style_validator", "static_analysis", "code style, formatting, and readability")


class SecurityValidator(LLMValidator):
    """Universal security validator using LLM"""
    
    def __init__(self):
        super().__init__("security_validator", "security", "security vulnerabilities and unsafe patterns")


class TypeValidator(LLMValidator):
    """Universal type validator using LLM"""
    
    def __init__(self):
        super().__init__("type_validator", "static_analysis", "type safety and data flow")


class LogicValidator(LLMValidator):
    """Universal logic validator using LLM"""
    
    def __init__(self):
        super().__init__("logic_validator", "logic_analysis", "logical correctness and algorithmic soundness")


class RuntimeValidator(LLMValidator):
    """Universal runtime behavior validator using LLM"""
    
    def __init__(self):
        super().__init__("runtime_validator", "runtime", "potential runtime issues and execution safety")


class ValidationMesh:
    """Orchestrates multiple LLM-powered validators with ensemble consensus"""
    
    def __init__(self):
        self.validators = [
            SyntaxValidator(),
            StyleValidator(),
            SecurityValidator(),
            TypeValidator(),
            LogicValidator(),
            RuntimeValidator()
        ]
        
    async def validate_code(self, code: str, language: str = "python") -> ValidationReport:
        """Run all validators and compute consensus"""
        # Run validators in parallel
        validation_tasks = [
            validator.validate(code, language) 
            for validator in self.validators
        ]
        
        checks = await asyncio.gather(*validation_tasks)
        
        # Compute overall status
        failed_count = sum(1 for check in checks if check.status == ValidationStatus.FAILED)
        warning_count = sum(1 for check in checks if check.status == ValidationStatus.WARNING)
        
        if failed_count > 0:
            overall_status = ValidationStatus.FAILED
        elif warning_count > 0:
            overall_status = ValidationStatus.WARNING
        else:
            overall_status = ValidationStatus.PASSED
        
        # Calculate confidence score
        total_checks = len(checks)
        passed_checks = sum(1 for check in checks if check.status == ValidationStatus.PASSED)
        confidence_score = passed_checks / total_checks if total_checks > 0 else 0.0
        
        # Determine if human review needed
        requires_human_review = (
            failed_count > 1 or 
            confidence_score < 0.7 or
            any(check.severity == "critical" for check in checks)
        )
        
        return ValidationReport(
            id=str(datetime.utcnow().timestamp()),
            execution_id="",  # Will be set by caller
            overall_status=overall_status,
            checks=checks,
            confidence_score=confidence_score,
            requires_human_review=requires_human_review,
            metadata={
                "language": language,
                "failed_count": failed_count,
                "warning_count": warning_count
            }
        )
    
    async def validate_results(self, results: Dict[str, TaskResult]) -> ValidationReport:
        """Validate multiple task results"""
        all_checks = []
        total_confidence = 0.0
        
        for task_id, result in results.items():
            if result.output_type == "code" and isinstance(result.output, dict):
                code = result.output.get("code", result.output.get("content", ""))
                if code:
                    report = await self.validate_code(code)
                    # Prefix check names with task_id
                    for check in report.checks:
                        check.name = f"{task_id}_{check.name}"
                    all_checks.extend(report.checks)
                    total_confidence += report.confidence_score
        
        # Compute overall metrics
        num_tasks = len(results)
        avg_confidence = total_confidence / num_tasks if num_tasks > 0 else 0.0
        
        failed_count = sum(1 for check in all_checks if check.status == ValidationStatus.FAILED)
        warning_count = sum(1 for check in all_checks if check.status == ValidationStatus.WARNING)
        
        if failed_count > 0:
            overall_status = ValidationStatus.FAILED
        elif warning_count > 0:
            overall_status = ValidationStatus.WARNING
        else:
            overall_status = ValidationStatus.PASSED
        
        return ValidationReport(
            id=str(datetime.utcnow().timestamp()),
            execution_id="batch_validation",
            overall_status=overall_status,
            checks=all_checks,
            confidence_score=avg_confidence,
            requires_human_review=avg_confidence < 0.8,
            metadata={
                "tasks_validated": num_tasks,
                "total_checks": len(all_checks),
                "failed_count": failed_count,
                "warning_count": warning_count
            }
        )


# Initialize validation mesh
validation_mesh = ValidationMesh()


# Import new runtime validation components
from src.validation.qlcapsule_runtime_validator import QLCapsuleRuntimeValidator
from src.validation.confidence_engine import AdvancedConfidenceEngine
from src.validation.capsule_schema import CapsuleValidator, CapsuleManifest

# Initialize runtime validation components
runtime_validator = QLCapsuleRuntimeValidator()
confidence_engine = AdvancedConfidenceEngine()
capsule_validator = CapsuleValidator()


# API Endpoints
@app.post("/validate", response_model=ValidationReport)
async def validate_execution(request: Dict[str, Any]):
    """Validate execution results"""
    results = {}
    for task_id, result_data in request.get("results", {}).items():
        results[task_id] = TaskResult(**result_data)
    
    report = await validation_mesh.validate_results(results)
    return report


@app.post("/validate/code")
async def validate_code(request: Dict[str, Any]):
    """Validate a specific piece of code"""
    code = request.get("code", "")
    language = request.get("language", "python")
    
    if not code:
        raise HTTPException(status_code=400, detail="No code provided")
    
    report = await validation_mesh.validate_code(code, language)
    return report


@app.post("/validate/capsule/runtime")
async def validate_capsule_runtime(request: Dict[str, Any]):
    """Validate QLCapsule by running it in a Docker container"""
    try:
        # Parse capsule from request
        from src.common.models import QLCapsule
        capsule_data = request.get("capsule")
        if not capsule_data:
            raise HTTPException(status_code=400, detail="No capsule provided")
        
        capsule = QLCapsule(**capsule_data)
        
        # Run runtime validation
        runtime_result = await runtime_validator.validate_capsule_runtime(capsule)
        
        return {
            "validation_id": f"runtime_{capsule.id}_{datetime.utcnow().timestamp()}",
            "capsule_id": capsule.id,
            "language": runtime_result.language,
            "success": runtime_result.success,
            "confidence_score": runtime_result.confidence_score,
            "execution_time": runtime_result.execution_time,
            "memory_usage": runtime_result.memory_usage,
            "install_success": runtime_result.install_success,
            "runtime_success": runtime_result.runtime_success,
            "test_success": runtime_result.test_success,
            "issues": runtime_result.issues,
            "recommendations": runtime_result.recommendations,
            "human_review_required": runtime_validator.should_escalate_to_human(runtime_result),
            "metrics": runtime_result.metrics,
            "stdout": runtime_result.stdout,
            "stderr": runtime_result.stderr
        }
        
    except Exception as e:
        logger.error(f"Runtime validation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Runtime validation failed: {str(e)}")


@app.post("/validate/capsule/confidence")
async def validate_capsule_confidence(request: Dict[str, Any]):
    """Perform advanced confidence analysis on QLCapsule"""
    try:
        # Parse capsule from request
        from src.common.models import QLCapsule
        capsule_data = request.get("capsule")
        if not capsule_data:
            raise HTTPException(status_code=400, detail="No capsule provided")
        
        capsule = QLCapsule(**capsule_data)
        
        # Parse optional manifest
        manifest = None
        manifest_data = request.get("manifest")
        if manifest_data:
            try:
                manifest = CapsuleManifest(**manifest_data)
            except Exception as e:
                logger.warning(f"Invalid manifest provided: {e}")
        
        # Parse optional runtime result
        runtime_result = None
        runtime_data = request.get("runtime_result")
        if runtime_data:
            try:
                from src.validation.qlcapsule_runtime_validator import RuntimeValidationResult
                runtime_result = RuntimeValidationResult(**runtime_data)
            except Exception as e:
                logger.warning(f"Invalid runtime result provided: {e}")
        
        # Run confidence analysis
        confidence_analysis = await confidence_engine.analyze_confidence(capsule, manifest, runtime_result)
        
        return {
            "analysis_id": f"confidence_{capsule.id}_{datetime.utcnow().timestamp()}",
            "capsule_id": capsule.id,
            "overall_score": confidence_analysis.overall_score,
            "confidence_level": confidence_analysis.confidence_level,
            "deployment_recommendation": confidence_analysis.deployment_recommendation,
            "human_review_required": confidence_analysis.human_review_required,
            "estimated_success_probability": confidence_analysis.estimated_success_probability,
            "dimensions": {
                dim.value: {
                    "score": metric.score,
                    "weight": metric.weight,
                    "evidence": metric.evidence,
                    "concerns": metric.concerns
                }
                for dim, metric in confidence_analysis.dimensions.items()
            },
            "risk_factors": confidence_analysis.risk_factors,
            "success_indicators": confidence_analysis.success_indicators,
            "failure_modes": confidence_analysis.failure_modes,
            "mitigation_strategies": confidence_analysis.mitigation_strategies,
            "metadata": confidence_analysis.metadata
        }
        
    except Exception as e:
        logger.error(f"Confidence analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Confidence analysis failed: {str(e)}")


@app.post("/validate/capsule/complete")
async def validate_capsule_complete(request: Dict[str, Any]):
    """Complete capsule validation including runtime and confidence analysis"""
    try:
        # Parse capsule from request
        from src.common.models import QLCapsule
        capsule_data = request.get("capsule")
        if not capsule_data:
            raise HTTPException(status_code=400, detail="No capsule provided")
        
        capsule = QLCapsule(**capsule_data)
        
        # Step 1: Runtime validation
        logger.info(f"Starting runtime validation for capsule {capsule.id}")
        runtime_result = await runtime_validator.validate_capsule_runtime(capsule)
        
        # Step 2: Validate manifest if present
        manifest = None
        if "capsule.yaml" in capsule.source_code:
            try:
                is_valid, manifest, errors = capsule_validator.validate_manifest(capsule.source_code["capsule.yaml"])
                if not is_valid:
                    logger.warning(f"Invalid manifest: {errors}")
            except Exception as e:
                logger.warning(f"Manifest validation failed: {e}")
        
        # Step 3: Confidence analysis
        logger.info(f"Starting confidence analysis for capsule {capsule.id}")
        confidence_analysis = await confidence_engine.analyze_confidence(capsule, manifest, runtime_result)
        
        # Step 4: Generate comprehensive report
        validation_report = {
            "validation_id": f"complete_{capsule.id}_{datetime.utcnow().timestamp()}",
            "capsule_id": capsule.id,
            "timestamp": datetime.utcnow().isoformat(),
            
            # Runtime validation results
            "runtime": {
                "language": runtime_result.language,
                "success": runtime_result.success,
                "confidence_score": runtime_result.confidence_score,
                "execution_time": runtime_result.execution_time,
                "memory_usage": runtime_result.memory_usage,
                "install_success": runtime_result.install_success,
                "runtime_success": runtime_result.runtime_success,
                "test_success": runtime_result.test_success,
                "issues": runtime_result.issues,
                "recommendations": runtime_result.recommendations
            },
            
            # Confidence analysis results
            "confidence": {
                "overall_score": confidence_analysis.overall_score,
                "confidence_level": confidence_analysis.confidence_level,
                "deployment_recommendation": confidence_analysis.deployment_recommendation,
                "estimated_success_probability": confidence_analysis.estimated_success_probability,
                "dimensions": {
                    dim.value: {
                        "score": metric.score,
                        "evidence": metric.evidence,
                        "concerns": metric.concerns
                    }
                    for dim, metric in confidence_analysis.dimensions.items()
                },
                "risk_factors": confidence_analysis.risk_factors,
                "success_indicators": confidence_analysis.success_indicators,
                "failure_modes": confidence_analysis.failure_modes,
                "mitigation_strategies": confidence_analysis.mitigation_strategies
            },
            
            # Overall assessment
            "assessment": {
                "deployment_ready": (
                    runtime_result.success and 
                    confidence_analysis.overall_score >= 0.7 and
                    not confidence_analysis.human_review_required
                ),
                "human_review_required": (
                    runtime_validator.should_escalate_to_human(runtime_result) or
                    confidence_analysis.human_review_required
                ),
                "blocking_issues": [
                    issue for issue in runtime_result.issues 
                    if any(keyword in issue.lower() for keyword in ['failed', 'error', 'critical'])
                ],
                "final_recommendation": _generate_final_recommendation(runtime_result, confidence_analysis)
            }
        }
        
        logger.info(f"Complete validation finished for capsule {capsule.id}")
        return validation_report
        
    except Exception as e:
        logger.error(f"Complete validation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Complete validation failed: {str(e)}")


def _generate_final_recommendation(runtime_result, confidence_analysis) -> str:
    """Generate final deployment recommendation"""
    if not runtime_result.success:
        return "🚫 BLOCK - Runtime validation failed"
    
    if confidence_analysis.confidence_level.value == "critical":
        return "🚀 DEPLOY - High confidence, ready for production"
    elif confidence_analysis.confidence_level.value == "high":
        return "✅ DEPLOY - Good confidence, monitor closely"
    elif confidence_analysis.confidence_level.value == "medium":
        return "⚠️ CAUTIOUS DEPLOY - Enhanced monitoring required"
    elif confidence_analysis.confidence_level.value == "low":
        return "🔍 HUMAN REVIEW - Manual approval needed"
    else:
        return "🚫 BLOCK - Critical issues must be resolved"


@app.get("/validate/capsule/schema")
async def get_capsule_schema():
    """Get the capsule.yaml schema definition"""
    return {
        "schema_version": "1.0.0",
        "description": "QLC Capsule manifest schema",
        "schema": CapsuleManifest.schema()
    }


@app.post("/validate/capsule/manifest")
async def validate_capsule_manifest(request: Dict[str, Any]):
    """Validate capsule manifest (capsule.yaml)"""
    try:
        manifest_content = request.get("manifest_content", "")
        if not manifest_content:
            raise HTTPException(status_code=400, detail="No manifest content provided")
        
        is_valid, manifest, errors = capsule_validator.validate_manifest(manifest_content)
        
        return {
            "valid": is_valid,
            "manifest": manifest.dict() if manifest else None,
            "errors": errors,
            "recommendations": [
                "Use semantic versioning for version field",
                "Include health check configuration for services",
                "Specify resource limits for production deployment",
                "Add comprehensive documentation and metadata"
            ] if not is_valid else []
        }
        
    except Exception as e:
        logger.error(f"Manifest validation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Manifest validation failed: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Docker connection
        client = get_docker_client()
        if client:
            client.ping()
            docker_status = "connected"
        else:
            docker_status = "not available"
    except:
        docker_status = "disconnected"
    
    return {
        "status": "healthy",
        "service": "validation-mesh",
        "validators": len(validation_mesh.validators),
        "docker_status": docker_status
    }


@app.get("/validators")
async def list_validators():
    """List available validators"""
    return {
        "validators": [
            {"name": v.name, "type": v.type} 
            for v in validation_mesh.validators
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
