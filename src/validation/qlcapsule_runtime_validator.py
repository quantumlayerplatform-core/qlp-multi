#!/usr/bin/env python3
"""
QLC Capsule Runtime Validation System
Dynamic deployment validation in language-specific Docker containers
"""

import asyncio
import docker
import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import yaml

import structlog
from pydantic import BaseModel, Field

from src.common.models import QLCapsule, ValidationReport, ValidationCheck, ValidationStatus

logger = structlog.get_logger()


class SupportedLanguage(str, Enum):
    """Languages supported by runtime validation"""
    PYTHON = "python"
    NODEJS = "nodejs"
    GOLANG = "go"
    JAVA = "java"
    TERRAFORM = "terraform"
    RUST = "rust"
    RUBY = "ruby"
    PHP = "php"
    CSHARP = "csharp"
    UNKNOWN = "unknown"


@dataclass
class RuntimeEnvironment:
    """Runtime environment configuration"""
    language: SupportedLanguage
    docker_image: str
    install_command: str
    run_command: str
    test_command: Optional[str] = None
    entry_point: str = "main"
    timeout: int = 300  # 5 minutes default


@dataclass
class RuntimeValidationResult:
    """Runtime validation result"""
    language: SupportedLanguage
    success: bool
    confidence_score: float
    execution_time: float
    memory_usage: int
    exit_code: int
    stdout: str
    stderr: str
    install_success: bool
    runtime_success: bool
    test_success: bool
    issues: List[str]
    recommendations: List[str]
    metrics: Dict[str, Any]


class CapsuleMetadata(BaseModel):
    """Capsule metadata schema"""
    name: str
    version: str = "1.0.0"
    language: str
    description: Optional[str] = None
    author: Optional[str] = None
    dependencies: Optional[List[str]] = []
    entry_point: str = "main"
    install_command: Optional[str] = None
    run_command: Optional[str] = None
    test_command: Optional[str] = None
    environment: Optional[Dict[str, str]] = {}
    ports: Optional[List[int]] = []
    volumes: Optional[List[str]] = []
    health_check: Optional[str] = None
    resource_limits: Optional[Dict[str, str]] = {}


class LanguageDetector:
    """Universal language detection for capsules"""
    
    @staticmethod
    def detect_language(capsule: QLCapsule) -> SupportedLanguage:
        """Detect primary language from capsule contents"""
        
        # Check manifest first
        if capsule.manifest and "language" in capsule.manifest:
            lang = capsule.manifest["language"].lower()
            try:
                return SupportedLanguage(lang)
            except ValueError:
                pass
        
        # Check file extensions
        file_extensions = {
            '.py': SupportedLanguage.PYTHON,
            '.js': SupportedLanguage.NODEJS,
            '.ts': SupportedLanguage.NODEJS,
            '.go': SupportedLanguage.GOLANG,
            '.java': SupportedLanguage.JAVA,
            '.tf': SupportedLanguage.TERRAFORM,
            '.rs': SupportedLanguage.RUST,
            '.rb': SupportedLanguage.RUBY,
            '.php': SupportedLanguage.PHP,
            '.cs': SupportedLanguage.CSHARP,
        }
        
        ext_counts = {}
        for file_path in capsule.source_code.keys():
            ext = Path(file_path).suffix.lower()
            if ext in file_extensions:
                lang = file_extensions[ext]
                ext_counts[lang] = ext_counts.get(lang, 0) + 1
        
        if ext_counts:
            # Return most common language
            return max(ext_counts, key=ext_counts.get)
        
        # Check for specific files
        files = list(capsule.source_code.keys())
        if any(f in files for f in ['package.json', 'yarn.lock', 'npm-shrinkwrap.json']):
            return SupportedLanguage.NODEJS
        elif any(f in files for f in ['go.mod', 'go.sum']):
            return SupportedLanguage.GOLANG
        elif any(f in files for f in ['pom.xml', 'build.gradle']):
            return SupportedLanguage.JAVA
        elif any(f in files for f in ['requirements.txt', 'setup.py', 'pyproject.toml']):
            return SupportedLanguage.PYTHON
        elif any(f in files for f in ['Cargo.toml', 'Cargo.lock']):
            return SupportedLanguage.RUST
        elif any(f in files for f in ['Gemfile', 'Gemfile.lock']):
            return SupportedLanguage.RUBY
        elif any(f in files for f in ['composer.json', 'composer.lock']):
            return SupportedLanguage.PHP
        elif any(f in files for f in ['*.csproj', '*.sln']):
            return SupportedLanguage.CSHARP
        
        return SupportedLanguage.UNKNOWN


class RuntimeEnvironmentManager:
    """Manages runtime environments for different languages"""
    
    def __init__(self):
        self.environments = self._initialize_environments()
    
    def _initialize_environments(self) -> Dict[SupportedLanguage, RuntimeEnvironment]:
        """Initialize runtime environments for each language"""
        return {
            SupportedLanguage.PYTHON: RuntimeEnvironment(
                language=SupportedLanguage.PYTHON,
                docker_image="python:3.11-slim",
                install_command="pip install -r requirements.txt",
                run_command="python main.py",
                test_command="python -m pytest tests/",
                entry_point="main.py"
            ),
            SupportedLanguage.NODEJS: RuntimeEnvironment(
                language=SupportedLanguage.NODEJS,
                docker_image="node:20-alpine",
                install_command="npm install",
                run_command="npm start",
                test_command="npm test",
                entry_point="index.js"
            ),
            SupportedLanguage.GOLANG: RuntimeEnvironment(
                language=SupportedLanguage.GOLANG,
                docker_image="golang:1.21-alpine",
                install_command="go mod download",
                run_command="go run .",
                test_command="go test ./...",
                entry_point="main.go"
            ),
            SupportedLanguage.JAVA: RuntimeEnvironment(
                language=SupportedLanguage.JAVA,
                docker_image="openjdk:17-slim",
                install_command="./mvnw install",
                run_command="java -jar target/*.jar",
                test_command="./mvnw test",
                entry_point="src/main/java/Main.java"
            ),
            SupportedLanguage.TERRAFORM: RuntimeEnvironment(
                language=SupportedLanguage.TERRAFORM,
                docker_image="hashicorp/terraform:latest",
                install_command="terraform init",
                run_command="terraform plan",
                test_command="terraform validate",
                entry_point="main.tf"
            ),
            SupportedLanguage.RUST: RuntimeEnvironment(
                language=SupportedLanguage.RUST,
                docker_image="rust:1.70-slim",
                install_command="cargo build",
                run_command="cargo run",
                test_command="cargo test",
                entry_point="src/main.rs"
            ),
            SupportedLanguage.RUBY: RuntimeEnvironment(
                language=SupportedLanguage.RUBY,
                docker_image="ruby:3.2-alpine",
                install_command="bundle install",
                run_command="ruby main.rb",
                test_command="rspec",
                entry_point="main.rb"
            ),
            SupportedLanguage.PHP: RuntimeEnvironment(
                language=SupportedLanguage.PHP,
                docker_image="php:8.2-cli",
                install_command="composer install",
                run_command="php main.php",
                test_command="./vendor/bin/phpunit",
                entry_point="main.php"
            ),
            SupportedLanguage.CSHARP: RuntimeEnvironment(
                language=SupportedLanguage.CSHARP,
                docker_image="mcr.microsoft.com/dotnet/sdk:7.0",
                install_command="dotnet restore",
                run_command="dotnet run",
                test_command="dotnet test",
                entry_point="Program.cs"
            )
        }
    
    def get_environment(self, language: SupportedLanguage) -> RuntimeEnvironment:
        """Get runtime environment for language"""
        return self.environments.get(language, self.environments[SupportedLanguage.PYTHON])


class DockerCapsuleRunner:
    """Runs capsules in Docker containers"""
    
    def __init__(self, docker_client: Optional[docker.DockerClient] = None):
        self.docker_client = docker_client or docker.from_env()
        self.env_manager = RuntimeEnvironmentManager()
    
    async def run_capsule(self, capsule: QLCapsule, language: SupportedLanguage) -> RuntimeValidationResult:
        """Run capsule in language-specific container"""
        start_time = time.time()
        
        try:
            # Get runtime environment
            env = self.env_manager.get_environment(language)
            
            # Create temporary directory for capsule
            with tempfile.TemporaryDirectory() as temp_dir:
                capsule_path = Path(temp_dir) / "capsule"
                capsule_path.mkdir(exist_ok=True)
                
                # Write capsule files
                await self._write_capsule_files(capsule, capsule_path)
                
                # Create capsule.yaml if not exists
                if not (capsule_path / "capsule.yaml").exists():
                    await self._create_capsule_metadata(capsule, capsule_path, language)
                
                # Pull Docker image
                await self._pull_docker_image(env.docker_image)
                
                # Run installation
                install_result = await self._run_install(capsule_path, env)
                
                # Run capsule
                run_result = await self._run_capsule_exec(capsule_path, env)
                
                # Run tests if available
                test_result = await self._run_tests(capsule_path, env)
                
                # Calculate metrics
                execution_time = time.time() - start_time
                confidence_score = self._calculate_confidence(install_result, run_result, test_result)
                
                return RuntimeValidationResult(
                    language=language,
                    success=install_result.success and run_result.success,
                    confidence_score=confidence_score,
                    execution_time=execution_time,
                    memory_usage=run_result.memory_usage,
                    exit_code=run_result.exit_code,
                    stdout=run_result.stdout,
                    stderr=run_result.stderr,
                    install_success=install_result.success,
                    runtime_success=run_result.success,
                    test_success=test_result.success if test_result else True,
                    issues=self._collect_issues(install_result, run_result, test_result),
                    recommendations=self._generate_recommendations(install_result, run_result, test_result),
                    metrics={
                        "install_time": install_result.execution_time,
                        "run_time": run_result.execution_time,
                        "test_time": test_result.execution_time if test_result else 0,
                        "docker_image": env.docker_image,
                        "language": language.value
                    }
                )
                
        except Exception as e:
            logger.error(f"Capsule execution failed: {e}")
            return RuntimeValidationResult(
                language=language,
                success=False,
                confidence_score=0.0,
                execution_time=time.time() - start_time,
                memory_usage=0,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                install_success=False,
                runtime_success=False,
                test_success=False,
                issues=[f"Execution failed: {str(e)}"],
                recommendations=["Check capsule structure and dependencies"],
                metrics={}
            )
    
    async def _write_capsule_files(self, capsule: QLCapsule, capsule_path: Path):
        """Write capsule files to temporary directory"""
        for file_path, content in capsule.source_code.items():
            full_path = capsule_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
    
    async def _create_capsule_metadata(self, capsule: QLCapsule, capsule_path: Path, language: SupportedLanguage):
        """Create capsule.yaml metadata file"""
        metadata = CapsuleMetadata(
            name=capsule.title or "unnamed-capsule",
            language=language.value,
            description=capsule.description,
            version="1.0.0"
        )
        
        yaml_content = yaml.dump(asdict(metadata), default_flow_style=False)
        (capsule_path / "capsule.yaml").write_text(yaml_content)
    
    async def _pull_docker_image(self, image: str):
        """Pull Docker image if not present"""
        try:
            self.docker_client.images.get(image)
        except docker.errors.ImageNotFound:
            logger.info(f"Pulling Docker image: {image}")
            self.docker_client.images.pull(image)
    
    async def _run_install(self, capsule_path: Path, env: RuntimeEnvironment) -> 'ExecutionResult':
        """Run installation command"""
        return await self._run_docker_command(
            capsule_path,
            env.docker_image,
            env.install_command,
            "install"
        )
    
    async def _run_capsule_exec(self, capsule_path: Path, env: RuntimeEnvironment) -> 'ExecutionResult':
        """Run capsule execution command"""
        return await self._run_docker_command(
            capsule_path,
            env.docker_image,
            env.run_command,
            "run"
        )
    
    async def _run_tests(self, capsule_path: Path, env: RuntimeEnvironment) -> Optional['ExecutionResult']:
        """Run tests if test command is available"""
        if not env.test_command:
            return None
        
        return await self._run_docker_command(
            capsule_path,
            env.docker_image,
            env.test_command,
            "test"
        )
    
    async def _run_docker_command(self, capsule_path: Path, image: str, command: str, stage: str) -> 'ExecutionResult':
        """Run command in Docker container"""
        start_time = time.time()
        
        try:
            # Run container
            container = self.docker_client.containers.run(
                image,
                command,
                volumes={str(capsule_path): {'bind': '/workspace', 'mode': 'rw'}},
                working_dir='/workspace',
                detach=True,
                remove=True,
                mem_limit='512m',
                cpu_count=1
            )
            
            # Wait for completion
            result = container.wait()
            exit_code = result['StatusCode']
            
            # Get output
            stdout = container.logs(stdout=True, stderr=False).decode('utf-8')
            stderr = container.logs(stdout=False, stderr=True).decode('utf-8')
            
            # Get stats
            stats = container.stats(stream=False)
            memory_usage = stats['memory_stats'].get('usage', 0) // (1024 * 1024)  # MB
            
            execution_time = time.time() - start_time
            success = exit_code == 0
            
            return ExecutionResult(
                success=success,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                execution_time=execution_time,
                memory_usage=memory_usage,
                stage=stage
            )
            
        except Exception as e:
            logger.error(f"Docker execution failed in {stage}: {e}")
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                execution_time=time.time() - start_time,
                memory_usage=0,
                stage=stage
            )
    
    def _calculate_confidence(self, install_result: 'ExecutionResult', run_result: 'ExecutionResult', test_result: Optional['ExecutionResult']) -> float:
        """Calculate confidence score based on results"""
        base_score = 0.0
        
        # Install success (30%)
        if install_result.success:
            base_score += 0.3
        
        # Runtime success (40%)
        if run_result.success:
            base_score += 0.4
        
        # Test success (30%)
        if test_result is None:
            base_score += 0.15  # Partial score if no tests
        elif test_result.success:
            base_score += 0.3
        
        # Penalty for errors
        if install_result.stderr or run_result.stderr:
            base_score -= 0.1
        
        # Bonus for clean execution
        if install_result.success and run_result.success and not (install_result.stderr or run_result.stderr):
            base_score += 0.1
        
        return max(0.0, min(1.0, base_score))
    
    def _collect_issues(self, install_result: 'ExecutionResult', run_result: 'ExecutionResult', test_result: Optional['ExecutionResult']) -> List[str]:
        """Collect issues from execution results"""
        issues = []
        
        if not install_result.success:
            issues.append(f"Installation failed: {install_result.stderr[:200]}")
        
        if not run_result.success:
            issues.append(f"Runtime execution failed: {run_result.stderr[:200]}")
        
        if test_result and not test_result.success:
            issues.append(f"Tests failed: {test_result.stderr[:200]}")
        
        return issues
    
    def _generate_recommendations(self, install_result: 'ExecutionResult', run_result: 'ExecutionResult', test_result: Optional['ExecutionResult']) -> List[str]:
        """Generate recommendations based on results"""
        recommendations = []
        
        if not install_result.success:
            recommendations.append("Check dependency requirements and installation commands")
        
        if not run_result.success:
            recommendations.append("Verify entry point and runtime configuration")
        
        if test_result and not test_result.success:
            recommendations.append("Fix failing tests and improve test coverage")
        
        if install_result.execution_time > 60:
            recommendations.append("Optimize installation process for faster deployment")
        
        return recommendations


@dataclass
class ExecutionResult:
    """Result of a single execution step"""
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    memory_usage: int
    stage: str


class QLCapsuleRuntimeValidator:
    """Main runtime validation orchestrator"""
    
    def __init__(self, docker_client: Optional[docker.DockerClient] = None):
        self.docker_runner = DockerCapsuleRunner(docker_client)
        self.language_detector = LanguageDetector()
    
    async def validate_capsule_runtime(self, capsule: QLCapsule) -> RuntimeValidationResult:
        """Validate capsule by running it in appropriate container"""
        
        # Detect language
        language = self.language_detector.detect_language(capsule)
        
        logger.info(f"Detected language: {language.value}", capsule_id=capsule.id)
        
        # Run in container
        result = await self.docker_runner.run_capsule(capsule, language)
        
        logger.info(
            f"Runtime validation complete",
            capsule_id=capsule.id,
            language=language.value,
            success=result.success,
            confidence=result.confidence_score
        )
        
        return result
    
    async def validate_multiple_capsules(self, capsules: List[QLCapsule]) -> List[RuntimeValidationResult]:
        """Validate multiple capsules concurrently"""
        tasks = [self.validate_capsule_runtime(capsule) for capsule in capsules]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    def should_escalate_to_human(self, result: RuntimeValidationResult) -> bool:
        """Determine if result requires human review"""
        return (
            result.confidence_score < 0.7 or
            not result.success or
            len(result.issues) > 3 or
            result.execution_time > 180  # 3 minutes
        )


# Example usage
if __name__ == "__main__":
    async def main():
        # Create example capsule
        capsule = QLCapsule(
            id="test-capsule",
            title="Test Python Capsule",
            description="A simple test capsule",
            source_code={
                "main.py": """
print("Hello, World!")
def add(a, b):
    return a + b

if __name__ == "__main__":
    result = add(2, 3)
    print(f"2 + 3 = {result}")
""",
                "requirements.txt": "# No external dependencies\n",
                "test_main.py": """
def test_add():
    from main import add
    assert add(2, 3) == 5
    assert add(0, 0) == 0
    assert add(-1, 1) == 0
"""
            },
            manifest={"language": "python", "version": "1.0.0"},
            documentation="A simple calculator capsule",
            tests={"test_main.py": "def test_add():\n    assert True"}
        )
        
        # Run validation
        validator = QLCapsuleRuntimeValidator()
        result = await validator.validate_capsule_runtime(capsule)
        
        print(f"Validation Result:")
        print(f"  Success: {result.success}")
        print(f"  Confidence: {result.confidence_score:.2f}")
        print(f"  Language: {result.language}")
        print(f"  Execution Time: {result.execution_time:.2f}s")
        print(f"  Issues: {result.issues}")
        print(f"  Recommendations: {result.recommendations}")
        
        # Check if human review needed
        if validator.should_escalate_to_human(result):
            print("🚨 Human review required!")
        else:
            print("✅ Capsule validated successfully!")
    
    asyncio.run(main())