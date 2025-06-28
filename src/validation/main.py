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


# Initialize Docker client
docker_client = docker.from_env()


class Validator:
    """Base validator class"""
    
    def __init__(self, name: str, validator_type: str):
        self.name = name
        self.type = validator_type
        
    async def validate(self, code: str, language: str = "python") -> ValidationCheck:
        """Validate code - to be implemented by subclasses"""
        raise NotImplementedError


class SyntaxValidator(Validator):
    """Validates syntax correctness"""
    
    def __init__(self):
        super().__init__("syntax_validator", "static_analysis")
        
    async def validate(self, code: str, language: str = "python") -> ValidationCheck:
        """Check syntax validity"""
        if language != "python":
            return ValidationCheck(
                name=self.name,
                type=self.type,
                status=ValidationStatus.SKIPPED,
                message=f"Syntax validation not implemented for {language}"
            )
        
        try:
            ast.parse(code)
            return ValidationCheck(
                name=self.name,
                type=self.type,
                status=ValidationStatus.PASSED,
                message="Syntax is valid"
            )
        except SyntaxError as e:
            return ValidationCheck(
                name=self.name,
                type=self.type,
                status=ValidationStatus.FAILED,
                message=f"Syntax error: {str(e)}",
                details={"line": e.lineno, "offset": e.offset},
                severity="error"
            )


class StyleValidator(Validator):
    """Validates code style and formatting"""
    
    def __init__(self):
        super().__init__("style_validator", "static_analysis")
        
    async def validate(self, code: str, language: str = "python") -> ValidationCheck:
        """Check code style"""
        if language != "python":
            return ValidationCheck(
                name=self.name,
                type=self.type,
                status=ValidationStatus.SKIPPED,
                message=f"Style validation not implemented for {language}"
            )
        
        try:
            # Format with black and check if it changes
            formatted = black.format_str(code, mode=black.FileMode())
            
            if formatted == code:
                return ValidationCheck(
                    name=self.name,
                    type=self.type,
                    status=ValidationStatus.PASSED,
                    message="Code style is correct"
                )
            else:
                return ValidationCheck(
                    name=self.name,
                    type=self.type,
                    status=ValidationStatus.WARNING,
                    message="Code style can be improved",
                    details={"formatted": formatted},
                    severity="warning"
                )
        except Exception as e:
            return ValidationCheck(
                name=self.name,
                type=self.type,
                status=ValidationStatus.FAILED,
                message=f"Style check error: {str(e)}",
                severity="error"
            )


class SecurityValidator(Validator):
    """Validates security issues"""
    
    def __init__(self):
        super().__init__("security_validator", "security")
        
    async def validate(self, code: str, language: str = "python") -> ValidationCheck:
        """Check for security vulnerabilities"""
        if language != "python":
            return ValidationCheck(
                name=self.name,
                type=self.type,
                status=ValidationStatus.SKIPPED,
                message=f"Security validation not implemented for {language}"
            )
        
        if not BANDIT_AVAILABLE:
            return ValidationCheck(
                name=self.name,
                type=self.type,
                status=ValidationStatus.SKIPPED,
                message="Bandit not available for security scanning"
            )
        
        try:
            # Write code to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            # Run bandit
            from bandit.core.config import Config
            conf = Config()
            b_mgr = bandit_manager.BanditManager(conf, 'file')
            b_mgr.discover_files([temp_file])
            b_mgr.run_tests()
            
            # Clean up
            os.unlink(temp_file)
            
            # Check results
            issues = []
            for issue in b_mgr.get_issue_list():
                issues.append({
                    "severity": issue.severity,
                    "confidence": issue.confidence,
                    "text": issue.text,
                    "line": issue.lineno
                })
            
            if not issues:
                return ValidationCheck(
                    name=self.name,
                    type=self.type,
                    status=ValidationStatus.PASSED,
                    message="No security issues found"
                )
            else:
                # Check severity
                high_severity = any(i["severity"] == "HIGH" for i in issues)
                status = ValidationStatus.FAILED if high_severity else ValidationStatus.WARNING
                
                return ValidationCheck(
                    name=self.name,
                    type=self.type,
                    status=status,
                    message=f"Found {len(issues)} security issues",
                    details={"issues": issues},
                    severity="error" if high_severity else "warning"
                )
                
        except Exception as e:
            return ValidationCheck(
                name=self.name,
                type=self.type,
                status=ValidationStatus.FAILED,
                message=f"Security check error: {str(e)}",
                severity="error"
            )


class TypeValidator(Validator):
    """Validates type correctness"""
    
    def __init__(self):
        super().__init__("type_validator", "static_analysis")
        
    async def validate(self, code: str, language: str = "python") -> ValidationCheck:
        """Check type safety"""
        if language != "python":
            return ValidationCheck(
                name=self.name,
                type=self.type,
                status=ValidationStatus.SKIPPED,
                message=f"Type validation not implemented for {language}"
            )
        
        try:
            # Write code to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            # Run mypy
            stdout, stderr, exit_status = mypy.api.run([temp_file, "--ignore-missing-imports"])
            
            # Clean up
            os.unlink(temp_file)
            
            if exit_status == 0:
                return ValidationCheck(
                    name=self.name,
                    type=self.type,
                    status=ValidationStatus.PASSED,
                    message="Type checking passed"
                )
            else:
                # Parse errors
                errors = []
                for line in stdout.split('\n'):
                    if line.strip() and 'error:' in line:
                        errors.append(line.strip())
                
                return ValidationCheck(
                    name=self.name,
                    type=self.type,
                    status=ValidationStatus.WARNING,
                    message=f"Type checking found {len(errors)} issues",
                    details={"errors": errors[:10]},  # Limit to 10 errors
                    severity="warning"
                )
                
        except Exception as e:
            return ValidationCheck(
                name=self.name,
                type=self.type,
                status=ValidationStatus.FAILED,
                message=f"Type check error: {str(e)}",
                severity="error"
            )


class RuntimeValidator(Validator):
    """Validates runtime behavior"""
    
    def __init__(self):
        super().__init__("runtime_validator", "runtime")
        self.docker = docker_client
        
    async def validate(self, code: str, language: str = "python") -> ValidationCheck:
        """Test runtime execution"""
        if language != "python":
            return ValidationCheck(
                name=self.name,
                type=self.type,
                status=ValidationStatus.SKIPPED,
                message=f"Runtime validation not implemented for {language}"
            )
        
        try:
            # Create a simple test wrapper
            test_code = f"""
import sys
import traceback

try:
{chr(10).join('    ' + line for line in code.split(chr(10)))}
    print("Runtime validation: SUCCESS")
except Exception as e:
    print(f"Runtime validation: ERROR - {{str(e)}}")
    traceback.print_exc()
    sys.exit(1)
"""
            
            # Run in Docker container
            container = self.docker.containers.run(
                "python:3.11-slim",
                command=["python", "-c", test_code],
                detach=True,
                remove=False,
                mem_limit="512m",
                cpu_quota=50000  # 0.5 CPU
            )
            
            # Wait for completion (timeout 30s)
            result = container.wait(timeout=30)
            logs = container.logs().decode('utf-8')
            container.remove()
            
            if result['StatusCode'] == 0:
                return ValidationCheck(
                    name=self.name,
                    type=self.type,
                    status=ValidationStatus.PASSED,
                    message="Runtime execution successful",
                    details={"output": logs[:500]}  # Limit output
                )
            else:
                return ValidationCheck(
                    name=self.name,
                    type=self.type,
                    status=ValidationStatus.FAILED,
                    message="Runtime execution failed",
                    details={"output": logs[:1000]},
                    severity="error"
                )
                
        except Exception as e:
            return ValidationCheck(
                name=self.name,
                type=self.type,
                status=ValidationStatus.FAILED,
                message=f"Runtime validation error: {str(e)}",
                severity="error"
            )


class ValidationMesh:
    """Orchestrates multiple validators with ensemble consensus"""
    
    def __init__(self):
        self.validators = [
            SyntaxValidator(),
            StyleValidator(),
            SecurityValidator(),
            TypeValidator(),
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


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Docker connection
        docker_client.ping()
        docker_status = "connected"
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
