"""
Base agent classes for the Quantum Layer Platform
These are the core agent implementations used by both the factory and ensemble
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime
import asyncio
import json
from uuid import uuid4

import structlog
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from src.common.models import (
    Task,
    TaskResult,
    AgentTier,
    TaskStatus
)
from src.common.config import settings
from src.common.error_handling import (
    error_handler,
    RetryableError,
    NonRetryableError,
    ErrorSeverity,
    with_retry,
    with_circuit_breaker
)
from src.memory.client import VectorMemoryClient
from src.sandbox.client import SandboxServiceClient
from src.agents.azure_llm_client import llm_client, get_model_for_tier, LLMProvider
from src.agents.language_utils import (
    LanguageDetector,
    get_language_example,
    ensure_language_in_output,
    extract_code_from_output
)

logger = structlog.get_logger()

# Security prompt template
SECURITY_REQUIREMENTS = """
Security Requirements:
- NEVER hardcode secrets, passwords, API keys, or tokens in the code
- Use environment variables for ALL sensitive configuration (e.g., os.getenv('API_KEY'))
- Implement proper input validation and sanitization for all user inputs
- Use parameterized queries for ALL database operations to prevent SQL injection
- Hash passwords with bcrypt using a minimum of 12 rounds
- Implement rate limiting on all public endpoints
- Use secure session management with proper expiration
- Enable CORS with specific allowed origins only (never use '*' in production)
- Add comprehensive error handling without exposing internal system details
- Use HTTPS/TLS for all external communications
- Validate and sanitize file uploads if applicable
- Implement proper authentication and authorization checks
- Use constant-time comparison for sensitive data (e.g., secrets.compare_digest())
- Escape output properly to prevent XSS attacks
- Set secure headers (CSP, X-Frame-Options, etc.)
"""

# Initialize clients
# Keep legacy clients for backward compatibility
openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY) if settings.ANTHROPIC_API_KEY else None
memory_client = VectorMemoryClient(settings.VECTOR_MEMORY_URL)
sandbox_client = SandboxServiceClient(f"http://localhost:{settings.SANDBOX_PORT}")


class Agent:
    """Base agent class"""
    
    def __init__(self, agent_id: str, tier: AgentTier):
        self.agent_id = agent_id
        self.tier = tier
        self.created_at = datetime.utcnow()
        
    async def execute(self, task: Task, context: Dict[str, Any]) -> TaskResult:
        """Execute a task - to be implemented by subclasses"""
        raise NotImplementedError
    
    def _detect_language_from_task(self, description: str) -> str:
        """Detect programming language from task description - delegated to LanguageDetector"""
        return LanguageDetector.detect_language(description=description)
    
    async def _detect_language_from_code_llm(self, code: str) -> str:
        """Use pattern-based detection to intelligently detect programming language from code"""
        # For now, use pattern-based detection directly
        # In the future, this could call an LLM service for more accurate detection
        return self._detect_language_from_patterns(code)
    
    def _detect_language_from_patterns(self, code: str) -> str:
        """Comprehensive pattern-based language detection as fallback"""
        # Language-specific patterns with confidence scoring
        patterns = {
            "python": [
                (r'^\s*def\s+\w+\s*\(', 10),  # Function definition
                (r'^\s*class\s+\w+', 10),      # Class definition  
                (r'^\s*import\s+\w+', 8),      # Import statement
                (r'^\s*from\s+\w+\s+import', 8),
                (r'if\s+__name__\s*==\s*["\']__main__["\']', 10),
                (r'print\s*\(', 5),
                (r'^\s*@\w+', 7),  # Decorators
                (r':\s*$', 3),     # Colon at end of line
                (r'self\.', 7),    # Self reference
            ],
            "javascript": [
                (r'function\s+\w+\s*\(', 10),
                (r'const\s+\w+\s*=', 8),
                (r'let\s+\w+\s*=', 8),
                (r'var\s+\w+\s*=', 7),
                (r'=>', 8),  # Arrow functions
                (r'console\.log\s*\(', 7),
                (r'module\.exports', 8),
                (r'require\s*\(', 8),
                (r'async\s+function', 8),
                (r'\.then\s*\(', 7),
            ],
            "java": [
                (r'public\s+class\s+\w+', 10),
                (r'private\s+\w+\s+\w+', 8),
                (r'public\s+static\s+void\s+main', 10),
                (r'import\s+java\.', 9),
                (r'System\.out\.println', 8),
                (r'@Override', 7),
                (r'new\s+\w+\s*\(', 6),
            ],
            "go": [
                (r'package\s+\w+', 10),
                (r'func\s+\w+\s*\(', 10),
                (r'import\s+\(', 8),
                (r'fmt\.Print', 8),
                (r':=', 9),  # Short variable declaration
                (r'go\s+func', 8),
            ],
            "rust": [
                (r'fn\s+\w+\s*\(', 10),
                (r'let\s+mut\s+', 9),
                (r'impl\s+\w+', 8),
                (r'pub\s+fn', 8),
                (r'use\s+\w+::', 8),
                (r'println!\s*\(', 7),
                (r'match\s+\w+\s*\{', 8),
            ],
            "cpp": [
                (r'#include\s*<', 10),
                (r'using\s+namespace\s+std', 9),
                (r'int\s+main\s*\(', 10),
                (r'cout\s*<<', 8),
                (r'class\s+\w+\s*\{', 8),
                (r'::', 6),  # Scope resolution
            ],
        }
        
        scores = {}
        for lang, lang_patterns in patterns.items():
            score = 0
            for pattern, weight in lang_patterns:
                import re
                if re.search(pattern, code, re.MULTILINE):
                    score += weight
            scores[lang] = score
        
        # Get language with highest score
        if scores:
            best_lang = max(scores, key=scores.get)
            if scores[best_lang] > 10:  # Minimum confidence threshold
                return best_lang
        
        # As last resort, return most common language for enterprise
        return "python"  # Most common in data science/ML context
    
    async def _clean_llm_response(self, response: str, expected_language: str = None) -> str:
        """Clean LLM response to extract pure code"""
        # Remove JSON wrapping if present
        if response.strip().startswith('```json') and response.strip().endswith('```'):
            # Extract content between backticks
            response = response.strip()[7:-3].strip()
            try:
                # Parse JSON and extract code field
                data = json.loads(response)
                if isinstance(data, dict) and 'code' in data:
                    response = data['code']
            except:
                pass
        
        # Remove language-specific code blocks
        if expected_language and response.strip().startswith(f'```{expected_language}'):
            response = response.strip()[len(f'```{expected_language}'):-3].strip()
        elif response.strip().startswith('```'):
            # Find the end of the first line to skip language identifier
            lines = response.strip().split('\n')
            if len(lines) > 2 and lines[0].startswith('```') and lines[-1] == '```':
                response = '\n'.join(lines[1:-1])
        
        return response


class T0Agent(Agent):
    """Tier 0: Simple task execution using Llama or small models"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id, AgentTier.T0)
        
    @with_circuit_breaker("llm_service", failure_threshold=3, recovery_timeout=30)
    @with_retry(max_attempts=3, service="t0_agent", exceptions=(RetryableError, ConnectionError, TimeoutError))
    async def execute(self, task: Task, context: Dict[str, Any]) -> TaskResult:
        logger.info(f"T0 Agent executing task", task_id=task.id, agent_id=self.agent_id)
        
        start_time = datetime.utcnow()
        
        try:
            # For T0, we use simple prompts with minimal context
            prompt = self._build_prompt(task, context)
            
            # Get appropriate model for T0 tier
            model, provider = get_model_for_tier("T0")
            
            # Use unified LLM client with enhanced error handling
            try:
                response = await llm_client.chat_completion(
                    messages=[
                        {"role": "system", "content": "You are a code generation assistant. Be concise and direct."},
                        {"role": "user", "content": prompt}
                    ],
                    model=model,
                    provider=provider,
                    temperature=0.3,
                    max_tokens=2000,
                    timeout=600.0,  # Increased to 600s for enterprise-scale tasks
                    # Add cost tracking context
                    workflow_id=context.get("request_id"),
                    tenant_id=context.get("tenant_id"),
                    user_id=context.get("user_id"),
                    metadata={
                        "task_id": task.id,
                        "task_type": task.type,
                        "agent_tier": "T0"
                    }
                )
            except (ConnectionError, TimeoutError) as e:
                # These are retryable errors
                logger.warning(f"Retryable error in T0 agent", error=str(e), task_id=task.id)
                raise RetryableError(f"LLM service temporarily unavailable: {str(e)}", 
                                   severity=ErrorSeverity.MEDIUM,
                                   service="llm_client",
                                   details={"model": model, "provider": provider.value})
            except Exception as e:
                # Non-retryable errors
                if "rate_limit" in str(e).lower():
                    raise RetryableError(f"Rate limit hit: {str(e)}", 
                                       severity=ErrorSeverity.MEDIUM,
                                       service="llm_client")
                else:
                    raise NonRetryableError(f"LLM error: {str(e)}", 
                                          severity=ErrorSeverity.HIGH,
                                          service="llm_client",
                                          details={"model": model, "provider": provider.value})
            
            output = response["content"]
            
            # Use LanguageDetector for comprehensive language detection
            language = LanguageDetector.detect_language(
                description=task.description,
                metadata=getattr(task, 'metadata', None),
                context=context
            )
            
            # Clean the LLM response
            output = await self._clean_llm_response(output, language)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(f"T0 Agent completed task", 
                       task_id=task.id, 
                       execution_time=execution_time,
                       model=model,
                       provider=provider.value)
            
            # Use language_utils to extract code properly
            code, detected_lang = extract_code_from_output(output, language)
            if detected_lang != language:
                logger.info(f"Language mismatch: expected {language}, detected {detected_lang}")
                language = detected_lang
            
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                output_type="code",
                output={"code": code, "content": output, "language": language},
                execution_time=execution_time,
                agent_tier_used=self.tier,
                confidence_score=0.7,  # T0 agents have lower confidence
                metadata={
                    "agent_id": self.agent_id,
                    "model": model,
                    "provider": provider.value,
                    "language": language,
                    "language_source": "metadata" if language != self._detect_language_from_task(task.description) else "detection"
                }
            )
            
        except (RetryableError, NonRetryableError):
            # Re-raise our custom errors
            raise
        except Exception as e:
            # Catch any unexpected errors
            error_details = error_handler.handle_error(
                e,
                service="t0_agent",
                context={"task_id": task.id, "agent_id": self.agent_id},
                raise_after=False
            )
            
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                output_type="error",
                output={"error": str(e), "details": error_details},
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
                agent_tier_used=self.tier,
                confidence_score=0.0,
                metadata={"agent_id": self.agent_id, "error": error_details}
            )
    
    def _build_prompt(self, task: Task, context: Dict[str, Any]) -> str:
        """Build a simple prompt for T0 tasks"""
        # Use LanguageDetector for comprehensive detection
        detected_language = LanguageDetector.detect_language(
            description=task.description,
            metadata=getattr(task, 'metadata', None),
            context=context
        )
        
        prompt = f"Task: {task.description}\n\n"
        
        if context:
            prompt += "Context:\n"
            for key, value in context.items():
                prompt += f"- {key}: {value}\n"
            prompt += "\n"
        
        # Add security requirements for relevant tasks
        include_security = any(keyword in task.description.lower() for keyword in [
            "api", "authentication", "auth", "login", "password", "user", "secure",
            "database", "sql", "web", "endpoint", "service", "server", "backend"
        ])
        
        prompt += f"""LANGUAGE DETECTION: Based on the task description, the required language is: {detected_language}

CRITICAL REQUIREMENT: You MUST generate code in {detected_language} language only.

IMPORTANT: Generate ACTUAL EXECUTABLE CODE, not directory structures or project layouts.

Requirements:
- Generate complete, working code in {detected_language} language
- Use {detected_language}-specific syntax, imports, and conventions
- Include proper imports, functions, and classes for {detected_language}
- Do NOT provide directory listings, file structures, or project layouts
- Do NOT use placeholder comments like "# implement this" or "// TODO"
- Generate real, functional implementation in {detected_language}

Example of what NOT to do:
- Directory listings or file structures
- Placeholder comments like "# implement this" or "// TODO: implement"
- Incomplete or pseudo-code
- Markdown formatting with backticks
- Code in wrong language (must be {detected_language})

Example of what TO do:
- Complete, functional {detected_language} code
- Proper {detected_language} imports and dependencies
- Real implementation using {detected_language} syntax

IMPORTANT: 
1. Generate code in {detected_language} language ONLY
2. Output ONLY the raw {detected_language} code without any markdown formatting, backticks, or code block markers
3. Do not wrap the code in ```{detected_language} or ``` blocks
4. Generate complete, executable {detected_language} code

"""
        
        # Add security requirements if applicable
        if include_security:
            prompt += f"\n{SECURITY_REQUIREMENTS}\n"
        
        prompt += f"Generate the complete, executable {detected_language} code now:"""
        
        return prompt


class T1Agent(Agent):
    """Tier 1: Context-aware generation using GPT-4/Claude"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id, AgentTier.T1)
        
    async def execute(self, task: Task, context: Dict[str, Any]) -> TaskResult:
        logger.info(f"T1 Agent executing task", task_id=task.id, agent_id=self.agent_id)
        
        start_time = datetime.utcnow()
        
        try:
            # Search for similar code patterns
            similar_patterns = await memory_client.search_code_patterns(
                task.description,
                limit=3
            )
            
            # Build enhanced prompt with context
            prompt = self._build_enhanced_prompt(task, context, similar_patterns)
            
            # Get appropriate model for T1 tier
            model, provider = get_model_for_tier("T1")
            
            # Use unified LLM client
            response = await llm_client.chat_completion(
                messages=[
                    {
                        "role": "system", 
                        "content": """You are an expert software engineer. Generate high-quality, 
                        production-ready code with proper error handling, documentation, and best practices."""
                    },
                    {"role": "user", "content": prompt}
                ],
                model=model,
                provider=provider,
                temperature=0.3,
                max_tokens=4000,
                timeout=120.0,  # Increased from 30s to 120s for complex TDD tasks
                # Add cost tracking context
                workflow_id=context.get("request_id"),
                tenant_id=context.get("tenant_id"),
                user_id=context.get("user_id"),
                metadata={
                    "task_id": task.id,
                    "task_type": task.type,
                    "agent_tier": "T1"
                }
            )
            
            output = response["content"]
            
            # Parse structured output (no need to clean first since _parse_output handles it)
            parsed_output = self._parse_output(output)
            
            # If we generated code, optionally test it in sandbox
            if parsed_output["type"] == "code" and "code" in parsed_output["content"]:
                try:
                    # Use LLM to intelligently detect language from code
                    code = parsed_output["content"]["code"]
                    # First try task-based detection, then use LLM for code analysis
                    task_language = self._detect_language_from_task(task.description)
                    code_language = await self._detect_language_from_code_llm(code)
                    # Prefer explicit task language, otherwise use LLM detection
                    language = task_language if task_language else code_language
                    
                    # Execute in sandbox for validation
                    sandbox_result = await sandbox_client.execute(
                        code=code,
                        language=language,
                        inputs={}
                    )
                    
                    parsed_output["content"]["execution_result"] = {
                        "status": sandbox_result["status"],
                        "output": sandbox_result.get("output", ""),
                        "error": sandbox_result.get("error", "")
                    }
                except Exception as e:
                    logger.warning(f"Sandbox execution failed: {e}")
                    # Continue without sandbox results
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Get language from task metadata/context first, fallback to detection
            language = None
            
            # Check task metadata for language constraint
            if hasattr(task, 'metadata') and task.metadata and 'language_constraint' in task.metadata:
                language = task.metadata.get('language_constraint')
                logger.info(f"T1: Using language from task metadata: {language}")
            
            # Check task meta for preferred_language
            elif hasattr(task, 'meta') and task.meta and 'preferred_language' in task.meta:
                language = task.meta.get('preferred_language')
                logger.info(f"T1: Using language from task meta: {language}")
            
            # Check context for required_language
            elif 'required_language' in context:
                language = context.get('required_language')
                logger.info(f"T1: Using language from context: {language}")
            
            # Check context for preferred_language
            elif 'preferred_language' in context:
                language = context.get('preferred_language')
                logger.info(f"T1: Using preferred language from context: {language}")
            
            # Fallback to detection if no explicit language
            if not language:
                language = self._detect_language_from_task(task.description)
                logger.info(f"T1: No explicit language found, detected: {language}")
            
            # Add language to output if not already present
            if isinstance(parsed_output["content"], dict) and "language" not in parsed_output["content"]:
                parsed_output["content"]["language"] = language
            
            # Ensure output has 'code' at the top level for validation
            output_data = parsed_output["content"]
            if isinstance(output_data, dict) and "code" not in output_data:
                # If code is nested or missing, try to extract it
                output_data["code"] = output_data.get("content", str(output_data))
            elif not isinstance(output_data, dict):
                # If output is not a dict, wrap it
                output_data = {"code": str(output_data), "language": language}
            
            # Ensure language is in output
            if isinstance(output_data, dict) and "language" not in output_data:
                output_data["language"] = language
            
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                output_type=parsed_output["type"],
                output=output_data,
                execution_time=execution_time,
                agent_tier_used=self.tier,
                confidence_score=0.85,
                metadata={
                    "agent_id": self.agent_id,
                    "patterns_used": len(similar_patterns),
                    "language": language,
                    "language_source": "metadata" if language != self._detect_language_from_task(task.description) else "detection"
                }
            )
            
        except Exception as e:
            logger.error(f"T1 Agent execution failed", error=str(e))
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                output_type="error",
                output={"error": str(e)},
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
                agent_tier_used=self.tier,
                confidence_score=0.0,
                metadata={"agent_id": self.agent_id}
            )
    
    def _build_enhanced_prompt(self, task: Task, context: Dict[str, Any], patterns: List[Dict]) -> str:
        """Build an enhanced prompt with context and patterns"""
        # Get language from task metadata/context first, fallback to detection
        language = None
        
        # Check task metadata for language constraint
        if hasattr(task, 'metadata') and task.metadata and 'language_constraint' in task.metadata:
            language = task.metadata.get('language_constraint')
        
        # Check context for required_language
        elif 'required_language' in context:
            language = context.get('required_language')
        
        # Check context for preferred_language
        elif 'preferred_language' in context:
            language = context.get('preferred_language')
        
        # Fallback to detection if no explicit language
        if not language:
            language = self._detect_language_from_task(task.description)
        
        detected_language = language
        
        prompt = f"Task: {task.description}\n\n"
        
        if context:
            prompt += "Context from previous tasks:\n"
            for key, value in context.items():
                prompt += f"- {key}: {json.dumps(value, indent=2)}\n"
            prompt += "\n"
        
        if patterns:
            prompt += "Similar successful patterns:\n"
            for pattern in patterns:
                prompt += f"- Pattern: {pattern['description']}\n"
                prompt += f"  Code: {pattern['code'][:200]}...\n\n"
        
        # Get language-specific example
        example_code, example_tests, example_deps = self._get_language_example(detected_language)
        
        # Add security requirements for relevant tasks
        include_security = any(keyword in task.description.lower() for keyword in [
            "api", "authentication", "auth", "login", "password", "user", "secure",
            "database", "sql", "web", "endpoint", "service", "server", "backend",
            "microservice", "rest", "graphql", "jwt", "oauth"
        ])
        
        prompt += f"""
LANGUAGE DETECTION: Based on the task description, the required language is: {detected_language}

CRITICAL REQUIREMENT: You MUST generate code in {detected_language} language only.

CRITICAL: Generate ACTUAL EXECUTABLE CODE, NOT directory structures or file layouts.

Requirements:
- Generate complete, working code in {detected_language} language
- Use {detected_language}-specific syntax, imports, and conventions
- Include all necessary imports and proper error handling for {detected_language}
- Do NOT provide directory listings, project structures, or placeholders
- Do NOT use comments like "# implement this" or "// TODO: implement"
- Generate functional, production-ready {detected_language} code

Generate a complete solution including:
1. Main implementation code (ACTUAL {detected_language} CODE, not structure)
2. Error handling and validation in {detected_language}
3. Brief documentation
4. All necessary {detected_language} imports and dependencies
"""
        
        # Add security requirements if applicable
        if include_security:
            prompt += f"\n{SECURITY_REQUIREMENTS}\n"
        
        prompt += f"""
Format your response as JSON:
{{
    "code": "complete executable {detected_language} code with imports, classes, functions",
    "tests": "actual {detected_language} test code with assertions and test cases",
    "documentation": "brief explanation of the implementation",
    "dependencies": ["list", "of", "required", "{detected_language}", "packages"]
}}

EXAMPLE OF GOOD RESPONSE FOR {detected_language.upper() if detected_language else 'PYTHON'}:
{{
    "code": "{example_code}",
    "tests": "{example_tests}",
    "documentation": "{detected_language} application with proper implementation",
    "dependencies": {example_deps}
}}
"""
        
        return prompt
    
    def _get_language_example(self, language: str) -> Tuple[str, str, str]:
        """Get language-specific example code for prompting"""
        examples = {
            "javascript": (
                "const express = require('express');\\nconst app = express();\\n\\napp.use(express.json());\\n\\napp.post('/users', (req, res) => {\\n    const { name, email } = req.body;\\n    res.json({ message: 'User created', user: { name, email } });\\n});\\n\\napp.listen(3000, () => console.log('Server running on port 3000'));",
                "const request = require('supertest');\\nconst app = require('./app');\\n\\ndescribe('POST /users', () => {\\n    it('should create a user', async () => {\\n        const response = await request(app)\\n            .post('/users')\\n            .send({ name: 'John', email: 'john@example.com' });\\n        expect(response.status).toBe(200);\\n    });\\n});",
                '["express", "supertest"]'
            ),
            "java": (
                "import org.springframework.boot.SpringApplication;\\nimport org.springframework.boot.autoconfigure.SpringBootApplication;\\nimport org.springframework.web.bind.annotation.*;\\n\\n@SpringBootApplication\\n@RestController\\npublic class Application {\\n    @PostMapping(\"/users\")\\n    public String createUser(@RequestBody User user) {\\n        return \"User created: \" + user.getName();\\n    }\\n\\n    public static void main(String[] args) {\\n        SpringApplication.run(Application.class, args);\\n    }\\n}",
                "import org.junit.jupiter.api.Test;\\nimport org.springframework.boot.test.context.SpringBootTest;\\nimport static org.junit.jupiter.api.Assertions.*;\\n\\n@SpringBootTest\\nclass ApplicationTest {\\n    @Test\\n    void testCreateUser() {\\n        User user = new User(\"John\", \"john@example.com\");\\n        assertNotNull(user);\\n    }\\n}",
                '["spring-boot-starter-web", "spring-boot-starter-test"]'
            ),
            "go": (
                "package main\\n\\nimport (\\n    \"encoding/json\"\\n    \"net/http\"\\n    \"github.com/gin-gonic/gin\"\\n)\\n\\ntype User struct {\\n    Name  string `json:\"name\"`\\n    Email string `json:\"email\"`\\n}\\n\\nfunc createUser(c *gin.Context) {\\n    var user User\\n    c.ShouldBindJSON(&user)\\n    c.JSON(http.StatusOK, gin.H{\"message\": \"User created\", \"user\": user})\\n}\\n\\nfunc main() {\\n    r := gin.Default()\\n    r.POST(\"/users\", createUser)\\n    r.Run(\":8080\")\\n}",
                "package main\\n\\nimport (\\n    \"testing\"\\n    \"net/http/httptest\"\\n    \"github.com/gin-gonic/gin\"\\n)\\n\\nfunc TestCreateUser(t *testing.T) {\\n    gin.SetMode(gin.TestMode)\\n    r := gin.Default()\\n    r.POST(\"/users\", createUser)\\n    // Add test implementation\\n}",
                '["gin"]'
            ),
            "python": (
                "from fastapi import FastAPI, HTTPException\\nfrom pydantic import BaseModel\\n\\napp = FastAPI()\\n\\nclass User(BaseModel):\\n    name: str\\n    email: str\\n\\n@app.post('/users')\\ndef create_user(user: User):\\n    return {'message': 'User created', 'user': user}",
                "import pytest\\nfrom fastapi.testclient import TestClient\\nfrom main import app\\n\\nclient = TestClient(app)\\n\\ndef test_create_user():\\n    response = client.post('/users', json={'name': 'John', 'email': 'john@example.com'})\\n    assert response.status_code == 200",
                '["fastapi", "pydantic"]'
            )
        }
        
        return examples.get(language, examples["python"])
    
    def _parse_output(self, output: str) -> Dict[str, Any]:
        """Parse structured output from LLM"""
        try:
            # Clean the output first - remove markdown code blocks if present
            cleaned_output = output.strip()
            if cleaned_output.startswith('```json') and cleaned_output.endswith('```'):
                cleaned_output = cleaned_output[7:-3].strip()
            elif cleaned_output.startswith('```') and cleaned_output.endswith('```'):
                # Find the first newline after ``` to skip language identifier
                first_newline = cleaned_output.find('\n')
                if first_newline > 0:
                    cleaned_output = cleaned_output[first_newline+1:-3].strip()
            
            # Try to parse as JSON
            parsed = json.loads(cleaned_output)
            
            # Ensure all expected fields are present
            if not isinstance(parsed, dict):
                raise ValueError("Response is not a JSON object")
            
            # If 'code' field contains stringified JSON, parse it
            if 'code' in parsed and isinstance(parsed['code'], str):
                if parsed['code'].strip().startswith('{') and '"code"' in parsed['code']:
                    try:
                        # Attempt to parse nested JSON
                        nested_data = json.loads(parsed['code'])
                        if isinstance(nested_data, dict) and 'code' in nested_data:
                            parsed['code'] = nested_data['code']
                            # Merge other fields if present
                            for key in ['tests', 'documentation', 'dependencies']:
                                if key in nested_data and key not in parsed:
                                    parsed[key] = nested_data[key]
                    except:
                        pass  # Keep original if parsing fails
            
            return {
                "type": "code",
                "content": parsed
            }
        except:
            # Extract code from markdown or plain text
            code, tests, docs = self._extract_code_from_response(output)
            
            return {
                "type": "code",
                "content": {
                    "code": code,
                    "tests": tests,
                    "documentation": docs,
                    "raw_response": output  # Keep original for debugging
                }
            }
    
    def _extract_code_from_response(self, response: str) -> Tuple[str, str, str]:
        """Extract code, tests, and documentation from LLM response"""
        import re
        
        # Look for code blocks
        code_pattern = r'```(?:python)?\n(.*?)```'
        code_blocks = re.findall(code_pattern, response, re.DOTALL)
        
        code = ""
        tests = ""
        docs = ""
        
        if code_blocks:
            # First block is usually the main code
            code = code_blocks[0].strip()
            
            # Look for test code
            for block in code_blocks[1:]:
                if 'test' in block.lower() or 'assert' in block:
                    tests = block.strip()
                    break
            
            # Extract documentation
            docs_before_code = response.split('```')[0].strip()
            if docs_before_code and len(docs_before_code) < 1000:
                docs = docs_before_code
        else:
            # No code blocks, assume pure code
            code = response.strip()
        
        return code, tests, docs


class T2Agent(Agent):
    """Tier 2: Reasoning + validation loops"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id, AgentTier.T2)
        
    async def execute(self, task: Task, context: Dict[str, Any]) -> TaskResult:
        logger.info(f"T2 Agent executing task", task_id=task.id, agent_id=self.agent_id)
        
        start_time = datetime.utcnow()
        max_iterations = 3
        
        # Use robust language detection
        language = LanguageDetector.detect_language(
            description=task.description,
            metadata=task.metadata if hasattr(task, 'metadata') else None,
            context=context
        )
        logger.info(f"T2: Detected language: {language}")
        
        try:
            for iteration in range(max_iterations):
                # Generate solution with language context
                solution = await self._generate_solution(task, context, iteration, language)
                
                # Validate solution
                validation_result = await self._validate_solution(solution, task)
                
                if validation_result["valid"]:
                    execution_time = (datetime.utcnow() - start_time).total_seconds()
                    
                    return TaskResult(
                        task_id=task.id,
                        status=TaskStatus.COMPLETED,
                        output_type="code",
                        output=solution,
                        execution_time=execution_time,
                        agent_tier_used=self.tier,
                        confidence_score=0.95,
                        metadata={
                            "agent_id": self.agent_id,
                            "iterations": iteration + 1,
                            "validation_passed": True,
                            "language": language,
                            "language_source": "metadata" if language != self._detect_language_from_task(task.description) else "detection"
                        }
                    )
                
                # Use validation feedback for next iteration
                context["validation_feedback"] = validation_result["feedback"]
            
            # Max iterations reached without valid solution
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                output_type="code",
                output=solution,
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
                agent_tier_used=self.tier,
                confidence_score=0.6,  # Lower confidence due to validation issues
                metadata={
                    "agent_id": self.agent_id,
                    "iterations": max_iterations,
                    "validation_passed": False,
                    "language": language,
                    "language_source": "metadata" if language != self._detect_language_from_task(task.description) else "detection"
                }
            )
            
        except Exception as e:
            logger.error(f"T2 Agent execution failed", error=str(e))
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                output_type="error",
                output={"error": str(e)},
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
                agent_tier_used=self.tier,
                confidence_score=0.0,
                metadata={"agent_id": self.agent_id}
            )
    
    async def _generate_solution(self, task: Task, context: Dict[str, Any], iteration: int, language: str) -> Dict[str, Any]:
        """Generate a solution with reasoning"""
        # Ensure language is safe
        safe_language = LanguageDetector.get_language_safe(language)
        
        system_prompt = f"""You are an expert software architect. Think step-by-step:
1. Understand the requirements
2. Design the solution architecture
3. Implement with best practices in {safe_language.upper()} language
4. Consider edge cases and error handling
5. Validate your approach

CRITICAL: Generate code in {safe_language.upper()} language only. Do not use any other language.
If this is a retry, use the validation feedback to improve."""
        
        user_prompt = f"Task: {task.description}\n\n"
        user_prompt += f"REQUIRED LANGUAGE: {safe_language}\n\n"
        
        if context:
            user_prompt += f"Context: {json.dumps(context, indent=2)}\n\n"
        
        if iteration > 0:
            user_prompt += f"This is iteration {iteration + 1}. Previous attempts had issues.\n\n"
        
        # Get appropriate model for T2 tier (reasoning)
        model, provider = get_model_for_tier("T2")
        
        # Use unified LLM client
        response = await llm_client.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model=model,
            provider=provider,
            temperature=0.4,
            max_tokens=4000
        )
        
        # Parse and structure the response with correct language
        return self._parse_solution(response["content"], safe_language)
    
    async def _validate_solution(self, solution: Dict[str, Any], task: Task) -> Dict[str, Any]:
        """Validate the generated solution"""
        # This would normally call the validation service
        # For now, we do a simple LLM-based validation
        
        validation_prompt = f"""
Review this solution for the task: {task.description}

Solution:
{json.dumps(solution, indent=2)}

Check for:
1. Correctness - Does it solve the problem?
2. Completeness - Are all requirements met?
3. Quality - Is it production-ready?
4. Security - Any vulnerabilities?

Respond with JSON:
{{
    "valid": true/false,
    "feedback": "specific issues to fix if any"
}}
"""
        
        # Use GPT-4 for validation (can be from Azure or OpenAI)
        response = await llm_client.chat_completion(
            messages=[
                {"role": "system", "content": "You are a code reviewer. Be strict but fair."},
                {"role": "user", "content": validation_prompt}
            ],
            model="gpt-4-turbo-preview",  # Will auto-select Azure if available
            temperature=0.1,
            response_format={"type": "json_object"}  # Note: response_format support varies by provider
        )
        
        return json.loads(response["content"])
    
    def _parse_solution(self, content: str, language: str) -> Dict[str, Any]:
        """Parse solution from LLM response"""
        # Extract code blocks and structure with language safety
        code, detected_language = extract_code_from_output(content, language)
        safe_language = LanguageDetector.get_language_safe(detected_language)
        
        return ensure_language_in_output({
            "code": code,
            "language": safe_language,
            "dependencies": []
        }, safe_language)


class T3Agent(Agent):
    """Tier 3: Meta-agents that can create other agents"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id, AgentTier.T3)
        
    async def execute(self, task: Task, context: Dict[str, Any]) -> TaskResult:
        logger.info(f"T3 Meta-Agent executing task", task_id=task.id, agent_id=self.agent_id)
        
        # T3 agents can spawn other agents dynamically
        # This is a simplified implementation
        
        start_time = datetime.utcnow()
        
        try:
            # Detect language and ensure it's in context for sub-agents
            language = LanguageDetector.detect_language(
                description=task.description,
                metadata=task.metadata if hasattr(task, 'metadata') else None,
                context=context
            )
            
            # Ensure language is propagated to sub-agents
            context = {**context, "required_language": language}
            
            # Analyze task to determine agent composition
            agent_plan = await self._plan_agent_composition(task, context)
            
            # Create and orchestrate sub-agents
            results = await self._execute_with_sub_agents(agent_plan, task, context)
            
            # Synthesize results
            final_output = await self._synthesize_results(results, task)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                output_type="meta_execution",
                output=final_output,
                execution_time=execution_time,
                agent_tier_used=self.tier,
                confidence_score=0.9,
                metadata={
                    "agent_id": self.agent_id,
                    "sub_agents_used": len(agent_plan["agents"]),
                    "agent_plan": agent_plan
                }
            )
            
        except Exception as e:
            logger.error(f"T3 Meta-Agent execution failed", error=str(e))
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                output_type="error",
                output={"error": str(e)},
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
                agent_tier_used=self.tier,
                confidence_score=0.0,
                metadata={"agent_id": self.agent_id}
            )
    
    async def _plan_agent_composition(self, task: Task, context: Dict[str, Any]) -> Dict[str, Any]:
        """Plan which agents to create for this task"""
        # This would use an LLM to analyze the task and determine optimal agent composition
        # Simplified for now
        return {
            "agents": [
                {"type": "T1", "subtask": "Generate initial solution"},
                {"type": "T2", "subtask": "Validate and refine"},
                {"type": "T0", "subtask": "Generate tests"}
            ]
        }
    
    async def _execute_with_sub_agents(self, plan: Dict[str, Any], task: Task, context: Dict[str, Any]) -> List[TaskResult]:
        """Execute task using sub-agents"""
        results = []
        
        for agent_spec in plan["agents"]:
            # Create appropriate agent
            if agent_spec["type"] == "T0":
                agent = T0Agent(str(uuid4()))
            elif agent_spec["type"] == "T1":
                agent = T1Agent(str(uuid4()))
            elif agent_spec["type"] == "T2":
                agent = T2Agent(str(uuid4()))
            else:
                continue
            
            # Create subtask
            subtask = Task(
                id=str(uuid4()),
                type=task.type,
                description=agent_spec["subtask"],
                complexity="medium"
            )
            
            # Execute with accumulated context
            result = await agent.execute(subtask, context)
            results.append(result)
            
            # Update context with result
            if result.status == TaskStatus.COMPLETED:
                context[f"result_{agent_spec['type']}"] = result.output
        
        return results
    
    async def _synthesize_results(self, results: List[TaskResult], task: Task) -> Dict[str, Any]:
        """Synthesize results from multiple agents"""
        successful_results = [r for r in results if r.status == TaskStatus.COMPLETED]
        
        # Extract language from results
        language = None
        for result in successful_results:
            if isinstance(result.output, dict) and 'language' in result.output:
                language = result.output['language']
                break
        
        # Use robust language detection if not found
        if not language:
            language = LanguageDetector.detect_language(
                description=task.description,
                metadata=task.metadata if hasattr(task, 'metadata') else None
            )
        
        # Extract code from results with proper structure handling
        code_result = None
        validation_result = None
        tests_result = None
        
        for idx, result in enumerate(successful_results):
            if idx == 0:  # First result is usually code
                if isinstance(result.output, dict):
                    code_result = result.output.get('code', result.output.get('content', ''))
                else:
                    code_result = str(result.output)
            elif idx == 1:  # Second is validation
                validation_result = result.output if isinstance(result.output, dict) else {"validation": str(result.output)}
            elif idx == 2:  # Third is tests
                if isinstance(result.output, dict):
                    tests_result = result.output.get('code', result.output.get('content', ''))
                else:
                    tests_result = str(result.output)
        
        return {
            "synthesized_output": {
                "code": code_result or "",
                "validation": validation_result or {},
                "tests": tests_result or "",
                "language": language
            },
            "sub_agent_results": [r.dict() for r in results],
            "language": language
        }


# Export all base agents
__all__ = ["Agent", "T0Agent", "T1Agent", "T2Agent", "T3Agent"]
