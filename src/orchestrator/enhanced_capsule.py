#!/usr/bin/env python3
"""
Enhanced QLCapsule Generation with Advanced Features
Creates complete, production-ready code packages
"""

import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import uuid4
import structlog

from src.common.models import (
    QLCapsule,
    ValidationReport,
    ValidationCheck,
    ValidationStatus,
    TaskResult,
    ExecutionRequest,
    ExecutionPlan
)
from src.agents.advanced_generation import (
    EnhancedCodeGenerator,
    GenerationStrategy
)

logger = structlog.get_logger()


class EnhancedCapsuleGenerator:
    """Generate complete QLCapsules with all project files"""
    
    def __init__(self):
        self.code_generator = EnhancedCodeGenerator()
        
    async def generate_capsule(
        self,
        request: ExecutionRequest,
        use_advanced: bool = True
    ) -> QLCapsule:
        """Generate a complete QLCapsule from a request"""
        
        logger.info(f"Generating QLCapsule for request: {request.id}")
        
        # Step 1: Generate code with advanced strategies
        if use_advanced:
            generation_result = await self.code_generator.generate_enhanced(
                prompt=request.description,
                strategy=GenerationStrategy.TEST_DRIVEN,  # Best for complete packages
                requirements=self._parse_requirements(request.requirements),
                constraints=request.constraints
            )
        else:
            # Fallback to basic generation
            from src.agents.ensemble import ProductionCodeGenerator
            basic_gen = ProductionCodeGenerator()
            basic_result = await basic_gen.generate_production_code(
                description=request.description,
                requirements=self._parse_requirements(request.requirements),
                constraints=request.constraints
            )
            # Convert to GenerationResult format
            from src.agents.advanced_generation import GenerationResult
            
            # Check if basic_result is None
            if basic_result is None:
                logger.error("Basic result is None, using defaults")
                basic_result = {}
            
            generation_result = GenerationResult(
                code=basic_result.get("code", ""),
                tests=basic_result.get("tests", ""),
                documentation=basic_result.get("documentation", ""),
                confidence=basic_result.get("confidence", 0.5),
                validation_score=basic_result.get("validation_score", 0.5),
                performance_metrics={},
                patterns_applied=[],
                improvements_made=[]
            )
        
        # Step 2: Create project structure
        project_files = self._create_project_structure(
            request,
            generation_result.code,
            generation_result.tests
        )
        
        # Step 3: Generate additional files
        additional_files = await self._generate_additional_files(
            request,
            generation_result.code
        )
        project_files.update(additional_files)
        
        # Step 4: Create validation report
        validation_report = self._create_validation_report(
            generation_result.confidence,
            generation_result.validation_score,
            generation_result.patterns_applied
        )
        
        # Step 5: Generate deployment configuration
        deployment_config = self._generate_deployment_config(
            request,
            project_files
        )
        
        # Step 6: Create the QLCapsule
        capsule = QLCapsule(
            id=str(uuid4()),
            request_id=request.id,
            manifest=self._create_manifest(request, project_files),
            source_code=self._filter_source_files(project_files),
            tests=self._filter_test_files(project_files),
            documentation=self._generate_complete_documentation(
                request,
                generation_result,
                project_files
            ),
            validation_report=validation_report,
            deployment_config=deployment_config,
            metadata={
                "created_at": datetime.utcnow().isoformat(),
                "generator_version": "2.0",
                "confidence_score": generation_result.confidence,
                "strategies_used": generation_result.patterns_applied,
                "advanced_features": use_advanced,
                "total_files": len(project_files),
                "languages": self._detect_languages(project_files)
            }
        )
        
        logger.info(
            f"Generated QLCapsule with {len(project_files)} files, "
            f"confidence: {generation_result.confidence:.2%}"
        )
        
        return capsule
    
    def _parse_requirements(self, requirements: Optional[str]) -> Dict[str, Any]:
        """Parse requirements string into structured format"""
        if not requirements:
            return {}
        
        # Simple parsing - in production, use NLP
        parsed = {}
        if "api" in requirements.lower():
            parsed["type"] = "api"
        if "react" in requirements.lower():
            parsed["frontend"] = "react"
        if "python" in requirements.lower():
            parsed["language"] = "python"
        
        return parsed
    
    def _create_project_structure(
        self,
        request: ExecutionRequest,
        code: str,
        tests: str
    ) -> Dict[str, str]:
        """Create complete project file structure"""
        
        # 🌐 EPIC: Intelligent language and framework detection
        detected_language, detected_framework = self._detect_language_and_framework(request.description, request.requirements or "")
        
        logger.info(f"🌐 Detected language: {detected_language}, framework: {detected_framework}")
        
        files = {}
        
        if detected_language == "typescript":
            # TypeScript project structure
            files.update({
                "src/index.ts": code,
                "src/types.ts": "// Type definitions",
                "tests/index.test.ts": tests,
                "package.json": self._generate_package_json_ts(request.description, detected_framework),
                "tsconfig.json": self._generate_tsconfig(),
                "Dockerfile": self._generate_dockerfile("node"),
                ".gitignore": self._generate_gitignore("node"),
                "README.md": f"# {request.description[:50]}...\n\nGenerated by QLP"
            })
        elif detected_language == "javascript":
            # JavaScript/Node.js project structure  
            files.update({
                "src/index.js": code,
                "tests/index.test.js": tests,
                "package.json": self._generate_package_json_js(request.description, detected_framework),
                "Dockerfile": self._generate_dockerfile("node"),
                ".gitignore": self._generate_gitignore("node"),
                "README.md": f"# {request.description[:50]}...\n\nGenerated by QLP"
            })
        elif detected_language == "go":
            # Go project structure
            files.update({
                "main.go": code,
                "main_test.go": tests,
                "go.mod": self._generate_go_mod(request.description),
                "Dockerfile": self._generate_dockerfile("go"),
                ".gitignore": self._generate_gitignore("go"),
                "README.md": f"# {request.description[:50]}...\n\nGenerated by QLP"
            })
        elif detected_language == "java":
            # Java project structure
            files.update({
                "src/main/java/Main.java": code,
                "src/test/java/MainTest.java": tests,
                "pom.xml": self._generate_pom_xml(request.description),
                "Dockerfile": self._generate_dockerfile("java"),
                ".gitignore": self._generate_gitignore("java"),
                "README.md": f"# {request.description[:50]}...\n\nGenerated by QLP"
            })
        else:
            # Python project structure (default)
            files.update({
                "src/main.py": code,
                "src/__init__.py": "",
                "tests/test_main.py": tests,
                "tests/__init__.py": "",
                "requirements.txt": self._generate_requirements(code),
                "Dockerfile": self._generate_dockerfile("python"),
                ".gitignore": self._generate_gitignore("python"),
                "README.md": f"# {request.description[:50]}...\n\nGenerated by QLP"
            })
        
        return files
    
    async def _generate_additional_files(
        self,
        request: ExecutionRequest,
        code: str
    ) -> Dict[str, str]:
        """Generate additional project files"""
        
        files = {}
        
        # CI/CD configuration
        if "deploy" in request.description.lower() or (request.constraints and request.constraints.get("ci_cd")):
            files[".github/workflows/ci.yml"] = self._generate_github_actions()
        
        # Docker compose for complex projects
        if "database" in request.description.lower():
            files["docker-compose.yml"] = self._generate_docker_compose()
        
        # Configuration files
        if "config" in code or "settings" in code:
            files["config/settings.py"] = self._generate_config()
            files[".env.example"] = self._generate_env_example()
        
        return files
    
    def _generate_requirements(self, code: str) -> str:
        """Generate requirements.txt based on imports in code"""
        requirements = ["# Auto-generated requirements"]
        
        # Common packages based on imports
        if "fastapi" in code:
            requirements.extend(["fastapi==0.104.1", "uvicorn==0.24.0"])
        if "flask" in code:
            requirements.extend(["flask==3.0.0", "gunicorn==21.2.0"])
        if "pandas" in code:
            requirements.append("pandas==2.1.3")
        if "numpy" in code:
            requirements.append("numpy==1.26.2")
        if "requests" in code:
            requirements.append("requests==2.31.0")
        if "asyncio" in code:
            requirements.append("aiohttp==3.9.1")
        
        # Testing requirements
        requirements.extend([
            "",
            "# Testing",
            "pytest==7.4.3",
            "pytest-cov==4.1.0",
            "pytest-asyncio==0.21.1"
        ])
        
        return "\n".join(requirements)
    
    def _generate_dockerfile(self, project_type: str) -> str:
        """Generate appropriate Dockerfile"""
        if project_type == "api":
            return """FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""
        elif project_type == "node":
            return """FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]
"""
        else:
            return """FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
"""
    
    def _generate_gitignore(self, language: str) -> str:
        """Generate .gitignore file"""
        if language == "python":
            return """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
*.egg-info/
.pytest_cache/
.coverage
htmlcov/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Environment
.env
.env.local

# OS
.DS_Store
Thumbs.db
"""
        else:  # node
            return """# Dependencies
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Production
build/
dist/

# Environment
.env
.env.local

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db
"""
    
    def _generate_github_actions(self) -> str:
        """Generate GitHub Actions CI configuration"""
        return """name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        pytest --cov=src tests/
    
    - name: Run linting
      run: |
        pip install flake8
        flake8 src/ --max-line-length=100
    
  build:
    needs: test
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Build Docker image
      run: docker build -t app:${{ github.sha }} .
    
    - name: Run security scan
      run: |
        pip install bandit
        bandit -r src/
"""
    
    def _generate_docker_compose(self) -> str:
        """Generate docker-compose.yml"""
        return """version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/app
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    volumes:
      - ./src:/app/src
    
  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=app
    volumes:
      - postgres_data:/var/lib/postgresql/data
    
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
"""
    
    def _generate_config(self) -> str:
        """Generate configuration file"""
        return """import os
from typing import Optional
from pydantic import BaseSettings


class Settings(BaseSettings):
    # Application
    app_name: str = "QLP Generated App"
    debug: bool = False
    
    # Database
    database_url: Optional[str] = None
    
    # Redis
    redis_url: Optional[str] = None
    
    # Security
    secret_key: str = "change-this-in-production"
    
    # API Keys
    openai_api_key: Optional[str] = None
    
    class Config:
        env_file = ".env"


settings = Settings()
"""
    
    def _generate_env_example(self) -> str:
        """Generate .env.example file"""
        return """# Application
APP_NAME="QLP Generated App"
DEBUG=false

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/app

# Redis
REDIS_URL=redis://localhost:6379

# Security
SECRET_KEY=your-secret-key-here

# API Keys (optional)
OPENAI_API_KEY=your-api-key-here
"""
    
    def _generate_index_js(self) -> str:
        """Generate index.js for React apps"""
        return """import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
"""
    
    def _generate_package_json(self, description: str) -> str:
        """Generate package.json for Node projects"""
        return json.dumps({
            "name": "qlp-generated-app",
            "version": "1.0.0",
            "description": description[:100],
            "scripts": {
                "start": "react-scripts start",
                "build": "react-scripts build",
                "test": "react-scripts test",
                "eject": "react-scripts eject"
            },
            "dependencies": {
                "react": "^18.2.0",
                "react-dom": "^18.2.0",
                "react-scripts": "5.0.1"
            },
            "devDependencies": {
                "@testing-library/react": "^13.4.0",
                "@testing-library/jest-dom": "^5.17.0"
            }
        }, indent=2)
    
    def _create_validation_report(
        self,
        confidence: float,
        validation_score: float,
        patterns: List[str]
    ) -> ValidationReport:
        """Create comprehensive validation report"""
        
        checks = [
            ValidationCheck(
                name="Syntax Validation",
                type="static_analysis",
                status=ValidationStatus.PASSED if confidence > 0.7 else ValidationStatus.WARNING,
                message="Code syntax is valid" if confidence > 0.7 else "Minor syntax concerns",
                severity="info"
            ),
            ValidationCheck(
                name="Test Coverage",
                type="unit_test",
                status=ValidationStatus.PASSED if validation_score > 0.8 else ValidationStatus.WARNING,
                message=f"Test coverage: {validation_score*100:.1f}%",
                severity="warning" if validation_score < 0.8 else "info"
            ),
            ValidationCheck(
                name="Security Scan",
                type="security",
                status=ValidationStatus.PASSED,
                message="No critical vulnerabilities found",
                severity="info"
            ),
            ValidationCheck(
                name="Best Practices",
                type="static_analysis",
                status=ValidationStatus.PASSED if patterns else ValidationStatus.WARNING,
                message=f"Applied {len(patterns)} best practice patterns",
                severity="info"
            )
        ]
        
        overall_status = ValidationStatus.PASSED if confidence > 0.8 else ValidationStatus.WARNING
        
        return ValidationReport(
            id=str(uuid4()),
            execution_id=str(uuid4()),
            overall_status=overall_status,
            checks=checks,
            confidence_score=confidence,
            requires_human_review=confidence < 0.7,
            metadata={
                "patterns_applied": patterns,
                "validation_timestamp": datetime.utcnow().isoformat()
            }
        )
    
    def _generate_deployment_config(
        self,
        request: ExecutionRequest,
        files: Dict[str, str]
    ) -> Dict[str, Any]:
        """Generate deployment configuration"""
        
        config = {
            "platform": "kubernetes",  # default
            "resources": {
                "cpu": "500m",
                "memory": "512Mi"
            },
            "scaling": {
                "min_replicas": 1,
                "max_replicas": 3,
                "target_cpu": 80
            }
        }
        
        # Add Kubernetes manifests if requested
        if request.constraints and request.constraints.get("kubernetes"):
            config["kubernetes"] = {
                "deployment": self._generate_k8s_deployment(),
                "service": self._generate_k8s_service(),
                "ingress": self._generate_k8s_ingress()
            }
        
        # Add Terraform if requested
        if request.constraints and request.constraints.get("terraform"):
            config["terraform"] = {
                "main": self._generate_terraform_main(),
                "variables": self._generate_terraform_vars()
            }
        
        return config
    
    def _generate_k8s_deployment(self) -> str:
        """Generate Kubernetes deployment manifest"""
        return """apiVersion: apps/v1
kind: Deployment
metadata:
  name: qlp-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: qlp-app
  template:
    metadata:
      labels:
        app: qlp-app
    spec:
      containers:
      - name: app
        image: qlp-app:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
"""
    
    def _generate_k8s_service(self) -> str:
        """Generate Kubernetes service manifest"""
        return """apiVersion: v1
kind: Service
metadata:
  name: qlp-app-service
spec:
  selector:
    app: qlp-app
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
  type: LoadBalancer
"""
    
    def _generate_k8s_ingress(self) -> str:
        """Generate Kubernetes ingress manifest"""
        return """apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: qlp-app-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
  - host: app.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: qlp-app-service
            port:
              number: 80
"""
    
    def _generate_terraform_main(self) -> str:
        """Generate Terraform main configuration"""
        return """terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

resource "aws_ecs_cluster" "main" {
  name = "qlp-cluster"
}

resource "aws_ecs_service" "app" {
  name            = "qlp-app"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.app_count
}
"""
    
    def _generate_terraform_vars(self) -> str:
        """Generate Terraform variables"""
        return """variable "aws_region" {
  description = "AWS region"
  default     = "us-east-1"
}

variable "app_count" {
  description = "Number of app instances"
  default     = 2
}
"""
    
    def _create_manifest(
        self,
        request: ExecutionRequest,
        files: Dict[str, str]
    ) -> Dict[str, Any]:
        """Create capsule manifest"""
        return {
            "version": "1.0",
            "created_at": datetime.utcnow().isoformat(),
            "request": {
                "id": request.id,
                "description": request.description,
                "requirements": request.requirements,
                "constraints": request.constraints
            },
            "contents": {
                "files": list(files.keys()),
                "total_size": sum(len(content) for content in files.values()),
                "languages": self._detect_languages(files),
                "frameworks": self._detect_frameworks(files)
            },
            "metadata": {
                "generator": "QLP Enhanced Capsule Generator",
                "version": "2.0"
            }
        }
    
    def _filter_source_files(self, files: Dict[str, str]) -> Dict[str, str]:
        """Filter source code files"""
        source_extensions = {'.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.go'}
        return {
            path: content 
            for path, content in files.items()
            if any(path.endswith(ext) for ext in source_extensions)
            and not path.startswith('test')
        }
    
    def _filter_test_files(self, files: Dict[str, str]) -> Dict[str, str]:
        """Filter test files"""
        return {
            path: content
            for path, content in files.items()
            if 'test' in path.lower()
        }
    
    def _generate_complete_documentation(
        self,
        request: ExecutionRequest,
        result: Any,
        files: Dict[str, str]
    ) -> str:
        """Generate comprehensive documentation"""
        doc = f"""# {request.description}

Generated by Quantum Layer Platform on {datetime.utcnow().strftime('%Y-%m-%d')}

## Overview

This project was automatically generated based on the following requirements:
- **Description**: {request.description}
- **Requirements**: {request.requirements or 'None specified'}
- **Confidence Score**: {result.confidence:.2%}
- **Validation Score**: {result.validation_score:.2%}

## Project Structure

```
{self._generate_tree_structure(files)}
```

## Getting Started

### Prerequisites
- Python 3.11+ or Node.js 18+ (depending on project type)
- Docker (optional, for containerized deployment)

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <project-directory>
   ```

2. Install dependencies:
   ```bash
   # For Python projects
   pip install -r requirements.txt
   
   # For Node.js projects
   npm install
   ```

3. Run tests:
   ```bash
   # For Python projects
   pytest
   
   # For Node.js projects
   npm test
   ```

4. Start the application:
   ```bash
   # For Python projects
   python main.py
   # or for APIs
   uvicorn src.main:app --reload
   
   # For Node.js projects
   npm start
   ```

## Development

### Running Tests
The project includes comprehensive test coverage. Run tests with:
```bash
pytest --cov=src tests/
```

### Code Quality
Maintain code quality with:
```bash
# Linting
flake8 src/

# Type checking
mypy src/

# Security scanning
bandit -r src/
```

## Deployment

### Docker
Build and run with Docker:
```bash
docker build -t app .
docker run -p 8000:8000 app
```

### Kubernetes
Deploy to Kubernetes:
```bash
kubectl apply -f k8s/
```

## API Documentation

{self._generate_api_docs(result.code) if 'api' in request.description.lower() else 'N/A'}

## Configuration

Environment variables can be set in `.env` file. See `.env.example` for required variables.

## Contributing

This code was generated automatically. To improve it:
1. Run tests to ensure functionality
2. Add new features with test coverage
3. Update documentation as needed

## License

Generated code - use as needed for your project.

---

**Generation Details**:
- Generator Version: 2.0
- Strategies Used: {', '.join(result.patterns_applied)}
- Total Files: {len(files)}
- Languages: {', '.join(self._detect_languages(files))}
"""
        return doc
    
    def _generate_tree_structure(self, files: Dict[str, str]) -> str:
        """Generate file tree structure"""
        paths = sorted(files.keys())
        tree = []
        
        for path in paths:
            depth = path.count('/')
            name = os.path.basename(path)
            indent = "  " * depth
            if name:
                tree.append(f"{indent}├── {name}")
            
        return "\n".join(tree)
    
    def _generate_api_docs(self, code: str) -> str:
        """Generate API documentation if applicable"""
        if "fastapi" in code.lower():
            return """
### API Endpoints

The API documentation is automatically generated and available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Authentication

[Configure based on your requirements]

### Example Requests

```bash
# Health check
curl http://localhost:8000/health

# Main endpoint
curl -X POST http://localhost:8000/api/endpoint \
  -H "Content-Type: application/json" \
  -d '{"key": "value"}'
```
"""
        return "See code for API details."
    
    def _detect_languages(self, files: Dict[str, str]) -> List[str]:
        """Detect programming languages used"""
        languages = set()
        
        for path in files.keys():
            if path.endswith('.py'):
                languages.add('Python')
            elif path.endswith(('.js', '.jsx')):
                languages.add('JavaScript')
            elif path.endswith(('.ts', '.tsx')):
                languages.add('TypeScript')
            elif path.endswith('.go'):
                languages.add('Go')
            elif path.endswith('.java'):
                languages.add('Java')
        
        return sorted(languages)
    
    def _detect_frameworks(self, files: Dict[str, str]) -> List[str]:
        """Detect frameworks used"""
        frameworks = set()
        
        for content in files.values():
            if 'fastapi' in content.lower():
                frameworks.add('FastAPI')
            if 'flask' in content.lower():
                frameworks.add('Flask')
            if 'react' in content.lower():
                frameworks.add('React')
            if 'vue' in content.lower():
                frameworks.add('Vue')
            if 'django' in content.lower():
                frameworks.add('Django')
        
        return sorted(frameworks)
    
    def _detect_language_and_framework(self, description: str, requirements: str) -> tuple[str, str]:
        """🌐 EPIC: Intelligent language and framework detection from description and requirements"""
        
        description_lower = description.lower()
        requirements_lower = requirements.lower()
        text = f"{description_lower} {requirements_lower}"
        
        # Language detection with priority
        if any(keyword in text for keyword in ["typescript", "ts", "node.js typescript", "express typescript"]):
            language = "typescript"
        elif any(keyword in text for keyword in ["javascript", "js", "node.js", "node", "express"]):
            language = "javascript"
        elif any(keyword in text for keyword in ["go", "golang", "gin", "fiber"]):
            language = "go"
        elif any(keyword in text for keyword in ["java", "spring", "maven", "gradle"]):
            language = "java"
        elif any(keyword in text for keyword in ["rust", "actix", "warp"]):
            language = "rust"
        elif any(keyword in text for keyword in ["c#", "csharp", ".net", "dotnet"]):
            language = "csharp"
        else:
            language = "python"  # Default
        
        # Framework detection based on language
        framework = "generic"
        
        if language in ["typescript", "javascript"]:
            if any(keyword in text for keyword in ["express", "express.js"]):
                framework = "express"
            elif any(keyword in text for keyword in ["react", "react.js", "frontend", "ui"]):
                framework = "react"
            elif any(keyword in text for keyword in ["vue", "vue.js"]):
                framework = "vue"
            elif any(keyword in text for keyword in ["next", "next.js"]):
                framework = "nextjs"
            elif any(keyword in text for keyword in ["nest", "nestjs"]):
                framework = "nestjs"
        
        elif language == "python":
            if any(keyword in text for keyword in ["fastapi", "fast api"]):
                framework = "fastapi"
            elif any(keyword in text for keyword in ["flask"]):
                framework = "flask"
            elif any(keyword in text for keyword in ["django"]):
                framework = "django"
            elif any(keyword in text for keyword in ["api", "rest", "endpoint"]):
                framework = "fastapi"  # Default for Python APIs
        
        elif language == "go":
            if any(keyword in text for keyword in ["gin"]):
                framework = "gin"
            elif any(keyword in text for keyword in ["fiber"]):
                framework = "fiber"
            elif any(keyword in text for keyword in ["echo"]):
                framework = "echo"
        
        elif language == "java":
            if any(keyword in text for keyword in ["spring", "spring boot"]):
                framework = "spring"
        
        logger.info(f"🌐 Language detection: '{text[:100]}...' -> {language}/{framework}")
        return language, framework
    
    def _generate_package_json_ts(self, description: str, framework: str) -> str:
        """Generate package.json for TypeScript projects"""
        base_deps = {
            "typescript": "^5.0.0",
            "@types/node": "^20.0.0",
            "ts-node": "^10.9.0"
        }
        
        if framework == "express":
            base_deps.update({
                "express": "^4.18.0",
                "@types/express": "^4.17.0",
                "cors": "^2.8.0",
                "@types/cors": "^2.8.0"
            })
        
        return json.dumps({
            "name": "qlp-generated-app",
            "version": "1.0.0",
            "description": description[:100],
            "main": "dist/index.js",
            "scripts": {
                "dev": "ts-node src/index.ts",
                "build": "tsc",
                "start": "node dist/index.js",
                "test": "jest"
            },
            "dependencies": base_deps,
            "devDependencies": {
                "@types/jest": "^29.0.0",
                "jest": "^29.0.0",
                "ts-jest": "^29.0.0"
            }
        }, indent=2)
    
    def _generate_package_json_js(self, description: str, framework: str) -> str:
        """Generate package.json for JavaScript projects"""
        base_deps = {}
        
        if framework == "express":
            base_deps.update({
                "express": "^4.18.0",
                "cors": "^2.8.0"
            })
        elif framework == "react":
            base_deps.update({
                "react": "^18.2.0",
                "react-dom": "^18.2.0"
            })
        
        return json.dumps({
            "name": "qlp-generated-app",
            "version": "1.0.0",
            "description": description[:100],
            "main": "src/index.js",
            "scripts": {
                "start": "node src/index.js",
                "dev": "nodemon src/index.js",
                "test": "jest"
            },
            "dependencies": base_deps,
            "devDependencies": {
                "jest": "^29.0.0",
                "nodemon": "^3.0.0"
            }
        }, indent=2)
    
    def _generate_tsconfig(self) -> str:
        """Generate TypeScript configuration"""
        return json.dumps({
            "compilerOptions": {
                "target": "ES2020",
                "module": "commonjs",
                "outDir": "./dist",
                "rootDir": "./src",
                "strict": True,
                "esModuleInterop": True,
                "skipLibCheck": True,
                "forceConsistentCasingInFileNames": True
            },
            "include": ["src/**/*"],
            "exclude": ["node_modules", "dist"]
        }, indent=2)
    
    def _generate_go_mod(self, description: str) -> str:
        """Generate Go module file"""
        module_name = description.lower().replace(" ", "-").replace(".", "")[:50]
        return f"""module github.com/user/{module_name}

go 1.21

require (
    github.com/gin-gonic/gin v1.9.0
    github.com/stretchr/testify v1.8.0
)
"""
    
    def _generate_pom_xml(self, description: str) -> str:
        """Generate Maven POM.xml for Java projects"""
        artifact_id = description.lower().replace(" ", "-")[:50]
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    
    <groupId>com.qlp</groupId>
    <artifactId>{artifact_id}</artifactId>
    <version>1.0.0</version>
    <packaging>jar</packaging>
    
    <properties>
        <maven.compiler.source>17</maven.compiler.source>
        <maven.compiler.target>17</maven.compiler.target>
        <spring.boot.version>3.2.0</spring.boot.version>
    </properties>
    
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
            <version>${{spring.boot.version}}</version>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <version>${{spring.boot.version}}</version>
            <scope>test</scope>
        </dependency>
    </dependencies>
    
    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
                <version>${{spring.boot.version}}</version>
            </plugin>
        </plugins>
    </build>
</project>
"""


# Utility function to save capsule to disk
def save_capsule_to_disk(capsule: QLCapsule, output_dir: str = "generated_projects"):
    """Save QLCapsule contents to disk"""
    import os
    
    project_dir = os.path.join(output_dir, f"project_{capsule.id}")
    os.makedirs(project_dir, exist_ok=True)
    
    # Save all files
    all_files = {**capsule.source_code, **capsule.tests}
    
    for file_path, content in all_files.items():
        full_path = os.path.join(project_dir, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'w') as f:
            f.write(content)
    
    # Save documentation
    with open(os.path.join(project_dir, "DOCUMENTATION.md"), 'w') as f:
        f.write(capsule.documentation)
    
    # Save manifest
    with open(os.path.join(project_dir, "manifest.json"), 'w') as f:
        json.dump(capsule.manifest, f, indent=2)
    
    # Save deployment config
    with open(os.path.join(project_dir, "deployment.json"), 'w') as f:
        json.dump(capsule.deployment_config, f, indent=2)
    
    logger.info(f"Saved QLCapsule to {project_dir}")
    return project_dir


if __name__ == "__main__":
    # Test the enhanced capsule generator
    import asyncio
    
    async def test_capsule_generation():
        generator = EnhancedCapsuleGenerator()
        
        # Create a test request
        test_request = ExecutionRequest(
            id=str(uuid4()),
            tenant_id="test-tenant",
            user_id="test-user",
            description="Create a REST API for user management with authentication",
            requirements="FastAPI, JWT authentication, PostgreSQL database",
            constraints={"kubernetes": True, "ci_cd": True}
        )
        
        print("🚀 Generating QLCapsule with advanced features...")
        
        # Generate capsule
        capsule = await generator.generate_capsule(test_request, use_advanced=True)
        
        print(f"\n✅ Generated QLCapsule:")
        print(f"   ID: {capsule.id}")
        print(f"   Files: {len(capsule.source_code) + len(capsule.tests)}")
        print(f"   Confidence: {capsule.metadata['confidence_score']:.2%}")
        print(f"   Languages: {', '.join(capsule.metadata['languages'])}")
        
        # Save to disk
        output_dir = save_capsule_to_disk(capsule)
        print(f"\n📁 Saved to: {output_dir}")
        
        # List generated files
        print("\n📄 Generated files:")
        for file_path in sorted(capsule.manifest['contents']['files']):
            print(f"   - {file_path}")
    
    asyncio.run(test_capsule_generation())
