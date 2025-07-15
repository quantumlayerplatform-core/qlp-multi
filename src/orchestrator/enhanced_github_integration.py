#!/usr/bin/env python3
"""
Enhanced GitHub Integration - Extends existing v2 with LLM-powered structure generation
"""

import os
import json
import re
import base64
import aiohttp
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from pathlib import Path
import structlog

from src.orchestrator.github_integration_v2 import GitHubIntegrationV2
from src.agents.azure_llm_client import llm_client
from src.common.models import QLCapsule, Task, TaskStatus
from src.agents.specialized_agents import ProductionArchitectAgent

logger = structlog.get_logger()


def extract_json_from_llm(content: str) -> Dict[str, Any]:
    """
    Extract JSON from LLM response, handling markdown blocks and common issues.
    """
    # Clean markdown code blocks
    content = content.strip()
    if content.startswith('```json'):
        content = content[7:]  # Remove ```json
    elif content.startswith('```'):
        content = content[3:]  # Remove ```
    if content.endswith('```'):
        content = content[:-3]  # Remove trailing ```
    content = content.strip()
    
    # Try to extract JSON object
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    if json_match:
        json_str = json_match.group(0)
        
        # Handle truncated JSON by counting braces
        open_braces = json_str.count('{')
        close_braces = json_str.count('}')
        
        if open_braces > close_braces:
            json_str += '}' * (open_braces - close_braces)
        
        # Handle arrays
        open_brackets = json_str.count('[')
        close_brackets = json_str.count(']')
        
        if open_brackets > close_brackets:
            json_str += ']' * (open_brackets - close_brackets)
        
        # Handle trailing commas which are common in LLM output
        # Remove commas before closing braces/brackets
        json_str = re.sub(r',\s*([\]}])', r'\1', json_str)
        
        return json.loads(json_str)
    
    # Fallback to direct parsing
    return json.loads(content)


class EnhancedGitHubIntegration(GitHubIntegrationV2):
    """
    Extends GitHubIntegrationV2 to add intelligent project structure generation
    using existing LLM agents
    """
    
    def __init__(self, token: Optional[str] = None):
        super().__init__(token)
        self.architect_agent = ProductionArchitectAgent("github-architect")
    
    async def push_capsule_atomic(
        self,
        capsule: QLCapsule,
        repo_name: Optional[str] = None,
        private: bool = False,
        use_intelligent_structure: bool = True
    ) -> Dict[str, Any]:
        """
        Enhanced push that intelligently organizes files using LLM
        
        Args:
            capsule: The capsule to push
            repo_name: Optional repository name
            private: Whether to create private repo
            use_intelligent_structure: If True, uses LLM to organize files
        """
        
        if use_intelligent_structure:
            try:
                # Use LLM to analyze and reorganize the capsule
                logger.info("Using LLM to create enterprise-grade structure")
                
                # Step 1: Analyze the capsule
                analysis = await self._analyze_capsule_with_llm(capsule)
                
                # Step 2: Generate organized file structure
                organized_files = await self._create_intelligent_structure(capsule, analysis)
                
                # Create a modified capsule with the new structure
                modified_capsule = self._create_modified_capsule(capsule, organized_files, analysis)
                
                # Call parent's push_capsule_atomic which handles the actual GitHub push
                # The parent method will use our CI/CD file if it's in the capsule
                return await super().push_capsule_atomic(modified_capsule, repo_name, private)
            except Exception as e:
                logger.error(f"Failed to use intelligent structure, falling back to standard push: {e}")
                # Fall back to standard push without intelligent structure
                return await super().push_capsule_atomic(capsule, repo_name, private)
        else:
            # Use original flat structure
            return await super().push_capsule_atomic(capsule, repo_name, private)
    
    async def _analyze_capsule_with_llm(self, capsule: QLCapsule) -> Dict[str, Any]:
        """
        Use LLM to analyze the capsule and determine the best structure
        """
        
        # Prepare context for the LLM
        code_samples = {}
        for filename, content in list(capsule.source_code.items())[:3]:  # First 3 files
            clean_content = self._clean_content(content)
            code_samples[filename] = clean_content[:500]  # First 500 chars
        
        analysis_prompt = f"""
        Analyze this code capsule and determine the optimal enterprise-grade folder structure.
        
        Language: {capsule.manifest.get('language', 'unknown')}
        Files: {list(capsule.source_code.keys())}
        Test Files: {list(capsule.tests.keys())}
        
        Code Samples:
        {json.dumps(code_samples, indent=2)}
        
        Based on this analysis, provide:
        1. Project type (library, microservice, CLI tool, web API, etc.)
        2. Recommended folder structure
        3. Module organization strategy
        4. Additional files needed (setup.py, requirements.txt, etc.)
        5. CI/CD recommendations
        6. Testing structure
        
        Consider best practices for {capsule.manifest.get('language', 'the detected language')}.
        
        Return a detailed JSON response with your recommendations.
        """
        
        response = await llm_client.chat_completion(
            model="gpt-4-turbo-preview",
            messages=[
                {
                    "role": "system", 
                    "content": "You are an expert software architect specializing in creating clean, maintainable project structures."
                },
                {"role": "user", "content": analysis_prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        try:
            analysis = extract_json_from_llm(response['content'])
            logger.info("LLM analysis complete", project_type=analysis.get('project_type'))
            return analysis
        except json.JSONDecodeError as e:
            logger.warning(
                "Failed to parse LLM response, using defaults",
                error=str(e),
                response_preview=response['content'][:500] if response.get('content') else None
            )
            return self._get_default_analysis(capsule)
    
    async def _create_intelligent_structure(
        self,
        capsule: QLCapsule,
        analysis: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Create an intelligent file structure based on LLM analysis
        """
        
        # Get the recommended structure from analysis
        project_type = analysis.get('project_type', 'library')
        structure_recommendation = analysis.get('folder_structure', {})
        
        # Ask LLM to map files to the new structure
        mapping_prompt = f"""
        Map the following files to an enterprise-grade folder structure for a {project_type}.
        
        Current files:
        Source: {list(capsule.source_code.keys())}
        Tests: {list(capsule.tests.keys())}
        
        Recommended structure: {json.dumps(structure_recommendation, indent=2)}
        
        For each file, determine:
        1. The best location in the new structure
        2. Whether to rename it for clarity
        3. What additional files should be created
        
        Language: {capsule.manifest.get('language', 'python')}
        
        Return a JSON mapping of:
        {{
            "file_mappings": {{
                "original_file": "new_path",
                ...
            }},
            "additional_files": {{
                "path": "content or template name",
                ...
            }}
        }}
        """
        
        response = await llm_client.chat_completion(
            model="gpt-4-turbo-preview",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert in software project organization and best practices."
                },
                {"role": "user", "content": mapping_prompt}
            ],
            temperature=0.2,
            max_tokens=2000
        )
        
        try:
            mapping_data = extract_json_from_llm(response['content'])
            
            # Create the new file structure
            organized_files = {}
            
            # Map existing source files
            file_mappings = mapping_data.get('file_mappings', {})
            for old_path, new_path in file_mappings.items():
                if old_path in capsule.source_code:
                    content = self._clean_content(capsule.source_code[old_path])
                    organized_files[new_path] = content
                elif old_path in capsule.tests:
                    content = self._clean_content(capsule.tests[old_path])
                    organized_files[new_path] = content
            
            # Add additional files
            additional_files = mapping_data.get('additional_files', {})
            for path, content_or_template in additional_files.items():
                if content_or_template in self._get_template_generators():
                    # Generate from template
                    content = self._generate_from_template(
                        content_or_template, 
                        capsule, 
                        analysis
                    )
                else:
                    content = content_or_template
                organized_files[path] = content
            
            # Add essential files if not already included
            organized_files = await self._ensure_essential_files(
                organized_files, 
                capsule, 
                analysis
            )
            
            # IMPORTANT: Add CI/CD workflow to organized_files so parent class doesn't override
            if ".github/workflows/ci.yml" not in organized_files:
                language = capsule.manifest.get('language', '').lower()
                project_type = analysis.get('project_type', 'library')
                organized_files[".github/workflows/ci.yml"] = await self._generate_enhanced_ci(
                    capsule, language, project_type
                )
            
            return organized_files
            
        except Exception as e:
            logger.error(f"Failed to create intelligent structure: {e}")
            # Fallback to basic organization
            return self._create_basic_structure(capsule)
    
    def _clean_content(self, content: Any) -> str:
        """Clean content for use in files"""
        if isinstance(content, dict):
            if 'content' in content:
                content = content['content']
            elif 'code' in content:
                content = content['code']
            else:
                content = str(content)
        
        content = str(content)
        
        # Remove markdown code blocks
        if content.strip().startswith("```"):
            lines = content.strip().split('\n')
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = '\n'.join(lines)
        
        # Remove dict wrapper if present
        if content.startswith("{'content': '") and content.endswith("'}"):
            content = content[13:-2]
            content = content.replace('\\n', '\n')
        
        return content.strip()
    
    def _create_modified_capsule(
        self,
        original: QLCapsule,
        organized_files: Dict[str, str],
        analysis: Dict[str, Any]
    ) -> QLCapsule:
        """
        Create a modified capsule with the new structure
        """
        # Create a copy of the original capsule with all required fields
        modified = QLCapsule(
            id=original.id,
            request_id=original.request_id,  # Fix: Include request_id
            manifest=original.manifest.copy(),
            source_code={},  # Will be populated below
            tests={},  # Will be populated below
            documentation=original.documentation,
            validation_report=original.validation_report,
            deployment_config=original.deployment_config.copy() if original.deployment_config else {},
            metadata=original.metadata.copy(),
            created_at=original.created_at
        )
        
        # Update manifest with project info
        modified.manifest['project_type'] = analysis.get('project_type', 'library')
        modified.manifest['structure_version'] = '2.0'
        
        for path, content in organized_files.items():
            if path == "README.md":
                modified.documentation = content
            elif path.startswith("tests/") or "test_" in path:
                modified.tests[path] = content
            elif path.endswith(('.py', '.js', '.java', '.go', '.rs', '.cpp', '.c')):
                modified.source_code[path] = content
            else:
                # Configuration files go to source_code
                modified.source_code[path] = content
        
        return modified
    
    async def _push_with_intelligent_files(
        self,
        capsule: QLCapsule,
        repo_name: Optional[str] = None,
        private: bool = False
    ) -> Dict[str, Any]:
        """
        Custom push method that respects files already in the capsule
        """
        # Call parent method which will handle the push
        result = await super().push_capsule_atomic(capsule, repo_name, private)
        
        return result
    
    async def _ensure_essential_files(
        self,
        files: Dict[str, str],
        capsule: QLCapsule,
        analysis: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Ensure essential files are present
        """
        language = capsule.manifest.get('language', '').lower()
        project_type = analysis.get('project_type', 'library')
        
        # Ensure README exists
        if "README.md" not in files:
            files["README.md"] = self._generate_readme(capsule, analysis)
        
        # Ensure .gitignore exists
        if ".gitignore" not in files:
            files[".gitignore"] = self._generate_enhanced_gitignore(language)
        
        # Always use enhanced CI/CD workflow (override basic one if exists)
        files[".github/workflows/ci.yml"] = await self._generate_enhanced_ci(
            capsule,
            language, 
            project_type
        )
        
        # Language-specific essentials
        if language == "python":
            if "requirements.txt" not in files and "pyproject.toml" not in files:
                files["requirements.txt"] = self._extract_requirements(capsule)
            
            if project_type == "library" and "setup.py" not in files:
                files["setup.py"] = self._generate_setup_py(capsule, analysis)
        
        return files
    
    def _generate_readme(self, capsule: QLCapsule, analysis: Dict[str, Any]) -> str:
        """Generate an enhanced README"""
        project_name = capsule.manifest.get('name', 'Project')
        project_type = analysis.get('project_type', 'project')
        
        readme = f"""# {project_name}

{capsule.manifest.get('description', 'A Quantum Layer Platform generated ' + project_type)}

## Overview

This {project_type} was generated by Quantum Layer Platform using AI-powered code generation and intelligent project structuring.

## Features

"""
        
        # Add features from analysis
        features = analysis.get('features', [])
        for feature in features:
            readme += f"- {feature}\n"
        
        readme += """
## Installation

```bash
# Clone the repository
git clone <repository-url>
cd <repository-name>
"""
        
        language = capsule.manifest.get('language', '').lower()
        if language == "python":
            readme += """
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt
"""
        
        readme += """```

## Usage

[Add usage examples here]

## Testing

```bash
"""
        
        if language == "python":
            readme += "pytest tests/"
        else:
            readme += "# Run tests"
        
        readme += """
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.

---
Generated by [Quantum Layer Platform](https://quantumlayerplatform.com)
"""
        
        return readme
    
    def _generate_enhanced_gitignore(self, language: str) -> str:
        """Generate an enhanced .gitignore"""
        base = super()._generate_gitignore(
            type('obj', (object,), {'manifest': {'language': language}})()
        )
        
        # Add QLP-specific ignores
        base += """
# Quantum Layer Platform
.qlp-cache/
qlp-output/
.qlp-temp/

# Local environment
.env.local
.env.*.local
"""
        
        return base
    
    async def _generate_enhanced_ci(self, capsule: QLCapsule, language: str, project_type: str) -> str:
        """Generate enhanced CI/CD workflow using intelligent LLM-based generation"""
        try:
            # Use intelligent CI/CD generator
            from .intelligent_cicd_generator import generate_intelligent_cicd, CICDPlatform
            
            logger.info("Using intelligent CI/CD generator for workflow creation")
            
            # Generate CI/CD pipeline using LLM
            cicd_content = await generate_intelligent_cicd(
                capsule=capsule,
                platform=CICDPlatform.GITHUB_ACTIONS,
                additional_requirements={
                    'project_type': project_type,
                    'enable_releases': True,
                    'enable_security_scanning': True,
                    'enable_dependency_updates': True
                }
            )
            
            return cicd_content
            
        except Exception as e:
            logger.error(f"Failed to generate intelligent CI/CD, falling back to template: {e}")
            # Fallback to language-specific template
            return self._generate_fallback_ci(language, project_type)
    
    def _generate_fallback_ci(self, language: str, project_type: str) -> str:
        """Fallback CI/CD generation with templates"""
        if language == "python":
            return f"""name: CI/CD

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  release:
    types: [created]

jobs:
  quality:
    name: Code Quality
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Cache dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install flake8 black mypy pytest pytest-cov
        if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
    
    - name: Format check with black
      run: black --check .
    
    - name: Lint with flake8
      run: flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
    
    - name: Type check with mypy
      run: mypy . --ignore-missing-imports || true

  test:
    name: Test
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ['3.9', '3.10', '3.11']
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install pytest pytest-cov
        if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
    
    - name: Run tests
      run: |
        pytest tests/ -v --cov=. --cov-report=xml --cov-report=term
    
    - name: Upload coverage
      if: matrix.os == 'ubuntu-latest' && matrix.python-version == '3.11'
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
"""
        else:
            # Generic CI for other languages
            return super()._generate_github_actions(
                type('obj', (object,), {'manifest': {'language': language}})()
            )
    
    def _extract_requirements(self, capsule: QLCapsule) -> str:
        """Extract Python requirements from code"""
        requirements = set()
        
        for content in capsule.source_code.values():
            clean_content = self._clean_content(content)
            
            # Find imports
            import_lines = re.findall(r'^(?:from|import)\s+(\w+)', clean_content, re.MULTILINE)
            for module in import_lines:
                # Skip standard library modules
                if module not in ['os', 'sys', 'json', 're', 'datetime', 'math', 
                                 'random', 'collections', 'itertools', 'functools']:
                    requirements.add(module)
        
        # Map common imports to package names
        package_map = {
            'pytest': 'pytest>=7.0.0',
            'numpy': 'numpy>=1.24.0',
            'pandas': 'pandas>=2.0.0',
            'requests': 'requests>=2.31.0',
            'flask': 'Flask>=3.0.0',
            'fastapi': 'fastapi>=0.104.0',
            'django': 'Django>=4.2.0',
            'matplotlib': 'matplotlib>=3.7.0',
            'scipy': 'scipy>=1.10.0',
            'sklearn': 'scikit-learn>=1.3.0',
            'tensorflow': 'tensorflow>=2.13.0',
            'torch': 'torch>=2.0.0',
            'aiohttp': 'aiohttp>=3.8.0',
            'sqlalchemy': 'SQLAlchemy>=2.0.0',
        }
        
        req_lines = []
        for req in sorted(requirements):
            if req in package_map:
                req_lines.append(package_map[req])
        
        return '\n'.join(req_lines) if req_lines else "# No external dependencies detected\n"
    
    def _generate_setup_py(self, capsule: QLCapsule, analysis: Dict[str, Any]) -> str:
        """Generate setup.py for Python libraries"""
        project_name = capsule.manifest.get('name', 'project').lower().replace(' ', '_')
        
        return f'''"""Setup configuration for {project_name}"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="{project_name}",
    version="0.1.0",
    author="Quantum Layer Platform",
    description="{capsule.manifest.get('description', '')}",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/{project_name}",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
    install_requires=[
        # Dependencies will be added here
    ],
)
'''
    
    def _get_default_analysis(self, capsule: QLCapsule) -> Dict[str, Any]:
        """Fallback analysis when LLM fails"""
        language = capsule.manifest.get('language', 'python').lower()
        
        # Simple heuristic-based analysis
        has_tests = bool(capsule.tests)
        file_count = len(capsule.source_code)
        
        if file_count == 1:
            project_type = "script"
        elif has_tests:
            project_type = "library"
        else:
            project_type = "utility"
        
        return {
            "project_type": project_type,
            "folder_structure": {
                "src": "Source code",
                "tests": "Test files",
                "docs": "Documentation"
            },
            "features": ["AI-generated code", "Test coverage" if has_tests else "Utility functions"],
            "recommendations": {
                "ci_cd": "basic",
                "testing": "pytest" if language == "python" else "jest"
            }
        }
    
    def _create_basic_structure(self, capsule: QLCapsule) -> Dict[str, str]:
        """Fallback basic structure organization"""
        organized = {}
        language = capsule.manifest.get('language', 'python').lower()
        
        # Organize source files
        for filename, content in capsule.source_code.items():
            if filename == "main.py" or filename == "index.js":
                organized[f"src/{filename}"] = self._clean_content(content)
            else:
                organized[f"src/{filename}"] = self._clean_content(content)
        
        # Organize test files
        for filename, content in capsule.tests.items():
            organized[f"tests/{filename}"] = self._clean_content(content)
        
        # Always generate a proper README instead of using capsule.documentation
        # which might contain code instead of documentation
        organized["README.md"] = self._generate_readme(capsule, self._get_default_analysis(capsule))
        
        # Add basic config files
        organized[".gitignore"] = self._generate_enhanced_gitignore(language)
        organized[".github/workflows/ci.yml"] = self._generate_enhanced_ci(language, "library")
        
        if language == "python":
            organized["requirements.txt"] = self._extract_requirements(capsule)
        
        return organized
    
    def _get_template_generators(self) -> List[str]:
        """Get list of available template names"""
        return [
            "requirements.txt",
            "setup.py",
            "Makefile",
            "Dockerfile",
            "docker-compose.yml",
            ".pre-commit-config.yaml",
            "pyproject.toml",
            "package.json",
            "tsconfig.json",
            ".eslintrc.json",
            "jest.config.js"
        ]
    
    def _generate_from_template(
        self,
        template_name: str,
        capsule: QLCapsule,
        analysis: Dict[str, Any]
    ) -> str:
        """Generate content from template name"""
        # This could be expanded to generate various template files
        # For now, return a placeholder
        return f"# Generated {template_name} for {capsule.manifest.get('name', 'project')}\n"
    
    def _generate_github_actions(self, capsule: QLCapsule) -> str:
        """Override parent method to always use intelligent CI/CD generation"""
        # Block the parent's method to ensure we use intelligent CI/CD
        # This method is called by the parent during push_capsule_atomic
        # By overriding it, we ensure the parent doesn't create a basic CI/CD
        # The intelligent CI/CD is already added in _create_intelligent_structure
        
        # Check if we already have an intelligent CI/CD in the capsule
        if ".github/workflows/ci.yml" in capsule.source_code:
            # Return the existing intelligent CI/CD
            return capsule.source_code[".github/workflows/ci.yml"]
        
        # Otherwise, generate a basic one (this shouldn't happen if intelligent structure is used)
        return super()._generate_github_actions(capsule)