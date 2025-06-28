"""
Confidence Scoring System for Code Generation
"""

from typing import Dict, Any, Optional
import ast
import subprocess
import tempfile
import structlog

logger = structlog.get_logger()


class ConfidenceScorer:
    """Multi-factor confidence scoring for generated code"""
    
    def calculate_confidence(self, code_result: Dict[str, Any]) -> float:
        """Calculate confidence score based on multiple factors"""
        
        code = code_result.get("code", "")
        tests = code_result.get("tests", "")
        
        # Handle case where code might be in raw_response
        if not code and "raw_response" in code_result:
            # Extract from raw response
            code, tests, _ = self._extract_code_from_response(code_result["raw_response"])
            if not code_result.get("tests"):
                code_result["tests"] = tests
        
        factors = {
            "syntax_valid": self.check_syntax(code),
            "has_tests": bool(tests and len(tests) > 50),
            "passes_tests": self.run_tests(code, tests) if tests else 0.5,
            "has_error_handling": self.check_error_handling(code),
            "has_type_hints": self.check_type_hints(code),
            "has_docstrings": self.check_docstrings(code),
            "complexity_appropriate": self.check_complexity(code),
            "security_score": code_result.get("security_analysis", {}).get("score", 0.8),
            "review_score": code_result.get("review", {}).get("score", 0.8),
        }
        
        # Weighted scoring
        weights = {
            "syntax_valid": 0.20,      # 20% - Must compile
            "has_tests": 0.15,         # 15% - Tests exist
            "passes_tests": 0.20,      # 20% - Tests pass
            "has_error_handling": 0.10, # 10% - Handles errors
            "has_type_hints": 0.05,    # 5%  - Type safety
            "has_docstrings": 0.05,    # 5%  - Documentation
            "complexity_appropriate": 0.05, # 5% - Not too complex
            "security_score": 0.10,    # 10% - Security review
            "review_score": 0.10,      # 10% - Code review
        }
        
        # Calculate weighted score
        confidence = sum(
            factors.get(k, 0) * weights[k] 
            for k in weights
        )
        
        # Log breakdown for debugging
        logger.debug("Confidence factors", factors=factors, total=confidence)
        
        return min(confidence, 0.99)  # Cap at 99%
    
    def check_syntax(self, code: str) -> float:
        """Check if code has valid Python syntax"""
        if not code or not code.strip():
            return 0.0
            
        # Clean code if needed
        clean_code = self._clean_code(code)
        
        try:
            ast.parse(clean_code)
            return 1.0
        except SyntaxError:
            return 0.0
    
    def _clean_code(self, code: str) -> str:
        """Clean code by removing markdown blocks if present"""
        import re
        
        # Check for markdown code blocks
        if '```' in code:
            code_blocks = re.findall(r'```(?:python)?\n(.*?)```', code, re.DOTALL)
            if code_blocks:
                return code_blocks[0].strip()
        
        return code.strip()
    
    def _extract_code_from_response(self, response: str) -> tuple[str, str, str]:
        """Extract code, tests, and docs from response"""
        import re
        
        code_pattern = r'```(?:python)?\n(.*?)```'
        code_blocks = re.findall(code_pattern, response, re.DOTALL)
        
        code = ""
        tests = ""
        docs = ""
        
        if code_blocks:
            code = code_blocks[0].strip()
            for block in code_blocks[1:]:
                if 'test' in block.lower() or 'assert' in block:
                    tests = block.strip()
                    break
            docs_before = response.split('```')[0].strip()
            if docs_before and len(docs_before) < 1000:
                docs = docs_before
        else:
            code = response.strip()
        
        return code, tests, docs
    
    def check_error_handling(self, code: str) -> float:
        """Check if code has proper error handling"""
        try:
            tree = ast.parse(code)
            try_blocks = sum(1 for node in ast.walk(tree) if isinstance(node, ast.Try))
            functions = sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))
            
            if functions == 0:
                return 0.5
            
            # Good if at least 30% of functions have error handling
            ratio = try_blocks / max(functions * 0.3, 1)
            return min(ratio, 1.0)
        except:
            return 0.0
    
    def check_type_hints(self, code: str) -> float:
        """Check if code has type hints"""
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
                return 0.5
            
            return functions_with_hints / total_functions
        except:
            return 0.0
    
    def check_docstrings(self, code: str) -> float:
        """Check if code has docstrings"""
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
                return 0.5
            
            return items_with_docs / total_items
        except:
            return 0.0
    
    def check_complexity(self, code: str) -> float:
        """Check if code complexity is appropriate"""
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
            return 0.5
    
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
        # For now, return a simulated score
        # In production, this would actually execute tests
        if not tests:
            return 0.0
        
        # Simple heuristic: if tests exist and code is valid, assume 80% pass
        if self.check_syntax(code) and self.check_syntax(tests):
            return 0.8
        else:
            return 0.3
