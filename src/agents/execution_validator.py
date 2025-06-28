"""
Execution Validator for Generated Code
"""

import asyncio
import subprocess
import tempfile
import os
import json
from typing import Dict, List, Any, Optional
import structlog

logger = structlog.get_logger()


class ExecutionValidator:
    """Execute code in sandbox and validate results"""
    
    def __init__(self, sandbox_client=None):
        self.sandbox_client = sandbox_client
        self.static_analyzers = ["pylint", "mypy", "bandit"]
    
    async def validate_code(self, code: str, tests: str = None) -> Dict[str, Any]:
        """Execute code in sandbox and validate"""
        
        validation_results = {
            "executable": False,
            "static_analysis": {},
            "runtime_errors": [],
            "performance": {},
            "issues": [],
            "confidence_boost": 0.0
        }
        
        # Run static analysis
        validation_results["static_analysis"] = await self.run_static_analysis(code)
        
        # Execute code
        if self.sandbox_client:
            execution_results = await self.execute_with_tests(code, tests)
            validation_results["executable"] = execution_results.get("success", False)
            validation_results["runtime_errors"] = execution_results.get("errors", [])
            validation_results["performance"] = execution_results.get("performance", {})
        else:
            # Fallback to local execution
            validation_results.update(self._local_validation(code))
        
        # Check for common issues
        validation_results["issues"] = await self.check_common_issues(code)
        
        # Calculate confidence boost
        validation_results["confidence_boost"] = self.calculate_boost(validation_results)
        
        return validation_results
    
    async def run_static_analysis(self, code: str) -> Dict[str, Any]:
        """Run multiple static analyzers"""
        results = {}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            for analyzer in self.static_analyzers:
                results[analyzer] = await self._run_analyzer(analyzer, temp_file)
        finally:
            os.unlink(temp_file)
        
        return results
    
    async def _run_analyzer(self, analyzer: str, file_path: str) -> Dict[str, Any]:
        """Run a single static analyzer"""
        try:
            if analyzer == "pylint":
                cmd = ["pylint", "--output-format=json", file_path]
            elif analyzer == "mypy":
                cmd = ["mypy", "--json-report", "-", file_path]
            elif analyzer == "bandit":
                cmd = ["bandit", "-f", "json", file_path]
            else:
                return {"passed": False, "error": f"Unknown analyzer: {analyzer}"}
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            return {
                "passed": result.returncode == 0,
                "output": stdout.decode() if stdout else "",
                "errors": stderr.decode() if stderr else "",
                "returncode": result.returncode
            }
        except Exception as e:
            return {"passed": False, "error": str(e)}
    
    async def execute_with_tests(self, code: str, tests: str = None) -> Dict[str, Any]:
        """Execute code with test cases"""
        if not self.sandbox_client:
            return self._local_validation(code)
        
        try:
            # Use sandbox for safe execution
            # Determine language from code
            language = "python" if ("def " in code or "import " in code) else "javascript"
            
            result = await self.sandbox_client.execute(
                code=code,
                language=language,
                inputs={"tests": tests} if tests else {}
            )
            
            # Handle ExecutionResult object
            return {
                "success": result.success,
                "output": result.output if result.output else "",
                "errors": [result.error] if result.error else [],
                "performance": {
                    "execution_time": result.execution_time,
                    "memory_used": result.metadata.get("memory_used", "N/A")
                }
            }
        except Exception as e:
            logger.error(f"Sandbox execution failed: {str(e)}")
            # Fall back to local validation
            return self._local_validation(code)
    
    async def check_common_issues(self, code: str) -> List[str]:
        """Check for common code issues"""
        issues = []
        
        # Check for common anti-patterns
        if "import *" in code:
            issues.append("wildcard-imports")
        
        if "except:" in code and "except Exception" not in code:
            issues.append("bare-except")
        
        if "eval(" in code or "exec(" in code:
            issues.append("unsafe-eval")
        
        if not any(pattern in code for pattern in ["def ", "class ", "async def"]):
            issues.append("no-functions-or-classes")
        
        # Check for missing imports
        common_modules = ["os", "sys", "json", "asyncio", "typing"]
        for module in common_modules:
            if f"{module}." in code and f"import {module}" not in code:
                issues.append(f"missing-import-{module}")
        
        return issues
    
    def calculate_boost(self, validation_results: Dict[str, Any]) -> float:
        """Calculate confidence boost from validation results"""
        boost = 0.0
        
        # Boost for passing static analysis
        static_results = validation_results.get("static_analysis", {})
        passed_analyzers = sum(1 for r in static_results.values() if r.get("passed", False))
        boost += (passed_analyzers / len(self.static_analyzers)) * 0.1
        
        # Boost for being executable
        if validation_results.get("executable", False):
            boost += 0.1
        
        # Penalty for runtime errors
        error_count = len(validation_results.get("runtime_errors", []))
        boost -= error_count * 0.02
        
        # Penalty for issues
        issue_count = len(validation_results.get("issues", []))
        boost -= issue_count * 0.01
        
        return max(-0.2, min(0.2, boost))  # Cap between -20% and +20%
    
    def _local_validation(self, code: str) -> Dict[str, Any]:
        """Fallback local validation"""
        try:
            compile(code, "validated_code", "exec")
            return {
                "executable": True,
                "runtime_errors": [],
                "performance": {"execution_time": 0.01}
            }
        except SyntaxError as e:
            return {
                "executable": False,
                "runtime_errors": [f"Syntax error: {str(e)}"],
                "performance": {}
            }
        except Exception as e:
            return {
                "executable": False,
                "runtime_errors": [str(e)],
                "performance": {}
            }
