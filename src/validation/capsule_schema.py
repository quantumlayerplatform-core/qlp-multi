#!/usr/bin/env python3
"""
QLC Capsule Schema Definition and Validation
Defines the capsule.yaml schema and validates capsule structure
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum
import yaml
import json
from pathlib import Path
import structlog

logger = structlog.get_logger()


class CapsuleLanguage(str, Enum):
    """Supported capsule languages"""
    PYTHON = "python"
    NODEJS = "nodejs"
    GOLANG = "go"
    JAVA = "java"
    TERRAFORM = "terraform"
    RUST = "rust"
    RUBY = "ruby"
    PHP = "php"
    CSHARP = "csharp"
    SHELL = "shell"
    DOCKER = "docker"


class CapsuleType(str, Enum):
    """Types of capsules"""
    APPLICATION = "application"
    LIBRARY = "library"
    SERVICE = "service"
    TOOL = "tool"
    INFRASTRUCTURE = "infrastructure"
    DATA_PIPELINE = "data_pipeline"
    ML_MODEL = "ml_model"
    API = "api"
    FRONTEND = "frontend"
    MICROSERVICE = "microservice"


class HealthCheckType(str, Enum):
    """Health check types"""
    HTTP = "http"
    TCP = "tcp"
    EXEC = "exec"
    GRPC = "grpc"


class ResourceLimits(BaseModel):
    """Resource limits for capsule execution"""
    memory: Optional[str] = Field(None, description="Memory limit (e.g., '512Mi', '1Gi')")
    cpu: Optional[str] = Field(None, description="CPU limit (e.g., '500m', '1')")
    storage: Optional[str] = Field(None, description="Storage limit (e.g., '1Gi', '10Gi')")
    
    @validator('memory', 'cpu', 'storage')
    def validate_resource_format(cls, v):
        if v is None:
            return v
        # Basic validation for Kubernetes resource format
        if not any(v.endswith(suffix) for suffix in ['m', 'Mi', 'Gi', 'Ti', 'Ki']):
            if not v.isdigit():
                raise ValueError(f"Invalid resource format: {v}")
        return v


class HealthCheck(BaseModel):
    """Health check configuration"""
    type: HealthCheckType
    endpoint: Optional[str] = Field(None, description="HTTP endpoint or TCP port")
    command: Optional[List[str]] = Field(None, description="Command to execute for exec checks")
    interval: Optional[int] = Field(30, description="Check interval in seconds")
    timeout: Optional[int] = Field(5, description="Timeout in seconds")
    retries: Optional[int] = Field(3, description="Number of retries")
    initial_delay: Optional[int] = Field(0, description="Initial delay in seconds")
    
    @validator('endpoint')
    def validate_endpoint(cls, v, values):
        if values.get('type') in [HealthCheckType.HTTP, HealthCheckType.TCP] and not v:
            raise ValueError(f"Endpoint required for {values.get('type')} health checks")
        return v
    
    @validator('command')
    def validate_command(cls, v, values):
        if values.get('type') == HealthCheckType.EXEC and not v:
            raise ValueError("Command required for exec health checks")
        return v


class Port(BaseModel):
    """Port configuration"""
    port: int = Field(..., ge=1, le=65535, description="Port number")
    protocol: str = Field("TCP", description="Protocol (TCP/UDP)")
    name: Optional[str] = Field(None, description="Port name")
    
    @validator('protocol')
    def validate_protocol(cls, v):
        if v.upper() not in ['TCP', 'UDP']:
            raise ValueError("Protocol must be TCP or UDP")
        return v.upper()


class VolumeMount(BaseModel):
    """Volume mount configuration"""
    name: str = Field(..., description="Volume name")
    mount_path: str = Field(..., description="Mount path in container")
    read_only: bool = Field(False, description="Read-only mount")
    sub_path: Optional[str] = Field(None, description="Sub-path within volume")


class EnvironmentVariable(BaseModel):
    """Environment variable configuration"""
    name: str = Field(..., description="Variable name")
    value: Optional[str] = Field(None, description="Variable value")
    secret: Optional[str] = Field(None, description="Secret reference")
    config_map: Optional[str] = Field(None, description="ConfigMap reference")
    
    @validator('value')
    def validate_value_or_reference(cls, v, values):
        if not v and not values.get('secret') and not values.get('config_map'):
            raise ValueError("Must specify value, secret, or config_map reference")
        return v


class Dependencies(BaseModel):
    """Dependency configuration"""
    runtime: List[str] = Field(default_factory=list, description="Runtime dependencies")
    build: List[str] = Field(default_factory=list, description="Build-time dependencies")
    system: List[str] = Field(default_factory=list, description="System packages")
    services: List[str] = Field(default_factory=list, description="Required services")


class Commands(BaseModel):
    """Command configuration"""
    install: Optional[str] = Field(None, description="Installation command")
    build: Optional[str] = Field(None, description="Build command")
    start: Optional[str] = Field(None, description="Start command")
    test: Optional[str] = Field(None, description="Test command")
    lint: Optional[str] = Field(None, description="Linting command")
    format: Optional[str] = Field(None, description="Code formatting command")
    dev: Optional[str] = Field(None, description="Development command")
    migrate: Optional[str] = Field(None, description="Migration command")
    seed: Optional[str] = Field(None, description="Seed data command")


class Metadata(BaseModel):
    """Capsule metadata"""
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    category: Optional[str] = Field(None, description="Capsule category")
    license: Optional[str] = Field(None, description="License type")
    repository: Optional[str] = Field(None, description="Source repository URL")
    documentation: Optional[str] = Field(None, description="Documentation URL")
    maintainer: Optional[str] = Field(None, description="Maintainer contact")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


class CapsuleManifest(BaseModel):
    """
    Complete capsule.yaml manifest schema
    Defines the structure and configuration of a QLC capsule
    """
    
    # Required fields
    name: str = Field(..., description="Capsule name")
    version: str = Field(..., description="Capsule version (semver)")
    language: CapsuleLanguage = Field(..., description="Primary programming language")
    type: CapsuleType = Field(..., description="Capsule type")
    description: str = Field(..., description="Capsule description")
    
    # Optional configuration
    author: Optional[str] = Field(None, description="Author name")
    homepage: Optional[str] = Field(None, description="Homepage URL")
    
    # Entry points
    entry_point: str = Field("main", description="Main entry point file")
    entry_points: Optional[Dict[str, str]] = Field(None, description="Multiple entry points")
    
    # Commands
    commands: Optional[Commands] = Field(None, description="Lifecycle commands")
    
    # Dependencies
    dependencies: Optional[Dependencies] = Field(None, description="Dependencies")
    
    # Runtime configuration
    environment: List[EnvironmentVariable] = Field(default_factory=list, description="Environment variables")
    ports: List[Port] = Field(default_factory=list, description="Exposed ports")
    volumes: List[VolumeMount] = Field(default_factory=list, description="Volume mounts")
    
    # Resource management
    resources: Optional[ResourceLimits] = Field(None, description="Resource limits")
    
    # Health checks
    health_check: Optional[HealthCheck] = Field(None, description="Health check configuration")
    
    # Deployment
    replicas: Optional[int] = Field(1, ge=1, description="Number of replicas")
    restart_policy: Optional[str] = Field("Always", description="Restart policy")
    
    # Metadata
    metadata: Optional[Metadata] = Field(None, description="Additional metadata")
    
    # Custom fields
    custom: Optional[Dict[str, Any]] = Field(None, description="Custom configuration")
    
    # Validation
    @validator('version')
    def validate_semver(cls, v):
        """Validate semantic version format"""
        import re
        semver_pattern = r'^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$'
        if not re.match(semver_pattern, v):
            raise ValueError(f"Invalid semantic version format: {v}")
        return v
    
    @validator('name')
    def validate_name(cls, v):
        """Validate capsule name format"""
        import re
        if not re.match(r'^[a-z0-9-_]+$', v):
            raise ValueError("Name must contain only lowercase letters, numbers, hyphens, and underscores")
        return v
    
    @validator('restart_policy')
    def validate_restart_policy(cls, v):
        """Validate restart policy"""
        if v not in ['Always', 'OnFailure', 'Never']:
            raise ValueError("Restart policy must be 'Always', 'OnFailure', or 'Never'")
        return v
    
    class Config:
        use_enum_values = True


class CapsuleValidator:
    """Validates capsule structure and manifest"""
    
    def __init__(self):
        self.required_files = {
            CapsuleLanguage.PYTHON: ['main.py', 'requirements.txt'],
            CapsuleLanguage.NODEJS: ['package.json', 'index.js'],
            CapsuleLanguage.GOLANG: ['main.go', 'go.mod'],
            CapsuleLanguage.JAVA: ['pom.xml', 'src/main/java/Main.java'],
            CapsuleLanguage.TERRAFORM: ['main.tf'],
            CapsuleLanguage.RUST: ['Cargo.toml', 'src/main.rs'],
            CapsuleLanguage.RUBY: ['Gemfile', 'main.rb'],
            CapsuleLanguage.PHP: ['composer.json', 'main.php'],
            CapsuleLanguage.CSHARP: ['Program.cs', '*.csproj'],
            CapsuleLanguage.SHELL: ['main.sh'],
            CapsuleLanguage.DOCKER: ['Dockerfile']
        }
    
    def validate_manifest(self, manifest_content: str) -> tuple[bool, CapsuleManifest, List[str]]:
        """
        Validate capsule manifest content
        
        Returns:
            (is_valid, manifest_object, errors)
        """
        errors = []
        
        try:
            # Parse YAML
            manifest_data = yaml.safe_load(manifest_content)
            
            # Validate against schema
            manifest = CapsuleManifest(**manifest_data)
            
            return True, manifest, errors
            
        except yaml.YAMLError as e:
            errors.append(f"YAML parsing error: {str(e)}")
            return False, None, errors
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
            return False, None, errors
    
    def validate_capsule_structure(self, source_code: Dict[str, str], manifest: CapsuleManifest) -> tuple[bool, List[str]]:
        """
        Validate capsule file structure
        
        Returns:
            (is_valid, errors)
        """
        errors = []
        
        # Check required files for language
        required_files = self.required_files.get(manifest.language, [])
        
        for required_file in required_files:
            if required_file not in source_code:
                # Check for wildcard patterns
                if '*' in required_file:
                    pattern = required_file.replace('*', '')
                    if not any(pattern in filename for filename in source_code.keys()):
                        errors.append(f"Missing required file pattern: {required_file}")
                else:
                    errors.append(f"Missing required file: {required_file}")
        
        # Check entry point exists
        if manifest.entry_point and manifest.entry_point not in source_code:
            errors.append(f"Entry point file not found: {manifest.entry_point}")
        
        # Validate additional entry points
        if manifest.entry_points:
            for name, path in manifest.entry_points.items():
                if path not in source_code:
                    errors.append(f"Entry point '{name}' file not found: {path}")
        
        # Check for common anti-patterns
        for filename, content in source_code.items():
            if filename.endswith('.py'):
                # Check for hardcoded secrets
                if any(secret in content.lower() for secret in ['api_key', 'password', 'secret', 'token']):
                    if '=' in content and '"' in content:
                        errors.append(f"Potential hardcoded secrets in {filename}")
            
            # Check for executable permissions needed
            if filename.endswith('.sh') and not content.startswith('#!/'):
                errors.append(f"Shell script {filename} missing shebang")
        
        return len(errors) == 0, errors
    
    def validate_commands(self, manifest: CapsuleManifest, source_code: Dict[str, str]) -> tuple[bool, List[str]]:
        """Validate command configuration"""
        errors = []
        
        if not manifest.commands:
            return True, []
        
        # Check if commands reference existing files
        commands_dict = manifest.commands.dict()
        
        for cmd_name, cmd_value in commands_dict.items():
            if cmd_value:
                # Extract potential file references
                words = cmd_value.split()
                for word in words:
                    if '.' in word and word in source_code:
                        continue  # File exists
                    elif word.startswith('./') or word.startswith('../'):
                        # Relative path reference
                        clean_path = word.replace('./', '').replace('../', '')
                        if clean_path and clean_path not in source_code:
                            errors.append(f"Command '{cmd_name}' references missing file: {word}")
        
        return len(errors) == 0, errors
    
    def generate_manifest_template(self, language: CapsuleLanguage, capsule_name: str) -> str:
        """Generate a template manifest for a given language"""
        
        template = CapsuleManifest(
            name=capsule_name,
            version="1.0.0",
            language=language,
            type=CapsuleType.APPLICATION,
            description=f"A {language.value} capsule",
            author="QLP Generator",
            entry_point=self._get_default_entry_point(language),
            commands=self._get_default_commands(language),
            dependencies=self._get_default_dependencies(language),
            ports=[Port(port=8080, protocol="TCP", name="http")] if language in [CapsuleLanguage.NODEJS, CapsuleLanguage.PYTHON] else [],
            resources=ResourceLimits(memory="512Mi", cpu="500m"),
            health_check=HealthCheck(
                type=HealthCheckType.HTTP,
                endpoint="/health",
                interval=30,
                timeout=5,
                retries=3
            ) if language in [CapsuleLanguage.NODEJS, CapsuleLanguage.PYTHON] else None,
            metadata=Metadata(
                tags=[language.value, "generated"],
                category="application",
                license="MIT"
            )
        )
        
        return yaml.dump(template.dict(), default_flow_style=False, sort_keys=False)
    
    def _get_default_entry_point(self, language: CapsuleLanguage) -> str:
        """Get default entry point for language"""
        entry_points = {
            CapsuleLanguage.PYTHON: "main.py",
            CapsuleLanguage.NODEJS: "index.js",
            CapsuleLanguage.GOLANG: "main.go",
            CapsuleLanguage.JAVA: "src/main/java/Main.java",
            CapsuleLanguage.TERRAFORM: "main.tf",
            CapsuleLanguage.RUST: "src/main.rs",
            CapsuleLanguage.RUBY: "main.rb",
            CapsuleLanguage.PHP: "main.php",
            CapsuleLanguage.CSHARP: "Program.cs",
            CapsuleLanguage.SHELL: "main.sh",
            CapsuleLanguage.DOCKER: "Dockerfile"
        }
        return entry_points.get(language, "main")
    
    def _get_default_commands(self, language: CapsuleLanguage) -> Commands:
        """Get default commands for language"""
        commands_map = {
            CapsuleLanguage.PYTHON: Commands(
                install="pip install -r requirements.txt",
                start="python main.py",
                test="python -m pytest",
                lint="flake8 .",
                format="black ."
            ),
            CapsuleLanguage.NODEJS: Commands(
                install="npm install",
                start="npm start",
                test="npm test",
                lint="npm run lint",
                format="npm run format",
                dev="npm run dev"
            ),
            CapsuleLanguage.GOLANG: Commands(
                install="go mod download",
                build="go build .",
                start="go run .",
                test="go test ./...",
                lint="golangci-lint run",
                format="go fmt ./..."
            ),
            CapsuleLanguage.JAVA: Commands(
                install="mvn install",
                build="mvn compile",
                start="java -jar target/*.jar",
                test="mvn test",
                lint="mvn checkstyle:check"
            ),
            CapsuleLanguage.TERRAFORM: Commands(
                install="terraform init",
                start="terraform apply",
                test="terraform validate",
                lint="terraform fmt -check"
            ),
            CapsuleLanguage.RUST: Commands(
                install="cargo build",
                start="cargo run",
                test="cargo test",
                lint="cargo clippy",
                format="cargo fmt"
            )
        }
        return commands_map.get(language, Commands())
    
    def _get_default_dependencies(self, language: CapsuleLanguage) -> Dependencies:
        """Get default dependencies structure for language"""
        return Dependencies(
            runtime=[],
            build=[],
            system=[],
            services=[]
        )


# Example usage and testing
if __name__ == "__main__":
    # Test manifest validation
    validator = CapsuleValidator()
    
    # Generate template
    template = validator.generate_manifest_template(CapsuleLanguage.PYTHON, "test-capsule")
    print("Generated template:")
    print(template)
    
    # Validate template
    is_valid, manifest, errors = validator.validate_manifest(template)
    print(f"\nTemplate validation: {'✅ Valid' if is_valid else '❌ Invalid'}")
    if errors:
        print(f"Errors: {errors}")
    
    # Test structure validation
    source_code = {
        "main.py": "print('Hello, World!')",
        "requirements.txt": "requests==2.28.0",
        "README.md": "# Test Capsule"
    }
    
    if manifest:
        struct_valid, struct_errors = validator.validate_capsule_structure(source_code, manifest)
        print(f"\nStructure validation: {'✅ Valid' if struct_valid else '❌ Invalid'}")
        if struct_errors:
            print(f"Structure errors: {struct_errors}")