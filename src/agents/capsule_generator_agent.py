"""
Enterprise Capsule Generator Agent
Advanced LLM-powered agent for creating production-ready, enterprise-grade capsules
with comprehensive documentation, best practices, and deployment configurations.
"""

import json
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import structlog

from src.agents.base_agents import Agent
from src.common.models import AgentTier, Task, TaskResult
from src.common.config import settings
from uuid import uuid4
from src.agents.azure_llm_client import llm_client


logger = structlog.get_logger()


@dataclass
class CapsuleMetadata:
    """Metadata for enterprise-grade capsule generation"""
    primary_language: str
    frameworks: List[str] = field(default_factory=list)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)  # lang -> deps
    project_type: str = ""  # web_app, cli_tool, library, microservice, etc.
    deployment_targets: List[str] = field(default_factory=list)  # docker, k8s, cloud_function, etc.
    testing_frameworks: List[str] = field(default_factory=list)
    documentation_style: str = "comprehensive"  # minimal, standard, comprehensive
    has_ci_cd: bool = True
    has_dockerfile: bool = True
    has_tests: bool = True
    architecture_pattern: str = ""  # mvc, microservice, serverless, etc.


@dataclass
class EnterpriseProjectStructure:
    """Enterprise-grade project structure"""
    source_files: Dict[str, str] = field(default_factory=dict)
    test_files: Dict[str, str] = field(default_factory=dict)
    config_files: Dict[str, str] = field(default_factory=dict)
    documentation_files: Dict[str, str] = field(default_factory=dict)
    deployment_files: Dict[str, str] = field(default_factory=dict)
    ci_cd_files: Dict[str, str] = field(default_factory=dict)
    script_files: Dict[str, str] = field(default_factory=dict)
    asset_files: Dict[str, Any] = field(default_factory=dict)


class CapsuleGeneratorAgent(Agent):
    """
    Specialized agent for generating enterprise-grade capsules.
    Uses meta-prompts and intelligent analysis to create production-ready projects.
    """
    
    def __init__(self):
        super().__init__(
            agent_id=f"capsule-generator-{str(uuid4())}",
            tier=AgentTier.T2  # Uses T2 for complex reasoning
        )
        self.name = "Enterprise Capsule Generator"
        self.capabilities = ["code_generation", "testing", "documentation"]
        self.specializations = ["enterprise_capsule_generation", "best_practices", "documentation"]
    
    async def _make_llm_request(
        self, 
        prompt: str, 
        temperature: float = 0.7,
        model: Optional[str] = None
    ) -> str:
        """Make LLM request using the centralized client"""
        try:
            response = await llm_client.generate(
                prompt=prompt,
                temperature=temperature,
                max_tokens=4000,
                model=model
            )
            return response.get('content', '')
        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            raise
        
    async def analyze_project_context(
        self,
        tasks: List[Dict[str, Any]],
        results: List[Dict[str, Any]],
        original_request: str
    ) -> CapsuleMetadata:
        """Analyze the project context to determine metadata"""
        
        # Create analysis prompt
        analysis_prompt = f"""Analyze this software project to determine its characteristics:

Original Request: {original_request}

Decomposed Tasks:
{json.dumps([{'type': t.get('type'), 'description': t.get('description')} for t in tasks], indent=2)}

Task Results Summary:
{json.dumps([{
    'task_type': r.get('task', {}).get('type'),
    'output_type': r.get('execution', {}).get('output_type'),
    'language': r.get('execution', {}).get('output', {}).get('language', 'unknown')
} for r in results], indent=2)}

Based on this information, determine:
1. Primary programming language
2. Frameworks/libraries being used
3. Project type (web_app, cli_tool, library, microservice, data_pipeline, etc.)
4. Architecture pattern (mvc, microservice, serverless, monolithic, etc.)
5. Deployment targets (docker, kubernetes, cloud_function, vm, etc.)
6. Testing requirements and frameworks

Respond with a JSON object containing these details."""

        # Get analysis from LLM
        response = await self._make_llm_request(
            prompt=analysis_prompt,
            temperature=0.3,
            model="gpt-4"  # Use GPT-4 for analysis
        )
        
        try:
            analysis = json.loads(response)
            
            return CapsuleMetadata(
                primary_language=analysis.get('primary_language', 'python'),
                frameworks=analysis.get('frameworks', []),
                dependencies={analysis.get('primary_language', 'python'): analysis.get('dependencies', [])},
                project_type=analysis.get('project_type', 'general'),
                deployment_targets=analysis.get('deployment_targets', ['docker']),
                testing_frameworks=analysis.get('testing_frameworks', []),
                architecture_pattern=analysis.get('architecture_pattern', 'modular'),
                has_ci_cd=analysis.get('requires_cicd', True),
                has_dockerfile=analysis.get('requires_docker', True),
                has_tests=analysis.get('requires_tests', True)
            )
        except json.JSONDecodeError:
            logger.warning("Failed to parse project analysis, using defaults")
            return CapsuleMetadata(primary_language="python")
    
    async def generate_readme(
        self,
        metadata: CapsuleMetadata,
        project_structure: EnterpriseProjectStructure,
        original_request: str
    ) -> str:
        """Generate comprehensive README.md"""
        
        # Get main functionality from source files
        main_files = [f for f in project_structure.source_files.keys() if 'main' in f.lower()]
        
        readme_prompt = f"""Generate a comprehensive, professional README.md for this project:

Project Type: {metadata.project_type}
Primary Language: {metadata.primary_language}
Frameworks: {', '.join(metadata.frameworks)}
Original Request: {original_request}

Project Files:
- Source: {list(project_structure.source_files.keys())}
- Tests: {list(project_structure.test_files.keys())}
- Config: {list(project_structure.config_files.keys())}

The README should include:
1. Project title and description
2. Features list
3. Technology stack
4. Prerequisites
5. Installation instructions
6. Usage examples with code snippets
7. API documentation (if applicable)
8. Testing instructions
9. Deployment guide
10. Contributing guidelines
11. License (MIT)
12. Contact/Support information

Make it professional, clear, and comprehensive. Include badges for build status, coverage, etc."""

        response = await self._make_llm_request(
            prompt=readme_prompt,
            temperature=0.7,
            model="gpt-4"
        )
        
        return response
    
    async def generate_dockerfile(
        self,
        metadata: CapsuleMetadata,
        project_structure: EnterpriseProjectStructure
    ) -> str:
        """Generate production-ready Dockerfile"""
        
        dockerfile_prompt = f"""Generate a production-ready, multi-stage Dockerfile for:

Language: {metadata.primary_language}
Frameworks: {', '.join(metadata.frameworks)}
Project Type: {metadata.project_type}

Requirements:
1. Use official base images with specific versions
2. Multi-stage build for smaller final image
3. Security best practices (non-root user, minimal attack surface)
4. Proper layer caching optimization
5. Health checks
6. Appropriate EXPOSE directives
7. Production-ready CMD/ENTRYPOINT

Dependencies to install:
{json.dumps(metadata.dependencies, indent=2)}"""

        response = await self._make_llm_request(
            prompt=dockerfile_prompt,
            temperature=0.3,
            model="gpt-4"
        )
        
        return response
    
    async def generate_ci_cd_pipeline(
        self,
        metadata: CapsuleMetadata,
        project_structure: EnterpriseProjectStructure
    ) -> Dict[str, str]:
        """Generate CI/CD pipeline configurations"""
        
        ci_cd_files = {}
        
        # GitHub Actions workflow
        github_actions_prompt = f"""Generate a comprehensive GitHub Actions workflow for:

Language: {metadata.primary_language}
Testing Frameworks: {', '.join(metadata.testing_frameworks)}
Deployment Targets: {', '.join(metadata.deployment_targets)}

Include:
1. Multiple trigger events (push, PR, schedule)
2. Matrix testing across multiple versions
3. Code quality checks (linting, formatting)
4. Security scanning
5. Test execution with coverage
6. Build and publish artifacts
7. Container image building and pushing
8. Deployment stages (dev, staging, prod)
9. Notifications on failure"""

        github_workflow = await self._make_llm_request(
            prompt=github_actions_prompt,
            temperature=0.3,
            model="gpt-4"
        )
        
        ci_cd_files['.github/workflows/main.yml'] = github_workflow
        
        # Add GitLab CI if needed
        if 'gitlab' in str(metadata.deployment_targets).lower():
            gitlab_prompt = github_actions_prompt.replace("GitHub Actions", "GitLab CI")
            gitlab_ci = await self._make_llm_request(
                prompt=gitlab_prompt,
                temperature=0.3,
                model="gpt-4"
            )
            ci_cd_files['.gitlab-ci.yml'] = gitlab_ci
        
        return ci_cd_files
    
    async def generate_documentation(
        self,
        metadata: CapsuleMetadata,
        project_structure: EnterpriseProjectStructure,
        original_request: str
    ) -> Dict[str, str]:
        """Generate comprehensive documentation"""
        
        docs = {}
        
        # API Documentation
        if metadata.project_type in ['web_app', 'microservice', 'api']:
            api_doc_prompt = f"""Generate comprehensive API documentation for this {metadata.project_type}.

Include:
1. API Overview
2. Authentication methods
3. Endpoint documentation with:
   - HTTP method
   - Path
   - Parameters
   - Request/Response examples
   - Error codes
4. Rate limiting
5. Versioning strategy
6. SDKs/Client libraries

Base it on these source files:
{list(project_structure.source_files.keys())}"""

            api_docs = await self._make_llm_request(
                prompt=api_doc_prompt,
                temperature=0.5,
                model="gpt-4"
            )
            docs['docs/API.md'] = api_docs
        
        # Architecture Documentation
        arch_doc_prompt = f"""Generate architecture documentation for this {metadata.architecture_pattern} {metadata.project_type}.

Include:
1. High-level architecture overview
2. Component descriptions
3. Data flow diagrams (mermaid format)
4. Design decisions and rationale
5. Scalability considerations
6. Security architecture
7. Technology choices justification"""

        arch_docs = await self._make_llm_request(
            prompt=arch_doc_prompt,
            temperature=0.5,
            model="gpt-4"
        )
        docs['docs/ARCHITECTURE.md'] = arch_docs
        
        # Development Guide
        dev_guide = await self._generate_development_guide(metadata, project_structure)
        docs['docs/DEVELOPMENT.md'] = dev_guide
        
        # Deployment Guide
        deploy_guide = await self._generate_deployment_guide(metadata)
        docs['docs/DEPLOYMENT.md'] = deploy_guide
        
        return docs
    
    async def generate_config_files(
        self,
        metadata: CapsuleMetadata,
        project_structure: EnterpriseProjectStructure
    ) -> Dict[str, str]:
        """Generate configuration files based on language and frameworks"""
        
        configs = {}
        
        # Language-specific configs
        if metadata.primary_language == 'python':
            # pyproject.toml
            configs['pyproject.toml'] = await self._generate_pyproject_toml(metadata)
            # requirements.txt
            configs['requirements.txt'] = '\n'.join(metadata.dependencies.get('python', []))
            # .flake8
            configs['.flake8'] = await self._generate_flake8_config()
            # pytest.ini
            if 'pytest' in str(metadata.testing_frameworks).lower():
                configs['pytest.ini'] = await self._generate_pytest_config()
                
        elif metadata.primary_language == 'javascript' or metadata.primary_language == 'typescript':
            # package.json
            configs['package.json'] = await self._generate_package_json(metadata)
            # .eslintrc.json
            configs['.eslintrc.json'] = await self._generate_eslint_config()
            # jest.config.js
            if 'jest' in str(metadata.testing_frameworks).lower():
                configs['jest.config.js'] = await self._generate_jest_config()
                
        elif metadata.primary_language == 'go':
            # go.mod
            configs['go.mod'] = await self._generate_go_mod(metadata)
            # Makefile
            configs['Makefile'] = await self._generate_makefile_go()
            
        # Universal configs
        configs['.gitignore'] = await self._generate_gitignore(metadata.primary_language)
        configs['.editorconfig'] = await self._generate_editorconfig()
        configs['.env.example'] = await self._generate_env_example(metadata)
        
        # Docker compose for local development
        if metadata.has_dockerfile:
            configs['docker-compose.yml'] = await self._generate_docker_compose(metadata)
        
        return configs
    
    async def execute(self, task: Task, context: Dict[str, Any]) -> TaskResult:
        """
        Execute capsule generation task.
        This is called when the agent is invoked to create an enterprise capsule.
        """
        start_time = datetime.utcnow()
        
        try:
            # Extract necessary data from context
            tasks = context.get('tasks', [])
            results = context.get('results', [])
            original_request = context.get('original_request', '')
            shared_context = context.get('shared_context', {})
            
            logger.info(f"Generating enterprise capsule for {len(tasks)} tasks")
            
            # Step 1: Analyze project context
            metadata = await self.analyze_project_context(tasks, results, original_request)
            logger.info(f"Project analysis complete: {metadata.project_type} in {metadata.primary_language}")
            
            # Step 2: Initialize project structure
            project_structure = EnterpriseProjectStructure()
            
            # Step 3: Organize existing code from results
            await self._organize_existing_code(results, project_structure, metadata)
            
            # Step 4: Generate README
            readme = await self.generate_readme(metadata, project_structure, original_request)
            project_structure.documentation_files['README.md'] = readme
            
            # Step 5: Generate Dockerfile if needed
            if metadata.has_dockerfile:
                dockerfile = await self.generate_dockerfile(metadata, project_structure)
                project_structure.deployment_files['Dockerfile'] = dockerfile
            
            # Step 6: Generate CI/CD pipelines
            if metadata.has_ci_cd:
                ci_cd_files = await self.generate_ci_cd_pipeline(metadata, project_structure)
                project_structure.ci_cd_files.update(ci_cd_files)
            
            # Step 7: Generate comprehensive documentation
            docs = await self.generate_documentation(metadata, project_structure, original_request)
            project_structure.documentation_files.update(docs)
            
            # Step 8: Generate configuration files
            configs = await self.generate_config_files(metadata, project_structure)
            project_structure.config_files.update(configs)
            
            # Step 9: Generate additional best practice files
            await self._add_best_practice_files(metadata, project_structure)
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Return the complete enterprise capsule
            return TaskResult(
                task_id=task.id,
                status=task.status,
                output_type="enterprise_capsule",
                output={
                    "metadata": metadata.__dict__,
                    "structure": {
                        "source_files": project_structure.source_files,
                        "test_files": project_structure.test_files,
                        "config_files": project_structure.config_files,
                        "documentation_files": project_structure.documentation_files,
                        "deployment_files": project_structure.deployment_files,
                        "ci_cd_files": project_structure.ci_cd_files,
                        "script_files": project_structure.script_files,
                        "asset_files": project_structure.asset_files
                    }
                },
                execution_time=execution_time,
                agent_tier_used=self.tier,
                confidence_score=0.95,
                metadata={
                    "total_files": sum([
                        len(project_structure.source_files),
                        len(project_structure.test_files),
                        len(project_structure.config_files),
                        len(project_structure.documentation_files),
                        len(project_structure.deployment_files),
                        len(project_structure.ci_cd_files),
                        len(project_structure.script_files)
                    ]),
                    "languages": [metadata.primary_language] + list(set(
                        lang for deps in metadata.dependencies.keys() 
                        for lang in [deps] if lang != metadata.primary_language
                    )),
                    "has_tests": len(project_structure.test_files) > 0,
                    "has_docs": len(project_structure.documentation_files) > 0,
                    "has_ci_cd": len(project_structure.ci_cd_files) > 0
                }
            )
            
        except Exception as e:
            logger.error(f"Error generating enterprise capsule: {e}")
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return TaskResult(
                task_id=task.id,
                status=task.status,
                output_type="error",
                output={"error": str(e)},
                execution_time=execution_time,
                agent_tier_used=self.tier,
                confidence_score=0.0,
                metadata={"error_type": type(e).__name__}
            )
    
    async def _organize_existing_code(
        self,
        results: List[Dict[str, Any]],
        project_structure: EnterpriseProjectStructure,
        metadata: CapsuleMetadata
    ):
        """Organize existing code from task results into proper structure"""
        
        for result in results:
            execution = result.get('execution', {})
            if execution.get('status') != 'completed':
                continue
                
            output = execution.get('output', {})
            task_type = result.get('task', {}).get('type', '')
            
            # Handle different output formats
            if isinstance(output, dict):
                code = output.get('code', '')
                language = output.get('language', metadata.primary_language)
                
                if code:
                    # Determine file type and name
                    if 'test' in task_type.lower():
                        filename = self._generate_test_filename(task_type, language)
                        project_structure.test_files[filename] = code
                    else:
                        filename = self._generate_source_filename(task_type, language)
                        project_structure.source_files[filename] = code
    
    async def _add_best_practice_files(
        self,
        metadata: CapsuleMetadata,
        project_structure: EnterpriseProjectStructure
    ):
        """Add additional best practice files"""
        
        # Security policy
        security_policy = await self._generate_security_policy(metadata)
        project_structure.documentation_files['SECURITY.md'] = security_policy
        
        # Contributing guidelines
        contributing = await self._generate_contributing_guide()
        project_structure.documentation_files['CONTRIBUTING.md'] = contributing
        
        # Code of conduct
        code_of_conduct = await self._generate_code_of_conduct()
        project_structure.documentation_files['CODE_OF_CONDUCT.md'] = code_of_conduct
        
        # License
        project_structure.documentation_files['LICENSE'] = self._get_mit_license()
        
        # Changelog
        project_structure.documentation_files['CHANGELOG.md'] = self._initial_changelog()
    
    # Helper methods for generating specific files
    async def _generate_pyproject_toml(self, metadata: CapsuleMetadata) -> str:
        """Generate pyproject.toml for Python projects"""
        prompt = f"""Generate a modern pyproject.toml file for a Python project with:
- Project type: {metadata.project_type}
- Dependencies: {metadata.dependencies.get('python', [])}
- Testing frameworks: {metadata.testing_frameworks}

Include: build system, project metadata, dependencies, dev dependencies, and tool configurations."""
        
        return await self._make_llm_request(prompt, temperature=0.3)
    
    async def _generate_package_json(self, metadata: CapsuleMetadata) -> str:
        """Generate package.json for JavaScript/TypeScript projects"""
        prompt = f"""Generate a complete package.json for a {metadata.primary_language} project:
- Project type: {metadata.project_type}
- Frameworks: {metadata.frameworks}
- Dependencies: {metadata.dependencies.get('javascript', [])}

Include: scripts for dev/build/test/lint, dependencies, devDependencies, and engines."""
        
        return await self._make_llm_request(prompt, temperature=0.3)
    
    async def _generate_gitignore(self, language: str) -> str:
        """Generate comprehensive .gitignore file"""
        prompt = f"""Generate a comprehensive .gitignore file for a {language} project.
Include: language-specific files, IDE files, OS files, environment files, build artifacts, and logs."""
        
        return await self._make_llm_request(prompt, temperature=0.2)
    
    def _generate_test_filename(self, task_type: str, language: str) -> str:
        """Generate appropriate test filename"""
        base_name = task_type.replace('test_', '').replace('_test', '')
        
        if language == 'python':
            return f"tests/test_{base_name}.py"
        elif language in ['javascript', 'typescript']:
            return f"tests/{base_name}.test.{language.replace('typescript', 'ts').replace('javascript', 'js')}"
        elif language == 'go':
            return f"{base_name}_test.go"
        else:
            return f"tests/{base_name}_test.{language}"
    
    def _generate_source_filename(self, task_type: str, language: str) -> str:
        """Generate appropriate source filename"""
        # Clean up task type to create meaningful filename
        name = task_type.replace('code_generation', '').replace('implementation', '').strip('_')
        if not name:
            name = 'main'
            
        ext_map = {
            'python': 'py',
            'javascript': 'js',
            'typescript': 'ts',
            'go': 'go',
            'java': 'java',
            'rust': 'rs',
            'cpp': 'cpp',
            'c': 'c'
        }
        
        ext = ext_map.get(language, language)
        
        # Organize by language conventions
        if language == 'python':
            return f"src/{name}.{ext}"
        elif language in ['javascript', 'typescript']:
            return f"src/{name}.{ext}"
        elif language == 'go':
            return f"{name}.{ext}"
        elif language == 'java':
            return f"src/main/java/{name}.{ext}"
        else:
            return f"src/{name}.{ext}"
    
    def _get_mit_license(self) -> str:
        """Return MIT license text"""
        year = datetime.now().year
        return f"""MIT License

Copyright (c) {year} [Project Author]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""
    
    def _initial_changelog(self) -> str:
        """Generate initial changelog"""
        date = datetime.now().strftime("%Y-%m-%d")
        return f"""# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - {date}

### Added
- Initial release
- Core functionality implementation
- Comprehensive test suite
- Documentation
- CI/CD pipeline
- Docker support
"""
    
    async def _generate_development_guide(self, metadata: CapsuleMetadata, project_structure: EnterpriseProjectStructure) -> str:
        """Generate development guide"""
        prompt = f"""Generate a comprehensive development guide for contributors to a {metadata.primary_language} {metadata.project_type} project.

Include:
1. Development environment setup
2. Project structure explanation
3. Coding standards and style guide
4. Testing guidelines
5. Debugging tips
6. Common development tasks
7. Performance considerations
8. Security best practices"""

        return await self._make_llm_request(prompt, temperature=0.5)
    
    async def _generate_deployment_guide(self, metadata: CapsuleMetadata) -> str:
        """Generate deployment guide"""
        prompt = f"""Generate a comprehensive deployment guide for a {metadata.project_type} targeting {', '.join(metadata.deployment_targets)}.

Include:
1. Prerequisites
2. Environment configuration
3. Step-by-step deployment instructions
4. Monitoring and logging setup
5. Scaling considerations
6. Backup and disaster recovery
7. Troubleshooting common issues
8. Rollback procedures"""

        return await self._make_llm_request(prompt, temperature=0.5)
    
    async def _generate_security_policy(self, metadata: CapsuleMetadata) -> str:
        """Generate security policy"""
        prompt = f"""Generate a SECURITY.md file for a {metadata.project_type} project.

Include:
1. Security disclosure policy
2. Supported versions
3. Reporting vulnerabilities process
4. Security update policy
5. Security best practices for the project"""

        return await self._make_llm_request(prompt, temperature=0.4)
    
    async def _generate_contributing_guide(self) -> str:
        """Generate contributing guidelines"""
        return """# Contributing Guidelines

Thank you for your interest in contributing to this project! We welcome contributions from the community.

## How to Contribute

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Development Process

1. Ensure your code follows the project's coding standards
2. Write tests for new functionality
3. Update documentation as needed
4. Ensure all tests pass before submitting PR
5. Keep commits atomic and well-described

## Code of Conduct

Please note that this project is released with a Contributor Code of Conduct. By participating in this project you agree to abide by its terms.

## Questions?

Feel free to open an issue for any questions about contributing.
"""
    
    async def _generate_code_of_conduct(self) -> str:
        """Generate code of conduct"""
        return """# Contributor Covenant Code of Conduct

## Our Pledge

We as members, contributors, and leaders pledge to make participation in our
community a harassment-free experience for everyone, regardless of age, body
size, visible or invisible disability, ethnicity, sex characteristics, gender
identity and expression, level of experience, education, socio-economic status,
nationality, personal appearance, race, religion, or sexual identity
and orientation.

## Our Standards

Examples of behavior that contributes to a positive environment:

* Using welcoming and inclusive language
* Being respectful of differing viewpoints and experiences
* Gracefully accepting constructive criticism
* Focusing on what is best for the community
* Showing empathy towards other community members

## Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be
reported to the community leaders responsible for enforcement.
All complaints will be reviewed and investigated promptly and fairly.

## Attribution

This Code of Conduct is adapted from the [Contributor Covenant][homepage],
version 2.0, available at
https://www.contributor-covenant.org/version/2/0/code_of_conduct.html.
"""
    
    async def _generate_flake8_config(self) -> str:
        """Generate .flake8 configuration"""
        return """[flake8]
max-line-length = 88
extend-ignore = E203, W503
exclude = 
    .git,
    __pycache__,
    .venv,
    venv,
    build,
    dist,
    *.egg-info,
    .tox,
    .mypy_cache,
    .pytest_cache
per-file-ignores =
    __init__.py:F401
    tests/*:F401,F811
"""
    
    async def _generate_pytest_config(self) -> str:
        """Generate pytest.ini configuration"""
        return """[pytest]
testpaths = tests
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*
addopts = 
    -ra
    --strict-markers
    --cov=src
    --cov-branch
    --cov-report=term-missing:skip-covered
    --cov-report=html
    --cov-report=xml
    --cov-fail-under=80
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
"""
    
    async def _generate_eslint_config(self) -> str:
        """Generate .eslintrc.json configuration"""
        return """{
  "env": {
    "browser": true,
    "es2021": true,
    "node": true,
    "jest": true
  },
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "prettier"
  ],
  "parser": "@typescript-eslint/parser",
  "parserOptions": {
    "ecmaVersion": 12,
    "sourceType": "module"
  },
  "plugins": [
    "@typescript-eslint"
  ],
  "rules": {
    "indent": ["error", 2],
    "quotes": ["error", "single"],
    "semi": ["error", "always"],
    "no-console": "warn",
    "@typescript-eslint/explicit-module-boundary-types": "off",
    "@typescript-eslint/no-explicit-any": "warn"
  }
}"""
    
    async def _generate_jest_config(self) -> str:
        """Generate jest.config.js configuration"""
        return """module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/src', '<rootDir>/tests'],
  testMatch: ['**/__tests__/**/*.ts', '**/?(*.)+(spec|test).ts'],
  transform: {
    '^.+\\.ts$': 'ts-jest',
  },
  collectCoverageFrom: [
    'src/**/*.ts',
    '!src/**/*.d.ts',
    '!src/**/*.interface.ts',
    '!src/index.ts',
  ],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80,
    },
  },
  coverageReporters: ['text', 'lcov', 'html'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
  },
};"""
    
    async def _generate_go_mod(self, metadata: CapsuleMetadata) -> str:
        """Generate go.mod file"""
        prompt = f"""Generate a go.mod file for a Go project:
- Project type: {metadata.project_type}
- Dependencies: {metadata.dependencies.get('go', [])}

Include appropriate module name and Go version."""
        
        return await self._make_llm_request(prompt, temperature=0.2)
    
    async def _generate_makefile_go(self) -> str:
        """Generate Makefile for Go projects"""
        return """# Makefile for Go project

.PHONY: build test clean run lint fmt vet coverage docker

# Variables
BINARY_NAME=app
DOCKER_IMAGE=myapp:latest
GO=go
GOFLAGS=-v

# Build the application
build:
\t$(GO) build $(GOFLAGS) -o $(BINARY_NAME) .

# Run tests
test:
\t$(GO) test $(GOFLAGS) -race -coverprofile=coverage.txt -covermode=atomic ./...

# Clean build artifacts
clean:
\t$(GO) clean
\trm -f $(BINARY_NAME)
\trm -f coverage.txt

# Run the application
run: build
\t./$(BINARY_NAME)

# Run linter
lint:
\tgolangci-lint run

# Format code
fmt:
\t$(GO) fmt ./...

# Run go vet
vet:
\t$(GO) vet ./...

# Generate coverage report
coverage: test
\t$(GO) tool cover -html=coverage.txt -o coverage.html

# Build Docker image
docker:
\tdocker build -t $(DOCKER_IMAGE) .

# Run all checks
check: fmt vet lint test
"""
    
    async def _generate_editorconfig(self) -> str:
        """Generate .editorconfig file"""
        return """# EditorConfig is awesome: https://EditorConfig.org

# top-most EditorConfig file
root = true

# Unix-style newlines with a newline ending every file
[*]
end_of_line = lf
insert_final_newline = true
charset = utf-8
trim_trailing_whitespace = true

# Python files
[*.py]
indent_style = space
indent_size = 4

# JavaScript/TypeScript files
[*.{js,jsx,ts,tsx}]
indent_style = space
indent_size = 2

# Go files
[*.go]
indent_style = tab

# YAML files
[*.{yml,yaml}]
indent_style = space
indent_size = 2

# Markdown files
[*.md]
trim_trailing_whitespace = false

# Makefile
[Makefile]
indent_style = tab
"""
    
    async def _generate_env_example(self, metadata: CapsuleMetadata) -> str:
        """Generate .env.example file"""
        prompt = f"""Generate a .env.example file for a {metadata.project_type} {metadata.primary_language} project.

Include common environment variables for:
- Database connections
- API keys (as placeholders)
- Service URLs
- Feature flags
- Logging levels
- Port configurations

Make it comprehensive but with placeholder values."""
        
        return await self._make_llm_request(prompt, temperature=0.3)
    
    async def _generate_docker_compose(self, metadata: CapsuleMetadata) -> str:
        """Generate docker-compose.yml for local development"""
        prompt = f"""Generate a docker-compose.yml file for local development of a {metadata.project_type}.

Include:
- Main application service
- Database service (if applicable)
- Cache service (if applicable)
- Volume mappings for development
- Network configuration
- Environment variables
- Health checks

Make it suitable for local development with hot reloading if possible."""
        
        return await self._make_llm_request(prompt, temperature=0.4)