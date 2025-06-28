#!/usr/bin/env python3
"""
Global code extraction utilities
"""

import re
from typing import Tuple, Optional


def extract_code_from_markdown(text: str) -> str:
    """Extract Python code from markdown blocks or return as-is"""
    if not text:
        return text
        
    # Check for markdown code blocks
    if '```' in text:
        code_blocks = re.findall(r'```(?:python)?\n(.*?)```', text, re.DOTALL)
        if code_blocks:
            return code_blocks[0].strip()
    
    return text.strip()


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
            output['code'] = extract_code_from_markdown(output['code'])
        
        # Clean content.code if it exists
        if 'content' in output and isinstance(output['content'], dict):
            if 'code' in output['content']:
                output['content']['code'] = extract_code_from_markdown(output['content']['code'])
    
    return output
