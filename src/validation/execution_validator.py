"""
Execution Validator for Generated Code
Validates code by running it in a sandboxed environment
"""

import asyncio
import subprocess
import tempfile
import os
import sys
import json
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import time
import ast

import structlog

logger = structlog.get_logger()


class ExecutionValidator:
    """
    Validates generated code by executing it and running static analysis
    """
    
    def __init__(self, sandbox_timeout: int = 30):
        self.sandbox_timeout = sandbox_timeout
        self.static_analyzers = {
            "pylint": self._run_pylint,
            "mypy": self._run_mypy,
            "bandit": self._run_bandit,
            "radon": self._run_radon
        }
    
    async def validate_code(
        self, 
        code: str, 
        tests: Optional[str] = None,
        requirements: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Execute code in sandbox and validate
        
        Args:
            code: The Python code to validate
            tests: Optional test code to run
            requirements: Optional list of required packages
            
        Returns:
            Validation results including execution status, errors, and analysis
        """
        logger.info("Starting code execution validation")
        
        validation_result = {
            "executable": False,
            "syntax_valid": False,
            "static_analysis": {},
            "runtime_errors": [],
            "test_results": {},
            "performance": {},
            "issues": [],
            "confidence_boost": 0.0
        }
        
        # First check syntax
        syntax_check = self._check_syntax(code)
        validation_result["syntax_valid"] = syntax_check["valid"]
        if not syntax_check["valid"]:
            validation_result["runtime_errors"].append(syntax_check["error"])
            validation_result["confidence_boost"] = -15.0
            return validation_result
        
        # Create temporary directory for execution
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                # Write code to file
                code_file = os.path.join(tmpdir, "solution.py")
                with open(code_file, 'w') as f:
                    f.write(code)
                
                # Write tests if provided
                test_file = None
                if tests:
                    test_file = os.path.join(tmpdir, "test_solution.py")
                    with open(test_file, 'w') as f:
                        f.write(tests)
                
                # Install requirements if needed
                if requirements:
                    await self._install_requirements(tmpdir, requirements)
                
                # Run static analysis
                validation_result["static_analysis"] = await self._run_static_analysis(code_file)
                
                # Execute the code
                execution_result = await self._execute_code(code_file, tmpdir)
                validation_result.update(execution_result)
                
                # Run tests if provided
                if test_file:
                    test_result = await self._run_tests(test_file, tmpdir)
                    validation_result["test_results"] = test_result
                
                # Check for common issues
                validation_result["issues"] = self._check_common_issues(code)
                
                # Calculate confidence boost
                validation_result["confidence_boost"] = self._calculate_boost(validation_result)
                
            except Exception as e:
                logger.error(f"Validation error: {e}")
                validation_result["runtime_errors"].append(str(e))
                validation_result["confidence_boost"] = -10.0
        
        return validation_result
    
    def _check_syntax(self, code: str) -> Dict[str, Any]:
        """Check Python syntax"""
        try:
            ast.parse(code)
            return {"valid": True, "error": None}
        except SyntaxError as e:
            return {
                "valid": False, 
                "error": f"Syntax error at line {e.lineno}: {e.msg}"
            }
    
    async def _install_requirements(self, tmpdir: str, requirements: List[str]):
        """Install required packages in virtual environment"""
        # Create a simple requirements.txt
        req_file = os.path.join(tmpdir, "requirements.txt")
        with open(req_file, 'w') as f:
            f.write('\n'.join(requirements))
        
        # Note: In production, this should use a proper sandbox
        # For now, we'll skip actual installation to avoid security issues
        logger.info(f"Would install requirements: {requirements}")
    
    async def _run_static_analysis(self, code_file: str) -> Dict[str, Any]:
        """Run all static analyzers"""
        results = {}
        
        for analyzer_name, analyzer_func in self.static_analyzers.items():
            try:
                result = await analyzer_func(code_file)
                results[analyzer_name] = result
            except Exception as e:
                logger.error(f"{analyzer_name} failed: {e}")
                results[analyzer_name] = {
                    "passed": False,
                    "error": str(e),
                    "output": ""
                }
        
        return results
    
    async def _run_pylint(self, code_file: str) -> Dict[str, Any]:
        """Run pylint analysis"""
        try:
            # Check if pylint is available
            result = subprocess.run(
                ["python", "-m", "pylint", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                return {"passed": False, "error": "pylint not installed", "output": ""}
            
            # Run pylint
            result = subprocess.run(
                ["python", "-m", "pylint", code_file, "--output-format=json"],
                capture_output=True,
                text=True,
                timeout=self.sandbox_timeout
            )
            
            # Parse results
            if result.stdout:
                try:
                    issues = json.loads(result.stdout)
                    score = 10.0 - (len(issues) * 0.5)  # Deduct 0.5 for each issue
                    passed = score >= 7.0
                    
                    return {
                        "passed": passed,
                        "score": max(0, score),
                        "issues": len(issues),
                        "output": result.stdout[:1000]  # Limit output size
                    }
                except json.JSONDecodeError:
                    pass
            
            return {
                "passed": result.returncode == 0,
                "output": result.stdout[:1000] if result.stdout else result.stderr[:1000]
            }
            
        except subprocess.TimeoutExpired:
            return {"passed": False, "error": "timeout", "output": ""}
        except FileNotFoundError:
            return {"passed": False, "error": "pylint not found", "output": ""}
    
    async def _run_mypy(self, code_file: str) -> Dict[str, Any]:
        """Run mypy type checking"""
        try:
            result = subprocess.run(
                ["python", "-m", "mypy", code_file, "--ignore-missing-imports"],
                capture_output=True,
                text=True,
                timeout=self.sandbox_timeout
            )
            
            return {
                "passed": result.returncode == 0,
                "output": result.stdout[:1000] if result.stdout else result.stderr[:1000]
            }
            
        except subprocess.TimeoutExpired:
            return {"passed": False, "error": "timeout", "output": ""}
        except FileNotFoundError:
            return {"passed": False, "error": "mypy not found", "output": ""}
    
    async def _run_bandit(self, code_file: str) -> Dict[str, Any]:
        """Run bandit security analysis"""
        try:
            result = subprocess.run(
                ["python", "-m", "bandit", code_file, "-f", "json"],
                capture_output=True,
                text=True,
                timeout=self.sandbox_timeout
            )
            
            # Parse results
            if result.stdout:
                try:
                    data = json.loads(result.stdout)
                    issues = data.get("results", [])
                    
                    return {
                        "passed": len(issues) == 0,
                        "security_issues": len(issues),
                        "severity": {
                            "high": sum(1 for i in issues if i.get("issue_severity") == "HIGH"),
                            "medium": sum(1 for i in issues if i.get("issue_severity") == "MEDIUM"),
                            "low": sum(1 for i in issues if i.get("issue_severity") == "LOW")
                        },
                        "output": result.stdout[:1000]
                    }
                except json.JSONDecodeError:
                    pass
            
            return {
                "passed": result.returncode == 0,
                "output": result.stdout[:1000] if result.stdout else result.stderr[:1000]
            }
            
        except subprocess.TimeoutExpired:
            return {"passed": False, "error": "timeout", "output": ""}
        except FileNotFoundError:
            return {"passed": False, "error": "bandit not found", "output": ""}
    
    async def _run_radon(self, code_file: str) -> Dict[str, Any]:
        """Run radon complexity analysis"""
        try:
            result = subprocess.run(
                ["python", "-m", "radon", "cc", code_file, "-j"],
                capture_output=True,
                text=True,
                timeout=self.sandbox_timeout
            )
            
            # Parse results
            if result.stdout:
                try:
                    data = json.loads(result.stdout)
                    
                    # Calculate average complexity
                    complexities = []
                    for file_data in data.values():
                        for func in file_data:
                            complexities.append(func.get("complexity", 0))
                    
                    avg_complexity = sum(complexities) / len(complexities) if complexities else 0
                    
                    return {
                        "passed": avg_complexity < 10,  # McCabe complexity threshold
                        "average_complexity": avg_complexity,
                        "max_complexity": max(complexities) if complexities else 0,
                        "output": result.stdout[:1000]
                    }
                except (json.JSONDecodeError, KeyError):
                    pass
            
            return {
                "passed": True,
                "output": result.stdout[:1000] if result.stdout else ""
            }
            
        except subprocess.TimeoutExpired:
            return {"passed": False, "error": "timeout", "output": ""}
        except FileNotFoundError:
            return {"passed": False, "error": "radon not found", "output": ""}
    
    async def _execute_code(self, code_file: str, tmpdir: str) -> Dict[str, Any]:
        """Execute the code and measure performance"""
        execution_result = {
            "executable": False,
            "runtime_errors": [],
            "performance": {}
        }
        
        try:
            # Measure execution time
            start_time = time.time()
            
            # Execute the code
            result = subprocess.run(
                [sys.executable, code_file],
                capture_output=True,
                text=True,
                timeout=self.sandbox_timeout,
                cwd=tmpdir,
                env={**os.environ, "PYTHONPATH": tmpdir}
            )
            
            execution_time = time.time() - start_time
            
            execution_result["executable"] = result.returncode == 0
            execution_result["performance"]["execution_time"] = execution_time
            
            if result.returncode != 0:
                execution_result["runtime_errors"].append(
                    result.stderr if result.stderr else "Execution failed"
                )
            
            # Check output for common error patterns
            if result.stderr:
                if "ImportError" in result.stderr:
                    execution_result["runtime_errors"].append("Import error detected")
                if "Exception" in result.stderr or "Error" in result.stderr:
                    execution_result["runtime_errors"].append("Runtime exception detected")
            
        except subprocess.TimeoutExpired:
            execution_result["runtime_errors"].append("Execution timeout")
            execution_result["performance"]["execution_time"] = self.sandbox_timeout
        except Exception as e:
            execution_result["runtime_errors"].append(f"Execution error: {str(e)}")
        
        return execution_result
    
    async def _run_tests(self, test_file: str, tmpdir: str) -> Dict[str, Any]:
        """Run test suite"""
        test_result = {
            "passed": False,
            "test_count": 0,
            "passed_count": 0,
            "failed_count": 0,
            "output": ""
        }
        
        try:
            # Try pytest first
            result = subprocess.run(
                [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=self.sandbox_timeout,
                cwd=tmpdir,
                env={**os.environ, "PYTHONPATH": tmpdir}
            )
            
            if result.returncode == 0 or "passed" in result.stdout:
                # Parse pytest output
                output = result.stdout
                test_result["output"] = output[:1000]
                
                # Extract test counts
                import re
                match = re.search(r'(\d+) passed', output)
                if match:
                    test_result["passed_count"] = int(match.group(1))
                    test_result["test_count"] = test_result["passed_count"]
                
                match = re.search(r'(\d+) failed', output)
                if match:
                    test_result["failed_count"] = int(match.group(1))
                    test_result["test_count"] += test_result["failed_count"]
                
                test_result["passed"] = test_result["failed_count"] == 0
                
            else:
                # Fallback to unittest
                result = subprocess.run(
                    [sys.executable, "-m", "unittest", test_file, "-v"],
                    capture_output=True,
                    text=True,
                    timeout=self.sandbox_timeout,
                    cwd=tmpdir,
                    env={**os.environ, "PYTHONPATH": tmpdir}
                )
                
                test_result["output"] = result.stdout[:1000] if result.stdout else result.stderr[:1000]
                test_result["passed"] = result.returncode == 0
                
        except subprocess.TimeoutExpired:
            test_result["output"] = "Test execution timeout"
        except Exception as e:
            test_result["output"] = f"Test execution error: {str(e)}"
        
        return test_result
    
    def _check_common_issues(self, code: str) -> List[str]:
        """Check for common code issues"""
        issues = []
        
        # Check for common bad practices
        patterns = [
            (r'print\s*\(.*\)\s*#.*debug', "Debug print statements found"),
            (r'TODO|FIXME|XXX', "Unfinished code markers found"),
            (r'pass\s*$', "Empty code blocks found"),
            (r'time\.sleep\s*\(\s*\d+\s*\)', "Blocking sleep calls found"),
            (r'globals?\s*\(\s*\)', "Use of globals detected"),
            (r'\*\s*import', "Wildcard imports detected"),
            (r'bare\s*except:', "Bare except clauses found")
        ]
        
        import re
        for pattern, message in patterns:
            if re.search(pattern, code, re.MULTILINE | re.IGNORECASE):
                issues.append(message)
        
        return issues
    
    def _calculate_boost(self, validation_result: Dict[str, Any]) -> float:
        """Calculate confidence boost based on validation results"""
        boost = 0.0
        
        # Execution success is most important
        if validation_result.get("executable", False):
            boost += 15.0
        else:
            boost -= 15.0
        
        # Static analysis results
        static_analysis = validation_result.get("static_analysis", {})
        if static_analysis:
            passed_count = sum(1 for r in static_analysis.values() if r.get("passed", False))
            total_count = len(static_analysis)
            static_score = passed_count / total_count if total_count > 0 else 0.5
            boost += (static_score - 0.5) * 10  # -5 to +5
        
        # Test results
        test_results = validation_result.get("test_results", {})
        if test_results.get("passed", False):
            boost += 10.0
        elif test_results.get("test_count", 0) > 0:
            # Partial credit for some passing tests
            pass_rate = test_results.get("passed_count", 0) / test_results.get("test_count", 1)
            boost += pass_rate * 5.0
        
        # Runtime errors penalty
        runtime_errors = len(validation_result.get("runtime_errors", []))
        boost -= min(runtime_errors * 3, 10)
        
        # Common issues penalty
        issues = len(validation_result.get("issues", []))
        boost -= min(issues * 1, 5)
        
        # Performance bonus
        performance = validation_result.get("performance", {})
        if performance.get("execution_time", float('inf')) < 1.0:
            boost += 2.5
        
        # Security bonus/penalty
        bandit_result = static_analysis.get("bandit", {})
        if bandit_result.get("security_issues", 0) == 0:
            boost += 2.5
        else:
            high_severity = bandit_result.get("severity", {}).get("high", 0)
            boost -= min(high_severity * 5, 10)
        
        return max(-20.0, min(20.0, boost))


# Convenience function
async def validate_generated_code(
    code: str,
    tests: Optional[str] = None,
    requirements: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Validate generated code by execution and analysis
    
    Args:
        code: The Python code to validate
        tests: Optional test code
        requirements: Optional package requirements
        
    Returns:
        Validation results with confidence boost
    """
    validator = ExecutionValidator()
    return await validator.validate_code(code, tests, requirements)