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
from src.agents.ensemble import SpecializedAgent, AgentRole
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
import structlog

from src.common.config import settings

logger = structlog.get_logger()

# Initialize LLM clients
# Use unified LLM client instead of direct OpenAI client to support Azure OpenAI
from src.agents.azure_llm_client import llm_client, LLMProvider
openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)  # Keep for backward compatibility
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
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                architecture_design = json.loads(json_match.group())
            else:
                # Fallback structure
                architecture_design = {
                    "architecture": {
                        "overview": content,
                        "components": [],
                        "technology_stack": {}
                    },
                    "implementation_notes": "",
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
            
            # Extract language from task requirements or context
            language = "python"  # Default
            
            # Check if language is specified in context requirements
            if 'requirements' in context:
                req = context['requirements']
                if isinstance(req, dict):
                    language = req.get('language', 'python')
                    # Also check for programming_language key
                    language = req.get('programming_language', language)
            
            # Check task description for language specification
            task_desc_lower = task.description.lower()
            if '**python**' in task_desc_lower or 'must be in python' in task_desc_lower:
                language = 'python'
            elif '**javascript**' in task_desc_lower or 'must be in javascript' in task_desc_lower:
                language = 'javascript'
            elif '**java**' in task_desc_lower or 'must be in java' in task_desc_lower:
                language = 'java'
            elif '**go**' in task_desc_lower or 'must be in go' in task_desc_lower:
                language = 'go'
            elif '**rust**' in task_desc_lower or 'must be in rust' in task_desc_lower:
                language = 'rust'
            
            # Fallback to detection if no explicit language specified
            if language == 'python' and 'python' not in task_desc_lower:
                language = self._detect_language(code_content)
            
            # Structure the output
            output = {
                "code": code_content,
                "language": language,
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
        # Count Python-specific patterns
        python_score = 0
        python_patterns = ['def ', 'import ', 'from ', 'class ', '__init__', 'self.', 'print(', 
                          'if __name__', ':', 'elif ', 'except ', 'async def', 'await ']
        for pattern in python_patterns:
            if pattern in code:
                python_score += 1
        
        # Count JavaScript-specific patterns  
        js_score = 0
        js_patterns = ['const ', 'let ', 'var ', '=>', 'console.', 'function(', 'require(',
                      'module.exports', 'export ', 'import {', '})', ');']
        for pattern in js_patterns:
            if pattern in code:
                js_score += 1
        
        # If Python score is higher or equal, prefer Python
        if python_score >= js_score and python_score > 0:
            return "python"
        elif js_score > python_score:
            return "javascript"
        
        # Other language checks
        if 'package main' in code or ('func ' in code and 'package ' in code):
            return "go"
        elif ('fn main' in code) or ('fn ' in code and 'let mut' in code):
            return "rust"
        elif 'public class' in code or 'public static void main' in code:
            return "java"
        
        # Default to python for this use case
        return "python"
    
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
        if "pytest" in code or "unittest" in code:
            features.append("Unit tests")
        if "@lru_cache" in code or "cache" in code:
            features.append("Caching")
        if "jwt" in code.lower() or "token" in code:
            features.append("Authentication")
        
        return features
    
    def _extract_dependencies(self, code: str) -> List[str]:
        """Extract dependencies from code"""
        dependencies = []
        
        # Python imports
        import_pattern = r'(?:from\s+(\S+)\s+)?import\s+(\S+)'
        imports = re.findall(import_pattern, code)
        
        for from_part, import_part in imports:
            if from_part:
                dependencies.append(from_part.split('.')[0])
            else:
                dependencies.append(import_part.split('.')[0])
        
        # Common package patterns
        if "fastapi" in code.lower():
            dependencies.append("fastapi")
        if "sqlalchemy" in code.lower():
            dependencies.append("sqlalchemy")
        if "pydantic" in code.lower():
            dependencies.append("pydantic")
        
        return list(set(dependencies))


class ProductionReviewerAgent(SpecializedAgent):
    """Specialized in code review and quality assurance"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id, AgentRole.REVIEWER, AgentTier.T2)
    
    async def execute(self, task: Task, context: Dict[str, Any]) -> TaskResult:
        """Review code for production readiness"""
        logger.info(f"Production Reviewer analyzing code", task_id=task.id)
        
        start_time = datetime.utcnow()
        
        try:
            # Get code to review from context
            code_to_review = None
            for key, value in context.items():
                if "implementer" in key.lower() and isinstance(value, dict):
                    code_to_review = value.get("code", value.get("content", ""))
                    break
            
            if not code_to_review:
                # If no code from implementer, check task description
                code_to_review = context.get("code", task.description)
            
            system_prompt = f"""{self.specialization_prompts[self.role]}

Perform a comprehensive code review checking for:
1. Security vulnerabilities (OWASP Top 10, injection, XSS, etc)
2. Performance issues (N+1 queries, memory leaks, inefficient algorithms)
3. Code quality (SOLID principles, clean code, maintainability)
4. Error handling completeness
5. Test coverage and quality
6. Documentation completeness
7. Production readiness

Provide specific, actionable feedback with line numbers where possible.
Rate the code on a scale of 1-10 for production readiness."""
            
            user_prompt = f"""Review this code for production deployment:

```
{code_to_review}
```

Original Requirements: {task.description}

Context: {json.dumps(context.get('requirements', {}), indent=2)}"""
            
            # Use Azure OpenAI GPT-4 for thorough review
            response = await llm_client.chat_completion(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=4000
            )
            
            review_content = response['content']
            
            # Parse review into structured format
            review_output = self._parse_review(review_content)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Calculate confidence based on issues found
            severity_weights = {
                "critical": 0.3,
                "high": 0.2,
                "medium": 0.1,
                "low": 0.05
            }
            
            confidence_penalty = 0
            for issue in review_output.get("issues", []):
                severity = issue.get("severity", "low")
                confidence_penalty += severity_weights.get(severity, 0.05)
            
            confidence = max(0.3, min(0.95, 1.0 - confidence_penalty))
            
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                output_type="review",
                output=review_output,
                execution_time=execution_time,
                agent_tier_used=self.tier,
                confidence_score=confidence,
                metadata={
                    "agent_id": self.agent_id,
                    "role": self.role,
                    "model_used": "gpt-4-turbo",
                    "issues_found": len(review_output.get("issues", []))
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
    
    def _parse_review(self, review_text: str) -> Dict[str, Any]:
        """Parse review text into structured format"""
        output = {
            "overall_rating": 0,
            "production_ready": False,
            "issues": [],
            "recommendations": [],
            "strengths": [],
            "summary": ""
        }
        
        # Extract rating
        rating_match = re.search(r'(?:rating|score).*?(\d+)\s*(?:/|out of)?\s*10', review_text, re.IGNORECASE)
        if rating_match:
            output["overall_rating"] = int(rating_match.group(1))
            output["production_ready"] = output["overall_rating"] >= 7
        
        # Extract sections
        lines = review_text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect sections
            if any(keyword in line.lower() for keyword in ['issue', 'problem', 'vulnerability', 'bug']):
                current_section = 'issues'
            elif any(keyword in line.lower() for keyword in ['recommend', 'suggest', 'improve']):
                current_section = 'recommendations'
            elif any(keyword in line.lower() for keyword in ['strength', 'good', 'well-done', 'excellent']):
                current_section = 'strengths'
            elif any(keyword in line.lower() for keyword in ['summary', 'overall', 'conclusion']):
                current_section = 'summary'
            
            # Add content to appropriate section
            if current_section == 'issues' and line.startswith('-'):
                # Parse issue
                severity = "medium"
                if any(word in line.lower() for word in ['critical', 'severe', 'dangerous']):
                    severity = "critical"
                elif any(word in line.lower() for word in ['high', 'important', 'major']):
                    severity = "high"
                elif any(word in line.lower() for word in ['low', 'minor', 'cosmetic']):
                    severity = "low"
                
                output["issues"].append({
                    "description": line.lstrip('- '),
                    "severity": severity
                })
            elif current_section == 'recommendations' and line.startswith('-'):
                output["recommendations"].append(line.lstrip('- '))
            elif current_section == 'strengths' and line.startswith('-'):
                output["strengths"].append(line.lstrip('- '))
            elif current_section == 'summary':
                output["summary"] += line + " "
        
        # Ensure we have a summary
        if not output["summary"]:
            output["summary"] = f"Code review completed. Found {len(output['issues'])} issues. " \
                               f"Production readiness: {output['overall_rating']}/10"
        
        return output


class ProductionSecurityAgent(SpecializedAgent):
    """Specialized in security analysis and hardening"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id, AgentRole.SECURITY_EXPERT, AgentTier.T2)
    
    async def execute(self, task: Task, context: Dict[str, Any]) -> TaskResult:
        """Perform security analysis and provide hardening recommendations"""
        logger.info(f"Security Expert analyzing code", task_id=task.id)
        
        start_time = datetime.utcnow()
        
        try:
            # Get code to analyze
            code_to_analyze = ""
            for key, value in context.items():
                if isinstance(value, dict) and "code" in value:
                    code_to_analyze = value["code"]
                    break
            
            system_prompt = f"""{self.specialization_prompts[self.role]}

Perform a comprehensive security analysis covering:
1. Authentication and authorization vulnerabilities
2. Input validation and sanitization
3. SQL injection, XSS, CSRF protection
4. Cryptographic weaknesses
5. Sensitive data exposure
6. Security misconfiguration
7. Using components with known vulnerabilities
8. Insufficient logging and monitoring
9. API security (rate limiting, CORS, etc)
10. Infrastructure security considerations

Provide specific fixes for each vulnerability found."""
            
            user_prompt = f"""Analyze security of this implementation:

```
{code_to_analyze}
```

Task: {task.description}
Requirements: {json.dumps(context.get('requirements', {}), indent=2)}

Provide a detailed security assessment with specific remediation steps."""
            
            response = await llm_client.chat_completion(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=4000
            )
            
            security_analysis = response['content']
            
            # Structure the security report
            output = {
                "security_assessment": security_analysis,
                "vulnerabilities": self._extract_vulnerabilities(security_analysis),
                "hardening_recommendations": self._extract_recommendations(security_analysis),
                "security_score": self._calculate_security_score(security_analysis),
                "compliance_notes": self._extract_compliance_notes(security_analysis)
            }
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                output_type="security_analysis",
                output=output,
                execution_time=execution_time,
                agent_tier_used=self.tier,
                confidence_score=0.9,
                metadata={
                    "agent_id": self.agent_id,
                    "role": self.role,
                    "vulnerabilities_found": len(output["vulnerabilities"])
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
    
    def _extract_vulnerabilities(self, analysis: str) -> List[Dict[str, Any]]:
        """Extract vulnerabilities from security analysis"""
        vulnerabilities = []
        
        # Common vulnerability patterns
        vuln_patterns = {
            "sql_injection": r"(?i)(sql\s*injection|parameterized\s*queries)",
            "xss": r"(?i)(cross-site\s*scripting|xss|html\s*encoding)",
            "csrf": r"(?i)(csrf|cross-site\s*request\s*forgery)",
            "auth": r"(?i)(authentication|authorization|access\s*control)",
            "crypto": r"(?i)(encryption|hashing|cryptograph)",
            "injection": r"(?i)(command\s*injection|code\s*injection)",
            "data_exposure": r"(?i)(sensitive\s*data|data\s*exposure|information\s*disclosure)"
        }
        
        for vuln_type, pattern in vuln_patterns.items():
            if re.search(pattern, analysis):
                vulnerabilities.append({
                    "type": vuln_type,
                    "severity": "high" if vuln_type in ["sql_injection", "injection"] else "medium",
                    "description": f"Potential {vuln_type.replace('_', ' ')} vulnerability detected"
                })
        
        return vulnerabilities
    
    def _extract_recommendations(self, analysis: str) -> List[str]:
        """Extract security recommendations"""
        recommendations = []
        
        # Look for recommendation patterns
        lines = analysis.split('\n')
        for i, line in enumerate(lines):
            if any(keyword in line.lower() for keyword in ['recommend', 'should', 'must', 'implement']):
                recommendations.append(line.strip())
        
        return recommendations[:10]  # Top 10 recommendations
    
    def _calculate_security_score(self, analysis: str) -> float:
        """Calculate overall security score"""
        # Simple scoring based on presence of security terms
        positive_terms = ['secure', 'protected', 'validated', 'sanitized', 'encrypted', 'authenticated']
        negative_terms = ['vulnerable', 'exposed', 'unprotected', 'weak', 'missing', 'lack']
        
        positive_count = sum(1 for term in positive_terms if term in analysis.lower())
        negative_count = sum(1 for term in negative_terms if term in analysis.lower())
        
        score = max(0.0, min(1.0, 0.7 + (positive_count * 0.05) - (negative_count * 0.1)))
        return round(score, 2)
    
    def _extract_compliance_notes(self, analysis: str) -> List[str]:
        """Extract compliance-related notes"""
        compliance_keywords = ['gdpr', 'pci', 'hipaa', 'sox', 'compliance', 'regulation', 'standard']
        notes = []
        
        lines = analysis.split('\n')
        for line in lines:
            if any(keyword in line.lower() for keyword in compliance_keywords):
                notes.append(line.strip())
        
        return notes


class ProductionTestEngineerAgent(SpecializedAgent):
    """Specialized in creating comprehensive test suites"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id, AgentRole.TEST_ENGINEER, AgentTier.T1)
    
    async def execute(self, task: Task, context: Dict[str, Any]) -> TaskResult:
        """Generate comprehensive test suite"""
        logger.info(f"Test Engineer creating tests", task_id=task.id)
        
        start_time = datetime.utcnow()
        
        try:
            # Get implementation code
            code_to_test = ""
            language = "python"
            
            for key, value in context.items():
                if isinstance(value, dict):
                    if "code" in value:
                        code_to_test = value["code"]
                        language = value.get("language", "python")
                        break
            
            system_prompt = f"""{self.specialization_prompts[self.role]}

Generate a COMPREHENSIVE test suite including:
1. Unit tests for all functions/methods
2. Integration tests for API endpoints
3. Edge case testing
4. Error condition testing
5. Performance/load tests
6. Security tests
7. Mock objects and fixtures
8. Test data generators
9. Property-based tests where applicable
10. End-to-end tests

Use appropriate testing frameworks (pytest for Python, Jest for JS, etc).
Aim for >90% code coverage."""
            
            user_prompt = f"""Create comprehensive tests for this code:

```{language}
{code_to_test}
```

Task: {task.description}
Requirements: {json.dumps(context.get('requirements', {}), indent=2)}

Generate production-quality tests with proper setup, teardown, and documentation."""
            
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
            
            # Structure test output
            output = {
                "tests": test_code,
                "test_framework": self._detect_test_framework(test_code, language),
                "test_types": self._categorize_tests(test_code),
                "coverage_estimate": self._estimate_coverage(test_code, code_to_test),
                "test_count": self._count_tests(test_code)
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
                    "test_count": output["test_count"]
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
    
    def _detect_test_framework(self, test_code: str, language: str) -> str:
        """Detect testing framework used"""
        if language == "python":
            if "pytest" in test_code:
                return "pytest"
            elif "unittest" in test_code:
                return "unittest"
        elif language == "javascript":
            if "jest" in test_code.lower() or "describe(" in test_code:
                return "jest"
            elif "mocha" in test_code.lower():
                return "mocha"
        
        return "unknown"
    
    def _categorize_tests(self, test_code: str) -> List[str]:
        """Categorize types of tests present"""
        categories = []
        
        patterns = {
            "unit": r"(?i)(unit\s*test|test_\w+|def\s+test_)",
            "integration": r"(?i)(integration|api\s*test|endpoint\s*test)",
            "performance": r"(?i)(performance|load\s*test|benchmark)",
            "security": r"(?i)(security|vulnerability|injection)",
            "edge_case": r"(?i)(edge\s*case|boundary|corner\s*case)",
            "error": r"(?i)(error|exception|failure)"
        }
        
        for category, pattern in patterns.items():
            if re.search(pattern, test_code):
                categories.append(category)
        
        return categories
    
    def _estimate_coverage(self, test_code: str, implementation_code: str) -> float:
        """Estimate test coverage"""
        # Simple heuristic: count functions/methods in implementation vs tests
        impl_functions = len(re.findall(r'def\s+\w+', implementation_code))
        test_functions = len(re.findall(r'test_\w+', test_code))
        
        if impl_functions == 0:
            return 0.0
        
        # Assume each test covers ~1.5 functions on average
        estimated_coverage = min(1.0, (test_functions * 1.5) / impl_functions)
        return round(estimated_coverage, 2)
    
    def _count_tests(self, test_code: str) -> int:
        """Count number of test cases"""
        # Count test functions/methods
        test_patterns = [
            r'def\s+test_\w+',  # Python
            r'it\s*\(',         # JavaScript Jest/Mocha
            r'test\s*\(',       # JavaScript Jest
            r'@Test',           # Java
        ]
        
        count = 0
        for pattern in test_patterns:
            count += len(re.findall(pattern, test_code))
        
        return count


# Export specialized agents
__all__ = [
    "ProductionArchitectAgent",
    "ProductionImplementerAgent", 
    "ProductionReviewerAgent",
    "ProductionSecurityAgent",
    "ProductionTestEngineerAgent"
]
