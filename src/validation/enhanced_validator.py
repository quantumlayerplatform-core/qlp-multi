"""
Enhanced code quality validation for production-grade code
"""

import re
from typing import Dict, List, Any, Tuple, Optional
import ast
import json
from dataclasses import dataclass, field

@dataclass
class ValidationIssue:
    """Represents a code quality issue"""
    type: str  # security, quality, style, performance
    severity: str  # critical, high, medium, low
    message: str
    line_number: Optional[int] = None
    suggestion: Optional[str] = None

class EnhancedCodeValidator:
    """Enhanced validator with security and quality checks"""
    
    def __init__(self):
        # Security patterns to detect
        self.security_patterns = [
            # Hardcoded secrets
            (r'password\s*=\s*["\'](?!.*\$|.*env|.*config|.*settings).*["\']', 
             "Hardcoded password detected", 
             "Use environment variables or secure configuration"),
            (r'api_key\s*=\s*["\'](?!.*\$|.*env|.*config).*["\']', 
             "Hardcoded API key detected",
             "Use environment variables for API keys"),
            (r'secret\s*=\s*["\'](?!.*\$|.*env|.*config).*["\']', 
             "Hardcoded secret detected",
             "Use environment variables for secrets"),
            
            # SQL injection vulnerabilities
            (r'query\s*=\s*["\'].*\%s.*["\']|query\s*=\s*f["\'].*\{.*\}.*["\']', 
             "Potential SQL injection vulnerability",
             "Use parameterized queries"),
            (r'execute\(["\'].*\+.*["\']|execute\(f["\'].*\{.*\}', 
             "SQL injection risk in execute statement",
             "Use parameterized queries with placeholders"),
            
            # Weak password hashing
            (r'hashlib\.(md5|sha1)\s*\(', 
             "Weak hashing algorithm for passwords",
             "Use bcrypt, scrypt, or argon2 for password hashing"),
            
            # Insecure random
            (r'random\.(random|randint|choice)\s*\(', 
             "Insecure random number generation",
             "Use secrets module for security-sensitive randomness"),
            
            # Broad exception handling
            (r'except\s*:', 
             "Broad exception handling detected",
             "Catch specific exceptions"),
            (r'except\s+Exception\s*:', 
             "Catching base Exception is too broad",
             "Catch specific exceptions"),
            
            # Timing attack vulnerabilities
            (r'==\s*.*password|password.*\s*==', 
             "Potential timing attack vulnerability",
             "Use secrets.compare_digest() for secure comparison"),
            
            # Unsafe deserialization
            (r'pickle\.loads?\s*\(', 
             "Unsafe deserialization with pickle",
             "Validate input before deserializing or use safer formats"),
            
            # Command injection
            (r'os\.(system|popen)\s*\(.*\+|subprocess\.(call|run)\s*\(.*\+', 
             "Potential command injection",
             "Use subprocess with list arguments, not string concatenation"),
            
            # Path traversal
            (r'open\s*\(.*\+.*["\']\.\.', 
             "Potential path traversal vulnerability",
             "Sanitize file paths and use os.path.join"),
            
            # CORS misconfiguration
            (r'Access-Control-Allow-Origin.*\*', 
             "Insecure CORS configuration",
             "Specify allowed origins explicitly"),
            
            # Missing HTTPS
            (r'http://(?!localhost|127\.0\.0\.1)', 
             "Insecure HTTP connection",
             "Use HTTPS for external connections"),
        ]
        
        # Code quality patterns
        self.quality_patterns = [
            # Long functions (simple heuristic)
            (r'def\s+\w+.*:\n(?:.*\n){50,}', 
             "Function is too long",
             "Break down into smaller functions"),
            
            # Missing error handling
            (r'requests\.(get|post|put|delete)\s*\([^)]*\)(?!\s*\.raise_for_status)', 
             "Missing error handling for HTTP request",
             "Check response status or use raise_for_status()"),
            
            # Hardcoded values
            (r'(port|host|url)\s*=\s*["\'](?!.*\$|.*env|.*config).*["\']', 
             "Hardcoded configuration value",
             "Use configuration files or environment variables"),
            
            # Missing input validation
            (r'request\.(args|form|json)\s*\[["\'].*["\']\](?!\s*\.strip\(\)|\s*\.replace)', 
             "Missing input validation",
             "Validate and sanitize user input"),
            
            # Synchronous I/O in async context
            (r'async\s+def.*\n(?:.*\n)*?.*(?:open|requests\.)', 
             "Synchronous I/O in async function",
             "Use async libraries (aiofiles, httpx)"),
        ]
    
    async def validate_code_quality(self, code: str, language: str) -> Dict[str, Any]:
        """Perform enhanced code quality validation"""
        issues = []
        
        # Security checks
        security_issues = self._check_security_patterns(code)
        issues.extend(security_issues)
        
        # Quality checks
        quality_issues = self._check_quality_patterns(code)
        issues.extend(quality_issues)
        
        # Language-specific checks
        if language.lower() == "python":
            python_issues = self._check_python_specific(code)
            issues.extend(python_issues)
        elif language.lower() in ["javascript", "typescript"]:
            js_issues = self._check_javascript_specific(code)
            issues.extend(js_issues)
        
        # Calculate security score
        critical_count = sum(1 for issue in issues if issue.severity == "critical")
        high_count = sum(1 for issue in issues if issue.severity == "high")
        security_score = max(0, 100 - (critical_count * 25) - (high_count * 10))
        
        return {
            "passed": len(issues) == 0,
            "issues": [self._issue_to_dict(issue) for issue in issues],
            "security_score": security_score,
            "total_issues": len(issues),
            "critical_issues": critical_count,
            "high_issues": high_count
        }
    
    def _check_security_patterns(self, code: str) -> List[ValidationIssue]:
        """Check for security vulnerabilities"""
        issues = []
        lines = code.split('\n')
        
        for pattern, message, suggestion in self.security_patterns:
            for i, line in enumerate(lines):
                if re.search(pattern, line, re.IGNORECASE):
                    # Skip if it's in a comment
                    if line.strip().startswith('#') or line.strip().startswith('//'):
                        continue
                    
                    severity = "critical" if any(keyword in message.lower() 
                                               for keyword in ["injection", "hardcoded password", "weak hash"]) else "high"
                    
                    issues.append(ValidationIssue(
                        type="security",
                        severity=severity,
                        message=message,
                        line_number=i + 1,
                        suggestion=suggestion
                    ))
        
        return issues
    
    def _check_quality_patterns(self, code: str) -> List[ValidationIssue]:
        """Check for code quality issues"""
        issues = []
        
        for pattern, message, suggestion in self.quality_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            for match in matches:
                # Find line number
                line_number = code[:match.start()].count('\n') + 1
                
                issues.append(ValidationIssue(
                    type="quality",
                    severity="medium",
                    message=message,
                    line_number=line_number,
                    suggestion=suggestion
                ))
        
        return issues
    
    def _check_python_specific(self, code: str) -> List[ValidationIssue]:
        """Python-specific checks"""
        issues = []
        
        try:
            # Parse AST for deeper analysis
            tree = ast.parse(code)
            
            # Check for missing docstrings
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    if not ast.get_docstring(node):
                        issues.append(ValidationIssue(
                            type="style",
                            severity="low",
                            message=f"Missing docstring for {node.name}",
                            line_number=node.lineno,
                            suggestion="Add a docstring describing the function/class"
                        ))
            
            # Check for mutable default arguments
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    for default in node.args.defaults:
                        if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                            issues.append(ValidationIssue(
                                type="quality",
                                severity="high",
                                message=f"Mutable default argument in function {node.name}",
                                line_number=node.lineno,
                                suggestion="Use None as default and initialize in function body"
                            ))
        
        except SyntaxError:
            # If AST parsing fails, it's already caught by syntax validation
            pass
        
        return issues
    
    def _check_javascript_specific(self, code: str) -> List[ValidationIssue]:
        """JavaScript/TypeScript specific checks"""
        issues = []
        
        # Check for var usage (should use let/const)
        var_pattern = r'\bvar\s+\w+'
        for match in re.finditer(var_pattern, code):
            line_number = code[:match.start()].count('\n') + 1
            issues.append(ValidationIssue(
                type="style",
                severity="low",
                message="Use 'let' or 'const' instead of 'var'",
                line_number=line_number,
                suggestion="Replace 'var' with 'let' or 'const'"
            ))
        
        # Check for == instead of ===
        eq_pattern = r'[^=!]==[^=]'
        for match in re.finditer(eq_pattern, code):
            line_number = code[:match.start()].count('\n') + 1
            issues.append(ValidationIssue(
                type="quality",
                severity="medium",
                message="Use '===' for strict equality",
                line_number=line_number,
                suggestion="Replace '==' with '==='"
            ))
        
        return issues
    
    def _issue_to_dict(self, issue: ValidationIssue) -> Dict[str, Any]:
        """Convert ValidationIssue to dictionary"""
        return {
            "type": issue.type,
            "severity": issue.severity,
            "message": issue.message,
            "line_number": issue.line_number,
            "suggestion": issue.suggestion
        }

# Global instance
enhanced_validator = EnhancedCodeValidator()