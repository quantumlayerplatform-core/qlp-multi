"""
Intelligent CI/CD Generator using LLM
Universal CI/CD pipeline generation for any language/framework
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import structlog
from openai import AsyncOpenAI, AsyncAzureOpenAI

from src.common.config import settings

logger = structlog.get_logger()


class CICDPlatform(Enum):
    GITHUB_ACTIONS = "github_actions"
    GITLAB_CI = "gitlab_ci"
    JENKINS = "jenkins"
    AZURE_DEVOPS = "azure_devops"
    CIRCLECI = "circleci"


@dataclass
class CICDAnalysis:
    """Analysis result for CI/CD pipeline generation"""
    detected_language: str
    detected_framework: str
    build_steps: List[str]
    test_commands: List[str]
    lint_commands: List[str]
    package_managers: List[str]
    artifacts: List[str]
    deployment_targets: List[str]
    required_services: List[str]  # databases, redis, etc.
    environment_variables: List[str]
    coverage_tool: Optional[str]
    docker_support: bool
    confidence: float


class IntelligentCICDGenerator:
    """LLM-powered CI/CD pipeline generator for universal language support"""
    
    def __init__(self):
        self.llm_client = self._init_llm_client()
        
    def _init_llm_client(self):
        """Initialize LLM client (Azure OpenAI or OpenAI)"""
        if settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_API_KEY:
            return AsyncAzureOpenAI(
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
            )
        else:
            return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def analyze_project_for_cicd(
        self,
        source_files: Dict[str, str],
        test_files: Dict[str, str],
        config_files: Dict[str, str],
        project_context: Dict[str, Any]
    ) -> CICDAnalysis:
        """
        Analyze project to determine CI/CD requirements
        
        Args:
            source_files: Source code files
            test_files: Test files
            config_files: Configuration files (package.json, requirements.txt, etc.)
            project_context: Additional project context
            
        Returns:
            CICDAnalysis with detected settings and commands
        """
        
        # Build comprehensive prompt for analysis
        prompt = self._build_analysis_prompt(
            source_files, test_files, config_files, project_context
        )
        
        try:
            model = getattr(settings, 'AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4')
            
            response = await self.llm_client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a CI/CD expert with deep knowledge of all programming languages, 
                        frameworks, and build systems. Your job is to analyze code and determine the optimal 
                        CI/CD pipeline configuration. Always respond with valid JSON."""
                    },
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=2000
            )
            
            result = json.loads(response.choices[0].message.content)
            return self._parse_analysis_result(result)
            
        except Exception as e:
            logger.error(f"Failed to analyze project for CI/CD: {e}")
            return self._fallback_analysis(source_files, config_files)
    
    async def generate_cicd_pipeline(
        self,
        analysis: CICDAnalysis,
        platform: CICDPlatform = CICDPlatform.GITHUB_ACTIONS,
        project_name: str = "project",
        additional_requirements: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate CI/CD pipeline configuration based on analysis
        
        Args:
            analysis: Project analysis results
            platform: Target CI/CD platform
            project_name: Name of the project
            additional_requirements: Any additional requirements
            
        Returns:
            Generated CI/CD configuration file content
        """
        
        prompt = self._build_generation_prompt(
            analysis, platform, project_name, additional_requirements
        )
        
        try:
            model = getattr(settings, 'AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4')
            
            response = await self.llm_client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are a CI/CD expert. Generate a production-ready {platform.value} 
                        configuration that follows best practices. Include caching, parallel jobs, multiple OS 
                        testing where appropriate, and security scanning. 
                        
                        CRITICAL: Output ONLY the raw YAML/configuration content without any markdown formatting, 
                        code blocks, or explanations. Do not wrap the output in ```yaml or any other markdown."""
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=3000
            )
            
            content = response.choices[0].message.content.strip()
            
            # Clean up markdown code blocks if present
            if content.startswith('```'):
                lines = content.split('\n')
                # Remove first line (```yaml or similar)
                if lines[0].startswith('```'):
                    lines = lines[1:]
                # Remove last line if it's just ```
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                content = '\n'.join(lines)
            
            return content
            
        except Exception as e:
            logger.error(f"Failed to generate CI/CD pipeline: {e}")
            return self._generate_fallback_pipeline(analysis, platform)
    
    def _build_analysis_prompt(
        self,
        source_files: Dict[str, str],
        test_files: Dict[str, str],
        config_files: Dict[str, str],
        project_context: Dict[str, Any]
    ) -> str:
        """Build prompt for project analysis"""
        
        # Sample key files for analysis
        source_samples = {}
        for filename, content in list(source_files.items())[:3]:
            source_samples[filename] = content[:500]
        
        test_samples = {}
        for filename, content in list(test_files.items())[:2]:
            test_samples[filename] = content[:300]
        
        return f"""
Analyze this project and determine CI/CD requirements:

PROJECT CONTEXT:
{json.dumps(project_context, indent=2)}

CONFIGURATION FILES:
{json.dumps(list(config_files.keys()), indent=2)}

SOURCE CODE SAMPLES:
{json.dumps(source_samples, indent=2)}

TEST FILE SAMPLES:
{json.dumps(test_samples, indent=2)}

PACKAGE/DEPENDENCY FILES CONTENT:
{json.dumps({k: v for k, v in config_files.items() 
            if any(pattern in k.lower() for pattern in 
            ['requirements', 'package.json', 'pom.xml', 'build.gradle', 'cargo.toml', 'go.mod', 'gemfile'])}, 
            indent=2)}

ANALYZE AND RETURN JSON:
{{
    "detected_language": "primary language",
    "detected_framework": "main framework/library",
    "build_steps": ["list of build commands"],
    "test_commands": ["list of test commands"],
    "lint_commands": ["list of linting/formatting commands"],
    "package_managers": ["npm", "pip", "maven", etc],
    "artifacts": ["build outputs to cache/store"],
    "deployment_targets": ["docker", "kubernetes", "serverless", etc],
    "required_services": ["postgres", "redis", "elasticsearch", etc],
    "environment_variables": ["required env vars"],
    "coverage_tool": "coverage tool name or null",
    "docker_support": true/false,
    "confidence": 0.0-1.0,
    "additional_insights": {{
        "test_framework": "detected test framework",
        "code_style": "detected style guide",
        "security_scanning": ["security tools to use"],
        "performance_testing": ["performance test tools"],
        "documentation_generation": ["doc generation tools"]
    }}
}}

IMPORTANT:
- Detect the ACTUAL language and framework from the code
- Include all necessary build/test/lint commands
- Consider the test framework being used
- Include dependency installation steps
- Identify any special requirements
"""
    
    def _build_generation_prompt(
        self,
        analysis: CICDAnalysis,
        platform: CICDPlatform,
        project_name: str,
        additional_requirements: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for CI/CD generation"""
        
        platform_examples = {
            CICDPlatform.GITHUB_ACTIONS: "uses GitHub Actions syntax with jobs, steps, and actions",
            CICDPlatform.GITLAB_CI: "uses GitLab CI YAML with stages and jobs",
            CICDPlatform.JENKINS: "uses Jenkinsfile with pipeline syntax",
            CICDPlatform.AZURE_DEVOPS: "uses Azure Pipelines YAML",
            CICDPlatform.CIRCLECI: "uses CircleCI 2.1 configuration"
        }
        
        return f"""
Generate a {platform.value} CI/CD pipeline for this project:

PROJECT: {project_name}
LANGUAGE: {analysis.detected_language}
FRAMEWORK: {analysis.detected_framework}
BUILD STEPS: {json.dumps(analysis.build_steps)}
TEST COMMANDS: {json.dumps(analysis.test_commands)}
LINT COMMANDS: {json.dumps(analysis.lint_commands)}
PACKAGE MANAGERS: {json.dumps(analysis.package_managers)}
REQUIRED SERVICES: {json.dumps(analysis.required_services)}
DOCKER SUPPORT: {analysis.docker_support}
COVERAGE TOOL: {analysis.coverage_tool}

ADDITIONAL REQUIREMENTS:
{json.dumps(additional_requirements or {}, indent=2)}

GENERATE A PRODUCTION-READY PIPELINE THAT:
1. Runs on multiple OS (if applicable)
2. Uses caching for dependencies
3. Runs linting and code quality checks
4. Executes all tests with coverage
5. Builds artifacts/docker images if needed
6. Includes security scanning
7. Has proper job dependencies
8. Uses matrix builds for multiple versions
9. Includes deployment steps (if deployment targets specified)
10. Follows {platform.value} best practices

The pipeline should be optimized for:
- Fast feedback (parallel jobs where possible)
- Reliability (proper error handling)
- Security (no hardcoded secrets)
- Maintainability (clear structure and comments)

Platform note: {platform_examples.get(platform, '')}

Output only the configuration file content.
"""
    
    def _parse_analysis_result(self, result: Dict[str, Any]) -> CICDAnalysis:
        """Parse LLM response into CICDAnalysis"""
        
        return CICDAnalysis(
            detected_language=result.get('detected_language', 'unknown'),
            detected_framework=result.get('detected_framework', ''),
            build_steps=result.get('build_steps', []),
            test_commands=result.get('test_commands', []),
            lint_commands=result.get('lint_commands', []),
            package_managers=result.get('package_managers', []),
            artifacts=result.get('artifacts', []),
            deployment_targets=result.get('deployment_targets', []),
            required_services=result.get('required_services', []),
            environment_variables=result.get('environment_variables', []),
            coverage_tool=result.get('coverage_tool'),
            docker_support=result.get('docker_support', False),
            confidence=result.get('confidence', 0.8)
        )
    
    def _fallback_analysis(
        self,
        source_files: Dict[str, str],
        config_files: Dict[str, str]
    ) -> CICDAnalysis:
        """Basic fallback analysis using heuristics"""
        
        # Detect language from file extensions
        language = "unknown"
        extensions = [Path(f).suffix for f in source_files.keys()]
        
        if '.py' in extensions:
            language = "python"
        elif '.js' in extensions or '.ts' in extensions:
            language = "javascript"
        elif '.java' in extensions:
            language = "java"
        elif '.go' in extensions:
            language = "go"
        elif '.rs' in extensions:
            language = "rust"
        elif '.rb' in extensions:
            language = "ruby"
        
        # Basic commands based on language
        commands_map = {
            "python": {
                "build": ["pip install -r requirements.txt"],
                "test": ["pytest", "python -m unittest"],
                "lint": ["flake8", "black --check", "mypy"]
            },
            "javascript": {
                "build": ["npm install", "npm run build"],
                "test": ["npm test"],
                "lint": ["eslint", "prettier --check"]
            },
            "java": {
                "build": ["mvn clean install", "gradle build"],
                "test": ["mvn test", "gradle test"],
                "lint": ["checkstyle", "spotbugs"]
            }
        }
        
        lang_commands = commands_map.get(language, {})
        
        return CICDAnalysis(
            detected_language=language,
            detected_framework="",
            build_steps=lang_commands.get("build", []),
            test_commands=lang_commands.get("test", []),
            lint_commands=lang_commands.get("lint", []),
            package_managers=[],
            artifacts=[],
            deployment_targets=[],
            required_services=[],
            environment_variables=[],
            coverage_tool=None,
            docker_support="Dockerfile" in config_files,
            confidence=0.5
        )
    
    def _generate_fallback_pipeline(
        self,
        analysis: CICDAnalysis,
        platform: CICDPlatform
    ) -> str:
        """Generate basic fallback pipeline"""
        
        if platform == CICDPlatform.GITHUB_ACTIONS:
            return f"""name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Build
      run: |
        {' && '.join(analysis.build_steps) if analysis.build_steps else 'echo "No build steps detected"'}
    
    - name: Test
      run: |
        {' && '.join(analysis.test_commands) if analysis.test_commands else 'echo "No test commands detected"'}
"""
        
        return "# Fallback CI/CD configuration\n# Manual configuration required"


async def generate_intelligent_cicd(
    capsule: Any,
    platform: CICDPlatform = CICDPlatform.GITHUB_ACTIONS,
    additional_requirements: Optional[Dict[str, Any]] = None
) -> str:
    """
    Main function to generate intelligent CI/CD pipeline
    
    Args:
        capsule: QLCapsule with source code and tests
        platform: Target CI/CD platform
        additional_requirements: Any additional requirements
        
    Returns:
        Generated CI/CD configuration
    """
    
    generator = IntelligentCICDGenerator()
    
    # Analyze the project
    analysis = await generator.analyze_project_for_cicd(
        source_files=capsule.source_code,
        test_files=capsule.tests,
        config_files={
            k: v for k, v in capsule.source_code.items() 
            if any(pattern in k.lower() for pattern in 
                   ['requirements', 'package', 'pom', 'build', 'cargo', 'go.mod', 'gemfile', 'dockerfile'])
        },
        project_context={
            'name': capsule.manifest.get('name', 'project'),
            'description': capsule.manifest.get('description', ''),
            'language': capsule.manifest.get('language', 'unknown')
        }
    )
    
    logger.info(
        f"CI/CD Analysis complete",
        language=analysis.detected_language,
        framework=analysis.detected_framework,
        confidence=analysis.confidence
    )
    
    # Generate the pipeline
    pipeline = await generator.generate_cicd_pipeline(
        analysis=analysis,
        platform=platform,
        project_name=capsule.manifest.get('name', 'project'),
        additional_requirements=additional_requirements
    )
    
    return pipeline