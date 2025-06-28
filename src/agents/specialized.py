"""
Specialized agents for production-grade code generation
Each agent has deep expertise in specific aspects of software development
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import re
import ast

from src.common.models import Task, TaskResult, TaskStatus, AgentTier
from src.agents.agent_roles import SpecializedAgent, AgentRole
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
import structlog

from src.common.config import settings
from src.agents.azure_llm_client import llm_client, LLMProvider

logger = structlog.get_logger()

# Initialize LLM clients - keep for backward compatibility but use unified client
openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)


class ProductionArchitectAgent(SpecializedAgent):
    """Specialized in system design and architecture"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id, AgentRole.ARCHITECT, AgentTier.T2)
    
    async def execute(self, task: Task, context: Dict[str, Any]) -> TaskResult:
        """Design comprehensive system architecture"""
        logger.info(f"Production Architect designing system", task_id=task.id)
        
        start_time = datetime.utcnow()
        
        try:
            # Build architecture-focused prompt
            system_prompt = f"""{self.specialization_prompts[self.role]}

You must produce a comprehensive architectural design that includes:
1. High-level system architecture
2. Component breakdown and responsibilities
3. Data flow and API contracts
4. Technology stack recommendations
5. Scalability and performance considerations
6. Security architecture
7. Error handling and resilience patterns
8. Deployment architecture

Output format must be JSON with these exact keys:
{{
    "architecture": {{
        "overview": "system overview",
        "components": [{{
            "name": "component name",
            "responsibility": "what it does",
            "interfaces": ["api1", "api2"],
            "dependencies": ["dep1", "dep2"]
        }}],
        "data_flow": "description of data flow",
        "api_contracts": [{{
            "endpoint": "/api/v1/resource",
            "method": "POST",
            "request": {{}},
            "response": {{}},
            "errors": []
        }}],
        "technology_stack": {{
            "language": "Python",
            "framework": "FastAPI",
            "database": "PostgreSQL",
            "cache": "Redis",
            "queue": "RabbitMQ"
        }},
        "scalability": {{
            "horizontal_scaling": "approach",
            "caching_strategy": "strategy",
            "database_sharding": "if needed"
        }},
        "security": {{
            "authentication": "method",
            "authorization": "RBAC/ABAC",
            "encryption": "at rest and in transit",
            "api_security": "rate limiting, CORS, etc"
        }},
        "deployment": {{
            "containerization": "Docker",
            "orchestration": "Kubernetes",
            "ci_cd": "GitHub Actions",
            "monitoring": "Prometheus + Grafana"
        }}
    }},
    "implementation_notes": "key implementation considerations",
    "risk_analysis": ["risk1", "risk2"]
}}"""
            
            user_prompt = f"""Design a production-ready architecture for: {task.description}

Requirements:
{json.dumps(context.get('requirements', {}), indent=2)}

Constraints:
{json.dumps(context.get('constraints', {}), indent=2)}

Quality Standards:
{json.dumps(context.get('quality_standards', {}), indent=2)}"""
            
            # Use Azure OpenAI GPT-4 for architecture
            response = await llm_client.chat_completion(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=4000
            )
            
            # Parse response
            content = response['content']
            
            # Extract JSON from response - look for code blocks first
            architecture_design = None
            
            # Try to find JSON in code blocks
            code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if code_block_match:
                try:
                    architecture_design = json.loads(code_block_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # If not found in code blocks, try to find any JSON object
            if not architecture_design:
                # Find all potential JSON objects
                json_candidates = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content)
                for candidate in json_candidates:
                    try:
                        # Try to parse each candidate
                        parsed = json.loads(candidate)
                        # Check if it looks like an architecture object
                        if isinstance(parsed, dict) and any(key in parsed for key in ['architecture', 'components', 'overview']):
                            architecture_design = parsed
                            break
                    except json.JSONDecodeError:
                        continue
            
            # Fallback structure if JSON extraction failed
            if not architecture_design:
                architecture_design = {
                    "architecture": {
                        "overview": content[:500],  # First 500 chars as overview
                        "components": [],
                        "technology_stack": {}
                    },
                    "implementation_notes": "Architecture extracted from text response",
                    "risk_analysis": []
                }
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                output_type="architecture",
                output=architecture_design,
                execution_time=execution_time,
                agent_tier_used=self.tier,
                confidence_score=0.9,
                metadata={
                    "agent_id": self.agent_id,
                    "role": self.role,
                    "model_used": "gpt-4-turbo"
                }
            )
            
        except Exception as e:
            logger.error(f"Architecture design failed", error=str(e))
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                output_type="error",
                output={"error": str(e)},
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
                agent_tier_used=self.tier,
                confidence_score=0.0,
                metadata={"agent_id": self.agent_id, "role": self.role}
            )


class ProductionImplementerAgent(SpecializedAgent):
    """Specialized in writing production-grade code"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id, AgentRole.IMPLEMENTER, AgentTier.T2)
    
    async def execute(self, task: Task, context: Dict[str, Any]) -> TaskResult:
        """Implement production-ready code based on architecture"""
        logger.info(f"Production Implementer coding solution", task_id=task.id)
        
        start_time = datetime.utcnow()
        
        try:
            # Get architecture from context if available
            architecture = None
            for key, value in context.items():
                if "architect" in key.lower() and isinstance(value, dict):
                    architecture = value.get("architecture", value)
                    break
            
            system_prompt = f"""{self.specialization_prompts[self.role]}

Generate PRODUCTION-READY code with:
- Comprehensive error handling and input validation
- Proper logging and monitoring hooks
- Performance optimizations
- Security best practices
- Clean code principles (SOLID, DRY, KISS)
- Type hints and documentation
- Configuration management
- Graceful degradation
- Health checks and metrics

The code must be immediately deployable to production."""
            
            user_prompt = f"""Implement production code for: {task.description}

Requirements:
{json.dumps(context.get('requirements', {}), indent=2)}"""
            
            if architecture:
                user_prompt += f"\n\nArchitecture Design:\n{json.dumps(architecture, indent=2)}"
            
            # Use GPT-4 for implementation (via unified client for Azure support)
            response = await llm_client.chat_completion(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=4000
            )
            
            code_content = response['content']
            
            # Structure the output
            output = {
                "code": code_content,
                "language": self._detect_language(code_content),
                "features_implemented": self._extract_features(code_content),
                "dependencies": self._extract_dependencies(code_content)
            }
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                output_type="implementation",
                output=output,
                execution_time=execution_time,
                agent_tier_used=self.tier,
                confidence_score=0.85,
                metadata={
                    "agent_id": self.agent_id,
                    "role": self.role,
                    "model_used": "gpt-4-turbo",
                    "has_architecture": architecture is not None
                }
            )
            
        except Exception as e:
            logger.error(f"Implementation failed", error=str(e))
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                output_type="error",
                output={"error": str(e)},
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
                agent_tier_used=self.tier,
                confidence_score=0.0,
                metadata={"agent_id": self.agent_id, "role": self.role}
            )
    
    def _detect_language(self, code: str) -> str:
        """Detect programming language from code"""
        if "import " in code and "def " in code:
            return "python"
        elif "const " in code or "function " in code or "=>" in code:
            return "javascript"
        elif "func " in code and "package " in code:
            return "go"
        elif "fn " in code and "let " in code:
            return "rust"
        elif "public class" in code or "public static" in code:
            return "java"
        else:
            return "unknown"
    
    def _extract_features(self, code: str) -> List[str]:
        """Extract implemented features from code"""
        features = []
        
        # Python patterns
        if "@app." in code:
            features.append("REST API endpoints")
        if "async def" in code:
            features.append("Async/await support")
        if "try:" in code or "except:" in code:
            features.append("Error handling")
        if "logger." in code or "logging." in code:
            features.append("Logging")
        if "class " in code:
            features.append("Object-oriented design")
        if "@pytest" in code or "unittest" in code:
            features.append("Unit tests")
        if "JWT" in code or "jwt" in code:
            features.append("JWT authentication")
        if "bcrypt" in code or "hashlib" in code:
            features.append("Password hashing")
        if "rate_limit" in code or "RateLimiter" in code:
            features.append("Rate limiting")
        if "cache" in code or "Redis" in code:
            features.append("Caching")
        if "health" in code and "check" in code:
            features.append("Health checks")
        
        return features
    
    def _extract_dependencies(self, code: str) -> List[str]:
        """Extract dependencies from code"""
        dependencies = set()
        
        # Python imports
        import_pattern = r'(?:from\s+([\w\.]+)|import\s+([\w\.]+))'
        for match in re.finditer(import_pattern, code):
            dep = match.group(1) or match.group(2)
            if dep and not dep.startswith(('src', '.', '__')):
                dependencies.add(dep.split('.')[0])
        
        # Package.json style
        if '"dependencies"' in code:
            try:
                deps_match = re.search(r'"dependencies"\s*:\s*\{([^}]+)\}', code)
                if deps_match:
                    deps_content = deps_match.group(1)
                    for dep in re.findall(r'"([^"]+)"\s*:', deps_content):
                        dependencies.add(dep)
            except:
                pass
        
        return list(dependencies)


class ProductionReviewerAgent(SpecializedAgent):
    """Specialized in code review and quality assurance"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id, AgentRole.REVIEWER, AgentTier.T2)
    
    async def execute(self, task: Task, context: Dict[str, Any]) -> TaskResult:
        """Review code for production readiness"""
        logger.info(f"Production Reviewer analyzing code", task_id=task.id)
        
        start_time = datetime.utcnow()
        
        try:
            # Get code from context
            code_to_review = None
            for key, value in context.items():
                if "implementer" in key.lower() and isinstance(value, dict):
                    code_to_review = value.get("code", value.get("content", ""))
                    break
            
            if not code_to_review:
                # If no implementer output, review the task itself
                code_to_review = task.description
            
            system_prompt = f"""{self.specialization_prompts[self.role]}

Perform a thorough code review checking for:
1. Security vulnerabilities (OWASP Top 10)
2. Performance issues and bottlenecks
3. Error handling completeness
4. Code maintainability and readability
5. Best practices and design patterns
6. Test coverage adequacy
7. Documentation quality
8. Production readiness

Provide specific, actionable feedback with severity levels."""
            
            user_prompt = f"""Review this code for production deployment:

```
{code_to_review[:3000]}  # Limit for token management
```

Original requirements: {task.description}

Provide a detailed review in JSON format:
{{
    "overall_assessment": "APPROVED|NEEDS_WORK|REJECTED",
    "score": 0-100,
    "issues": [
        {{
            "severity": "CRITICAL|HIGH|MEDIUM|LOW",
            "category": "SECURITY|PERFORMANCE|MAINTAINABILITY|TESTING|DOCUMENTATION",
            "description": "issue description",
            "recommendation": "how to fix",
            "line_numbers": [1, 2, 3]
        }}
    ],
    "strengths": ["what's done well"],
    "recommendations": ["specific improvements"],
    "security_analysis": {{
        "vulnerabilities_found": [],
        "security_score": 0-100
    }},
    "performance_analysis": {{
        "potential_bottlenecks": [],
        "optimization_suggestions": []
    }},
    "test_coverage_assessment": "assessment of testing",
    "production_readiness": {{
        "ready": true/false,
        "blockers": [],
        "warnings": []
    }}
}}"""
            
            # Use Azure OpenAI GPT-4 for thorough review
            response = await llm_client.chat_completion(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Low temperature for consistent reviews
                max_tokens=4000
            )
            
            review_content = response['content']
            
            # Parse JSON response
            json_match = re.search(r'\{.*\}', review_content, re.DOTALL)
            if json_match:
                review_result = json.loads(json_match.group())
            else:
                # Fallback review structure
                review_result = {
                    "overall_assessment": "NEEDS_WORK",
                    "score": 70,
                    "issues": [],
                    "strengths": [],
                    "recommendations": [review_content],
                    "production_readiness": {"ready": False, "blockers": ["Could not parse review"]}
                }
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Calculate confidence based on review thoroughness
            confidence = min(0.95, 0.7 + len(review_result.get("issues", [])) * 0.05)
            
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                output_type="review",
                output=review_result,
                execution_time=execution_time,
                agent_tier_used=self.tier,
                confidence_score=confidence,
                metadata={
                    "agent_id": self.agent_id,
                    "role": self.role,
                    "model_used": "gpt-4-turbo",
                    "code_reviewed": bool(code_to_review)
                }
            )
            
        except Exception as e:
            logger.error(f"Code review failed", error=str(e))
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                output_type="error",
                output={"error": str(e)},
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
                agent_tier_used=self.tier,
                confidence_score=0.0,
                metadata={"agent_id": self.agent_id, "role": self.role}
            )


class ProductionSecurityAgent(SpecializedAgent):
    """Specialized in security analysis and hardening"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id, AgentRole.SECURITY_EXPERT, AgentTier.T2)
    
    async def execute(self, task: Task, context: Dict[str, Any]) -> TaskResult:
        """Perform security analysis and provide hardening recommendations"""
        logger.info(f"Security Expert analyzing for vulnerabilities", task_id=task.id)
        
        start_time = datetime.utcnow()
        
        try:
            system_prompt = f"""{self.specialization_prompts[self.role]}

Perform comprehensive security analysis including:
1. OWASP Top 10 vulnerability assessment
2. Authentication and authorization review
3. Input validation and sanitization
4. Encryption and data protection
5. API security (rate limiting, CORS, etc)
6. Dependency vulnerability scanning
7. Security headers and configurations
8. Compliance requirements (GDPR, PCI-DSS, etc)

Provide specific remediation steps for each finding."""
            
            # Gather all code from context
            code_snippets = []
            for key, value in context.items():
                if isinstance(value, dict) and ("code" in value or "content" in value):
                    code_snippets.append(value.get("code", value.get("content", "")))
            
            combined_code = "\n\n".join(code_snippets) if code_snippets else task.description
            
            user_prompt = f"""Perform security analysis for: {task.description}

Code to analyze:
```
{combined_code[:3000]}
```

Requirements:
{json.dumps(context.get('requirements', {}), indent=2)}

Provide security analysis in JSON format:
{{
    "security_score": 0-100,
    "vulnerabilities": [
        {{
            "type": "SQL Injection|XSS|CSRF|etc",
            "severity": "CRITICAL|HIGH|MEDIUM|LOW",
            "description": "detailed description",
            "location": "where found",
            "remediation": "how to fix",
            "cwe_id": "CWE-XXX"
        }}
    ],
    "security_controls": {{
        "authentication": {{
            "implemented": true/false,
            "method": "JWT|OAuth2|etc",
            "strength": "STRONG|ADEQUATE|WEAK"
        }},
        "authorization": {{
            "implemented": true/false,
            "model": "RBAC|ABAC|etc",
            "granularity": "fine|coarse"
        }},
        "encryption": {{
            "at_rest": true/false,
            "in_transit": true/false,
            "algorithms": []
        }},
        "input_validation": {{
            "implemented": true/false,
            "coverage": "percentage"
        }}
    }},
    "recommendations": [
        {{
            "priority": "HIGH|MEDIUM|LOW",
            "action": "specific action to take",
            "implementation": "how to implement"
        }}
    ],
    "compliance": {{
        "gdpr": "COMPLIANT|PARTIAL|NON_COMPLIANT",
        "pci_dss": "if applicable",
        "issues": []
    }},
    "secure_code_snippets": {{
        "description": "secure implementation examples"
    }}
}}"""
            
            response = await llm_client.chat_completion(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=4000
            )
            
            security_analysis = json.loads(response['content'])
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                output_type="security_analysis",
                output=security_analysis,
                execution_time=execution_time,
                agent_tier_used=self.tier,
                confidence_score=0.9,
                metadata={
                    "agent_id": self.agent_id,
                    "role": self.role,
                    "model_used": "gpt-4-turbo",
                    "vulnerabilities_found": len(security_analysis.get("vulnerabilities", []))
                }
            )
            
        except Exception as e:
            logger.error(f"Security analysis failed", error=str(e))
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                output_type="error",
                output={"error": str(e)},
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
                agent_tier_used=self.tier,
                confidence_score=0.0,
                metadata={"agent_id": self.agent_id, "role": self.role}
            )


class ProductionTestAgent(SpecializedAgent):
    """Specialized in comprehensive test generation"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id, AgentRole.TEST_ENGINEER, AgentTier.T1)
    
    async def execute(self, task: Task, context: Dict[str, Any]) -> TaskResult:
        """Generate comprehensive test suite"""
        logger.info(f"Test Engineer creating test suite", task_id=task.id)
        
        start_time = datetime.utcnow()
        
        try:
            # Get implementation code
            implementation_code = ""
            for key, value in context.items():
                if "implementer" in key.lower() and isinstance(value, dict):
                    implementation_code = value.get("code", value.get("content", ""))
                    break
            
            system_prompt = f"""{self.specialization_prompts[self.role]}

Generate a COMPREHENSIVE test suite including:
1. Unit tests for all functions/methods
2. Integration tests for API endpoints
3. Edge cases and error scenarios
4. Performance tests
5. Security tests
6. Mock objects and fixtures
7. Test data generation
8. CI/CD integration

Use appropriate testing frameworks (pytest, jest, etc)."""
            
            user_prompt = f"""Generate comprehensive tests for: {task.description}

Implementation to test:
```
{implementation_code[:2000]}
```

Generate tests with:
- High code coverage (aim for >90%)
- Edge case handling
- Error scenario testing
- Performance benchmarks
- Security test cases
- Clear test names and documentation"""
            
            response = await llm_client.chat_completion(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=4000
            )
            
            test_code = response['content']
            
            # Analyze test coverage
            test_analysis = self._analyze_test_coverage(test_code, implementation_code)
            
            output = {
                "tests": test_code,
                "test_framework": self._detect_test_framework(test_code),
                "test_types": self._categorize_tests(test_code),
                "coverage_analysis": test_analysis,
                "ci_cd_config": self._generate_ci_config(test_code)
            }
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                output_type="tests",
                output=output,
                execution_time=execution_time,
                agent_tier_used=self.tier,
                confidence_score=0.85,
                metadata={
                    "agent_id": self.agent_id,
                    "role": self.role,
                    "model_used": "gpt-4-turbo",
                    "has_implementation": bool(implementation_code)
                }
            )
            
        except Exception as e:
            logger.error(f"Test generation failed", error=str(e))
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                output_type="error",
                output={"error": str(e)},
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
                agent_tier_used=self.tier,
                confidence_score=0.0,
                metadata={"agent_id": self.agent_id, "role": self.role}
            )
    
    def _detect_test_framework(self, test_code: str) -> str:
        """Detect testing framework used"""
        if "pytest" in test_code or "@pytest" in test_code:
            return "pytest"
        elif "jest" in test_code or "describe(" in test_code:
            return "jest"
        elif "unittest" in test_code:
            return "unittest"
        elif "go test" in test_code:
            return "go test"
        else:
            return "unknown"
    
    def _categorize_tests(self, test_code: str) -> List[str]:
        """Categorize types of tests present"""
        categories = []
        
        if "test_" in test_code or "it(" in test_code:
            categories.append("unit tests")
        if "integration" in test_code.lower():
            categories.append("integration tests")
        if "performance" in test_code.lower() or "benchmark" in test_code.lower():
            categories.append("performance tests")
        if "security" in test_code.lower():
            categories.append("security tests")
        if "mock" in test_code.lower() or "Mock" in test_code:
            categories.append("mocked tests")
        
        return categories
    
    def _analyze_test_coverage(self, test_code: str, implementation_code: str) -> Dict[str, Any]:
        """Analyze test coverage (simplified)"""
        # Extract function/method names from implementation
        impl_functions = re.findall(r'(?:def|function|func)\s+(\w+)', implementation_code)
        
        # Check how many are tested
        tested_functions = []
        for func in impl_functions:
            if func in test_code:
                tested_functions.append(func)
        
        coverage_percent = (len(tested_functions) / len(impl_functions) * 100) if impl_functions else 0
        
        return {
            "estimated_coverage": f"{coverage_percent:.1f}%",
            "functions_found": len(impl_functions),
            "functions_tested": len(tested_functions),
            "untested_functions": list(set(impl_functions) - set(tested_functions))
        }
    
    def _generate_ci_config(self, test_code: str) -> str:
        """Generate basic CI/CD configuration"""
        if "pytest" in test_code:
            return """# GitHub Actions CI
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - uses: actions/setup-python@v2
    - run: pip install -r requirements.txt
    - run: pytest --cov=. --cov-report=xml
    - uses: codecov/codecov-action@v1"""
        elif "jest" in test_code:
            return """# GitHub Actions CI
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - uses: actions/setup-node@v2
    - run: npm install
    - run: npm test -- --coverage"""
        else:
            return "# Add your CI/CD configuration here"


class ProductionOptimizerAgent(SpecializedAgent):
    """Specialized in performance optimization"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id, AgentRole.OPTIMIZER, AgentTier.T2)
    
    async def execute(self, task: Task, context: Dict[str, Any]) -> TaskResult:
        """Optimize code for production performance"""
        logger.info(f"Optimizer improving performance", task_id=task.id)
        
        start_time = datetime.utcnow()
        
        try:
            # Get code to optimize
            code_to_optimize = ""
            for key, value in context.items():
                if isinstance(value, dict) and ("code" in value or "content" in value):
                    code_to_optimize = value.get("code", value.get("content", ""))
                    if code_to_optimize:
                        break
            
            system_prompt = f"""{self.specialization_prompts[self.role]}

Optimize the code for production with focus on:
1. Algorithm efficiency (time and space complexity)
2. Database query optimization
3. Caching strategies
4. Asynchronous operations
5. Memory management
6. Connection pooling
7. Batch processing
8. Resource utilization

Provide specific optimizations with performance impact estimates."""
            
            user_prompt = f"""Optimize this code for production performance:

```
{code_to_optimize[:2500]}
```

Task requirements: {task.description}

Provide optimizations in JSON format:
{{
    "optimized_code": "the optimized version",
    "optimizations": [
        {{
            "type": "ALGORITHM|DATABASE|CACHING|ASYNC|MEMORY",
            "description": "what was optimized",
            "impact": "estimated performance improvement",
            "before": "original code snippet",
            "after": "optimized code snippet"
        }}
    ],
    "performance_metrics": {{
        "estimated_latency_reduction": "percentage",
        "memory_savings": "percentage",
        "throughput_increase": "percentage"
    }},
    "caching_strategy": {{
        "cache_points": [],
        "ttl_recommendations": {{}},
        "cache_invalidation": ""
    }},
    "scaling_recommendations": [
        {{
            "aspect": "what to scale",
            "approach": "how to scale",
            "threshold": "when to scale"
        }}
    ],
    "monitoring_points": [
        "metrics to track"
    ]
}}"""
            
            response = await llm_client.chat_completion(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=4000
            )
            
            optimization_result = json.loads(response['content'])
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                output_type="optimization",
                output=optimization_result,
                execution_time=execution_time,
                agent_tier_used=self.tier,
                confidence_score=0.85,
                metadata={
                    "agent_id": self.agent_id,
                    "role": self.role,
                    "model_used": "gpt-4-turbo",
                    "optimizations_count": len(optimization_result.get("optimizations", []))
                }
            )
            
        except Exception as e:
            logger.error(f"Optimization failed", error=str(e))
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                output_type="error",
                output={"error": str(e)},
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
                agent_tier_used=self.tier,
                confidence_score=0.0,
                metadata={"agent_id": self.agent_id, "role": self.role}
            )


class ProductionDocumentorAgent(SpecializedAgent):
    """Specialized in comprehensive documentation"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id, AgentRole.DOCUMENTOR, AgentTier.T1)
    
    async def execute(self, task: Task, context: Dict[str, Any]) -> TaskResult:
        """Generate comprehensive documentation"""
        logger.info(f"Documentor creating documentation", task_id=task.id)
        
        start_time = datetime.utcnow()
        
        try:
            # Gather all context
            architecture = None
            implementation = None
            tests = None
            
            for key, value in context.items():
                if "architect" in key.lower():
                    architecture = value
                elif "implementer" in key.lower():
                    implementation = value
                elif "test" in key.lower():
                    tests = value
            
            system_prompt = f"""{self.specialization_prompts[self.role]}

Create comprehensive documentation including:
1. API documentation with examples
2. Architecture overview and diagrams
3. Installation and setup guide
4. Configuration documentation
5. Usage examples and tutorials
6. Troubleshooting guide
7. Performance tuning guide
8. Security best practices
9. Deployment guide
10. Monitoring and maintenance

Use clear, concise language with lots of examples."""
            
            user_prompt = f"""Create comprehensive documentation for: {task.description}

Context available:
- Architecture design: {'Yes' if architecture else 'No'}
- Implementation code: {'Yes' if implementation else 'No'}
- Test suite: {'Yes' if tests else 'No'}

Requirements:
{json.dumps(context.get('requirements', {}), indent=2)}

Generate documentation in Markdown format with proper sections."""
            
            response = await llm_client.chat_completion(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=4000
            )
            
            documentation = response['content']
            
            # Structure the documentation
            output = {
                "documentation": documentation,
                "sections": self._extract_sections(documentation),
                "api_docs": self._extract_api_docs(documentation, implementation),
                "examples": self._extract_examples(documentation),
                "deployment_guide": self._extract_deployment_info(documentation)
            }
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                output_type="documentation",
                output=output,
                execution_time=execution_time,
                agent_tier_used=self.tier,
                confidence_score=0.8,
                metadata={
                    "agent_id": self.agent_id,
                    "role": self.role,
                    "model_used": "gpt-4-turbo",
                    "documentation_length": len(documentation)
                }
            )
            
        except Exception as e:
            logger.error(f"Documentation generation failed", error=str(e))
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                output_type="error",
                output={"error": str(e)},
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
                agent_tier_used=self.tier,
                confidence_score=0.0,
                metadata={"agent_id": self.agent_id, "role": self.role}
            )
    
    def _extract_sections(self, documentation: str) -> List[str]:
        """Extract main sections from documentation"""
        sections = []
        for match in re.finditer(r'^#{1,3}\s+(.+)$', documentation, re.MULTILINE):
            sections.append(match.group(1))
        return sections
    
    def _extract_api_docs(self, documentation: str, implementation: Optional[Dict]) -> Dict[str, Any]:
        """Extract API documentation"""
        api_docs = {
            "endpoints": [],
            "has_examples": "example" in documentation.lower(),
            "has_auth_docs": "authentication" in documentation.lower()
        }
        
        # Find API endpoint documentation
        endpoint_pattern = r'(?:GET|POST|PUT|DELETE|PATCH)\s+(/[\w/\-{}]+)'
        for match in re.finditer(endpoint_pattern, documentation):
            api_docs["endpoints"].append(match.group(0))
        
        return api_docs
    
    def _extract_examples(self, documentation: str) -> List[str]:
        """Extract code examples from documentation"""
        examples = []
        code_block_pattern = r'```[\w]*\n(.*?)\n```'
        for match in re.finditer(code_block_pattern, documentation, re.DOTALL):
            examples.append(match.group(1))
        return examples[:5]  # Limit to first 5 examples
    
    def _extract_deployment_info(self, documentation: str) -> Dict[str, bool]:
        """Check what deployment information is included"""
        return {
            "has_docker": "docker" in documentation.lower(),
            "has_kubernetes": "kubernetes" in documentation.lower() or "k8s" in documentation.lower(),
            "has_ci_cd": "ci/cd" in documentation.lower() or "github actions" in documentation.lower(),
            "has_monitoring": "monitoring" in documentation.lower() or "prometheus" in documentation.lower(),
            "has_scaling": "scaling" in documentation.lower() or "scale" in documentation.lower()
        }


# Factory function to create specialized agents
def create_specialized_agent(role: AgentRole, agent_id: str) -> SpecializedAgent:
    """Factory to create the appropriate specialized agent"""
    agent_classes = {
        AgentRole.ARCHITECT: ProductionArchitectAgent,
        AgentRole.IMPLEMENTER: ProductionImplementerAgent,
        AgentRole.REVIEWER: ProductionReviewerAgent,
        AgentRole.SECURITY_EXPERT: ProductionSecurityAgent,
        AgentRole.TEST_ENGINEER: ProductionTestAgent,
        AgentRole.OPTIMIZER: ProductionOptimizerAgent,
        AgentRole.DOCUMENTOR: ProductionDocumentorAgent
    }
    
    agent_class = agent_classes.get(role)
    if not agent_class:
        raise ValueError(f"Unknown agent role: {role}")
    
    return agent_class(agent_id)


# Export all specialized agents
__all__ = [
    "ProductionArchitectAgent",
    "ProductionImplementerAgent", 
    "ProductionReviewerAgent",
    "ProductionSecurityAgent",
    "ProductionTestAgent",
    "ProductionOptimizerAgent",
    "ProductionDocumentorAgent",
    "create_specialized_agent"
]
