"""
Enhanced Confidence Scorer with Syntax Fallback
Improves handling of generated code that may have formatting issues
"""

from typing import Dict, Any, Optional
import ast
import subprocess
import tempfile
import structlog
import re

logger = structlog.get_logger()


class EnhancedConfidenceScorer:
    """Enhanced confidence scoring with better syntax handling"""
    
    def calculate_confidence(self, code_result: Dict[str, Any]) -> float:
        """Calculate confidence score based on multiple factors"""
        
        code = code_result.get("code", "")
        tests = code_result.get("tests", "")
        
        # Clean up code for better syntax checking
        cleaned_code = self._clean_code(code)
        
        factors = {
            "syntax_valid": self.check_syntax(cleaned_code),
            "has_tests": bool(tests and len(tests) > 50),
            "passes_tests": self.run_tests(cleaned_code, tests) if tests else 0.5,
            "has_error_handling": self.check_error_handling(cleaned_code),
            "has_type_hints": self.check_type_hints(cleaned_code),
            "has_docstrings": self.check_docstrings(cleaned_code),
            "complexity_appropriate": self.check_complexity(cleaned_code),
            "security_score": code_result.get("security_analysis", {}).get("score", 0.8),
            "review_score": code_result.get("review", {}).get("score", 0.8),
            "code_structure": self.check_code_structure(cleaned_code)
        }
        
        # Weighted scoring
        weights = {
            "syntax_valid": 0.15,      # 15% - Must compile
            "has_tests": 0.10,         # 10% - Tests exist
            "passes_tests": 0.15,      # 15% - Tests pass
            "has_error_handling": 0.10, # 10% - Handles errors
            "has_type_hints": 0.05,    # 5%  - Type safety
            "has_docstrings": 0.05,    # 5%  - Documentation
            "complexity_appropriate": 0.10, # 10% - Not too complex
            "security_score": 0.10,    # 10% - Security review
            "review_score": 0.10,      # 10% - Code review
            "code_structure": 0.10     # 10% - Well structured
        }
        
        # Calculate weighted score
        confidence = sum(
            factors.get(k, 0) * weights[k] 
            for k in weights
        )
        
        # Log breakdown for debugging
        logger.debug("Enhanced confidence factors", factors=factors, total=confidence)
        
        return min(confidence, 0.99)  # Cap at 99%
    
    def _clean_code(self, code: str) -> str:
        """Clean up code for better parsing"""
        if not code:
            return ""
        
        # Remove markdown code blocks if present
        code = re.sub(r'^```[a-zA-Z]*\n', '', code, flags=re.MULTILINE)
        code = re.sub(r'\n```$', '', code, flags=re.MULTILINE)
        
        # Remove any non-code artifacts
        lines = []
        for line in code.split('\n'):
            # Skip obvious non-code lines
            if line.strip().startswith('#') and not line.strip().startswith('#!'):
                lines.append(line)
            elif line.strip() and not line.strip().startswith('//'):
                lines.append(line)
            elif not line.strip():
                lines.append(line)
        
        return '\n'.join(lines)
    
    def check_syntax(self, code: str) -> float:
        """Check if code has valid Python syntax"""
        if not code.strip():
            return 0.0
            
        try:
            ast.parse(code)
            return 1.0
        except SyntaxError as e:
            # Partial credit for nearly valid syntax
            if "unexpected EOF" in str(e):
                return 0.3
            elif "invalid syntax" in str(e):
                # Check if it's just missing colons or similar
                if any(keyword in code for keyword in ['def', 'class', 'if', 'for', 'while']):
                    return 0.5
            return 0.0
    
    def check_code_structure(self, code: str) -> float:
        """Check if code has good structure"""
        if not code.strip():
            return 0.0
        
        score = 0.0
        
        # Check for functions or classes
        if 'def ' in code or 'class ' in code:
            score += 0.3
        
        # Check for imports
        if 'import ' in code:
            score += 0.2
        
        # Check for main guard
        if '__name__' in code and '__main__' in code:
            score += 0.1
        
        # Check for reasonable length
        lines = code.split('\n')
        if 10 <= len(lines) <= 200:
            score += 0.2
        elif 5 <= len(lines) < 10:
            score += 0.1
        
        # Check for comments
        if any(line.strip().startswith('#') for line in lines):
            score += 0.2
        
        return min(score, 1.0)
    
    def check_error_handling(self, code: str) -> float:
        """Check if code has proper error handling"""
        if not code.strip():
            return 0.0
            
        try:
            tree = ast.parse(code)
            try_blocks = sum(1 for node in ast.walk(tree) if isinstance(node, ast.Try))
            functions = sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))
            
            if functions == 0:
                # Check for try blocks in general code
                return min(try_blocks * 0.3, 1.0)
            
            # Good if at least 30% of functions have error handling
            ratio = try_blocks / max(functions * 0.3, 1)
            return min(ratio, 1.0)
        except:
            # Give partial credit if code mentions error handling
            if any(word in code for word in ['try:', 'except', 'Exception', 'error']):
                return 0.3
            return 0.0
    
    def check_type_hints(self, code: str) -> float:
        """Check if code has type hints"""
        if not code.strip():
            return 0.0
            
        try:
            tree = ast.parse(code)
            functions_with_hints = 0
            total_functions = 0
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    total_functions += 1
                    if node.returns or any(arg.annotation for arg in node.args.args):
                        functions_with_hints += 1
            
            if total_functions == 0:
                # Check for type hints in variable annotations
                if any(word in code for word in [': int', ': str', ': float', ': bool', ': List', ': Dict']):
                    return 0.5
                return 0.0
            
            return functions_with_hints / total_functions
        except:
            # Partial credit for attempting type hints
            if '->' in code or ': ' in code:
                return 0.3
            return 0.0
    
    def check_docstrings(self, code: str) -> float:
        """Check if code has docstrings"""
        if not code.strip():
            return 0.0
            
        try:
            tree = ast.parse(code)
            items_with_docs = 0
            total_items = 0
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    total_items += 1
                    if ast.get_docstring(node):
                        items_with_docs += 1
            
            if total_items == 0:
                # Check for module docstring
                if '"""' in code or "'''" in code:
                    return 0.5
                return 0.0
            
            return items_with_docs / total_items
        except:
            # Partial credit for having docstrings
            if '"""' in code or "'''" in code:
                return 0.3
            return 0.0
    
    def check_complexity(self, code: str) -> float:
        """Check if code complexity is appropriate"""
        if not code.strip():
            return 0.0
            
        try:
            tree = ast.parse(code)
            
            # Count nested levels
            max_depth = 0
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    depth = self._get_max_depth(node)
                    max_depth = max(max_depth, depth)
            
            # Good if max depth <= 4
            if max_depth <= 2:
                return 1.0
            elif max_depth <= 4:
                return 0.8
            elif max_depth <= 6:
                return 0.6
            else:
                return 0.4
        except:
            # Default to medium complexity if can't parse
            return 0.7
    
    def _get_max_depth(self, node, current_depth=0):
        """Get maximum nesting depth in a node"""
        max_depth = current_depth
        
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                child_depth = self._get_max_depth(child, current_depth + 1)
                max_depth = max(max_depth, child_depth)
            else:
                child_depth = self._get_max_depth(child, current_depth)
                max_depth = max(max_depth, child_depth)
        
        return max_depth
    
    def run_tests(self, code: str, tests: str) -> float:
        """Run tests and return pass rate"""
        if not tests:
            return 0.0
        
        # Check if both code and tests are syntactically valid
        code_valid = self.check_syntax(code) > 0
        tests_valid = self.check_syntax(tests) > 0
        
        if code_valid and tests_valid:
            # High confidence if both are valid
            return 0.9
        elif code_valid or tests_valid:
            # Medium confidence if one is valid
            return 0.6
        else:
            # Low confidence if neither is valid
            return 0.3
