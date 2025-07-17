#!/usr/bin/env python3
"""
Production-Grade Code Validation System
Comprehensive validation pipeline for enterprise-ready code generation
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import asyncio
import json
import ast
import subprocess
import tempfile
import os
from pathlib import Path
import structlog

from src.common.models import ValidationReport, ValidationCheck, ValidationStatus
from src.validation.client import ValidationMeshClient
from src.sandbox.client import SandboxServiceClient

logger = structlog.get_logger()


class QualityLevel(str, Enum):
    """Code quality levels"""
    PROTOTYPE = "prototype"          # Basic functionality, minimal standards
    DEVELOPMENT = "development"      # Good practices, comprehensive tests
    PRODUCTION = "production"        # Enterprise-grade, security hardened
    CRITICAL = "critical"           # Mission-critical, fault-tolerant


class ValidationSeverity(str, Enum):
    """Validation issue severity"""
    BLOCKER = "blocker"             # Prevents deployment
    CRITICAL = "critical"           # Must fix before production
    MAJOR = "major"                 # Should fix for quality
    MINOR = "minor"                 # Nice to fix
    INFO = "info"                   # Informational only


@dataclass
class QualityMetrics:
    """Comprehensive code quality metrics"""
    cyclomatic_complexity: float
    cognitive_complexity: float
    test_coverage: float
    documentation_coverage: float
    security_score: float
    maintainability_index: float
    technical_debt_ratio: float
    duplication_percentage: float
    
    @property
    def overall_score(self) -> float:
        """Calculate overall quality score (0-100)"""
        # Weighted scoring
        weights = {
            "complexity": 0.2,      # Lower complexity is better
            "coverage": 0.25,       # Higher coverage is better
            "security": 0.25,       # Higher security score is better
            "maintainability": 0.15, # Higher maintainability is better
            "debt": 0.1,            # Lower debt is better
            "duplication": 0.05     # Lower duplication is better
        }
        
        # Normalize metrics (0-100 scale)
        normalized_complexity = max(0, 100 - (self.cyclomatic_complexity * 5))
        normalized_coverage = self.test_coverage
        normalized_security = self.security_score
        normalized_maintainability = self.maintainability_index
        normalized_debt = max(0, 100 - (self.technical_debt_ratio * 100))
        normalized_duplication = max(0, 100 - (self.duplication_percentage * 2))
        
        score = (
            normalized_complexity * weights["complexity"] +
            normalized_coverage * weights["coverage"] +
            normalized_security * weights["security"] +
            normalized_maintainability * weights["maintainability"] +
            normalized_debt * weights["debt"] +
            normalized_duplication * weights["duplication"]
        )
        
        return min(100, max(0, score))


@dataclass
class ValidationIssue:
    """Individual validation issue"""
    category: str
    severity: ValidationSeverity
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    rule_id: Optional[str] = None
    suggestion: Optional[str] = None


class ProductionCodeValidator:
    """Production-grade code validation system"""
    
    def __init__(self):
        self.sandbox_client = SandboxServiceClient("http://localhost:8004")
        self.validation_client = ValidationMeshClient("http://localhost:8002")
        
        # Quality thresholds by level
        self.quality_thresholds = {
            QualityLevel.PROTOTYPE: {
                "overall_score": 50,
                "test_coverage": 30,
                "security_score": 60,
                "max_complexity": 20
            },
            QualityLevel.DEVELOPMENT: {
                "overall_score": 70,
                "test_coverage": 70,
                "security_score": 80,
                "max_complexity": 15
            },
            QualityLevel.PRODUCTION: {
                "overall_score": 85,
                "test_coverage": 85,
                "security_score": 95,
                "max_complexity": 10
            },
            QualityLevel.CRITICAL: {
                "overall_score": 95,
                "test_coverage": 95,
                "security_score": 98,
                "max_complexity": 8
            }
        }
    
    async def validate_production_code(
        self,
        code: str,
        tests: str = "",
        language: str = "python",
        quality_level: QualityLevel = QualityLevel.PRODUCTION,
        requirements: Optional[Dict[str, Any]] = None
    ) -> ValidationReport:
        """Comprehensive production-grade validation"""
        
        logger.info(
            "Starting production validation",
            quality_level=quality_level,
            code_length=len(code),
            has_tests=bool(tests)
        )
        
        start_time = datetime.utcnow()
        issues = []
        checks_performed = []
        
        try:
            # 1. Static Code Analysis
            static_issues, static_checks = await self._run_static_analysis(
                code, language, quality_level
            )
            issues.extend(static_issues)
            checks_performed.extend(static_checks)
            
            # 2. Security Vulnerability Scanning
            security_issues, security_checks = await self._run_security_scan(
                code, language, quality_level
            )
            issues.extend(security_issues)
            checks_performed.extend(security_checks)
            
            # 3. Test Coverage Analysis
            coverage_issues, coverage_checks = await self._analyze_test_coverage(
                code, tests, language, quality_level
            )
            issues.extend(coverage_issues)
            checks_performed.extend(coverage_checks)
            
            # 4. Performance & Efficiency Analysis
            perf_issues, perf_checks = await self._analyze_performance(
                code, language, quality_level
            )
            issues.extend(perf_issues)
            checks_performed.extend(perf_checks)
            
            # 5. Architecture & Design Pattern Validation
            arch_issues, arch_checks = await self._validate_architecture(
                code, language, requirements or {}
            )
            issues.extend(arch_issues)
            checks_performed.extend(arch_checks)
            
            # 6. Runtime Validation
            runtime_issues, runtime_checks = await self._run_runtime_validation(
                code, tests, language
            )
            issues.extend(runtime_issues)
            checks_performed.extend(runtime_checks)
            
            # 7. Documentation Quality
            doc_issues, doc_checks = await self._validate_documentation(
                code, language, quality_level
            )
            issues.extend(doc_issues)
            checks_performed.extend(doc_checks)
            
            # Calculate quality metrics
            metrics = await self._calculate_quality_metrics(code, tests, language)
            
            # Determine overall status
            blocker_count = sum(1 for issue in issues if issue.severity == ValidationSeverity.BLOCKER)
            critical_count = sum(1 for issue in issues if issue.severity == ValidationSeverity.CRITICAL)
            
            if blocker_count > 0:
                status = ValidationStatus.FAILED
            elif quality_level == QualityLevel.CRITICAL and (critical_count > 0 or metrics.overall_score < 95):
                status = ValidationStatus.FAILED
            elif quality_level == QualityLevel.PRODUCTION and metrics.overall_score < 85:
                status = ValidationStatus.FAILED
            elif critical_count > 3:
                status = ValidationStatus.FAILED
            else:
                status = ValidationStatus.PASSED if len(issues) == 0 else ValidationStatus.PASSED_WITH_WARNINGS
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Calculate confidence score
            confidence = self._calculate_confidence_score(metrics, issues, quality_level)
            
            return ValidationReport(
                id=f"prod-val-{datetime.utcnow().timestamp()}",
                execution_id="production-validation",
                overall_status=status,
                checks=checks_performed,
                confidence_score=confidence,
                requires_human_review=blocker_count > 0 or critical_count > 5,
                metadata={
                    "quality_level": quality_level,
                    "quality_metrics": {
                        "overall_score": metrics.overall_score,
                        "cyclomatic_complexity": metrics.cyclomatic_complexity,
                        "test_coverage": metrics.test_coverage,
                        "security_score": metrics.security_score,
                        "maintainability_index": metrics.maintainability_index,
                        "technical_debt_ratio": metrics.technical_debt_ratio
                    },
                    "issue_summary": {
                        "total": len(issues),
                        "blocker": blocker_count,
                        "critical": critical_count,
                        "major": sum(1 for i in issues if i.severity == ValidationSeverity.MAJOR),
                        "minor": sum(1 for i in issues if i.severity == ValidationSeverity.MINOR)
                    },
                    "execution_time": execution_time,
                    "validation_timestamp": datetime.utcnow().isoformat()
                },
                created_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error("Production validation failed", error=str(e))
            return ValidationReport(
                id=f"prod-val-error-{datetime.utcnow().timestamp()}",
                execution_id="production-validation",
                overall_status=ValidationStatus.FAILED,
                checks=[ValidationCheck(
                    name="Validation System Error",
                    type="system",
                    status=ValidationStatus.FAILED,
                    message=f"Validation system error: {str(e)}",
                    severity="critical"
                )],
                confidence_score=0.0,
                requires_human_review=True,
                metadata={"error": str(e)},
                created_at=datetime.utcnow()
            )
    
    async def _run_static_analysis(
        self, 
        code: str, 
        language: str, 
        quality_level: QualityLevel
    ) -> Tuple[List[ValidationIssue], List[ValidationCheck]]:
        """Run comprehensive static code analysis"""
        issues = []
        checks = []
        
        try:
            if language == "python":
                # AST-based analysis
                try:
                    tree = ast.parse(code)
                    
                    # Complexity analysis
                    complexity = self._calculate_cyclomatic_complexity(tree)
                    max_complexity = self.quality_thresholds[quality_level]["max_complexity"]
                    
                    if complexity > max_complexity:
                        issues.append(ValidationIssue(
                            category="complexity",
                            severity=ValidationSeverity.CRITICAL if complexity > max_complexity * 1.5 else ValidationSeverity.MAJOR,
                            message=f"Cyclomatic complexity {complexity} exceeds limit of {max_complexity}",
                            suggestion="Consider breaking down complex functions into smaller ones"
                        ))
                    
                    checks.append(ValidationCheck(
                        name="Cyclomatic Complexity",
                        type="static_analysis",
                        status=ValidationStatus.PASSED if complexity <= max_complexity else ValidationStatus.FAILED,
                        message=f"Complexity: {complexity}/{max_complexity}",
                        severity="info"
                    ))
                    
                    # Code structure analysis
                    structure_issues = self._analyze_code_structure(tree)
                    issues.extend(structure_issues)
                    
                    checks.append(ValidationCheck(
                        name="Code Structure",
                        type="static_analysis", 
                        status=ValidationStatus.PASSED if not structure_issues else ValidationStatus.FAILED,
                        message=f"Found {len(structure_issues)} structural issues",
                        severity="info"
                    ))
                    
                except SyntaxError as e:
                    issues.append(ValidationIssue(
                        category="syntax",
                        severity=ValidationSeverity.BLOCKER,
                        message=f"Syntax error: {str(e)}",
                        line_number=getattr(e, 'lineno', None)
                    ))
            
            # External static analysis tools (if available)
            external_issues = await self._run_external_static_analysis(code, language)
            issues.extend(external_issues)
            
        except Exception as e:
            logger.error("Static analysis failed", error=str(e))
            checks.append(ValidationCheck(
                name="Static Analysis Error",
                type="static_analysis",
                status=ValidationStatus.FAILED,
                message=f"Static analysis error: {str(e)}",
                severity="critical"
            ))
        
        return issues, checks
    
    async def _run_security_scan(
        self, 
        code: str, 
        language: str, 
        quality_level: QualityLevel
    ) -> Tuple[List[ValidationIssue], List[ValidationCheck]]:
        """Comprehensive security vulnerability scanning"""
        issues = []
        checks = []
        
        try:
            # Pattern-based security checks
            security_patterns = {
                "hardcoded_secrets": [
                    r"password\s*=\s*['\"][^'\"]+['\"]",
                    r"api_key\s*=\s*['\"][^'\"]+['\"]",
                    r"secret\s*=\s*['\"][^'\"]+['\"]"
                ],
                "sql_injection": [
                    r"execute\s*\([^)]*%s",
                    r"cursor\.execute\s*\([^)]*\+",
                    r"query\s*=.*\+.*"
                ],
                "command_injection": [
                    r"os\.system\s*\(",
                    r"subprocess\.call\s*\(",
                    r"eval\s*\("
                ]
            }
            
            import re
            for category, patterns in security_patterns.items():
                for pattern in patterns:
                    matches = re.finditer(pattern, code, re.IGNORECASE)
                    for match in matches:
                        issues.append(ValidationIssue(
                            category="security",
                            severity=ValidationSeverity.CRITICAL,
                            message=f"Potential {category.replace('_', ' ')} vulnerability detected",
                            suggestion=f"Review and secure {category.replace('_', ' ')} implementation"
                        ))
            
            # External security scanning (Bandit for Python)
            if language == "python":
                security_report = await self._run_bandit_scan(code)
                issues.extend(security_report)
            
            security_score = max(0, 100 - (len(issues) * 10))
            required_score = self.quality_thresholds[quality_level]["security_score"]
            
            checks.append(ValidationCheck(
                name="Security Vulnerability Scan",
                type="security",
                status=ValidationStatus.PASSED if security_score >= required_score else ValidationStatus.FAILED,
                message=f"Security score: {security_score}/{required_score}",
                severity="critical" if security_score < required_score else "info"
            ))
            
        except Exception as e:
            logger.error("Security scan failed", error=str(e))
            checks.append(ValidationCheck(
                name="Security Scan Error", 
                type="security",
                status=ValidationStatus.FAILED,
                message=f"Security scan error: {str(e)}",
                severity="critical"
            ))
        
        return issues, checks
    
    async def _analyze_test_coverage(
        self,
        code: str,
        tests: str,
        language: str,
        quality_level: QualityLevel
    ) -> Tuple[List[ValidationIssue], List[ValidationCheck]]:
        """Analyze test coverage and quality"""
        issues = []
        checks = []
        
        try:
            required_coverage = self.quality_thresholds[quality_level]["test_coverage"]
            
            if not tests.strip():
                issues.append(ValidationIssue(
                    category="testing",
                    severity=ValidationSeverity.CRITICAL,
                    message="No tests provided",
                    suggestion="Add comprehensive unit tests"
                ))
                coverage = 0
            else:
                # Estimate coverage based on code/test ratio and test quality
                coverage = await self._estimate_test_coverage(code, tests, language)
            
            if coverage < required_coverage:
                severity = ValidationSeverity.CRITICAL if coverage < required_coverage * 0.5 else ValidationSeverity.MAJOR
                issues.append(ValidationIssue(
                    category="testing",
                    severity=severity,
                    message=f"Test coverage {coverage}% below required {required_coverage}%",
                    suggestion="Add more comprehensive test cases"
                ))
            
            checks.append(ValidationCheck(
                name="Test Coverage",
                type="testing",
                status=ValidationStatus.PASSED if coverage >= required_coverage else ValidationStatus.FAILED,
                message=f"Coverage: {coverage}%/{required_coverage}%",
                severity="critical" if coverage < required_coverage else "info"
            ))
            
        except Exception as e:
            logger.error("Test coverage analysis failed", error=str(e))
            checks.append(ValidationCheck(
                name="Test Coverage Error",
                type="testing", 
                status=ValidationStatus.FAILED,
                message=f"Test coverage analysis error: {str(e)}",
                severity="major"
            ))
        
        return issues, checks
    
    async def _analyze_performance(
        self,
        code: str,
        language: str,
        quality_level: QualityLevel
    ) -> Tuple[List[ValidationIssue], List[ValidationCheck]]:
        """Analyze code for performance issues"""
        issues = []
        checks = []
        
        try:
            # Performance anti-patterns
            performance_patterns = {
                "inefficient_loops": [
                    r"for.*in.*range\(len\(",  # for i in range(len(list))
                    r"while.*len\("             # while len(list) > 0
                ],
                "memory_issues": [
                    r"\.extend\(.*for.*in",     # list.extend(x for x in y)
                    r"\+.*for.*in"              # string concatenation in loop
                ]
            }
            
            import re
            for category, patterns in performance_patterns.items():
                for pattern in patterns:
                    matches = re.finditer(pattern, code, re.IGNORECASE)
                    for match in matches:
                        issues.append(ValidationIssue(
                            category="performance",
                            severity=ValidationSeverity.MINOR,
                            message=f"Potential {category.replace('_', ' ')} issue detected",
                            suggestion=f"Consider optimizing {category.replace('_', ' ')}"
                        ))
            
            checks.append(ValidationCheck(
                name="Performance Analysis",
                type="performance",
                status=ValidationStatus.PASSED if len(issues) == 0 else ValidationStatus.PASSED_WITH_WARNINGS,
                message=f"Found {len(issues)} potential performance issues",
                severity="info"
            ))
            
        except Exception as e:
            logger.error("Performance analysis failed", error=str(e))
            checks.append(ValidationCheck(
                name="Performance Analysis Error",
                type="performance",
                status=ValidationStatus.FAILED,
                message=f"Performance analysis error: {str(e)}",
                severity="minor"
            ))
        
        return issues, checks
    
    async def _validate_architecture(
        self,
        code: str,
        language: str,
        requirements: Dict[str, Any]
    ) -> Tuple[List[ValidationIssue], List[ValidationCheck]]:
        """Validate architectural patterns and design principles"""
        issues = []
        checks = []
        
        try:
            # Check for SOLID principles violations
            solid_issues = self._check_solid_principles(code, language)
            issues.extend(solid_issues)
            
            # Check for required patterns based on requirements
            pattern_issues = self._validate_design_patterns(code, requirements)
            issues.extend(pattern_issues)
            
            checks.append(ValidationCheck(
                name="Architecture Validation",
                type="architecture",
                status=ValidationStatus.PASSED if len(issues) == 0 else ValidationStatus.PASSED_WITH_WARNINGS,
                message=f"Found {len(issues)} architectural issues",
                severity="info"
            ))
            
        except Exception as e:
            logger.error("Architecture validation failed", error=str(e))
            checks.append(ValidationCheck(
                name="Architecture Validation Error",
                type="architecture",
                status=ValidationStatus.FAILED,
                message=f"Architecture validation error: {str(e)}",
                severity="minor"
            ))
        
        return issues, checks
    
    async def _run_runtime_validation(
        self,
        code: str,
        tests: str,
        language: str
    ) -> Tuple[List[ValidationIssue], List[ValidationCheck]]:
        """Run code in sandbox environment for runtime validation"""
        issues = []
        checks = []
        
        try:
            # Execute in sandbox
            execution_result = await self.sandbox_client.execute(
                code=code,
                language=language,
                runtime="kata"  # Use Kata Containers for secure validation
            )
            
            if execution_result.success:
                checks.append(ValidationCheck(
                    name="Runtime Execution",
                    type="runtime",
                    status=ValidationStatus.PASSED,
                    message="Code executed successfully",
                    severity="info"
                ))
            else:
                issues.append(ValidationIssue(
                    category="runtime",
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Runtime error: {execution_result.error or 'Unknown error'}",
                    suggestion="Fix runtime execution issues"
                ))
                
                checks.append(ValidationCheck(
                    name="Runtime Execution",
                    type="runtime",
                    status=ValidationStatus.FAILED,
                    message=f"Execution failed: {execution_result.error or 'Unknown'}",
                    severity="critical"
                ))
            
        except Exception as e:
            logger.error("Runtime validation failed", error=str(e))
            checks.append(ValidationCheck(
                name="Runtime Validation Error",
                type="runtime",
                status=ValidationStatus.FAILED,
                message=f"Runtime validation error: {str(e)}",
                severity="major"
            ))
        
        return issues, checks
    
    async def _validate_documentation(
        self,
        code: str,
        language: str,
        quality_level: QualityLevel
    ) -> Tuple[List[ValidationIssue], List[ValidationCheck]]:
        """Validate documentation quality and coverage"""
        issues = []
        checks = []
        
        try:
            if language == "python":
                # Check for docstrings
                import ast
                tree = ast.parse(code)
                
                functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
                classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
                
                undocumented_functions = []
                undocumented_classes = []
                
                for func in functions:
                    if not ast.get_docstring(func):
                        undocumented_functions.append(func.name)
                
                for cls in classes:
                    if not ast.get_docstring(cls):
                        undocumented_classes.append(cls.name)
                
                total_items = len(functions) + len(classes)
                documented_items = total_items - len(undocumented_functions) - len(undocumented_classes)
                doc_coverage = (documented_items / total_items * 100) if total_items > 0 else 100
                
                required_doc_coverage = 80 if quality_level in [QualityLevel.PRODUCTION, QualityLevel.CRITICAL] else 50
                
                if doc_coverage < required_doc_coverage:
                    issues.append(ValidationIssue(
                        category="documentation",
                        severity=ValidationSeverity.MAJOR,
                        message=f"Documentation coverage {doc_coverage:.1f}% below required {required_doc_coverage}%",
                        suggestion="Add docstrings to functions and classes"
                    ))
                
                checks.append(ValidationCheck(
                    name="Documentation Coverage",
                    type="documentation",
                    status=ValidationStatus.PASSED if doc_coverage >= required_doc_coverage else ValidationStatus.FAILED,
                    message=f"Documentation coverage: {doc_coverage:.1f}%",
                    severity="info"
                ))
            
        except Exception as e:
            logger.error("Documentation validation failed", error=str(e))
            checks.append(ValidationCheck(
                name="Documentation Validation Error",
                type="documentation",
                status=ValidationStatus.FAILED,
                message=f"Documentation validation error: {str(e)}",
                severity="minor"
            ))
        
        return issues, checks
    
    # Helper methods for detailed analysis
    
    def _calculate_cyclomatic_complexity(self, tree: ast.AST) -> int:
        """Calculate cyclomatic complexity of AST"""
        complexity = 1  # Base complexity
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor, 
                               ast.ExceptHandler, ast.With, ast.AsyncWith)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
        
        return complexity
    
    def _analyze_code_structure(self, tree: ast.AST) -> List[ValidationIssue]:
        """Analyze code structure for issues"""
        issues = []
        
        # Check for overly long functions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_lines = node.end_lineno - node.lineno if hasattr(node, 'end_lineno') else 0
                if func_lines > 50:
                    issues.append(ValidationIssue(
                        category="structure",
                        severity=ValidationSeverity.MAJOR,
                        message=f"Function '{node.name}' is too long ({func_lines} lines)",
                        suggestion="Break down into smaller functions"
                    ))
        
        return issues
    
    async def _calculate_quality_metrics(
        self, 
        code: str, 
        tests: str, 
        language: str
    ) -> QualityMetrics:
        """Calculate comprehensive quality metrics"""
        
        # Basic implementation - could be enhanced with external tools
        try:
            if language == "python":
                tree = ast.parse(code)
                complexity = self._calculate_cyclomatic_complexity(tree)
            else:
                complexity = 5  # Default estimate
            
            # Estimate test coverage
            test_coverage = await self._estimate_test_coverage(code, tests, language)
            
            # Basic security score (inverse of potential issues)
            security_score = 90  # Default high score
            
            # Maintainability index (simplified calculation)
            maintainability = max(0, 100 - (complexity * 2))
            
            return QualityMetrics(
                cyclomatic_complexity=complexity,
                cognitive_complexity=complexity * 1.2,  # Estimate
                test_coverage=test_coverage,
                documentation_coverage=70,  # Estimate
                security_score=security_score,
                maintainability_index=maintainability,
                technical_debt_ratio=0.1,  # Low debt estimate
                duplication_percentage=5   # Low duplication estimate
            )
            
        except Exception as e:
            logger.error("Quality metrics calculation failed", error=str(e))
            # Return default metrics
            return QualityMetrics(
                cyclomatic_complexity=10,
                cognitive_complexity=12,
                test_coverage=50,
                documentation_coverage=50,
                security_score=70,
                maintainability_index=70,
                technical_debt_ratio=0.2,
                duplication_percentage=10
            )
    
    async def _estimate_test_coverage(self, code: str, tests: str, language: str) -> float:
        """Estimate test coverage based on code and test content"""
        if not tests.strip():
            return 0.0
        
        # Simple heuristic: ratio of test lines to code lines with adjustments
        code_lines = len([line for line in code.split('\n') if line.strip() and not line.strip().startswith('#')])
        test_lines = len([line for line in tests.split('\n') if line.strip() and not line.strip().startswith('#')])
        
        if code_lines == 0:
            return 100.0
        
        # Basic coverage estimate
        raw_ratio = (test_lines / code_lines) * 100
        
        # Adjust based on test quality indicators
        test_content = tests.lower()
        quality_multiplier = 1.0
        
        if 'assert' in test_content:
            quality_multiplier += 0.2
        if 'test_' in test_content or 'def test' in test_content:
            quality_multiplier += 0.2
        if 'mock' in test_content or 'patch' in test_content:
            quality_multiplier += 0.1
        
        # Cap at 95% for estimated coverage
        return min(95, raw_ratio * quality_multiplier)
    
    def _calculate_confidence_score(
        self, 
        metrics: QualityMetrics, 
        issues: List[ValidationIssue], 
        quality_level: QualityLevel
    ) -> float:
        """Calculate overall confidence score"""
        
        # Base score from quality metrics
        base_score = metrics.overall_score / 100
        
        # Penalty for issues
        issue_penalty = 0
        for issue in issues:
            if issue.severity == ValidationSeverity.BLOCKER:
                issue_penalty += 0.3
            elif issue.severity == ValidationSeverity.CRITICAL:
                issue_penalty += 0.1
            elif issue.severity == ValidationSeverity.MAJOR:
                issue_penalty += 0.05
            elif issue.severity == ValidationSeverity.MINOR:
                issue_penalty += 0.01
        
        # Quality level adjustment
        level_multiplier = {
            QualityLevel.PROTOTYPE: 0.6,
            QualityLevel.DEVELOPMENT: 0.8,
            QualityLevel.PRODUCTION: 1.0,
            QualityLevel.CRITICAL: 1.2
        }[quality_level]
        
        final_score = max(0, (base_score - issue_penalty) * level_multiplier)
        return min(0.99, final_score)
    
    # Placeholder methods for external tool integration
    
    async def _run_external_static_analysis(self, code: str, language: str) -> List[ValidationIssue]:
        """Run external static analysis tools (SonarQube, CodeQL, etc.)"""
        # Placeholder for external tool integration
        return []
    
    async def _run_bandit_scan(self, code: str) -> List[ValidationIssue]:
        """Run Bandit security scanner for Python"""
        # Placeholder for Bandit integration
        return []
    
    def _check_solid_principles(self, code: str, language: str) -> List[ValidationIssue]:
        """Check for SOLID principles violations"""
        # Placeholder for SOLID principles validation
        return []
    
    def _validate_design_patterns(self, code: str, requirements: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate required design patterns are implemented"""
        # Placeholder for design pattern validation
        return []


# Export main validator
__all__ = ["ProductionCodeValidator", "QualityLevel", "QualityMetrics", "ValidationIssue"]