#!/usr/bin/env python3
"""
Production-Grade Automated Testing Framework
Comprehensive test generation and execution for enterprise code quality
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import asyncio
import json
import ast
import tempfile
import os
from pathlib import Path
import structlog

from src.common.models import Task, TaskResult
from src.agents.base_agents import T1Agent, T2Agent
from src.sandbox.client import SandboxServiceClient
from src.validation.production_validator import ProductionCodeValidator, QualityLevel

logger = structlog.get_logger()


class TestType(str, Enum):
    """Types of tests to generate"""
    UNIT = "unit"                      # Function-level tests
    INTEGRATION = "integration"        # Component interaction tests
    FUNCTIONAL = "functional"          # Feature behavior tests
    PERFORMANCE = "performance"        # Load and stress tests
    SECURITY = "security"             # Security vulnerability tests
    REGRESSION = "regression"         # Prevent known issues
    CONTRACT = "contract"             # API contract tests
    END_TO_END = "e2e"               # Full user journey tests


class TestFramework(str, Enum):
    """Supported testing frameworks"""
    PYTEST = "pytest"
    UNITTEST = "unittest"
    JEST = "jest"
    MOCHA = "mocha"
    JUNIT = "junit"


@dataclass
class TestGenerationConfig:
    """Configuration for test generation"""
    frameworks: List[TestFramework]
    test_types: List[TestType]
    coverage_target: float = 90.0
    include_edge_cases: bool = True
    include_error_cases: bool = True
    include_performance_tests: bool = True
    include_security_tests: bool = True
    mock_external_dependencies: bool = True
    generate_fixtures: bool = True


@dataclass
class TestResult:
    """Result of test execution"""
    test_name: str
    test_type: TestType
    status: str  # PASSED, FAILED, SKIPPED, ERROR
    execution_time: float
    coverage: Optional[float] = None
    error_message: Optional[str] = None
    assertions_count: int = 0
    performance_metrics: Optional[Dict[str, Any]] = None


@dataclass
class TestSuiteResult:
    """Result of entire test suite execution"""
    total_tests: int
    passed: int
    failed: int
    skipped: int
    errors: int
    overall_coverage: float
    execution_time: float
    results: List[TestResult]
    quality_score: float


class ProductionTestGenerator:
    """Generate comprehensive test suites for production code"""
    
    def __init__(self):
        self.sandbox_client = SandboxServiceClient("http://localhost:8004")
        self.validator = ProductionCodeValidator()
        
        # Test generation agents
        self.unit_test_agent = T1Agent("unit-test-generator")
        self.integration_test_agent = T2Agent("integration-test-generator")
        self.security_test_agent = T2Agent("security-test-generator")
        
    async def generate_comprehensive_tests(
        self,
        code: str,
        language: str = "python",
        config: Optional[TestGenerationConfig] = None
    ) -> Dict[str, str]:
        """Generate comprehensive test suite for given code"""
        
        if config is None:
            config = TestGenerationConfig(
                frameworks=[TestFramework.PYTEST],
                test_types=[
                    TestType.UNIT, 
                    TestType.INTEGRATION, 
                    TestType.FUNCTIONAL,
                    TestType.SECURITY
                ]
            )
        
        logger.info(
            "Generating comprehensive test suite",
            language=language,
            test_types=config.test_types,
            coverage_target=config.coverage_target
        )
        
        generated_tests = {}
        
        try:
            # 1. Analyze code structure
            code_analysis = await self._analyze_code_structure(code, language)
            
            # 2. Generate different types of tests
            for test_type in config.test_types:
                if test_type == TestType.UNIT:
                    tests = await self._generate_unit_tests(
                        code, language, code_analysis, config
                    )
                    generated_tests["unit_tests"] = tests
                    
                elif test_type == TestType.INTEGRATION:
                    tests = await self._generate_integration_tests(
                        code, language, code_analysis, config
                    )
                    generated_tests["integration_tests"] = tests
                    
                elif test_type == TestType.FUNCTIONAL:
                    tests = await self._generate_functional_tests(
                        code, language, code_analysis, config
                    )
                    generated_tests["functional_tests"] = tests
                    
                elif test_type == TestType.SECURITY:
                    tests = await self._generate_security_tests(
                        code, language, code_analysis, config
                    )
                    generated_tests["security_tests"] = tests
                    
                elif test_type == TestType.PERFORMANCE:
                    tests = await self._generate_performance_tests(
                        code, language, code_analysis, config
                    )
                    generated_tests["performance_tests"] = tests
            
            # 3. Generate test fixtures and utilities
            if config.generate_fixtures:
                fixtures = await self._generate_test_fixtures(
                    code, language, code_analysis
                )
                generated_tests["fixtures"] = fixtures
            
            # 4. Generate test configuration files
            test_configs = await self._generate_test_configs(
                language, config.frameworks
            )
            generated_tests.update(test_configs)
            
            logger.info(
                "Test generation completed",
                test_files_generated=len(generated_tests)
            )
            
            return generated_tests
            
        except Exception as e:
            logger.error("Test generation failed", error=str(e))
            raise
    
    async def execute_test_suite(
        self,
        code: str,
        tests: Dict[str, str],
        language: str = "python"
    ) -> TestSuiteResult:
        """Execute generated test suite and return results"""
        
        logger.info("Executing comprehensive test suite")
        
        start_time = datetime.utcnow()
        test_results = []
        
        try:
            # Execute different test categories
            for test_category, test_code in tests.items():
                if test_category.endswith("_tests"):
                    category_results = await self._execute_test_category(
                        code, test_code, test_category, language
                    )
                    test_results.extend(category_results)
            
            # Calculate summary statistics
            total_tests = len(test_results)
            passed = sum(1 for r in test_results if r.status == "PASSED")
            failed = sum(1 for r in test_results if r.status == "FAILED") 
            skipped = sum(1 for r in test_results if r.status == "SKIPPED")
            errors = sum(1 for r in test_results if r.status == "ERROR")
            
            # Calculate overall coverage
            coverage_results = [r.coverage for r in test_results if r.coverage is not None]
            overall_coverage = sum(coverage_results) / len(coverage_results) if coverage_results else 0.0
            
            # Calculate quality score
            quality_score = self._calculate_test_quality_score(test_results, overall_coverage)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return TestSuiteResult(
                total_tests=total_tests,
                passed=passed,
                failed=failed,
                skipped=skipped,
                errors=errors,
                overall_coverage=overall_coverage,
                execution_time=execution_time,
                results=test_results,
                quality_score=quality_score
            )
            
        except Exception as e:
            logger.error("Test suite execution failed", error=str(e))
            return TestSuiteResult(
                total_tests=0,
                passed=0,
                failed=1,
                skipped=0,
                errors=1,
                overall_coverage=0.0,
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
                results=[TestResult(
                    test_name="Test Suite Execution",
                    test_type=TestType.UNIT,
                    status="ERROR",
                    execution_time=0,
                    error_message=str(e)
                )],
                quality_score=0.0
            )
    
    async def _analyze_code_structure(
        self, 
        code: str, 
        language: str
    ) -> Dict[str, Any]:
        """Analyze code structure for test generation"""
        
        analysis = {
            "functions": [],
            "classes": [],
            "imports": [],
            "complexity": 1,
            "api_endpoints": [],
            "database_interactions": [],
            "external_dependencies": []
        }
        
        try:
            if language == "python":
                tree = ast.parse(code)
                
                # Extract functions
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        func_info = {
                            "name": node.name,
                            "args": [arg.arg for arg in node.args.args],
                            "returns": self._extract_return_type(node),
                            "docstring": ast.get_docstring(node),
                            "line_number": node.lineno,
                            "is_async": isinstance(node, ast.AsyncFunctionDef)
                        }
                        analysis["functions"].append(func_info)
                    
                    elif isinstance(node, ast.ClassDef):
                        class_info = {
                            "name": node.name,
                            "methods": [],
                            "docstring": ast.get_docstring(node),
                            "line_number": node.lineno
                        }
                        
                        # Extract methods
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef):
                                class_info["methods"].append({
                                    "name": item.name,
                                    "args": [arg.arg for arg in item.args.args],
                                    "is_property": self._has_property_decorator(item)
                                })
                        
                        analysis["classes"].append(class_info)
                    
                    elif isinstance(node, (ast.Import, ast.ImportFrom)):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                analysis["imports"].append(alias.name)
                        else:
                            module = node.module or ""
                            for alias in node.names:
                                analysis["imports"].append(f"{module}.{alias.name}")
                
                # Detect API endpoints (FastAPI, Flask patterns)
                analysis["api_endpoints"] = self._detect_api_endpoints(code)
                
                # Detect database interactions
                analysis["database_interactions"] = self._detect_database_calls(code)
                
                # Detect external dependencies
                analysis["external_dependencies"] = self._detect_external_deps(analysis["imports"])
            
        except Exception as e:
            logger.error("Code structure analysis failed", error=str(e))
        
        return analysis
    
    async def _generate_unit_tests(
        self,
        code: str,
        language: str,
        analysis: Dict[str, Any],
        config: TestGenerationConfig
    ) -> str:
        """Generate comprehensive unit tests"""
        
        task = Task(
            id=f"unit-test-gen-{datetime.utcnow().timestamp()}",
            type="test_generation",
            description="Generate comprehensive unit tests for the provided code",
            metadata={
                "code": code,
                "language": language,
                "analysis": analysis,
                "test_type": "unit",
                "coverage_target": config.coverage_target
            }
        )
        
        context = {
            "test_generation_prompt": self._create_unit_test_prompt(code, analysis, config),
            "language": language,
            "framework": config.frameworks[0].value if config.frameworks else "pytest"
        }
        
        result = await self.unit_test_agent.execute(task, context)
        
        # Extract and clean the generated test code
        test_code = result.output.get("content", "")
        return self._clean_generated_test_code(test_code, language)
    
    async def _generate_integration_tests(
        self,
        code: str,
        language: str,
        analysis: Dict[str, Any],
        config: TestGenerationConfig
    ) -> str:
        """Generate integration tests for component interactions"""
        
        task = Task(
            id=f"integration-test-gen-{datetime.utcnow().timestamp()}",
            type="test_generation",
            description="Generate integration tests for component interactions",
            metadata={
                "code": code,
                "analysis": analysis,
                "test_type": "integration",
                "api_endpoints": analysis.get("api_endpoints", []),
                "database_interactions": analysis.get("database_interactions", [])
            }
        )
        
        context = {
            "test_generation_prompt": self._create_integration_test_prompt(code, analysis, config),
            "language": language,
            "framework": config.frameworks[0].value if config.frameworks else "pytest"
        }
        
        result = await self.integration_test_agent.execute(task, context)
        test_code = result.output.get("content", "")
        return self._clean_generated_test_code(test_code, language)
    
    async def _generate_functional_tests(
        self,
        code: str,
        language: str,
        analysis: Dict[str, Any],
        config: TestGenerationConfig
    ) -> str:
        """Generate functional/behavior-driven tests"""
        
        # Functional tests focus on business logic and user scenarios
        functional_prompt = f"""
        Generate functional tests that verify business logic and user scenarios for this code:
        
        {code}
        
        Focus on:
        1. Business rule validation
        2. User workflow testing  
        3. Error handling scenarios
        4. Edge cases and boundary conditions
        5. Data validation
        
        Generate tests using {config.frameworks[0].value} framework.
        Include both positive and negative test cases.
        """
        
        task = Task(
            id=f"functional-test-gen-{datetime.utcnow().timestamp()}",
            type="test_generation",
            description="Generate functional tests for business logic",
            metadata={"code": code, "test_type": "functional"}
        )
        
        context = {
            "test_generation_prompt": functional_prompt,
            "language": language
        }
        
        result = await self.integration_test_agent.execute(task, context)
        test_code = result.output.get("content", "")
        return self._clean_generated_test_code(test_code, language)
    
    async def _generate_security_tests(
        self,
        code: str,
        language: str,
        analysis: Dict[str, Any],
        config: TestGenerationConfig
    ) -> str:
        """Generate security-focused tests"""
        
        security_prompt = f"""
        Generate security tests for this code to identify vulnerabilities:
        
        {code}
        
        Generate tests for:
        1. Input validation and sanitization
        2. SQL injection prevention
        3. Cross-site scripting (XSS) prevention
        4. Authentication and authorization
        5. Data encryption and secure storage
        6. Rate limiting and DoS protection
        7. Sensitive data exposure
        
        Use {config.frameworks[0].value} framework with security testing patterns.
        Include tests for common security vulnerabilities (OWASP Top 10).
        """
        
        task = Task(
            id=f"security-test-gen-{datetime.utcnow().timestamp()}",
            type="test_generation", 
            description="Generate security vulnerability tests",
            metadata={"code": code, "test_type": "security"}
        )
        
        context = {
            "test_generation_prompt": security_prompt,
            "language": language
        }
        
        result = await self.security_test_agent.execute(task, context)
        test_code = result.output.get("content", "")
        return self._clean_generated_test_code(test_code, language)
    
    async def _generate_performance_tests(
        self,
        code: str,
        language: str,
        analysis: Dict[str, Any],
        config: TestGenerationConfig
    ) -> str:
        """Generate performance and load tests"""
        
        performance_prompt = f"""
        Generate performance tests for this code:
        
        {code}
        
        Create tests for:
        1. Response time benchmarks
        2. Memory usage validation
        3. CPU utilization checks
        4. Concurrent execution testing
        5. Load testing scenarios
        6. Stress testing edge cases
        7. Resource leak detection
        
        Use appropriate performance testing libraries and establish baselines.
        Include both micro-benchmarks and integration performance tests.
        """
        
        task = Task(
            id=f"performance-test-gen-{datetime.utcnow().timestamp()}",
            type="test_generation",
            description="Generate performance and load tests",
            metadata={"code": code, "test_type": "performance"}
        )
        
        context = {
            "test_generation_prompt": performance_prompt,
            "language": language
        }
        
        result = await self.integration_test_agent.execute(task, context)
        test_code = result.output.get("content", "")
        return self._clean_generated_test_code(test_code, language)
    
    async def _generate_test_fixtures(
        self,
        code: str,
        language: str,
        analysis: Dict[str, Any]
    ) -> str:
        """Generate test fixtures and test data"""
        
        fixtures_prompt = f"""
        Generate test fixtures and test data for this code:
        
        {code}
        
        Create:
        1. Sample data fixtures for testing
        2. Mock objects for external dependencies
        3. Test database setup/teardown
        4. Common test utilities
        5. Configuration fixtures
        6. Error scenario fixtures
        
        Make fixtures reusable across different test types.
        Include both valid and invalid data scenarios.
        """
        
        task = Task(
            id=f"fixtures-gen-{datetime.utcnow().timestamp()}",
            type="test_generation",
            description="Generate test fixtures and utilities",
            metadata={"code": code, "test_type": "fixtures"}
        )
        
        context = {
            "test_generation_prompt": fixtures_prompt,
            "language": language
        }
        
        result = await self.unit_test_agent.execute(task, context)
        return result.output.get("content", "")
    
    async def _generate_test_configs(
        self,
        language: str,
        frameworks: List[TestFramework]
    ) -> Dict[str, str]:
        """Generate test configuration files"""
        
        configs = {}
        
        for framework in frameworks:
            if framework == TestFramework.PYTEST and language == "python":
                configs["pytest.ini"] = self._generate_pytest_config()
                configs["conftest.py"] = self._generate_pytest_conftest()
            
            elif framework == TestFramework.JEST and language == "javascript":
                configs["jest.config.js"] = self._generate_jest_config()
            
            # Coverage configuration
            if language == "python":
                configs[".coveragerc"] = self._generate_coverage_config()
        
        return configs
    
    async def _execute_test_category(
        self,
        code: str,
        test_code: str,
        category: str,
        language: str
    ) -> List[TestResult]:
        """Execute a specific category of tests"""
        
        results = []
        
        try:
            # Execute in sandbox
            execution_result = await self.sandbox_client.execute_code(
                code=f"{code}\n\n{test_code}",
                language=language,
                tests=test_code,
                timeout=60
            )
            
            if execution_result.get("status") == "success":
                # Parse test results from output
                test_output = execution_result.get("output", "")
                parsed_results = self._parse_test_output(test_output, category)
                results.extend(parsed_results)
            else:
                # Test execution failed
                results.append(TestResult(
                    test_name=f"{category}_execution",
                    test_type=TestType(category.replace("_tests", "")),
                    status="ERROR",
                    execution_time=0,
                    error_message=execution_result.get("error", "Unknown error")
                ))
        
        except Exception as e:
            logger.error(f"Test execution failed for {category}", error=str(e))
            results.append(TestResult(
                test_name=f"{category}_execution",
                test_type=TestType(category.replace("_tests", "")),
                status="ERROR",
                execution_time=0,
                error_message=str(e)
            ))
        
        return results
    
    # Helper methods
    
    def _create_unit_test_prompt(
        self, 
        code: str, 
        analysis: Dict[str, Any], 
        config: TestGenerationConfig
    ) -> str:
        """Create detailed prompt for unit test generation"""
        
        functions = analysis.get("functions", [])
        classes = analysis.get("classes", [])
        
        prompt = f"""
        Generate comprehensive unit tests for the following code:
        
        {code}
        
        Code Analysis:
        - Functions: {len(functions)} ({[f["name"] for f in functions[:5]]})
        - Classes: {len(classes)} ({[c["name"] for c in classes[:3]]})
        - External Dependencies: {analysis.get("external_dependencies", [])}
        
        Requirements:
        - Coverage Target: {config.coverage_target}%
        - Include Edge Cases: {config.include_edge_cases}
        - Include Error Cases: {config.include_error_cases}
        - Mock External Dependencies: {config.mock_external_dependencies}
        
        Generate tests that:
        1. Test all public functions and methods
        2. Cover normal, edge, and error cases
        3. Mock external dependencies appropriately
        4. Use appropriate assertions
        5. Follow testing best practices
        6. Include setup and teardown as needed
        
        Use {config.frameworks[0].value} framework.
        
        IMPORTANT: Generate actual working test code, not pseudocode or comments.
        """
        
        return prompt
    
    def _create_integration_test_prompt(
        self, 
        code: str, 
        analysis: Dict[str, Any], 
        config: TestGenerationConfig
    ) -> str:
        """Create prompt for integration test generation"""
        
        api_endpoints = analysis.get("api_endpoints", [])
        db_interactions = analysis.get("database_interactions", [])
        
        prompt = f"""
        Generate integration tests for the following code:
        
        {code}
        
        Focus on testing:
        - API Endpoints: {api_endpoints}
        - Database Interactions: {db_interactions}
        - Service Dependencies: {analysis.get("external_dependencies", [])}
        
        Generate tests that:
        1. Test end-to-end workflows
        2. Verify component interactions
        3. Test database operations
        4. Test API contracts
        5. Test error propagation
        6. Test transaction handling
        
        Use {config.frameworks[0].value} with appropriate integration testing patterns.
        Include test data setup and cleanup.
        """
        
        return prompt
    
    def _clean_generated_test_code(self, test_code: str, language: str) -> str:
        """Clean and validate generated test code"""
        
        # Remove markdown code block markers
        if "```" in test_code:
            lines = test_code.split('\n')
            in_code_block = False
            cleaned_lines = []
            
            for line in lines:
                if line.strip().startswith("```"):
                    in_code_block = not in_code_block
                    continue
                if in_code_block:
                    cleaned_lines.append(line)
            
            test_code = '\n'.join(cleaned_lines)
        
        # Basic syntax validation
        if language == "python":
            try:
                ast.parse(test_code)
            except SyntaxError as e:
                logger.warning(f"Generated test code has syntax error: {e}")
                # Could implement auto-fixing here
        
        return test_code.strip()
    
    def _parse_test_output(self, output: str, category: str) -> List[TestResult]:
        """Parse test execution output into structured results"""
        
        results = []
        
        # Simple parsing - could be enhanced based on specific test framework output
        lines = output.split('\n')
        
        for line in lines:
            if "PASSED" in line or "FAILED" in line or "ERROR" in line:
                # Extract test name and status
                parts = line.split()
                if len(parts) >= 2:
                    test_name = parts[0] if "::" not in parts[0] else parts[0].split("::")[-1]
                    status = "PASSED" if "PASSED" in line else "FAILED" if "FAILED" in line else "ERROR"
                    
                    results.append(TestResult(
                        test_name=test_name,
                        test_type=TestType(category.replace("_tests", "")),
                        status=status,
                        execution_time=0  # Could extract from output
                    ))
        
        # If no specific results found, create a summary result
        if not results:
            status = "PASSED" if "error" not in output.lower() and "failed" not in output.lower() else "FAILED"
            results.append(TestResult(
                test_name=f"{category}_suite",
                test_type=TestType(category.replace("_tests", "")),
                status=status,
                execution_time=0
            ))
        
        return results
    
    def _calculate_test_quality_score(
        self, 
        test_results: List[TestResult], 
        coverage: float
    ) -> float:
        """Calculate overall test quality score"""
        
        if not test_results:
            return 0.0
        
        # Pass rate score
        total_tests = len(test_results)
        passed_tests = sum(1 for r in test_results if r.status == "PASSED")
        pass_rate = passed_tests / total_tests if total_tests > 0 else 0
        
        # Coverage score
        coverage_score = coverage / 100
        
        # Combined score (weighted)
        quality_score = (pass_rate * 0.6) + (coverage_score * 0.4)
        
        return min(1.0, quality_score)
    
    # Configuration generators
    
    def _generate_pytest_config(self) -> str:
        """Generate pytest.ini configuration"""
        return """[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --strict-config
    --verbose
    --tb=short
    --cov=src
    --cov-report=term-missing
    --cov-report=html
    --cov-report=xml
    --cov-fail-under=80
markers =
    unit: Unit tests
    integration: Integration tests
    functional: Functional tests
    security: Security tests
    performance: Performance tests
    slow: Slow running tests
"""
    
    def _generate_pytest_conftest(self) -> str:
        """Generate conftest.py for pytest fixtures"""
        return """import pytest
import asyncio
from unittest.mock import Mock, patch


@pytest.fixture(scope="session")
def event_loop():
    \"\"\"Create an instance of the default event loop for the test session.\"\"\"
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_database():
    \"\"\"Mock database connection.\"\"\"
    with patch('src.database.get_connection') as mock_conn:
        yield mock_conn


@pytest.fixture
def sample_data():
    \"\"\"Sample test data.\"\"\"
    return {
        "test_user": {"id": 1, "name": "Test User", "email": "test@example.com"},
        "test_product": {"id": 1, "name": "Test Product", "price": 99.99},
    }
"""
    
    def _generate_coverage_config(self) -> str:
        """Generate .coveragerc configuration"""
        return """[run]
source = src/
omit = 
    */tests/*
    */venv/*
    */migrations/*
    */__pycache__/*
    */site-packages/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:

[html]
directory = htmlcov

[xml]
output = coverage.xml
"""
    
    # Code analysis helpers
    
    def _extract_return_type(self, node: ast.FunctionDef) -> Optional[str]:
        """Extract return type annotation from function"""
        if node.returns:
            return ast.unparse(node.returns) if hasattr(ast, 'unparse') else "Any"
        return None
    
    def _has_property_decorator(self, node: ast.FunctionDef) -> bool:
        """Check if function has @property decorator"""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "property":
                return True
        return False
    
    def _detect_api_endpoints(self, code: str) -> List[str]:
        """Detect API endpoints in code"""
        endpoints = []
        
        # Simple pattern matching for common frameworks
        import re
        patterns = [
            r"@app\.route\(['\"]([^'\"]+)['\"]",          # Flask
            r"@router\.\w+\(['\"]([^'\"]+)['\"]",         # FastAPI
            r"@\w+\.mapping\(['\"]([^'\"]+)['\"]"        # Spring-like
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, code)
            endpoints.extend(matches)
        
        return endpoints
    
    def _detect_database_calls(self, code: str) -> List[str]:
        """Detect database interaction patterns"""
        interactions = []
        
        # Common database patterns
        import re
        patterns = [
            r"\.execute\(",
            r"\.query\(",
            r"\.save\(",
            r"\.delete\(",
            r"\.update\(",
            r"\.insert\(",
            r"SELECT.*FROM",
            r"INSERT.*INTO",
            r"UPDATE.*SET",
            r"DELETE.*FROM"
        ]
        
        for pattern in patterns:
            if re.search(pattern, code, re.IGNORECASE):
                interactions.append(pattern)
        
        return list(set(interactions))
    
    def _detect_external_deps(self, imports: List[str]) -> List[str]:
        """Detect external dependencies that need mocking"""
        external_deps = []
        
        # Common external dependencies
        external_patterns = [
            "requests", "httpx", "aiohttp",  # HTTP clients
            "redis", "pymongo",              # Databases
            "boto3", "azure",                # Cloud services
            "stripe", "paypal",              # Payment services
            "sendgrid", "mailgun"            # Email services
        ]
        
        for imp in imports:
            for pattern in external_patterns:
                if pattern in imp.lower():
                    external_deps.append(imp)
                    break
        
        return external_deps


# Export main classes
__all__ = [
    "ProductionTestGenerator", 
    "TestType", 
    "TestFramework", 
    "TestGenerationConfig",
    "TestSuiteResult"
]