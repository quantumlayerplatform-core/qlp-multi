#!/usr/bin/env python3
"""
Advanced Confidence Scoring Engine for QLC Capsules
Multi-dimensional confidence analysis with ML-based scoring
"""

import asyncio
import json
import math
import statistics
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import structlog

from src.common.models import QLCapsule, ValidationReport, ValidationStatus
from src.validation.qlcapsule_runtime_validator import RuntimeValidationResult
from src.validation.capsule_schema import CapsuleManifest, CapsuleValidator

logger = structlog.get_logger()


class ConfidenceLevel(str, Enum):
    """Confidence levels for deployment decision"""
    CRITICAL = "critical"      # 0.95-1.0: Deploy immediately
    HIGH = "high"             # 0.85-0.94: Deploy with monitoring
    MEDIUM = "medium"         # 0.70-0.84: Deploy with caution
    LOW = "low"              # 0.50-0.69: Human review required
    VERY_LOW = "very_low"    # 0.0-0.49: Block deployment


class ConfidenceDimension(str, Enum):
    """Dimensions of confidence analysis"""
    SYNTAX = "syntax"                    # Code syntax correctness
    STRUCTURE = "structure"              # Project structure quality
    SECURITY = "security"                # Security vulnerability assessment
    PERFORMANCE = "performance"          # Performance characteristics
    RELIABILITY = "reliability"          # Error handling and robustness
    MAINTAINABILITY = "maintainability"  # Code quality and documentation
    TESTABILITY = "testability"          # Test coverage and quality
    DEPLOYABILITY = "deployability"      # Deployment readiness
    SCALABILITY = "scalability"          # Scalability considerations
    COMPLIANCE = "compliance"            # Standards compliance


@dataclass
class ConfidenceMetric:
    """Individual confidence metric"""
    dimension: ConfidenceDimension
    score: float  # 0.0 to 1.0
    weight: float  # Importance weight
    evidence: List[str]  # Supporting evidence
    concerns: List[str]  # Areas of concern
    metadata: Dict[str, Any]


@dataclass
class ConfidenceAnalysis:
    """Complete confidence analysis result"""
    overall_score: float
    confidence_level: ConfidenceLevel
    dimensions: Dict[ConfidenceDimension, ConfidenceMetric]
    deployment_recommendation: str
    risk_factors: List[str]
    success_indicators: List[str]
    human_review_required: bool
    estimated_success_probability: float
    failure_modes: List[str]
    mitigation_strategies: List[str]
    metadata: Dict[str, Any]


class ConfidenceFeatureExtractor:
    """Extracts features for confidence scoring"""
    
    def extract_capsule_features(self, capsule: QLCapsule, manifest: Optional[CapsuleManifest] = None, 
                                runtime_result: Optional[RuntimeValidationResult] = None) -> Dict[str, float]:
        """Extract numerical features from capsule for ML scoring"""
        
        features = {}
        
        # Basic capsule features
        features['source_files_count'] = len(capsule.source_code)
        features['total_lines'] = sum(len(code.split('\n')) for code in capsule.source_code.values())
        features['avg_file_size'] = features['total_lines'] / max(1, features['source_files_count'])
        features['has_documentation'] = 1.0 if capsule.documentation else 0.0
        features['has_tests'] = 1.0 if capsule.tests else 0.0
        features['test_files_count'] = len(capsule.tests) if capsule.tests else 0
        
        # Manifest features
        if manifest:
            features['has_manifest'] = 1.0
            features['has_health_check'] = 1.0 if manifest.health_check else 0.0
            features['has_resource_limits'] = 1.0 if manifest.resources else 0.0
            features['port_count'] = len(manifest.ports)
            features['env_var_count'] = len(manifest.environment)
            features['has_dependencies'] = 1.0 if manifest.dependencies else 0.0
        else:
            features['has_manifest'] = 0.0
            features['has_health_check'] = 0.0
            features['has_resource_limits'] = 0.0
            features['port_count'] = 0
            features['env_var_count'] = 0
            features['has_dependencies'] = 0.0
        
        # Runtime features
        if runtime_result:
            features['runtime_success'] = 1.0 if runtime_result.success else 0.0
            features['install_success'] = 1.0 if runtime_result.install_success else 0.0
            features['test_success'] = 1.0 if runtime_result.test_success else 0.0
            features['execution_time'] = min(runtime_result.execution_time, 300) / 300  # Normalize to 5 min
            features['memory_usage'] = min(runtime_result.memory_usage, 1024) / 1024  # Normalize to 1GB
            features['exit_code'] = 1.0 if runtime_result.exit_code == 0 else 0.0
            features['error_count'] = len(runtime_result.issues)
        else:
            features['runtime_success'] = 0.0
            features['install_success'] = 0.0
            features['test_success'] = 0.0
            features['execution_time'] = 0.0
            features['memory_usage'] = 0.0
            features['exit_code'] = 0.0
            features['error_count'] = 0
        
        # Code quality features
        features.update(self._extract_code_quality_features(capsule))
        
        # Security features
        features.update(self._extract_security_features(capsule))
        
        return features
    
    def _extract_code_quality_features(self, capsule: QLCapsule) -> Dict[str, float]:
        """Extract code quality features"""
        features = {}
        
        all_code = '\n'.join(capsule.source_code.values())
        
        # Error handling
        features['has_try_catch'] = 1.0 if 'try:' in all_code and 'except' in all_code else 0.0
        features['has_logging'] = 1.0 if any(log_term in all_code for log_term in ['logging', 'logger', 'log.']) else 0.0
        
        # Documentation
        features['has_docstrings'] = 1.0 if '"""' in all_code or "'''" in all_code else 0.0
        features['has_comments'] = 1.0 if '#' in all_code or '//' in all_code else 0.0
        features['comment_ratio'] = min(all_code.count('#') / max(1, len(all_code.split('\n'))), 1.0)
        
        # Code structure
        features['function_count'] = all_code.count('def ') + all_code.count('function ')
        features['class_count'] = all_code.count('class ')
        features['import_count'] = all_code.count('import ') + all_code.count('from ')
        
        # Complexity indicators
        complexity_keywords = ['if ', 'for ', 'while ', 'switch ', 'case ']
        features['complexity_score'] = min(sum(all_code.count(kw) for kw in complexity_keywords) / 100, 1.0)
        
        return features
    
    def _extract_security_features(self, capsule: QLCapsule) -> Dict[str, float]:
        """Extract security-related features"""
        features = {}
        
        all_code = '\n'.join(capsule.source_code.values())
        
        # Security risks
        security_risks = [
            'eval(', 'exec(', 'pickle.loads', 'subprocess.call', 'os.system',
            'password', 'secret', 'api_key', 'token', 'credentials'
        ]
        
        risk_count = sum(1 for risk in security_risks if risk in all_code.lower())
        features['security_risk_score'] = min(risk_count / 10, 1.0)
        
        # Security best practices
        features['uses_env_vars'] = 1.0 if 'os.environ' in all_code or 'process.env' in all_code else 0.0
        features['has_input_validation'] = 1.0 if any(val in all_code for val in ['validate', 'sanitize', 'clean']) else 0.0
        
        return features


class DimensionalConfidenceAnalyzer:
    """Analyzes confidence across multiple dimensions"""
    
    def __init__(self):
        self.dimension_weights = {
            ConfidenceDimension.SYNTAX: 0.15,
            ConfidenceDimension.STRUCTURE: 0.10,
            ConfidenceDimension.SECURITY: 0.20,
            ConfidenceDimension.PERFORMANCE: 0.10,
            ConfidenceDimension.RELIABILITY: 0.15,
            ConfidenceDimension.MAINTAINABILITY: 0.10,
            ConfidenceDimension.TESTABILITY: 0.10,
            ConfidenceDimension.DEPLOYABILITY: 0.10
        }
    
    async def analyze_dimension(self, dimension: ConfidenceDimension, capsule: QLCapsule, 
                              manifest: Optional[CapsuleManifest] = None,
                              runtime_result: Optional[RuntimeValidationResult] = None) -> ConfidenceMetric:
        """Analyze a specific confidence dimension"""
        
        if dimension == ConfidenceDimension.SYNTAX:
            return await self._analyze_syntax(capsule, runtime_result)
        elif dimension == ConfidenceDimension.STRUCTURE:
            return await self._analyze_structure(capsule, manifest)
        elif dimension == ConfidenceDimension.SECURITY:
            return await self._analyze_security(capsule)
        elif dimension == ConfidenceDimension.PERFORMANCE:
            return await self._analyze_performance(capsule, runtime_result)
        elif dimension == ConfidenceDimension.RELIABILITY:
            return await self._analyze_reliability(capsule, runtime_result)
        elif dimension == ConfidenceDimension.MAINTAINABILITY:
            return await self._analyze_maintainability(capsule)
        elif dimension == ConfidenceDimension.TESTABILITY:
            return await self._analyze_testability(capsule, runtime_result)
        elif dimension == ConfidenceDimension.DEPLOYABILITY:
            return await self._analyze_deployability(capsule, manifest)
        else:
            return ConfidenceMetric(dimension, 0.5, 0.1, [], [], {})
    
    async def _analyze_syntax(self, capsule: QLCapsule, runtime_result: Optional[RuntimeValidationResult]) -> ConfidenceMetric:
        """Analyze syntax correctness"""
        evidence = []
        concerns = []
        
        # Check runtime compilation
        if runtime_result:
            if runtime_result.install_success:
                evidence.append("Installation successful")
            else:
                concerns.append("Installation failed")
            
            if runtime_result.runtime_success:
                evidence.append("Code executed successfully")
            else:
                concerns.append("Runtime execution failed")
        
        # Basic syntax checks
        syntax_errors = 0
        for file_path, code in capsule.source_code.items():
            if file_path.endswith('.py'):
                try:
                    compile(code, file_path, 'exec')
                    evidence.append(f"Python syntax valid in {file_path}")
                except SyntaxError as e:
                    syntax_errors += 1
                    concerns.append(f"Syntax error in {file_path}: {str(e)}")
        
        score = 1.0 - (syntax_errors * 0.3)
        if runtime_result and not runtime_result.install_success:
            score *= 0.5
        
        return ConfidenceMetric(
            ConfidenceDimension.SYNTAX,
            max(0.0, score),
            self.dimension_weights[ConfidenceDimension.SYNTAX],
            evidence,
            concerns,
            {"syntax_errors": syntax_errors}
        )
    
    async def _analyze_structure(self, capsule: QLCapsule, manifest: Optional[CapsuleManifest]) -> ConfidenceMetric:
        """Analyze project structure quality"""
        evidence = []
        concerns = []
        score = 0.5
        
        # Check for manifest
        if manifest:
            evidence.append("Capsule manifest present")
            score += 0.2
        else:
            concerns.append("No capsule manifest")
        
        # Check for essential files
        essential_files = ['README.md', 'requirements.txt', 'package.json', 'go.mod', 'pom.xml']
        found_essential = any(ef in capsule.source_code or ef.lower() in [f.lower() for f in capsule.source_code] for ef in essential_files)
        
        if found_essential:
            evidence.append("Essential dependency files present")
            score += 0.1
        else:
            concerns.append("Missing dependency files")
        
        # Check for documentation
        if capsule.documentation:
            evidence.append("Documentation provided")
            score += 0.1
        else:
            concerns.append("No documentation")
        
        # Check for tests
        if capsule.tests:
            evidence.append("Tests included")
            score += 0.1
        else:
            concerns.append("No tests found")
        
        return ConfidenceMetric(
            ConfidenceDimension.STRUCTURE,
            min(1.0, score),
            self.dimension_weights[ConfidenceDimension.STRUCTURE],
            evidence,
            concerns,
            {"essential_files": found_essential}
        )
    
    async def _analyze_security(self, capsule: QLCapsule) -> ConfidenceMetric:
        """Analyze security aspects"""
        evidence = []
        concerns = []
        score = 1.0
        
        all_code = '\n'.join(capsule.source_code.values())
        
        # Check for security risks
        security_risks = [
            ('eval(', 'Use of eval() function'),
            ('exec(', 'Use of exec() function'),
            ('pickle.loads', 'Unsafe deserialization'),
            ('shell=True', 'Shell injection risk'),
            ('os.system', 'System command execution'),
            ('password', 'Hardcoded password'),
            ('secret', 'Hardcoded secret'),
            ('api_key', 'Hardcoded API key')
        ]
        
        for risk_pattern, description in security_risks:
            if risk_pattern in all_code.lower():
                concerns.append(description)
                score -= 0.15
        
        # Check for security best practices
        if 'os.environ' in all_code or 'process.env' in all_code:
            evidence.append("Uses environment variables")
            score += 0.05
        
        if any(val in all_code for val in ['validate', 'sanitize', 'escape']):
            evidence.append("Input validation present")
            score += 0.05
        
        return ConfidenceMetric(
            ConfidenceDimension.SECURITY,
            max(0.0, score),
            self.dimension_weights[ConfidenceDimension.SECURITY],
            evidence,
            concerns,
            {"risk_count": len(concerns)}
        )
    
    async def _analyze_performance(self, capsule: QLCapsule, runtime_result: Optional[RuntimeValidationResult]) -> ConfidenceMetric:
        """Analyze performance characteristics"""
        evidence = []
        concerns = []
        score = 0.7  # Default neutral score
        
        if runtime_result:
            # Execution time analysis
            if runtime_result.execution_time < 5:
                evidence.append("Fast execution time")
                score += 0.1
            elif runtime_result.execution_time > 30:
                concerns.append("Slow execution time")
                score -= 0.1
            
            # Memory usage analysis
            if runtime_result.memory_usage < 100:  # MB
                evidence.append("Low memory usage")
                score += 0.1
            elif runtime_result.memory_usage > 500:
                concerns.append("High memory usage")
                score -= 0.1
        
        # Code analysis for performance patterns
        all_code = '\n'.join(capsule.source_code.values())
        
        # Check for performance anti-patterns
        if 'time.sleep' in all_code or 'Thread.sleep' in all_code:
            concerns.append("Blocking sleep calls found")
            score -= 0.05
        
        if 'while True:' in all_code and 'break' not in all_code:
            concerns.append("Infinite loop detected")
            score -= 0.1
        
        return ConfidenceMetric(
            ConfidenceDimension.PERFORMANCE,
            max(0.0, min(1.0, score)),
            self.dimension_weights[ConfidenceDimension.PERFORMANCE],
            evidence,
            concerns,
            {"execution_time": runtime_result.execution_time if runtime_result else 0}
        )
    
    async def _analyze_reliability(self, capsule: QLCapsule, runtime_result: Optional[RuntimeValidationResult]) -> ConfidenceMetric:
        """Analyze reliability and error handling"""
        evidence = []
        concerns = []
        score = 0.5
        
        all_code = '\n'.join(capsule.source_code.values())
        
        # Error handling
        if 'try:' in all_code and 'except' in all_code:
            evidence.append("Error handling present")
            score += 0.2
        else:
            concerns.append("No error handling found")
        
        # Logging
        if any(log_term in all_code for log_term in ['logging', 'logger', 'log.']):
            evidence.append("Logging implementation found")
            score += 0.1
        else:
            concerns.append("No logging implementation")
        
        # Runtime reliability
        if runtime_result:
            if runtime_result.success:
                evidence.append("Successful runtime execution")
                score += 0.2
            else:
                concerns.append("Runtime execution failed")
                score -= 0.2
        
        return ConfidenceMetric(
            ConfidenceDimension.RELIABILITY,
            max(0.0, min(1.0, score)),
            self.dimension_weights[ConfidenceDimension.RELIABILITY],
            evidence,
            concerns,
            {"runtime_success": runtime_result.success if runtime_result else False}
        )
    
    async def _analyze_maintainability(self, capsule: QLCapsule) -> ConfidenceMetric:
        """Analyze code maintainability"""
        evidence = []
        concerns = []
        score = 0.5
        
        all_code = '\n'.join(capsule.source_code.values())
        
        # Documentation
        if '"""' in all_code or "'''" in all_code:
            evidence.append("Docstrings present")
            score += 0.1
        
        if '#' in all_code or '//' in all_code:
            evidence.append("Code comments present")
            score += 0.05
        
        # Code structure
        function_count = all_code.count('def ') + all_code.count('function ')
        if function_count > 0:
            evidence.append("Structured with functions")
            score += 0.1
        
        class_count = all_code.count('class ')
        if class_count > 0:
            evidence.append("Object-oriented structure")
            score += 0.1
        
        # Complexity
        complexity_indicators = ['if ', 'for ', 'while ', 'switch ', 'case ']
        complexity_score = sum(all_code.count(kw) for kw in complexity_indicators)
        
        if complexity_score > 50:
            concerns.append("High complexity detected")
            score -= 0.1
        
        return ConfidenceMetric(
            ConfidenceDimension.MAINTAINABILITY,
            max(0.0, min(1.0, score)),
            self.dimension_weights[ConfidenceDimension.MAINTAINABILITY],
            evidence,
            concerns,
            {"complexity_score": complexity_score}
        )
    
    async def _analyze_testability(self, capsule: QLCapsule, runtime_result: Optional[RuntimeValidationResult]) -> ConfidenceMetric:
        """Analyze testability and test quality"""
        evidence = []
        concerns = []
        score = 0.3  # Low default for testability
        
        # Check for tests
        if capsule.tests:
            evidence.append("Tests included")
            score += 0.4
            
            # Test execution results
            if runtime_result and runtime_result.test_success:
                evidence.append("Tests pass successfully")
                score += 0.3
            elif runtime_result and not runtime_result.test_success:
                concerns.append("Tests are failing")
                score -= 0.1
        else:
            concerns.append("No tests found")
        
        # Check for test frameworks
        all_code = '\n'.join(capsule.source_code.values())
        test_frameworks = ['pytest', 'unittest', 'jest', 'mocha', 'junit']
        
        for framework in test_frameworks:
            if framework in all_code:
                evidence.append(f"Uses {framework} test framework")
                score += 0.05
                break
        
        return ConfidenceMetric(
            ConfidenceDimension.TESTABILITY,
            max(0.0, min(1.0, score)),
            self.dimension_weights[ConfidenceDimension.TESTABILITY],
            evidence,
            concerns,
            {"has_tests": bool(capsule.tests)}
        )
    
    async def _analyze_deployability(self, capsule: QLCapsule, manifest: Optional[CapsuleManifest]) -> ConfidenceMetric:
        """Analyze deployment readiness"""
        evidence = []
        concerns = []
        score = 0.3
        
        # Check for deployment configuration
        if manifest:
            evidence.append("Deployment manifest present")
            score += 0.2
            
            if manifest.health_check:
                evidence.append("Health check configured")
                score += 0.1
            
            if manifest.resources:
                evidence.append("Resource limits configured")
                score += 0.1
            
            if manifest.ports:
                evidence.append("Ports configured")
                score += 0.1
        else:
            concerns.append("No deployment manifest")
        
        # Check for containerization
        if 'Dockerfile' in capsule.source_code:
            evidence.append("Dockerfile present")
            score += 0.2
        else:
            concerns.append("No Dockerfile found")
        
        # Check for environment configuration
        if any('env' in f.lower() for f in capsule.source_code.keys()):
            evidence.append("Environment configuration present")
            score += 0.1
        
        return ConfidenceMetric(
            ConfidenceDimension.DEPLOYABILITY,
            max(0.0, min(1.0, score)),
            self.dimension_weights[ConfidenceDimension.DEPLOYABILITY],
            evidence,
            concerns,
            {"has_dockerfile": 'Dockerfile' in capsule.source_code}
        )


class AdvancedConfidenceEngine:
    """Advanced confidence engine with ML-based scoring"""
    
    def __init__(self):
        self.feature_extractor = ConfidenceFeatureExtractor()
        self.dimensional_analyzer = DimensionalConfidenceAnalyzer()
        self.ml_model = self._initialize_ml_model()
        self.scaler = StandardScaler()
        self.confidence_thresholds = {
            ConfidenceLevel.CRITICAL: 0.95,
            ConfidenceLevel.HIGH: 0.85,
            ConfidenceLevel.MEDIUM: 0.70,
            ConfidenceLevel.LOW: 0.50,
            ConfidenceLevel.VERY_LOW: 0.0
        }
    
    def _initialize_ml_model(self) -> RandomForestClassifier:
        """Initialize ML model for confidence prediction"""
        # In production, this would be loaded from a trained model
        return RandomForestClassifier(
            n_estimators=100,
            random_state=42,
            max_depth=10
        )
    
    async def analyze_confidence(self, capsule: QLCapsule, manifest: Optional[CapsuleManifest] = None,
                               runtime_result: Optional[RuntimeValidationResult] = None) -> ConfidenceAnalysis:
        """Perform comprehensive confidence analysis"""
        
        logger.info(f"Starting confidence analysis for capsule {capsule.id}")
        
        # Extract features
        features = self.feature_extractor.extract_capsule_features(capsule, manifest, runtime_result)
        
        # Analyze each dimension
        dimension_analyses = {}
        for dimension in ConfidenceDimension:
            if dimension in self.dimensional_analyzer.dimension_weights:
                analysis = await self.dimensional_analyzer.analyze_dimension(dimension, capsule, manifest, runtime_result)
                dimension_analyses[dimension] = analysis
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(dimension_analyses)
        
        # Determine confidence level
        confidence_level = self._determine_confidence_level(overall_score)
        
        # Generate recommendations and risk assessment
        risk_factors = self._identify_risk_factors(dimension_analyses)
        success_indicators = self._identify_success_indicators(dimension_analyses)
        failure_modes = self._predict_failure_modes(dimension_analyses)
        mitigation_strategies = self._generate_mitigation_strategies(dimension_analyses)
        
        # Determine if human review is needed
        human_review_required = self._requires_human_review(overall_score, dimension_analyses)
        
        # Estimate success probability
        success_probability = self._estimate_success_probability(features, dimension_analyses)
        
        # Generate deployment recommendation
        deployment_recommendation = self._generate_deployment_recommendation(confidence_level, risk_factors)
        
        analysis = ConfidenceAnalysis(
            overall_score=overall_score,
            confidence_level=confidence_level,
            dimensions=dimension_analyses,
            deployment_recommendation=deployment_recommendation,
            risk_factors=risk_factors,
            success_indicators=success_indicators,
            human_review_required=human_review_required,
            estimated_success_probability=success_probability,
            failure_modes=failure_modes,
            mitigation_strategies=mitigation_strategies,
            metadata={
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "capsule_id": capsule.id,
                "feature_count": len(features),
                "dimension_count": len(dimension_analyses)
            }
        )
        
        logger.info(f"Confidence analysis complete: {confidence_level.value} ({overall_score:.3f})")
        return analysis
    
    def _calculate_overall_score(self, dimension_analyses: Dict[ConfidenceDimension, ConfidenceMetric]) -> float:
        """Calculate weighted overall confidence score"""
        total_score = 0.0
        total_weight = 0.0
        
        for dimension, metric in dimension_analyses.items():
            total_score += metric.score * metric.weight
            total_weight += metric.weight
        
        if total_weight > 0:
            return total_score / total_weight
        return 0.0
    
    def _determine_confidence_level(self, score: float) -> ConfidenceLevel:
        """Determine confidence level from score"""
        if score >= self.confidence_thresholds[ConfidenceLevel.CRITICAL]:
            return ConfidenceLevel.CRITICAL
        elif score >= self.confidence_thresholds[ConfidenceLevel.HIGH]:
            return ConfidenceLevel.HIGH
        elif score >= self.confidence_thresholds[ConfidenceLevel.MEDIUM]:
            return ConfidenceLevel.MEDIUM
        elif score >= self.confidence_thresholds[ConfidenceLevel.LOW]:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW
    
    def _identify_risk_factors(self, dimension_analyses: Dict[ConfidenceDimension, ConfidenceMetric]) -> List[str]:
        """Identify major risk factors"""
        risk_factors = []
        
        for dimension, metric in dimension_analyses.items():
            if metric.score < 0.5:
                risk_factors.append(f"Low {dimension.value} score ({metric.score:.2f})")
            
            # Add specific concerns
            risk_factors.extend(metric.concerns)
        
        return risk_factors[:10]  # Top 10 risks
    
    def _identify_success_indicators(self, dimension_analyses: Dict[ConfidenceDimension, ConfidenceMetric]) -> List[str]:
        """Identify success indicators"""
        success_indicators = []
        
        for dimension, metric in dimension_analyses.items():
            if metric.score > 0.8:
                success_indicators.append(f"Strong {dimension.value} score ({metric.score:.2f})")
            
            # Add specific evidence
            success_indicators.extend(metric.evidence)
        
        return success_indicators[:10]  # Top 10 indicators
    
    def _predict_failure_modes(self, dimension_analyses: Dict[ConfidenceDimension, ConfidenceMetric]) -> List[str]:
        """Predict potential failure modes"""
        failure_modes = []
        
        for dimension, metric in dimension_analyses.items():
            if metric.score < 0.3:
                if dimension == ConfidenceDimension.SECURITY:
                    failure_modes.append("Security vulnerability exploitation")
                elif dimension == ConfidenceDimension.PERFORMANCE:
                    failure_modes.append("Performance degradation under load")
                elif dimension == ConfidenceDimension.RELIABILITY:
                    failure_modes.append("Unexpected crashes or errors")
                elif dimension == ConfidenceDimension.DEPLOYABILITY:
                    failure_modes.append("Deployment configuration issues")
        
        return failure_modes
    
    def _generate_mitigation_strategies(self, dimension_analyses: Dict[ConfidenceDimension, ConfidenceMetric]) -> List[str]:
        """Generate mitigation strategies for identified risks"""
        strategies = []
        
        for dimension, metric in dimension_analyses.items():
            if metric.score < 0.5:
                if dimension == ConfidenceDimension.SECURITY:
                    strategies.append("Implement security scanning and code review")
                elif dimension == ConfidenceDimension.TESTABILITY:
                    strategies.append("Add comprehensive test suite")
                elif dimension == ConfidenceDimension.RELIABILITY:
                    strategies.append("Implement error handling and logging")
                elif dimension == ConfidenceDimension.DEPLOYABILITY:
                    strategies.append("Add health checks and resource limits")
        
        return strategies
    
    def _requires_human_review(self, overall_score: float, dimension_analyses: Dict[ConfidenceDimension, ConfidenceMetric]) -> bool:
        """Determine if human review is required"""
        if overall_score < 0.7:
            return True
        
        # Check for critical dimension failures
        critical_dimensions = [ConfidenceDimension.SECURITY, ConfidenceDimension.RELIABILITY]
        for dimension in critical_dimensions:
            if dimension in dimension_analyses and dimension_analyses[dimension].score < 0.5:
                return True
        
        # Check for high number of concerns
        total_concerns = sum(len(metric.concerns) for metric in dimension_analyses.values())
        if total_concerns > 5:
            return True
        
        return False
    
    def _estimate_success_probability(self, features: Dict[str, float], 
                                    dimension_analyses: Dict[ConfidenceDimension, ConfidenceMetric]) -> float:
        """Estimate probability of successful deployment"""
        # Simple heuristic-based probability
        base_probability = 0.5
        
        # Adjust based on critical factors
        if all(metric.score > 0.7 for metric in dimension_analyses.values()):
            base_probability += 0.3
        
        # Runtime success boost
        if features.get('runtime_success', 0) > 0:
            base_probability += 0.2
        
        # Test success boost
        if features.get('test_success', 0) > 0:
            base_probability += 0.1
        
        # Security penalty
        if ConfidenceDimension.SECURITY in dimension_analyses:
            security_score = dimension_analyses[ConfidenceDimension.SECURITY].score
            if security_score < 0.5:
                base_probability -= 0.2
        
        return max(0.0, min(1.0, base_probability))
    
    def _generate_deployment_recommendation(self, confidence_level: ConfidenceLevel, risk_factors: List[str]) -> str:
        """Generate deployment recommendation"""
        if confidence_level == ConfidenceLevel.CRITICAL:
            return "🚀 Deploy immediately - High confidence, minimal risk"
        elif confidence_level == ConfidenceLevel.HIGH:
            return "✅ Deploy with standard monitoring - Good confidence"
        elif confidence_level == ConfidenceLevel.MEDIUM:
            return "⚠️ Deploy with enhanced monitoring - Moderate confidence"
        elif confidence_level == ConfidenceLevel.LOW:
            return "🔍 Human review required before deployment"
        else:
            return "🚫 Block deployment - Critical issues must be resolved"


# Example usage
if __name__ == "__main__":
    async def main():
        # Create test capsule
        capsule = QLCapsule(
            id="test-confidence",
            title="Test Capsule",
            description="Test capsule for confidence analysis",
            source_code={
                "main.py": """
import logging
import os

logger = logging.getLogger(__name__)

def main():
    try:
        print("Hello, World!")
        return 0
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1

if __name__ == "__main__":
    main()
""",
                "requirements.txt": "requests==2.28.0",
                "test_main.py": "def test_main(): assert True"
            },
            documentation="Test capsule with basic functionality",
            tests={"test_main.py": "def test_main(): assert True"}
        )
        
        # Run confidence analysis
        engine = AdvancedConfidenceEngine()
        analysis = await engine.analyze_confidence(capsule)
        
        print(f"🎯 Confidence Analysis Results")
        print(f"Overall Score: {analysis.overall_score:.3f}")
        print(f"Confidence Level: {analysis.confidence_level.value}")
        print(f"Deployment Recommendation: {analysis.deployment_recommendation}")
        print(f"Success Probability: {analysis.estimated_success_probability:.3f}")
        print(f"Human Review Required: {analysis.human_review_required}")
        
        print(f"\n📊 Dimensional Scores:")
        for dimension, metric in analysis.dimensions.items():
            print(f"  {dimension.value}: {metric.score:.3f}")
        
        if analysis.risk_factors:
            print(f"\n⚠️ Risk Factors:")
            for risk in analysis.risk_factors[:5]:
                print(f"  - {risk}")
        
        if analysis.success_indicators:
            print(f"\n✅ Success Indicators:")
            for indicator in analysis.success_indicators[:5]:
                print(f"  - {indicator}")
    
    asyncio.run(main())