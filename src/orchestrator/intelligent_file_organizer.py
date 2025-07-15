"""
Intelligent File Organization using LLM
Universal file categorization and organization for any language/framework
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import structlog
from openai import AsyncOpenAI, AsyncAzureOpenAI

from src.common.config import settings

logger = structlog.get_logger()


class FileType(Enum):
    SOURCE = "source"
    TEST = "test"
    DOCUMENTATION = "documentation"
    CONFIG = "config"
    SCRIPT = "script"
    MIXED = "mixed"
    UNKNOWN = "unknown"


@dataclass
class FileAnalysis:
    """Analysis result for a piece of code"""
    file_type: FileType
    primary_purpose: str
    contains_tests: bool
    contains_implementation: bool
    contains_documentation: bool
    suggested_files: List[Dict[str, Any]]
    language_insights: Dict[str, Any]
    confidence: float


class IntelligentFileOrganizer:
    """LLM-powered file organization for universal language support"""
    
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
    
    async def analyze_and_organize_code(
        self,
        code: str,
        task_context: Dict[str, Any],
        project_context: Dict[str, Any]
    ) -> FileAnalysis:
        """
        Analyze code and determine how to organize it into files
        
        Args:
            code: The code to analyze
            task_context: Context about the task (type, description, etc.)
            project_context: Overall project context (language, structure, etc.)
            
        Returns:
            FileAnalysis with categorization and file suggestions
        """
        
        # Build a comprehensive prompt for the LLM
        prompt = self._build_analysis_prompt(code, task_context, project_context)
        
        try:
            # Use appropriate model
            model = getattr(settings, 'AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4')
            
            response = await self.llm_client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert software architect and code organizer. 
                        Your job is to analyze code and determine the best way to organize it into files,
                        following best practices for the detected language and framework.
                        Always respond with valid JSON."""
                    },
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=2000
            )
            
            # Parse the response
            result = json.loads(response.choices[0].message.content)
            
            # Convert to FileAnalysis
            return self._parse_analysis_result(result)
            
        except Exception as e:
            logger.error(f"Failed to analyze code with LLM: {e}")
            # Fallback to basic analysis
            return self._fallback_analysis(code, task_context)
    
    def _build_analysis_prompt(
        self,
        code: str,
        task_context: Dict[str, Any],
        project_context: Dict[str, Any]
    ) -> str:
        """Build comprehensive prompt for code analysis"""
        
        language = project_context.get('file_structure', {}).get('primary_language', 'unknown')
        task_type = task_context.get('type', 'unknown')
        task_description = task_context.get('description', '')
        
        return f"""
Analyze this code and determine how to organize it into proper files.

CONTEXT:
- Primary Language: {language}
- Task Type: {task_type}
- Task Description: {task_description}
- Project Structure: {project_context.get('project_structure', 'unknown')}
- Architecture Pattern: {project_context.get('architecture_pattern', 'unknown')}

CODE TO ANALYZE:
```{language}
{code}
```

INSTRUCTIONS:
1. Identify what this code contains (implementation, tests, documentation, etc.)
2. If it contains mixed content, intelligently split it into appropriate files
3. Follow best practices for {language} projects
4. Preserve all functionality while organizing properly
5. Use appropriate naming conventions for the detected language/framework

RESPOND WITH JSON:
{{
    "file_type": "source|test|documentation|config|mixed",
    "primary_purpose": "describe main purpose",
    "contains_tests": true/false,
    "contains_implementation": true/false,
    "contains_documentation": true/false,
    "confidence": 0.0-1.0,
    "suggested_files": [
        {{
            "filename": "appropriate_name.ext",
            "directory": "src|tests|docs|config|scripts|lib|etc",
            "content": "exact content for this file",
            "purpose": "what this file does",
            "file_type": "source|test|documentation|config"
        }}
    ],
    "language_insights": {{
        "detected_language": "actual language if different from context",
        "framework": "detected framework/library",
        "patterns": ["design patterns", "coding patterns found"],
        "conventions": "naming/structure conventions observed",
        "dependencies": ["detected dependencies/imports"]
    }}
}}

IMPORTANT:
- For mixed content, split intelligently (e.g., separate tests from implementation)
- Preserve ALL code - don't drop anything
- If code has both function and tests, create separate files
- Use language-appropriate file extensions and naming
- For tests, use the language's testing conventions (test_*.py, *.test.js, *_test.go, etc.)
"""
    
    def _parse_analysis_result(self, result: Dict[str, Any]) -> FileAnalysis:
        """Parse LLM response into FileAnalysis"""
        
        file_type_str = result.get('file_type', 'unknown').lower()
        file_type_map = {
            'source': FileType.SOURCE,
            'test': FileType.TEST,
            'documentation': FileType.DOCUMENTATION,
            'config': FileType.CONFIG,
            'script': FileType.SCRIPT,
            'mixed': FileType.MIXED
        }
        
        return FileAnalysis(
            file_type=file_type_map.get(file_type_str, FileType.UNKNOWN),
            primary_purpose=result.get('primary_purpose', ''),
            contains_tests=result.get('contains_tests', False),
            contains_implementation=result.get('contains_implementation', False),
            contains_documentation=result.get('contains_documentation', False),
            suggested_files=result.get('suggested_files', []),
            language_insights=result.get('language_insights', {}),
            confidence=result.get('confidence', 0.0)
        )
    
    def _fallback_analysis(
        self,
        code: str,
        task_context: Dict[str, Any]
    ) -> FileAnalysis:
        """Basic fallback analysis if LLM fails"""
        
        # Simple heuristics as fallback
        contains_tests = any(pattern in code.lower() for pattern in [
            'test', 'spec', 'assert', 'expect', 'should'
        ])
        
        contains_impl = any(pattern in code for pattern in [
            'def ', 'function ', 'class ', 'const ', 'var ', 'let '
        ])
        
        task_type = task_context.get('type', '').lower()
        
        if 'test' in task_type:
            file_type = FileType.TEST
        elif 'doc' in task_type:
            file_type = FileType.DOCUMENTATION
        elif contains_tests and contains_impl:
            file_type = FileType.MIXED
        elif contains_tests:
            file_type = FileType.TEST
        else:
            file_type = FileType.SOURCE
            
        # Basic file suggestion
        suggested_files = [{
            "filename": "code.txt",
            "directory": "src",
            "content": code,
            "purpose": "Generated code",
            "file_type": file_type.value
        }]
        
        return FileAnalysis(
            file_type=file_type,
            primary_purpose="Fallback analysis",
            contains_tests=contains_tests,
            contains_implementation=contains_impl,
            contains_documentation=False,
            suggested_files=suggested_files,
            language_insights={},
            confidence=0.3
        )


async def organize_code_intelligently(
    code: str,
    task_context: Dict[str, Any],
    project_context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Main function to organize code intelligently using LLM
    
    Returns dict with:
    - source_files: Dict[filename, content]
    - test_files: Dict[filename, content]
    - doc_files: Dict[filename, content]
    - config_files: Dict[filename, content]
    - analysis: The full FileAnalysis object
    """
    
    organizer = IntelligentFileOrganizer()
    analysis = await organizer.analyze_and_organize_code(
        code, task_context, project_context
    )
    
    # Organize files by type
    source_files = {}
    test_files = {}
    doc_files = {}
    config_files = {}
    script_files = {}
    
    for file_info in analysis.suggested_files:
        filename = file_info['filename']
        content = file_info['content']
        file_type = file_info.get('file_type', 'source')
        
        if file_type == 'test':
            test_files[filename] = content
        elif file_type == 'documentation':
            doc_files[filename] = content
        elif file_type == 'config':
            config_files[filename] = content
        elif file_type == 'script':
            script_files[filename] = content
        else:
            source_files[filename] = content
    
    logger.info(
        f"Organized code into {len(source_files)} source, "
        f"{len(test_files)} test, {len(doc_files)} doc files",
        confidence=analysis.confidence,
        language=analysis.language_insights.get('detected_language', 'unknown')
    )
    
    return {
        'source_files': source_files,
        'test_files': test_files,
        'doc_files': doc_files,
        'config_files': config_files,
        'script_files': script_files,
        'analysis': analysis,
        'success': True
    }