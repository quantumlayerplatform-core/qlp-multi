"""
Capsule Packaging Service
Handles packaging capsules into various formats for delivery
"""

import io
import json
import zipfile
import tarfile
import tempfile
from typing import Dict, Any, Optional, BinaryIO
from datetime import datetime
import structlog

logger = structlog.get_logger()

class CapsulePackager:
    """Package capsules into various formats for delivery"""
    
    def package_as_zip(self, capsule_data: Dict[str, Any]) -> bytes:
        """Package capsule as ZIP file"""
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add manifest
            manifest = {
                "capsule_id": capsule_data.get("capsule_id"),
                "created_at": capsule_data.get("created_at"),
                "manifest": capsule_data.get("manifest", {}),
                "metadata": capsule_data.get("metadata", {})
            }
            zip_file.writestr("manifest.json", json.dumps(manifest, indent=2))
            
            # Add source code files
            source_code = capsule_data.get("source_code", {})
            for filename, content in source_code.items():
                zip_file.writestr(f"src/{filename}", content)
            
            # Add test files
            tests = capsule_data.get("tests", {})
            for filename, content in tests.items():
                zip_file.writestr(f"tests/{filename}", content)
            
            # Add documentation
            documentation = capsule_data.get("documentation", "")
            if documentation:
                zip_file.writestr("README.md", documentation)
            
            # Add requirements.txt if Python project
            if any(f.endswith('.py') for f in source_code.keys()):
                requirements = self._extract_requirements(capsule_data)
                if requirements:
                    zip_file.writestr("requirements.txt", "\n".join(requirements))
            
            # Add .gitignore
            gitignore_content = self._generate_gitignore(capsule_data)
            zip_file.writestr(".gitignore", gitignore_content)
        
        zip_buffer.seek(0)
        return zip_buffer.read()
    
    def package_as_tar_gz(self, capsule_data: Dict[str, Any]) -> bytes:
        """Package capsule as TAR.GZ file"""
        tar_buffer = io.BytesIO()
        
        with tarfile.open(fileobj=tar_buffer, mode='w:gz') as tar_file:
            # Add manifest
            manifest = {
                "capsule_id": capsule_data.get("capsule_id"),
                "created_at": capsule_data.get("created_at"),
                "manifest": capsule_data.get("manifest", {}),
                "metadata": capsule_data.get("metadata", {})
            }
            manifest_data = json.dumps(manifest, indent=2).encode('utf-8')
            manifest_info = tarfile.TarInfo(name="manifest.json")
            manifest_info.size = len(manifest_data)
            tar_file.addfile(manifest_info, io.BytesIO(manifest_data))
            
            # Add source code files
            source_code = capsule_data.get("source_code", {})
            for filename, content in source_code.items():
                self._add_file_to_tar(tar_file, f"src/{filename}", content)
            
            # Add test files
            tests = capsule_data.get("tests", {})
            for filename, content in tests.items():
                self._add_file_to_tar(tar_file, f"tests/{filename}", content)
            
            # Add documentation
            documentation = capsule_data.get("documentation", "")
            if documentation:
                self._add_file_to_tar(tar_file, "README.md", documentation)
            
            # Add requirements.txt if Python project
            if any(f.endswith('.py') for f in source_code.keys()):
                requirements = self._extract_requirements(capsule_data)
                if requirements:
                    self._add_file_to_tar(tar_file, "requirements.txt", "\n".join(requirements))
            
            # Add .gitignore
            gitignore_content = self._generate_gitignore(capsule_data)
            self._add_file_to_tar(tar_file, ".gitignore", gitignore_content)
        
        tar_buffer.seek(0)
        return tar_buffer.read()
    
    def _add_file_to_tar(self, tar_file: tarfile.TarFile, filename: str, content: str):
        """Helper to add file to tar archive"""
        data = content.encode('utf-8')
        info = tarfile.TarInfo(name=filename)
        info.size = len(data)
        info.mtime = int(datetime.now().timestamp())
        tar_file.addfile(info, io.BytesIO(data))
    
    def _extract_requirements(self, capsule_data: Dict[str, Any]) -> list:
        """Extract Python requirements from capsule"""
        requirements = set()
        
        # Check source code for imports
        source_code = capsule_data.get("source_code", {})
        for content in source_code.values():
            if isinstance(content, str):
                # Basic import detection
                lines = content.split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith('import ') or line.startswith('from '):
                        # Extract module name
                        if line.startswith('import '):
                            module = line.split()[1].split('.')[0]
                        else:  # from X import Y
                            module = line.split()[1].split('.')[0]
                        
                        # Map common modules to packages
                        package_map = {
                            'fastapi': 'fastapi',
                            'pydantic': 'pydantic',
                            'sqlalchemy': 'sqlalchemy',
                            'requests': 'requests',
                            'numpy': 'numpy',
                            'pandas': 'pandas',
                            'pytest': 'pytest',
                            'jwt': 'pyjwt',
                            'passlib': 'passlib[bcrypt]',
                            'jose': 'python-jose[cryptography]'
                        }
                        
                        if module in package_map:
                            requirements.add(package_map[module])
        
        # Add common requirements for FastAPI projects
        if any('fastapi' in str(content).lower() for content in source_code.values()):
            requirements.update(['fastapi', 'uvicorn[standard]', 'pydantic'])
        
        return sorted(list(requirements))
    
    def _generate_gitignore(self, capsule_data: Dict[str, Any]) -> str:
        """Generate appropriate .gitignore file"""
        gitignore_lines = [
            "# Byte-compiled / optimized / DLL files",
            "__pycache__/",
            "*.py[cod]",
            "*$py.class",
            "",
            "# Virtual environment",
            "venv/",
            "env/",
            ".venv/",
            "",
            "# IDE",
            ".vscode/",
            ".idea/",
            "*.swp",
            "*.swo",
            "",
            "# Testing",
            ".pytest_cache/",
            ".coverage",
            "htmlcov/",
            "",
            "# Environment variables",
            ".env",
            ".env.local",
            "",
            "# OS files",
            ".DS_Store",
            "Thumbs.db",
            "",
            "# Logs",
            "*.log",
            "logs/",
            "",
            "# Distribution / packaging",
            "dist/",
            "build/",
            "*.egg-info/"
        ]
        
        return "\n".join(gitignore_lines)
    
    def prepare_for_github(self, capsule_data: Dict[str, Any]) -> Dict[str, str]:
        """Prepare capsule files for GitHub push"""
        files = {}
        
        # Add source code files
        source_code = capsule_data.get("source_code", {})
        for filename, content in source_code.items():
            files[f"src/{filename}"] = content
        
        # Add test files
        tests = capsule_data.get("tests", {})
        for filename, content in tests.items():
            files[f"tests/{filename}"] = content
        
        # Add documentation as README.md
        documentation = capsule_data.get("documentation", "")
        if documentation:
            files["README.md"] = documentation
        else:
            # Generate basic README
            files["README.md"] = self._generate_readme(capsule_data)
        
        # Add requirements.txt if Python project
        if any(f.endswith('.py') for f in source_code.keys()):
            requirements = self._extract_requirements(capsule_data)
            if requirements:
                files["requirements.txt"] = "\n".join(requirements)
        
        # Add .gitignore
        files[".gitignore"] = self._generate_gitignore(capsule_data)
        
        # Add GitHub Actions workflow if tests exist
        if tests:
            files[".github/workflows/test.yml"] = self._generate_github_actions_workflow(capsule_data)
        
        return files
    
    def _generate_readme(self, capsule_data: Dict[str, Any]) -> str:
        """Generate a basic README.md file"""
        capsule_id = capsule_data.get("capsule_id", "Unknown")
        created_at = capsule_data.get("created_at", "")
        
        readme = f"""# Capsule {capsule_id}

Generated by Quantum Layer Platform on {created_at}

## Overview

This project was automatically generated based on natural language requirements.

## Structure

- `src/` - Source code files
- `tests/` - Unit tests
- `requirements.txt` - Python dependencies

## Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running Tests

```bash
pytest tests/
```

## Usage

See the source code in `src/` for implementation details.

---
Generated by [Quantum Layer Platform](https://quantumlayer.ai)
"""
        return readme
    
    def _generate_github_actions_workflow(self, capsule_data: Dict[str, Any]) -> str:
        """Generate GitHub Actions workflow for testing"""
        workflow = """name: Tests

on:
  push:
    branches: [ main ]
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
        pip install pytest pytest-cov
    
    - name: Run tests
      run: |
        pytest tests/ -v --cov=src --cov-report=term-missing
    
    - name: Upload coverage reports
      uses: codecov/codecov-action@v3
      if: always()
"""
        return workflow