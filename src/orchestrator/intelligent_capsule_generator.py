"""
Intelligent Capsule Generator - LLM-Powered Enterprise Project Structure
Uses AI agents to intelligently create optimal project structures
"""

import json
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
import structlog

from src.common.models import Task, AgentTier
from src.agents.client import AgentFactoryClient
from src.common.config import settings

logger = structlog.get_logger()


class IntelligentCapsuleGenerator:
    """
    Uses LLM agents to intelligently generate enterprise-grade project structures
    No hardcoded templates - pure AI-driven decisions
    """
    
    def __init__(self):
        self.agent_client = AgentFactoryClient(f"http://localhost:{settings.AGENT_FACTORY_PORT}")
        
    async def generate_enterprise_capsule(
        self, 
        base_capsule: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Transform a basic capsule into an enterprise-grade project structure
        using AI agents to make intelligent decisions
        """
        logger.info("Starting intelligent enterprise capsule generation", 
                   capsule_id=base_capsule.get("capsule_id"))
        
        # Step 1: Analyze project context with AI
        project_analysis = await self._analyze_project_context(base_capsule, context)
        
        # Step 2: Determine optimal project structure
        structure_plan = await self._determine_project_structure(project_analysis)
        
        # Step 3: Generate configuration files
        config_files = await self._generate_configuration_files(project_analysis, structure_plan)
        
        # Step 4: Create documentation structure
        documentation = await self._generate_documentation(project_analysis, base_capsule)
        
        # Step 5: Setup CI/CD pipeline
        cicd_files = await self._generate_cicd_pipeline(project_analysis, structure_plan)
        
        # Step 6: Add development tooling
        dev_tools = await self._generate_dev_tooling(project_analysis)
        
        # Step 7: Reorganize code into proper structure
        reorganized_code = await self._reorganize_code_structure(
            base_capsule.get("source_code", {}),
            base_capsule.get("tests", {}),
            structure_plan
        )
        
        # Step 8: Add enterprise patterns
        enterprise_patterns = await self._add_enterprise_patterns(
            reorganized_code,
            project_analysis
        )
        
        # Combine everything into enterprise capsule
        enterprise_capsule = {
            **base_capsule,
            "enterprise_grade": True,
            "structure_version": "2.0",
            "files": {
                **reorganized_code,
                **config_files,
                **documentation,
                **cicd_files,
                **dev_tools,
                **enterprise_patterns
            },
            "project_metadata": {
                **base_capsule.get("metadata", {}),
                "project_analysis": project_analysis,
                "structure_plan": structure_plan,
                "enterprise_features": {
                    "has_ci_cd": True,
                    "has_documentation": True,
                    "has_testing": True,
                    "has_containerization": bool(config_files.get("Dockerfile")),
                    "has_monitoring": bool(enterprise_patterns.get("src/monitoring")),
                    "has_security": bool(enterprise_patterns.get("security"))
                }
            }
        }
        
        return enterprise_capsule
    
    async def _analyze_project_context(
        self, 
        capsule: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use AI to deeply analyze the project and determine its characteristics"""
        
        # Prepare context for AI analysis
        code_samples = []
        for filename, code in capsule.get("source_code", {}).items():
            code_samples.append(f"File: {filename}\n{code[:500]}...")
        
        analysis_task = Task(
            id="analyze-project",
            type="analysis",
            description=f"""Analyze this project and determine its characteristics:

Project Description: {context.get('description', 'N/A')}
Language: {context.get('language', 'auto-detect')}
Files: {list(capsule.get('source_code', {}).keys())}

Code Samples:
{chr(10).join(code_samples[:3])}

Determine:
1. Project type (web app, API, library, CLI tool, data science, etc.)
2. Complexity level (simple, moderate, complex, enterprise)
3. Key frameworks/libraries used
4. Architectural patterns present
5. Deployment requirements
6. Testing requirements
7. Documentation needs
8. Security considerations
9. Performance requirements
10. Scalability needs

Respond with a comprehensive JSON analysis.""",
            complexity="complex",
            metadata={"analysis_type": "project_context"}
        )
        
        # Use T2 agent for intelligent analysis
        result = await self.agent_client.execute_task(
            analysis_task, 
            tier=AgentTier.T2,
            context=context
        )
        
        # Parse the analysis
        try:
            if isinstance(result.output, dict):
                analysis = result.output.get("content", "{}")
            else:
                analysis = result.output
            
            # Extract JSON from the response
            if isinstance(analysis, str):
                # Try to find JSON in the response
                import re
                json_match = re.search(r'\{.*\}', analysis, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    # Fallback analysis
                    analysis = {
                        "project_type": "general",
                        "complexity": "moderate",
                        "frameworks": [],
                        "patterns": ["modular"],
                        "deployment": "standard",
                        "testing": "unit",
                        "documentation": "basic",
                        "security": "standard",
                        "performance": "normal",
                        "scalability": "vertical"
                    }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to parse project analysis: {e}")
            return {
                "project_type": "general",
                "complexity": "moderate",
                "error": str(e)
            }
    
    async def _determine_project_structure(
        self, 
        project_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use AI to determine the optimal folder structure"""
        
        structure_task = Task(
            id="determine-structure",
            type="architecture",
            description=f"""Based on this project analysis, determine the optimal enterprise folder structure:

{json.dumps(project_analysis, indent=2)}

Create a comprehensive folder structure that includes:
1. Source code organization
2. Test structure (unit, integration, e2e)
3. Documentation layout
4. Configuration management
5. CI/CD setup
6. Docker/containerization if needed
7. Scripts and tooling
8. Security configurations
9. Monitoring and logging setup
10. Environment management

Respond with a JSON structure mapping paths to their purposes.
Consider best practices for the identified project type and language.""",
            complexity="complex",
            metadata={"structure_type": "enterprise"}
        )
        
        result = await self.agent_client.execute_task(
            structure_task,
            tier=AgentTier.T2,
            context={"project_analysis": project_analysis}
        )
        
        try:
            structure = self._parse_ai_response(result.output)
            return structure
        except:
            # Fallback to a sensible default
            return self._get_intelligent_default_structure(project_analysis)
    
    async def _generate_configuration_files(
        self, 
        project_analysis: Dict[str, Any],
        structure_plan: Dict[str, Any]
    ) -> Dict[str, str]:
        """Use AI to generate all necessary configuration files"""
        
        config_task = Task(
            id="generate-configs",
            type="configuration",
            description=f"""Generate configuration files for this project:

Project Analysis:
{json.dumps(project_analysis, indent=2)}

Project Structure:
{json.dumps(structure_plan, indent=2)}

Generate appropriate configuration files such as:
- Package management (package.json, requirements.txt, go.mod, Cargo.toml, etc.)
- Build configuration
- Linting and formatting configs
- Testing configuration
- Docker files if applicable
- Environment configuration templates
- IDE settings
- Git configuration files

Each file should be production-ready with best practices.
Return as JSON with filename as key and content as value.""",
            complexity="complex",
            metadata={"config_type": "enterprise"}
        )
        
        result = await self.agent_client.execute_task(
            config_task,
            tier=AgentTier.T2,
            context={"project_analysis": project_analysis}
        )
        
        return self._parse_config_files(result.output)
    
    async def _generate_documentation(
        self,
        project_analysis: Dict[str, Any],
        capsule: Dict[str, Any]
    ) -> Dict[str, str]:
        """Use AI to generate comprehensive documentation"""
        
        doc_task = Task(
            id="generate-docs",
            type="documentation",
            description=f"""Generate comprehensive documentation for this project:

Project Analysis:
{json.dumps(project_analysis, indent=2)}

Project Files: {list(capsule.get('source_code', {}).keys())}

Create professional documentation including:
1. README.md - comprehensive project overview
2. CONTRIBUTING.md - contribution guidelines
3. API documentation (if applicable)
4. Architecture documentation
5. Setup and installation guides
6. Usage examples
7. Troubleshooting guide
8. CHANGELOG.md template
9. Security documentation
10. Performance guidelines

Make it enterprise-grade with proper sections, badges, and professional formatting.
Return as JSON with filepath as key and content as value.""",
            complexity="complex",
            metadata={"doc_type": "enterprise"}
        )
        
        result = await self.agent_client.execute_task(
            doc_task,
            tier=AgentTier.T2,
            context={"project_analysis": project_analysis}
        )
        
        return self._parse_documentation_files(result.output)
    
    async def _generate_cicd_pipeline(
        self,
        project_analysis: Dict[str, Any],
        structure_plan: Dict[str, Any]
    ) -> Dict[str, str]:
        """Use AI to generate CI/CD pipeline configurations"""
        
        cicd_task = Task(
            id="generate-cicd",
            type="devops",
            description=f"""Generate CI/CD pipeline configurations for this project:

Project Analysis:
{json.dumps(project_analysis, indent=2)}

Create production-ready CI/CD configurations for:
1. GitHub Actions workflows
2. GitLab CI configuration (if applicable)
3. Jenkinsfile (if applicable)
4. Build scripts
5. Deployment configurations
6. Testing pipelines
7. Security scanning
8. Code quality checks
9. Release automation
10. Environment-specific deployments

Consider the project type and generate appropriate pipelines.
Return as JSON with filepath as key and content as value.""",
            complexity="complex",
            metadata={"cicd_type": "enterprise"}
        )
        
        result = await self.agent_client.execute_task(
            cicd_task,
            tier=AgentTier.T2,
            context={"project_analysis": project_analysis}
        )
        
        return self._parse_cicd_files(result.output)
    
    async def _generate_dev_tooling(
        self,
        project_analysis: Dict[str, Any]
    ) -> Dict[str, str]:
        """Use AI to generate development tooling configurations"""
        
        tooling_task = Task(
            id="generate-tooling",
            type="configuration",
            description=f"""Generate development tooling for this project:

Project Analysis:
{json.dumps(project_analysis, indent=2)}

Create configurations for:
1. Pre-commit hooks
2. Editor configurations (.editorconfig)
3. VS Code settings and recommended extensions
4. Debugging configurations
5. Code formatting rules
6. Linting rules
7. Git hooks
8. Development scripts
9. Environment setup scripts
10. Developer documentation

Make it developer-friendly and follow best practices.
Return as JSON with filepath as key and content as value.""",
            complexity="medium",
            metadata={"tooling_type": "developer"}
        )
        
        result = await self.agent_client.execute_task(
            tooling_task,
            tier=AgentTier.T1,
            context={"project_analysis": project_analysis}
        )
        
        return self._parse_tooling_files(result.output)
    
    async def _reorganize_code_structure(
        self,
        source_code: Dict[str, str],
        tests: Dict[str, str],
        structure_plan: Dict[str, Any]
    ) -> Dict[str, str]:
        """Use AI to intelligently reorganize code into proper structure"""
        
        reorg_task = Task(
            id="reorganize-code",
            type="refactoring",
            description=f"""Reorganize this code into the planned enterprise structure:

Current Files:
Source: {list(source_code.keys())}
Tests: {list(tests.keys())}

Target Structure:
{json.dumps(structure_plan, indent=2)}

Reorganize the files intelligently:
1. Move files to appropriate directories
2. Update import statements
3. Add __init__.py files where needed
4. Create proper module structure
5. Separate concerns appropriately
6. Add missing test files
7. Create interface/protocol files if needed
8. Add configuration files
9. Create utility modules
10. Ensure proper dependency management

Return as JSON with new filepath as key and updated content as value.""",
            complexity="complex",
            metadata={"reorg_type": "enterprise"}
        )
        
        result = await self.agent_client.execute_task(
            reorg_task,
            tier=AgentTier.T2,
            context={
                "source_code": source_code,
                "tests": tests,
                "structure_plan": structure_plan
            }
        )
        
        return self._parse_reorganized_code(result.output, source_code, tests)
    
    async def _add_enterprise_patterns(
        self,
        code_structure: Dict[str, str],
        project_analysis: Dict[str, Any]
    ) -> Dict[str, str]:
        """Use AI to add enterprise patterns like logging, monitoring, security"""
        
        patterns_task = Task(
            id="add-patterns",
            type="enhancement",
            description=f"""Add enterprise patterns to this project:

Project Analysis:
{json.dumps(project_analysis, indent=2)}

Current Structure Files: {list(code_structure.keys())[:10]}...

Add enterprise-grade patterns:
1. Structured logging setup
2. Error handling and recovery patterns
3. Health check endpoints
4. Metrics and monitoring integration
5. Security middleware/decorators
6. Caching layer setup
7. Rate limiting implementation
8. API versioning (if applicable)
9. Database migration setup (if applicable)
10. Feature flags system

Create new files and update existing ones as needed.
Return as JSON with filepath as key and content as value.""",
            complexity="complex",
            metadata={"patterns_type": "enterprise"}
        )
        
        result = await self.agent_client.execute_task(
            patterns_task,
            tier=AgentTier.T2,
            context={
                "project_analysis": project_analysis,
                "current_files": list(code_structure.keys())
            }
        )
        
        return self._parse_enterprise_patterns(result.output)
    
    # Helper methods for parsing AI responses
    def _parse_ai_response(self, output: Any) -> Dict[str, Any]:
        """Parse AI response into structured data"""
        if isinstance(output, dict):
            content = output.get("content", output)
        else:
            content = output
        
        if isinstance(content, str):
            try:
                # Try to extract JSON
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except:
                pass
        
        return content if isinstance(content, dict) else {}
    
    def _parse_config_files(self, output: Any) -> Dict[str, str]:
        """Parse configuration files from AI output"""
        parsed = self._parse_ai_response(output)
        return {k: v for k, v in parsed.items() if isinstance(v, str)}
    
    def _parse_documentation_files(self, output: Any) -> Dict[str, str]:
        """Parse documentation files from AI output"""
        parsed = self._parse_ai_response(output)
        return {k: v for k, v in parsed.items() if isinstance(v, str)}
    
    def _parse_cicd_files(self, output: Any) -> Dict[str, str]:
        """Parse CI/CD files from AI output"""
        parsed = self._parse_ai_response(output)
        return {k: v for k, v in parsed.items() if isinstance(v, str)}
    
    def _parse_tooling_files(self, output: Any) -> Dict[str, str]:
        """Parse tooling files from AI output"""
        parsed = self._parse_ai_response(output)
        return {k: v for k, v in parsed.items() if isinstance(v, str)}
    
    def _parse_reorganized_code(
        self, 
        output: Any, 
        original_source: Dict[str, str],
        original_tests: Dict[str, str]
    ) -> Dict[str, str]:
        """Parse reorganized code from AI output"""
        parsed = self._parse_ai_response(output)
        
        # If AI didn't provide a full reorganization, do basic reorganization
        if not parsed or len(parsed) < len(original_source):
            result = {}
            # Place source files in src directory
            for filename, content in original_source.items():
                result[f"src/{filename}"] = content
            # Place test files in tests directory  
            for filename, content in original_tests.items():
                result[f"tests/{filename}"] = content
            return result
        
        return {k: v for k, v in parsed.items() if isinstance(v, str)}
    
    def _parse_enterprise_patterns(self, output: Any) -> Dict[str, str]:
        """Parse enterprise pattern files from AI output"""
        parsed = self._parse_ai_response(output)
        return {k: v for k, v in parsed.items() if isinstance(v, str)}
    
    def _get_intelligent_default_structure(
        self, 
        project_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Intelligent fallback structure based on project type"""
        project_type = project_analysis.get("project_type", "general").lower()
        
        base_structure = {
            "src/": "Source code",
            "tests/": "Test files",
            "docs/": "Documentation",
            "scripts/": "Utility scripts",
            ".github/": "GitHub specific files",
            "config/": "Configuration files"
        }
        
        # Add type-specific directories
        if "api" in project_type or "web" in project_type:
            base_structure.update({
                "src/api/": "API endpoints",
                "src/models/": "Data models",
                "src/services/": "Business logic",
                "src/middleware/": "Middleware components",
                "src/utils/": "Utility functions"
            })
        
        if "data" in project_type or "ml" in project_type:
            base_structure.update({
                "notebooks/": "Jupyter notebooks",
                "data/": "Data files",
                "models/": "Trained models",
                "src/preprocessing/": "Data preprocessing",
                "src/training/": "Model training"
            })
        
        return base_structure