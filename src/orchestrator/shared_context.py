"""
Shared Context System for Temporal Workflows
Provides intelligent context coordination across all agents and services
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json


class ArchitecturePattern(Enum):
    """Common architecture patterns"""
    MONOLITH = "monolith"
    MICROSERVICES = "microservices"
    SERVERLESS = "serverless"
    LAYERED = "layered"
    HEXAGONAL = "hexagonal"


class ProjectStructure(Enum):
    """Project structure types"""
    FLAT = "flat"
    FEATURE_BASED = "feature_based"
    DOMAIN_DRIVEN = "domain_driven"
    ENTERPRISE = "enterprise"


@dataclass
class FileStructureContext:
    """File structure and naming conventions"""
    primary_language: str
    main_file_name: str
    test_file_pattern: str
    module_naming: str
    directory_structure: Dict[str, str]
    import_patterns: List[str]
    
    @classmethod
    def from_language(cls, language: str) -> 'FileStructureContext':
        """Create file structure context from language"""
        language_configs = {
            "python": cls(
                primary_language="python",
                main_file_name="main.py",
                test_file_pattern="test_*.py",
                module_naming="snake_case",
                directory_structure={
                    "src": "source code",
                    "tests": "test files",
                    "docs": "documentation"
                },
                import_patterns=["from module import function", "import module"]
            ),
            "javascript": cls(
                primary_language="javascript",
                main_file_name="index.js",
                test_file_pattern="*.test.js",
                module_naming="camelCase",
                directory_structure={
                    "src": "source code",
                    "test": "test files",
                    "docs": "documentation"
                },
                import_patterns=["import { function } from 'module'", "const module = require('module')"]
            ),
            "typescript": cls(
                primary_language="typescript",
                main_file_name="index.ts",
                test_file_pattern="*.test.ts",
                module_naming="camelCase",
                directory_structure={
                    "src": "source code",
                    "test": "test files",
                    "docs": "documentation"
                },
                import_patterns=["import { function } from 'module'", "import * as module from 'module'"]
            ),
            "java": cls(
                primary_language="java",
                main_file_name="Main.java",
                test_file_pattern="*Test.java",
                module_naming="PascalCase",
                directory_structure={
                    "src/main/java": "source code",
                    "src/test/java": "test files",
                    "docs": "documentation"
                },
                import_patterns=["import package.Class", "import package.*"]
            ),
            "go": cls(
                primary_language="go",
                main_file_name="main.go",
                test_file_pattern="*_test.go",
                module_naming="snake_case",
                directory_structure={
                    "cmd": "entry points",
                    "pkg": "library code",
                    "internal": "private code"
                },
                import_patterns=["import \"package\"", "import \"package/subpackage\""]
            ),
            "rust": cls(
                primary_language="rust",
                main_file_name="main.rs",
                test_file_pattern="*_test.rs",
                module_naming="snake_case",
                directory_structure={
                    "src": "source code",
                    "tests": "integration tests",
                    "examples": "examples"
                },
                import_patterns=["use module::function", "use module::*"]
            )
        }
        
        return language_configs.get(language, language_configs["python"])


@dataclass
class DependencyContext:
    """Dependency and integration context"""
    dependency_graph: Dict[str, List[str]]
    shared_dependencies: List[str]
    integration_points: List[Dict[str, Any]]
    data_flow: Dict[str, List[str]]
    
    def add_dependency(self, task_id: str, depends_on: str):
        """Add dependency relationship"""
        if task_id not in self.dependency_graph:
            self.dependency_graph[task_id] = []
        self.dependency_graph[task_id].append(depends_on)
    
    def get_dependencies(self, task_id: str) -> List[str]:
        """Get dependencies for a task"""
        return self.dependency_graph.get(task_id, [])
    
    def get_execution_order(self) -> List[str]:
        """Get topological execution order"""
        # Simple topological sort
        visited = set()
        order = []
        
        def visit(node):
            if node in visited:
                return
            visited.add(node)
            for dep in self.dependency_graph.get(node, []):
                visit(dep)
            order.append(node)
        
        for node in self.dependency_graph:
            visit(node)
        
        return order[::-1]  # Reverse for correct order


@dataclass
class QualityContext:
    """Quality and validation context"""
    quality_standards: Dict[str, Any]
    validation_requirements: List[str]
    security_requirements: List[str]
    performance_requirements: Dict[str, Any]
    compliance_requirements: List[str]
    
    @classmethod
    def enterprise_standards(cls) -> 'QualityContext':
        """Create enterprise-grade quality context"""
        return cls(
            quality_standards={
                "code_coverage": 80,
                "complexity_threshold": 10,
                "duplication_threshold": 5,
                "documentation_required": True
            },
            validation_requirements=[
                "syntax_validation",
                "style_validation",
                "security_validation",
                "type_validation",
                "runtime_validation"
            ],
            security_requirements=[
                "no_hardcoded_secrets",
                "input_validation",
                "secure_communication",
                "access_control"
            ],
            performance_requirements={
                "response_time_ms": 200,
                "memory_usage_mb": 512,
                "cpu_usage_percent": 80
            },
            compliance_requirements=["GDPR", "SOC2", "ISO27001"]
        )


@dataclass
class SharedContext:
    """
    Shared context that flows through all Temporal activities
    Provides coordination and consistency across all agents
    
    Note: Uses only JSON-serializable types for Temporal compatibility
    """
    
    # Request identification
    request_id: str
    tenant_id: str
    user_id: str
    
    # Core requirements
    original_description: str
    processed_requirements: Dict[str, Any]
    constraints: Dict[str, Any]
    
    # Architecture decisions (using string values for Temporal compatibility)
    architecture_pattern: str  # ArchitecturePattern.value
    project_structure: str     # ProjectStructure.value
    file_structure: FileStructureContext
    
    # Dependency management
    dependency_context: DependencyContext
    
    # Quality standards
    quality_context: QualityContext
    
    # Execution context
    execution_metadata: Dict[str, Any] = field(default_factory=dict)
    agent_coordination: Dict[str, Any] = field(default_factory=dict)
    
    # Progress tracking
    completed_tasks: List[str] = field(default_factory=list)
    current_phase: str = "initialization"
    
    # Learning context
    patterns_used: List[str] = field(default_factory=list)
    insights_gained: List[str] = field(default_factory=list)
    
    # Timestamps (using ISO string format for Temporal compatibility)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def update_progress(self, task_id: str, phase: str, metadata: Dict[str, Any] = None):
        """Update progress and metadata"""
        self.completed_tasks.append(task_id)
        self.current_phase = phase
        self.updated_at = datetime.utcnow().isoformat()
        
        if metadata:
            self.execution_metadata.update(metadata)
    
    def add_pattern_usage(self, pattern: str):
        """Track pattern usage"""
        if pattern not in self.patterns_used:
            self.patterns_used.append(pattern)
    
    def add_insight(self, insight: str):
        """Add learning insight"""
        if insight not in self.insights_gained:
            self.insights_gained.append(insight)
    
    def get_context_for_task(self, task_id: str) -> Dict[str, Any]:
        """Get relevant context for a specific task"""
        return {
            "request_id": self.request_id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "original_description": self.original_description,
            "processed_requirements": self.processed_requirements,
            "constraints": self.constraints,
            "architecture_pattern": self.architecture_pattern,
            "project_structure": self.project_structure,
            "file_structure": {
                "primary_language": self.file_structure.primary_language,
                "main_file_name": self.file_structure.main_file_name,
                "test_file_pattern": self.file_structure.test_file_pattern,
                "module_naming": self.file_structure.module_naming,
                "directory_structure": self.file_structure.directory_structure,
                "import_patterns": self.file_structure.import_patterns
            },
            "dependencies": self.dependency_context.get_dependencies(task_id),
            "quality_standards": self.quality_context.quality_standards,
            "validation_requirements": self.quality_context.validation_requirements,
            "security_requirements": self.quality_context.security_requirements,
            "execution_metadata": self.execution_metadata,
            "completed_tasks": self.completed_tasks,
            "current_phase": self.current_phase,
            "patterns_used": self.patterns_used
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "request_id": self.request_id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "original_description": self.original_description,
            "processed_requirements": self.processed_requirements,
            "constraints": self.constraints,
            "architecture_pattern": self.architecture_pattern,
            "project_structure": self.project_structure,
            "file_structure": {
                "primary_language": self.file_structure.primary_language,
                "main_file_name": self.file_structure.main_file_name,
                "test_file_pattern": self.file_structure.test_file_pattern,
                "module_naming": self.file_structure.module_naming,
                "directory_structure": self.file_structure.directory_structure,
                "import_patterns": self.file_structure.import_patterns
            },
            "dependency_context": {
                "dependency_graph": self.dependency_context.dependency_graph,
                "shared_dependencies": self.dependency_context.shared_dependencies,
                "integration_points": self.dependency_context.integration_points,
                "data_flow": self.dependency_context.data_flow
            },
            "quality_context": {
                "quality_standards": self.quality_context.quality_standards,
                "validation_requirements": self.quality_context.validation_requirements,
                "security_requirements": self.quality_context.security_requirements,
                "performance_requirements": self.quality_context.performance_requirements,
                "compliance_requirements": self.quality_context.compliance_requirements
            },
            "execution_metadata": self.execution_metadata,
            "agent_coordination": self.agent_coordination,
            "completed_tasks": self.completed_tasks,
            "current_phase": self.current_phase,
            "patterns_used": self.patterns_used,
            "insights_gained": self.insights_gained,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SharedContext':
        """Create from dictionary (for JSON deserialization)"""
        file_structure_data = data["file_structure"]
        file_structure = FileStructureContext(
            primary_language=file_structure_data["primary_language"],
            main_file_name=file_structure_data["main_file_name"],
            test_file_pattern=file_structure_data["test_file_pattern"],
            module_naming=file_structure_data["module_naming"],
            directory_structure=file_structure_data["directory_structure"],
            import_patterns=file_structure_data["import_patterns"]
        )
        
        dependency_data = data["dependency_context"]
        dependency_context = DependencyContext(
            dependency_graph=dependency_data["dependency_graph"],
            shared_dependencies=dependency_data["shared_dependencies"],
            integration_points=dependency_data["integration_points"],
            data_flow=dependency_data["data_flow"]
        )
        
        quality_data = data["quality_context"]
        quality_context = QualityContext(
            quality_standards=quality_data["quality_standards"],
            validation_requirements=quality_data["validation_requirements"],
            security_requirements=quality_data["security_requirements"],
            performance_requirements=quality_data["performance_requirements"],
            compliance_requirements=quality_data["compliance_requirements"]
        )
        
        return cls(
            request_id=data["request_id"],
            tenant_id=data["tenant_id"],
            user_id=data["user_id"],
            original_description=data["original_description"],
            processed_requirements=data["processed_requirements"],
            constraints=data["constraints"],
            architecture_pattern=data["architecture_pattern"],
            project_structure=data["project_structure"],
            file_structure=file_structure,
            dependency_context=dependency_context,
            quality_context=quality_context,
            execution_metadata=data["execution_metadata"],
            agent_coordination=data["agent_coordination"],
            completed_tasks=data["completed_tasks"],
            current_phase=data["current_phase"],
            patterns_used=data["patterns_used"],
            insights_gained=data["insights_gained"],
            created_at=data["created_at"],
            updated_at=data["updated_at"]
        )


class ContextBuilder:
    """Builder for creating shared context from requests"""
    
    @staticmethod
    def create_from_request(
        request_id: str,
        tenant_id: str,
        user_id: str,
        description: str,
        requirements: Optional[str] = None,
        constraints: Optional[Dict[str, Any]] = None
    ) -> SharedContext:
        """Create shared context from initial request"""
        
        # Intelligent language detection from description
        language = ContextBuilder._detect_language(description, requirements)
        
        # Intelligent architecture pattern detection
        architecture = ContextBuilder._detect_architecture_pattern(description, requirements)
        
        # Intelligent project structure detection
        structure = ContextBuilder._detect_project_structure(description, requirements)
        
        # Create file structure context
        file_structure = FileStructureContext.from_language(language)
        
        # Create dependency context
        dependency_context = DependencyContext(
            dependency_graph={},
            shared_dependencies=[],
            integration_points=[],
            data_flow={}
        )
        
        # Create quality context
        quality_context = QualityContext.enterprise_standards()
        
        # Process requirements
        processed_requirements = ContextBuilder._process_requirements(
            description, requirements, constraints
        )
        
        return SharedContext(
            request_id=request_id,
            tenant_id=tenant_id,
            user_id=user_id,
            original_description=description,
            processed_requirements=processed_requirements,
            constraints=constraints or {},
            architecture_pattern=architecture.value,  # Use string value
            project_structure=structure.value,         # Use string value
            file_structure=file_structure,
            dependency_context=dependency_context,
            quality_context=quality_context
        )
    
    @staticmethod
    def _detect_language(description: str, requirements: Optional[str] = None) -> str:
        """Intelligently detect primary language from description"""
        text = f"{description} {requirements or ''}".lower()
        
        # Check for explicit TypeScript mentions first (higher priority)
        if "typescript" in text or " ts " in text:
            return "typescript"
        
        # Language detection patterns with weighted scoring
        language_patterns = {
            "python": ["python", "django", "flask", "fastapi", "pandas", "numpy", "pytest", "pip"],
            "javascript": ["javascript", "js", "node", "nodejs", "express", "npm", "yarn"],
            "typescript": ["typescript", "ts", "angular", "nest", "nestjs", "tsx", "type-safe", "@types"],
            "java": ["java", "spring", "hibernate", "maven", "gradle", "junit"],
            "go": ["go", "golang", "gin", "gorilla", "gopher"],
            "rust": ["rust", "cargo", "actix", "tokio", "crate"]
        }
        
        # Score each language with weighted patterns
        scores = {}
        for lang, patterns in language_patterns.items():
            score = 0
            for pattern in patterns:
                if pattern in text:
                    # Give higher weight to more specific patterns
                    weight = 2 if len(pattern) > 4 else 1
                    score += weight
            scores[lang] = score
        
        # Special handling for React/Vue/Angular which could be JS or TS
        if any(framework in text for framework in ["react", "vue"]):
            # If TypeScript indicators are present, prefer TypeScript
            if any(indicator in text for indicator in ["typescript", "ts", "tsx", "type", "@types"]):
                scores["typescript"] = scores.get("typescript", 0) + 3
            else:
                scores["javascript"] = scores.get("javascript", 0) + 2
        
        # Angular strongly suggests TypeScript
        if "angular" in text:
            scores["typescript"] = scores.get("typescript", 0) + 3
        
        # Return language with highest score, default to python
        return max(scores, key=scores.get) if max(scores.values()) > 0 else "python"
    
    @staticmethod
    def _detect_architecture_pattern(description: str, requirements: Optional[str] = None) -> ArchitecturePattern:
        """Intelligently detect architecture pattern"""
        text = f"{description} {requirements or ''}".lower()
        
        # Check for microservices indicators (including enterprise which often implies microservices)
        if any(word in text for word in ["microservice", "distributed", "service mesh", "event-driven"]):
            return ArchitecturePattern.MICROSERVICES
        # Enterprise platforms often use microservices
        elif "enterprise" in text and "platform" in text:
            return ArchitecturePattern.MICROSERVICES
        elif any(word in text for word in ["serverless", "lambda", "function as a service", "faas"]):
            return ArchitecturePattern.SERVERLESS
        elif any(word in text for word in ["hexagonal", "ports and adapters", "clean architecture"]):
            return ArchitecturePattern.HEXAGONAL
        elif any(word in text for word in ["layered", "n-tier", "three-tier", "mvc"]):
            return ArchitecturePattern.LAYERED
        # Default to monolith only if no other pattern is detected
        else:
            return ArchitecturePattern.MONOLITH
    
    @staticmethod
    def _detect_project_structure(description: str, requirements: Optional[str] = None) -> ProjectStructure:
        """Intelligently detect project structure"""
        text = f"{description} {requirements or ''}".lower()
        
        # Check for domain-driven indicators first (more specific)
        if any(word in text for word in ["domain", "ddd", "domain-driven", "bounded context", "aggregate"]):
            return ProjectStructure.DOMAIN_DRIVEN
        # Hexagonal architecture often implies domain-driven design
        elif any(word in text for word in ["hexagonal", "ports and adapters", "clean architecture"]):
            return ProjectStructure.DOMAIN_DRIVEN
        elif any(word in text for word in ["enterprise", "large scale", "complex", "multi-team"]):
            return ProjectStructure.ENTERPRISE
        elif any(word in text for word in ["feature", "module", "component", "modular"]):
            return ProjectStructure.FEATURE_BASED
        else:
            return ProjectStructure.FLAT
    
    @staticmethod
    def _process_requirements(
        description: str,
        requirements: Optional[str] = None,
        constraints: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process and structure requirements"""
        return {
            "description": description,
            "requirements": requirements,
            "constraints": constraints or {},
            "processed_at": datetime.utcnow().isoformat()
        }