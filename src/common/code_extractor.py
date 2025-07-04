#!/usr/bin/env python3
"""
Global code extraction utilities
"""

import re
from typing import Tuple, Optional


def is_directory_listing(text: str) -> bool:
    """Detect if text contains directory listings instead of actual code"""
    if not text or len(text.strip()) < 10:
        return True
    
    # Common directory listing patterns
    directory_patterns = [
        r'├──',  # Tree structure symbols
        r'└──',
        r'│\s+├──',
        r'│\s+└──',
        r'src/\n',  # Directory paths without code
        r'tests/\n',
        r'^\s*[a-zA-Z_][a-zA-Z0-9_]*/$',  # Directory names ending with /
        r'conftest\.py\n',
        r'__init__\.py\n.*__init__\.py',  # Multiple __init__.py mentions
    ]
    
    # Check if text matches directory listing patterns
    for pattern in directory_patterns:
        if re.search(pattern, text, re.MULTILINE):
            return True
    
    # Check for lack of actual code indicators
    code_indicators = [
        r'def\s+\w+\(',  # Function definitions
        r'class\s+\w+',  # Class definitions
        r'import\s+\w+',  # Import statements
        r'from\s+\w+\s+import',  # From imports
        r'=\s*["\']',  # Variable assignments
        r'if\s+__name__\s*==\s*["\']__main__["\']',  # Main block
        r'@\w+',  # Decorators
        r'return\s+',  # Return statements
        r'print\(',  # Print statements
    ]
    
    has_code = any(re.search(pattern, text) for pattern in code_indicators)
    
    # If it has directory patterns but no code, it's a listing
    return not has_code and len(text.split('\n')) > 3


def extract_code_from_markdown(text: str) -> str:
    """Extract Python code from markdown blocks or return as-is"""
    if not text:
        return text
    
    # Check if it's a directory listing first
    if is_directory_listing(text):
        raise ValueError(f"Directory listing detected instead of code: {text[:100]}...")
        
    # Check for markdown code blocks
    if '```' in text:
        code_blocks = re.findall(r'```(?:python|py)?\n(.*?)```', text, re.DOTALL)
        if code_blocks:
            # Find the best code block (longest one with actual code)
            best_block = ""
            for block in code_blocks:
                block = block.strip()
                if not is_directory_listing(block) and len(block) > len(best_block):
                    best_block = block
            if best_block:
                return best_block
            else:
                raise ValueError("All code blocks contain directory listings")
    
    # Check final result
    cleaned = text.strip()
    if is_directory_listing(cleaned):
        raise ValueError(f"Content is a directory listing, not code: {cleaned[:100]}...")
    
    return cleaned


def extract_code_tests_docs(response: str) -> Tuple[str, str, str]:
    """Extract code, tests, and documentation from LLM response"""
    
    # Look for code blocks
    code_pattern = r'```(?:python)?\n(.*?)```'
    code_blocks = re.findall(code_pattern, response, re.DOTALL)
    
    code = ""
    tests = ""
    docs = ""
    
    if code_blocks:
        # First block is usually the main code
        code = code_blocks[0].strip()
        
        # Look for test code
        for block in code_blocks[1:]:
            if 'test' in block.lower() or 'assert' in block:
                tests = block.strip()
                break
        
        # Extract documentation from the explanation
        docs_before_code = response.split('```')[0].strip()
        if docs_before_code and len(docs_before_code) < 1000:
            docs = docs_before_code
    else:
        # Check if it's JSON
        try:
            import json
            parsed = json.loads(response)
            if isinstance(parsed, dict):
                code = parsed.get('code', '')
                tests = parsed.get('tests', '')
                docs = parsed.get('documentation', '')
        except:
            # Assume it's pure code
            code = response.strip()
    
    return code, tests, docs


def clean_code_output(output: dict) -> dict:
    """Clean code output by extracting from markdown if needed"""
    if isinstance(output, dict):
        # Clean the code field
        if 'code' in output and output['code']:
            try:
                output['code'] = extract_code_from_markdown(output['code'])
            except ValueError as e:
                # Directory listing detected - mark as invalid
                output['code'] = ""
                output['_extraction_error'] = str(e)
                output['_needs_regeneration'] = True
        
        # Clean content.code if it exists
        if 'content' in output and isinstance(output['content'], dict):
            if 'code' in output['content']:
                try:
                    output['content']['code'] = extract_code_from_markdown(output['content']['code'])
                except ValueError as e:
                    output['content']['code'] = ""
                    output['content']['_extraction_error'] = str(e)
                    output['content']['_needs_regeneration'] = True
    
    return output
