#!/usr/bin/env python3
"""
Comprehensive QLCapsule Validation System
Determines if a capsule is "good" for production use
"""

from typing import Dict, List, Tuple, Optional, Any
import asyncio
from dataclasses import dataclass
from enum import Enum
import ast
import re
from datetime import datetime
import structlog

from src.common.models import QLCapsule, ValidationReport, ValidationCheck, ValidationStatus
from src.sandbox.client import SandboxServiceClient

logger = structlog.get_logger()


class ValidationLevel(Enum):
    BASIC = "basic"          # Syntax, imports, structure
    FUNCTIONAL = "functional" # Tests pass, code runs
    QUALITY = "quality"      # Performance, security, best practices  
    PRODUCTION = "production" # Deployment ready, scalable, maintainable


@dataclass
class ValidationResult:
    level: ValidationLevel
    passed: bool
    score: float  # 0.0 to 1.0
    metrics: Dict[str, Any]
    issues: List[str]
    recommendations: List[str]


class CapsuleValidator:
    """Comprehensive validation to determine if a capsule is 'good'"""
    
    def __init__(self, sandbox_client: Optional[SandboxServiceClient] = None):
        self.sandbox = sandbox_client or SandboxServiceClient(base_url="http://localhost:8004")
        
    async def validate_capsule(self, capsule: QLCapsule) -> Dict[str, ValidationResult]:
        """Run all validation levels and return comprehensive results"""
        
        results = {}
        
        # Level 1: Basic Validation
        logger.info("Running basic validation", capsule_id=capsule.id)
        results['basic'] = await self.validate_basic(capsule)
        if not results['basic'].passed:
            logger.warning("Basic validation failed", score=results['basic'].score)
            results['overall'] = self.calculate_overall_score(results)
            return results
            
        # Level 2: Functional Validation
        logger.info("Running functional validation", capsule_id=capsule.id)
        results['functional'] = await self.validate_functional(capsule)
        if not results['functional'].passed:
            logger.warning("Functional validation failed", score=results['functional'].score)
            results['overall'] = self.calculate_overall_score(results)
            return results
            
        # Level 3: Quality Validation
        logger.info("Running quality validation", capsule_id=capsule.id)
        results['quality'] = await self.validate_quality(capsule)
        
        # Level 4: Production Validation
        logger.info("Running production validation", capsule_id=capsule.id)
        results['production'] = await self.validate_production(capsule)
        
        # Calculate overall score
        results['overall'] = self.calculate_overall_score(results)
        
        logger.info(
            "Validation complete",
            capsule_id=capsule.id,
            overall_score=results['overall'].score,
            passed=results['overall'].passed
        )
        
        return results
    
    async def validate_basic(self, capsule: QLCapsule) -> ValidationResult:
        """Check syntax, structure, dependencies"""
        
        checks = {}
        issues = []
        recommendations = []
        
        # Check syntax for all source files
        syntax_results = await self.check_syntax(capsule.source_code)
        checks['syntax_valid'] = syntax_results['valid']
        if not syntax_results['valid']:
            issues.extend(syntax_results['errors'])
            recommendations.append("Fix syntax errors in source files")
        
        # Check imports
        import_results = await self.check_imports(capsule.source_code)
        checks['imports_resolved'] = import_results['valid']
        if not import_results['valid']:
            issues.extend(import_results['missing'])
            recommendations.append("Add missing dependencies to requirements")
        
        # Check structure
        structure_valid = self.check_structure(capsule)
        checks['structure_valid'] = structure_valid
        if not structure_valid:
            issues.append("Incomplete project structure")
            recommendations.append("Ensure all required files are present")
        
        # Check documentation
        has_docs = bool(capsule.documentation) and len(capsule.documentation) > 100
        checks['has_documentation'] = has_docs
        if not has_docs:
            issues.append("Missing or insufficient documentation")
            recommendations.append("Add comprehensive documentation")
        
        passed = all(checks.values())
        score = sum(1 for v in checks.values() if v) / len(checks)
        
        return ValidationResult(
            level=ValidationLevel.BASIC,
            passed=passed,
            score=score,
            metrics=checks,
            issues=issues,
            recommendations=recommendations
        )
    
    async def validate_functional(self, capsule: QLCapsule) -> ValidationResult:
        """Run code and tests in sandbox"""
        
        checks = {}
        issues = []
        recommendations = []
        metrics = {}
        
        try:
            # Prepare code for execution
            main_file = self._get_main_file(capsule.source_code)
            if not main_file:
                checks['code_executes'] = False
                issues.append("No main file found")
            else:
                # Execute in sandbox
                execution_result = await self.sandbox.execute(
                    code=capsule.source_code[main_file],
                    language="python"
                )
                
                checks['code_executes'] = execution_result.success
                checks['no_runtime_errors'] = not bool(execution_result.error)
                
                if execution_result.error:
                    issues.append(f"Runtime error: {execution_result.error}")
                    recommendations.append("Fix runtime errors")
                
                metrics['execution_time'] = execution_result.execution_time
                metrics['memory_usage'] = execution_result.metadata.get('resource_usage', {}).get('memory_used', 0)
            
            # Run tests if available
            if capsule.tests:
                test_results = await self.run_tests_in_sandbox(capsule)
                checks['all_tests_pass'] = test_results['pass_rate'] == 1.0
                checks['has_tests'] = True
                metrics['test_coverage'] = test_results.get('coverage', 0)
                metrics['test_pass_rate'] = test_results['pass_rate']
                
                if test_results['pass_rate'] < 1.0:
                    issues.append(f"Tests failing: {test_results['failed']} failed")
                    recommendations.append("Fix failing tests")
            else:
                checks['has_tests'] = False
                checks['all_tests_pass'] = False
                issues.append("No tests found")
                recommendations.append("Add comprehensive test suite")
            
            # Check resource usage
            resource_ok = metrics.get('memory_usage', 0) < 100  # MB
            checks['resource_usage_ok'] = resource_ok
            if not resource_ok:
                issues.append("High resource usage detected")
                recommendations.append("Optimize memory usage")
                
        except Exception as e:
            logger.error(f"Functional validation error: {e}")
            checks['code_executes'] = False
            issues.append(f"Validation error: {str(e)}")
        
        passed = checks.get('code_executes', False) and checks.get('no_runtime_errors', True)
        score = sum(1 for v in checks.values() if v) / len(checks) if checks else 0
        
        return ValidationResult(
            level=ValidationLevel.FUNCTIONAL,
            passed=passed,
            score=score,
            metrics={**checks, **metrics},
            issues=issues,
            recommendations=recommendations
        )
    
    async def validate_quality(self, capsule: QLCapsule) -> ValidationResult:
        """Check code quality, security, performance"""
        
        # Run multiple quality checks
        quality_metrics = {}
        issues = []
        recommendations = []
        
        # Code quality checks
        for file_path, code in capsule.source_code.items():
            if file_path.endswith('.py'):
                file_metrics = await self.analyze_code_quality(code)
                quality_metrics[file_path] = file_metrics
                
                if file_metrics['complexity'] > 10:
                    issues.append(f"High complexity in {file_path}")
                    recommendations.append(f"Refactor complex functions in {file_path}")
                
                if file_metrics['lint_score'] < 8.0:
                    issues.append(f"Low code quality score in {file_path}")
                    recommendations.append(f"Fix linting issues in {file_path}")
        
        # Security checks
        security_results = await self.check_security(capsule)
        quality_metrics['security_score'] = security_results['score']
        
        if security_results['score'] < 0.9:
            issues.extend(security_results['vulnerabilities'])
            recommendations.extend(security_results['fixes'])
        
        # Best practices
        best_practices = self.check_best_practices(capsule)
        quality_metrics.update(best_practices)
        
        # Calculate overall quality score
        scores = [
            quality_metrics.get('security_score', 0),
            min(m.get('lint_score', 0) / 10 for m in quality_metrics.values() if isinstance(m, dict)),
            1.0 if best_practices.get('has_error_handling') else 0.5,
            1.0 if best_practices.get('has_logging') else 0.7,
            1.0 if best_practices.get('follows_conventions') else 0.8
        ]
        
        overall_score = sum(scores) / len(scores)
        passed = overall_score >= 0.7 and quality_metrics.get('security_score', 0) >= 0.8
        
        return ValidationResult(
            level=ValidationLevel.QUALITY,
            passed=passed,
            score=overall_score,
            metrics=quality_metrics,
            issues=issues,
            recommendations=recommendations
        )
    
    async def validate_production(self, capsule: QLCapsule) -> ValidationResult:
        """Check if ready for production deployment"""
        
        production_checks = {}
        issues = []
        recommendations = []
        
        # Check deployment configuration
        has_docker = 'Dockerfile' in capsule.source_code or any('dockerfile' in k.lower() for k in capsule.source_code)
        production_checks['has_dockerfile'] = has_docker
        if not has_docker:
            issues.append("Missing Dockerfile")
            recommendations.append("Add Dockerfile for containerization")
        
        # Check CI/CD configuration
        has_ci = any('.github' in k or 'gitlab-ci' in k for k in capsule.source_code)
        production_checks['has_ci_cd'] = has_ci
        if not has_ci:
            issues.append("Missing CI/CD configuration")
            recommendations.append("Add GitHub Actions or GitLab CI configuration")
        
        # Check configuration management
        has_config = any('config' in k or 'settings' in k or '.env' in k for k in capsule.source_code)
        production_checks['has_config_management'] = has_config
        
        # Check logging
        has_logging = any('logging' in code or 'logger' in code for code in capsule.source_code.values())
        production_checks['has_logging'] = has_logging
        if not has_logging:
            issues.append("No logging implementation found")
            recommendations.append("Add structured logging")
        
        # Check error handling
        has_error_handling = any(
            'try:' in code and 'except' in code 
            for code in capsule.source_code.values()
        )
        production_checks['has_error_handling'] = has_error_handling
        
        # Check for secrets management
        no_hardcoded_secrets = not any(
            self._has_hardcoded_secrets(code) 
            for code in capsule.source_code.values()
        )
        production_checks['no_hardcoded_secrets'] = no_hardcoded_secrets
        if not no_hardcoded_secrets:
            issues.append("Potential hardcoded secrets detected")
            recommendations.append("Use environment variables for secrets")
        
        # Check scalability considerations
        if capsule.deployment_config:
            has_scaling = 'scaling' in capsule.deployment_config or 'replicas' in str(capsule.deployment_config)
            production_checks['scalability_configured'] = has_scaling
        else:
            production_checks['scalability_configured'] = False
            issues.append("No deployment configuration found")
        
        passed = (
            production_checks.get('has_dockerfile', False) and
            production_checks.get('no_hardcoded_secrets', False) and
            sum(production_checks.values()) >= len(production_checks) * 0.7
        )
        
        score = sum(1 for v in production_checks.values() if v) / len(production_checks)
        
        return ValidationResult(
            level=ValidationLevel.PRODUCTION,
            passed=passed,
            score=score,
            metrics=production_checks,
            issues=issues,
            recommendations=recommendations
        )
    
    async def check_syntax(self, source_code: Dict[str, str]) -> Dict[str, Any]:
        """Check syntax validity for all source files"""
        
        results = {'valid': True, 'errors': []}
        
        for file_path, code in source_code.items():
            if file_path.endswith('.py'):
                try:
                    ast.parse(code)
                except SyntaxError as e:
                    results['valid'] = False
                    results['errors'].append(f"{file_path}: {str(e)}")
        
        return results
    
    async def check_imports(self, source_code: Dict[str, str]) -> Dict[str, Any]:
        """Check if all imports are valid"""
        
        results = {'valid': True, 'missing': []}
        standard_libs = {
            'os', 'sys', 'time', 'datetime', 'json', 're', 'math',
            'random', 'collections', 'itertools', 'functools', 'typing'
        }
        
        for file_path, code in source_code.items():
            if file_path.endswith('.py'):
                # Extract imports
                import_pattern = r'(?:from\s+(\S+)\s+)?import\s+([^#\n]+)'
                imports = re.findall(import_pattern, code)
                
                for module, items in imports:
                    base_module = (module or items.split(',')[0].strip()).split('.')[0]
                    # Skip standard library and relative imports
                    if base_module and base_module not in standard_libs and not base_module.startswith('.'):
                        # In real implementation, check against requirements.txt
                        if base_module not in ['fastapi', 'pydantic', 'pytest']:
                            results['valid'] = False
                            results['missing'].append(base_module)
        
        return results
    
    def check_structure(self, capsule: QLCapsule) -> bool:
        """Check if capsule has proper structure"""
        
        # Must have source code
        if not capsule.source_code:
            return False
        
        # Should have manifest
        if not capsule.manifest:
            return False
        
        # Should have some documentation
        if not capsule.documentation:
            return False
        
        return True
    
    async def run_tests_in_sandbox(self, capsule: QLCapsule) -> Dict[str, Any]:
        """Run tests and return results"""
        
        if not capsule.tests:
            return {'pass_rate': 0, 'total': 0, 'passed': 0, 'failed': 0}
        
        # Combine test files
        test_code = "\n\n".join(capsule.tests.values())
        
        # Add test runner
        test_runner = """
import sys
import traceback

test_count = 0
passed_count = 0
failed_tests = []

# Find all test functions
test_functions = [name for name in globals() if name.startswith('test_')]

for test_name in test_functions:
    test_count += 1
    try:
        globals()[test_name]()
        passed_count += 1
        print(f"✓ {test_name}")
    except Exception as e:
        failed_tests.append((test_name, str(e)))
        print(f"✗ {test_name}: {str(e)}")

print(f"\\nTests: {passed_count}/{test_count} passed")
if failed_tests:
    print("\\nFailed tests:")
    for name, error in failed_tests:
        print(f"  - {name}: {error}")
"""
        
        # Execute tests
        full_test_code = test_code + "\n\n" + test_runner
        
        result = await self.sandbox.execute(
            code=full_test_code,
            language="python"
        )
        
        # Parse results
        if result.success and result.output:
            # Extract pass rate from output
            import re
            match = re.search(r'(\d+)/(\d+) passed', result.output)
            if match:
                passed = int(match.group(1))
                total = int(match.group(2))
                return {
                    'pass_rate': passed / total if total > 0 else 0,
                    'total': total,
                    'passed': passed,
                    'failed': total - passed,
                    'output': result.output
                }
        
        return {'pass_rate': 0, 'total': 0, 'passed': 0, 'failed': 0, 'error': result.error}
    
    async def analyze_code_quality(self, code: str) -> Dict[str, Any]:
        """Analyze code quality metrics"""
        
        metrics = {
            'lines': len(code.split('\n')),
            'complexity': 1,  # Default
            'lint_score': 10.0,
            'has_docstrings': False,
            'has_type_hints': False
        }
        
        # Check for docstrings
        metrics['has_docstrings'] = '"""' in code or "'''" in code
        
        # Check for type hints
        metrics['has_type_hints'] = '->' in code or ': ' in code
        
        # Calculate complexity (simplified)
        complexity_indicators = ['if ', 'for ', 'while ', 'try:', 'except:']
        metrics['complexity'] = sum(code.count(ind) for ind in complexity_indicators)
        
        # Calculate lint score (simplified)
        deductions = 0
        if not metrics['has_docstrings']:
            deductions += 2
        if not metrics['has_type_hints']:
            deductions += 1
        if metrics['complexity'] > 10:
            deductions += 2
        
        metrics['lint_score'] = max(0, 10 - deductions)
        
        return metrics
    
    async def check_security(self, capsule: QLCapsule) -> Dict[str, Any]:
        """Check for security vulnerabilities"""
        
        vulnerabilities = []
        fixes = []
        
        # Check for common security issues
        for file_path, code in capsule.source_code.items():
            # SQL injection
            if 'execute' in code and 'f"' in code:
                vulnerabilities.append(f"Potential SQL injection in {file_path}")
                fixes.append("Use parameterized queries")
            
            # Hardcoded secrets
            if self._has_hardcoded_secrets(code):
                vulnerabilities.append(f"Potential hardcoded secrets in {file_path}")
                fixes.append("Use environment variables for secrets")
            
            # Unsafe deserialization
            if 'pickle.loads' in code or 'eval(' in code:
                vulnerabilities.append(f"Unsafe deserialization in {file_path}")
                fixes.append("Use safe serialization methods")
        
        score = 1.0 - (len(vulnerabilities) * 0.2)
        score = max(0, score)
        
        return {
            'score': score,
            'vulnerabilities': vulnerabilities,
            'fixes': fixes
        }
    
    def check_best_practices(self, capsule: QLCapsule) -> Dict[str, bool]:
        """Check if follows best practices"""
        
        practices = {
            'has_error_handling': False,
            'has_logging': False,
            'follows_conventions': False,
            'has_readme': False,
            'has_requirements': False
        }
        
        # Check in all source files
        all_code = '\n'.join(capsule.source_code.values())
        
        practices['has_error_handling'] = 'try:' in all_code and 'except' in all_code
        practices['has_logging'] = 'logging' in all_code or 'logger' in all_code
        practices['has_readme'] = any('readme' in k.lower() for k in capsule.source_code)
        practices['has_requirements'] = any('requirements' in k for k in capsule.source_code)
        
        # Check naming conventions (simplified)
        practices['follows_conventions'] = not any(
            # Check for non-conventional Python naming
            re.search(r'def [A-Z]', code) or  # Functions should be lowercase
            re.search(r'class [a-z]', code)    # Classes should be CamelCase
            for code in capsule.source_code.values()
            if code
        )
        
        return practices
    
    def _get_main_file(self, source_code: Dict[str, str]) -> Optional[str]:
        """Find the main executable file"""
        
        # Look for common main file patterns
        for pattern in ['main.py', 'app.py', '__main__.py', 'run.py']:
            if pattern in source_code:
                return pattern
        
        # Return first Python file
        for file_path in source_code:
            if file_path.endswith('.py'):
                return file_path
        
        return None
    
    def _has_hardcoded_secrets(self, code: str) -> bool:
        """Check for potential hardcoded secrets"""
        
        # Simple patterns for demonstration
        secret_patterns = [
            r'api[_-]?key\s*=\s*["\'][^"\']+["\']',
            r'password\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][^"\']+["\']'
        ]
        
        for pattern in secret_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                return True
        
        return False
    
    def calculate_overall_score(self, results: Dict[str, ValidationResult]) -> ValidationResult:
        """Calculate weighted overall score"""
        
        weights = {
            'basic': 0.2,
            'functional': 0.4,
            'quality': 0.2,
            'production': 0.2
        }
        
        total_score = 0
        total_weight = 0
        all_issues = []
        all_recommendations = []
        
        for level, weight in weights.items():
            if level in results:
                total_score += results[level].score * weight
                total_weight += weight
                all_issues.extend(results[level].issues)
                all_recommendations.extend(results[level].recommendations)
        
        if total_weight > 0:
            final_score = total_score / total_weight
        else:
            final_score = 0
        
        # Determine if capsule is "good"
        is_good = (
            results.get('basic', ValidationResult(ValidationLevel.BASIC, False, 0, {}, [], [])).passed and
            results.get('functional', ValidationResult(ValidationLevel.FUNCTIONAL, False, 0, {}, [], [])).passed and
            final_score >= 0.8
        )
        
        return ValidationResult(
            level=ValidationLevel.PRODUCTION,
            passed=is_good,
            score=final_score,
            metrics={
                f'{level}_score': results[level].score 
                for level in results 
                if level != 'overall'
            },
            issues=list(set(all_issues))[:10],  # Top 10 unique issues
            recommendations=list(set(all_recommendations))[:5]  # Top 5 recommendations
        )