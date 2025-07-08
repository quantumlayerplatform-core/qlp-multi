"""
AITL Comprehensive Logging System
Advanced logging, metrics, and audit trail for AI-in-the-Loop decisions
"""

import asyncio
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import structlog
from collections import defaultdict, deque

from src.orchestrator.aitl_system import AITLReviewResult, AITLDecision, AITLRequest

logger = structlog.get_logger()


@dataclass
class AITLAuditEntry:
    """Comprehensive audit entry for AITL decisions"""
    timestamp: datetime
    request_id: str
    task_id: str
    decision: str
    confidence: float
    quality_score: float
    reviewer_tier: str
    security_issues_count: int
    modifications_count: int
    estimated_fix_time: int
    task_complexity: str
    code_size: int
    validation_checks_count: int
    processing_time_ms: float
    model_used: str
    cost_estimate: float
    session_id: str
    user_context: Dict[str, Any]
    decision_factors: Dict[str, Any]
    metadata: Dict[str, Any]


class AITLMetricsCollector:
    """
    Collects and aggregates metrics for AITL system performance
    """
    
    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.decision_history = deque(maxlen=window_size)
        self.processing_times = deque(maxlen=window_size)
        self.quality_scores = deque(maxlen=window_size)
        self.confidence_scores = deque(maxlen=window_size)
        
        # Aggregated metrics
        self.metrics_by_hour = defaultdict(lambda: {
            "decisions": defaultdict(int),
            "avg_confidence": 0.0,
            "avg_quality": 0.0,
            "total_requests": 0,
            "escalations": 0,
            "processing_time_avg": 0.0
        })
        
        # Real-time metrics
        self.current_session_metrics = {
            "session_start": datetime.utcnow(),
            "total_processed": 0,
            "current_escalation_rate": 0.0,
            "average_confidence": 0.0,
            "performance_score": 0.0
        }
        
        logger.info(f"AITL Metrics Collector initialized with window size {window_size}")
    
    def record_decision(self, audit_entry: AITLAuditEntry):
        """Record a decision for metrics collection"""
        
        # Add to rolling windows
        self.decision_history.append(audit_entry.decision)
        self.processing_times.append(audit_entry.processing_time_ms)
        self.quality_scores.append(audit_entry.quality_score)
        self.confidence_scores.append(audit_entry.confidence)
        
        # Update hourly metrics
        hour_key = audit_entry.timestamp.strftime("%Y-%m-%d-%H")
        hourly_metrics = self.metrics_by_hour[hour_key]
        
        hourly_metrics["decisions"][audit_entry.decision] += 1
        hourly_metrics["total_requests"] += 1
        
        if audit_entry.decision in ["escalate_to_human", "requires_senior_review"]:
            hourly_metrics["escalations"] += 1
        
        # Update averages
        total = hourly_metrics["total_requests"]
        hourly_metrics["avg_confidence"] = (
            (hourly_metrics["avg_confidence"] * (total - 1) + audit_entry.confidence) / total
        )
        hourly_metrics["avg_quality"] = (
            (hourly_metrics["avg_quality"] * (total - 1) + audit_entry.quality_score) / total
        )
        hourly_metrics["processing_time_avg"] = (
            (hourly_metrics["processing_time_avg"] * (total - 1) + audit_entry.processing_time_ms) / total
        )
        
        # Update session metrics
        self.current_session_metrics["total_processed"] += 1
        self._update_session_metrics()
        
        logger.debug("Decision recorded in metrics", request_id=audit_entry.request_id)
    
    def _update_session_metrics(self):
        """Update real-time session metrics"""
        if not self.decision_history:
            return
        
        # Calculate escalation rate
        escalations = sum(1 for d in self.decision_history 
                         if d in ["escalate_to_human", "requires_senior_review"])
        self.current_session_metrics["current_escalation_rate"] = escalations / len(self.decision_history)
        
        # Calculate average confidence
        if self.confidence_scores:
            self.current_session_metrics["average_confidence"] = sum(self.confidence_scores) / len(self.confidence_scores)
        
        # Calculate performance score (composite metric)
        if self.quality_scores and self.confidence_scores and self.processing_times:
            avg_quality = sum(self.quality_scores) / len(self.quality_scores)
            avg_confidence = sum(self.confidence_scores) / len(self.confidence_scores)
            avg_processing = sum(self.processing_times) / len(self.processing_times)
            
            # Performance score: quality * confidence * speed_factor
            speed_factor = max(0.1, min(1.0, 2000 / avg_processing))  # Faster = better
            self.current_session_metrics["performance_score"] = avg_quality * avg_confidence * speed_factor
    
    def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get current real-time metrics"""
        
        recent_decisions = dict()
        for decision in AITLDecision:
            count = sum(1 for d in self.decision_history if d == decision.value)
            recent_decisions[decision.value] = count
        
        return {
            "session_metrics": self.current_session_metrics,
            "recent_decisions": recent_decisions,
            "window_size": len(self.decision_history),
            "average_processing_time": sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0,
            "quality_trend": list(self.quality_scores)[-10:],  # Last 10 quality scores
            "confidence_trend": list(self.confidence_scores)[-10:],  # Last 10 confidence scores
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def get_hourly_analytics(self, hours_back: int = 24) -> Dict[str, Any]:
        """Get hourly analytics for the specified time period"""
        
        analytics = {}
        current_time = datetime.utcnow()
        
        for i in range(hours_back):
            hour_time = current_time - timedelta(hours=i)
            hour_key = hour_time.strftime("%Y-%m-%d-%H")
            
            if hour_key in self.metrics_by_hour:
                analytics[hour_key] = self.metrics_by_hour[hour_key]
            else:
                analytics[hour_key] = {
                    "decisions": {},
                    "avg_confidence": 0.0,
                    "avg_quality": 0.0,
                    "total_requests": 0,
                    "escalations": 0,
                    "processing_time_avg": 0.0
                }
        
        return analytics
    
    def get_performance_insights(self) -> Dict[str, Any]:
        """Generate performance insights and recommendations"""
        
        insights = {
            "performance_summary": {},
            "trends": {},
            "recommendations": [],
            "alerts": []
        }
        
        if not self.decision_history:
            insights["recommendations"].append("Insufficient data for analysis")
            return insights
        
        # Performance summary
        total_decisions = len(self.decision_history)
        escalation_rate = sum(1 for d in self.decision_history 
                            if d in ["escalate_to_human", "requires_senior_review"]) / total_decisions
        
        avg_confidence = sum(self.confidence_scores) / len(self.confidence_scores) if self.confidence_scores else 0
        avg_quality = sum(self.quality_scores) / len(self.quality_scores) if self.quality_scores else 0
        avg_processing = sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
        
        insights["performance_summary"] = {
            "total_decisions": total_decisions,
            "escalation_rate": escalation_rate,
            "average_confidence": avg_confidence,
            "average_quality": avg_quality,
            "average_processing_time_ms": avg_processing,
            "performance_grade": self._calculate_performance_grade(escalation_rate, avg_confidence, avg_quality)
        }
        
        # Generate recommendations
        if escalation_rate > 0.2:
            insights["recommendations"].append("High escalation rate detected. Consider improving agent training or adjusting thresholds.")
        
        if avg_confidence < 0.7:
            insights["recommendations"].append("Low average confidence. Review decision criteria and model parameters.")
        
        if avg_processing > 3000:  # > 3 seconds
            insights["recommendations"].append("High processing times detected. Consider optimizing review algorithms.")
        
        if avg_quality < 0.6:
            insights["recommendations"].append("Low quality scores. Review code generation patterns and training data.")
        
        # Generate alerts
        if escalation_rate > 0.3:
            insights["alerts"].append("CRITICAL: Escalation rate above 30%")
        
        if avg_confidence < 0.5:
            insights["alerts"].append("WARNING: Average confidence below 50%")
        
        return insights
    
    def _calculate_performance_grade(self, escalation_rate: float, avg_confidence: float, avg_quality: float) -> str:
        """Calculate overall performance grade"""
        
        # Scoring system
        escalation_score = max(0, 1 - escalation_rate * 2)  # Lower escalation = better
        confidence_score = avg_confidence
        quality_score = avg_quality
        
        overall_score = (escalation_score * 0.4 + confidence_score * 0.3 + quality_score * 0.3)
        
        if overall_score >= 0.9:
            return "A+"
        elif overall_score >= 0.8:
            return "A"
        elif overall_score >= 0.7:
            return "B"
        elif overall_score >= 0.6:
            return "C"
        elif overall_score >= 0.5:
            return "D"
        else:
            return "F"


class AITLAuditLogger:
    """
    Comprehensive audit logging system for AITL decisions
    """
    
    def __init__(self, log_directory: str = "logs/aitl"):
        self.log_directory = Path(log_directory)
        self.log_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize metrics collector
        self.metrics = AITLMetricsCollector()
        
        # Log files
        self.audit_log_file = self.log_directory / "aitl_audit.jsonl"
        self.metrics_log_file = self.log_directory / "aitl_metrics.jsonl"
        self.error_log_file = self.log_directory / "aitl_errors.jsonl"
        
        # Session tracking
        self.session_id = f"session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"AITL Audit Logger initialized: {self.log_directory}")
    
    async def log_aitl_decision(self, request: AITLRequest, result: AITLReviewResult, 
                              processing_time_ms: float, user_context: Optional[Dict] = None):
        """Log a comprehensive AITL decision"""
        
        try:
            # Create audit entry
            audit_entry = AITLAuditEntry(
                timestamp=datetime.utcnow(),
                request_id=request.request_id,
                task_id=request.task_id,
                decision=result.decision.value,
                confidence=result.confidence,
                quality_score=result.quality_score,
                reviewer_tier=result.reviewer_tier,
                security_issues_count=len(result.security_issues),
                modifications_count=len(result.modifications_required),
                estimated_fix_time=result.estimated_fix_time,
                task_complexity=request.task_context.get("complexity", "unknown"),
                code_size=len(request.code),
                validation_checks_count=len(request.validation_result.checks) if request.validation_result.checks else 0,
                processing_time_ms=processing_time_ms,
                model_used="claude-3-sonnet + gpt-4",  # Based on implementation
                cost_estimate=self._estimate_cost(request, processing_time_ms),
                session_id=self.session_id,
                user_context=user_context or {},
                decision_factors=self._extract_decision_factors(result),
                metadata=result.metadata
            )
            
            # Write to audit log
            await self._write_audit_entry(audit_entry)
            
            # Record in metrics
            self.metrics.record_decision(audit_entry)
            
            # Log metrics periodically
            if self.metrics.current_session_metrics["total_processed"] % 10 == 0:
                await self._write_metrics_snapshot()
            
            logger.info("AITL decision logged", request_id=request.request_id, decision=result.decision.value)
            
        except Exception as e:
            await self._log_error(f"Failed to log AITL decision: {e}", request.request_id)
    
    async def _write_audit_entry(self, audit_entry: AITLAuditEntry):
        """Write audit entry to log file"""
        
        log_data = asdict(audit_entry)
        log_data["timestamp"] = audit_entry.timestamp.isoformat()
        
        async with asyncio.Lock():
            with open(self.audit_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_data) + "\n")
    
    async def _write_metrics_snapshot(self):
        """Write current metrics snapshot to log"""
        
        metrics_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": self.session_id,
            "metrics": self.metrics.get_real_time_metrics(),
            "performance_insights": self.metrics.get_performance_insights()
        }
        
        async with asyncio.Lock():
            with open(self.metrics_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(metrics_data) + "\n")
    
    async def _log_error(self, error_message: str, request_id: Optional[str] = None):
        """Log error to error log file"""
        
        error_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": self.session_id,
            "request_id": request_id,
            "error": error_message,
            "error_type": "aitl_logging_error"
        }
        
        try:
            async with asyncio.Lock():
                with open(self.error_log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(error_data) + "\n")
        except Exception as e:
            logger.error(f"Failed to write error log: {e}")
    
    def _estimate_cost(self, request: AITLRequest, processing_time_ms: float) -> float:
        """Estimate cost of AITL processing"""
        
        # Rough cost estimation based on:
        # - Code size (token count approximation)
        # - Processing time
        # - Model usage
        
        code_tokens = len(request.code) / 4  # Rough approximation
        context_tokens = 2000  # System prompts and context
        total_tokens = code_tokens + context_tokens
        
        # Assume $0.002 per 1K tokens for Claude-3-Sonnet + GPT-4
        cost_per_1k_tokens = 0.002
        estimated_cost = (total_tokens / 1000) * cost_per_1k_tokens
        
        return round(estimated_cost, 6)
    
    def _extract_decision_factors(self, result: AITLReviewResult) -> Dict[str, Any]:
        """Extract key decision factors from result"""
        
        factors = {
            "primary_factor": "unknown",
            "security_weight": 0.0,
            "quality_weight": 0.0,
            "logic_weight": 0.0,
            "confidence_threshold_met": result.confidence >= 0.75,
            "security_issues_blocking": len(result.security_issues) > 0,
            "modifications_extensive": len(result.modifications_required) > 5
        }
        
        # Determine primary decision factor
        if result.decision == AITLDecision.REJECTED:
            if len(result.security_issues) > 0:
                factors["primary_factor"] = "security_issues"
            elif result.quality_score < 0.4:
                factors["primary_factor"] = "low_quality"
            else:
                factors["primary_factor"] = "multiple_issues"
        
        elif result.decision == AITLDecision.APPROVED:
            factors["primary_factor"] = "high_quality"
        
        elif result.decision == AITLDecision.APPROVED_WITH_MODIFICATIONS:
            factors["primary_factor"] = "acceptable_with_fixes"
        
        return factors
    
    async def get_audit_summary(self, hours_back: int = 24) -> Dict[str, Any]:
        """Get audit summary for specified time period"""
        
        summary = {
            "period": f"Last {hours_back} hours",
            "metrics": self.metrics.get_real_time_metrics(),
            "hourly_analytics": self.metrics.get_hourly_analytics(hours_back),
            "performance_insights": self.metrics.get_performance_insights(),
            "session_info": {
                "session_id": self.session_id,
                "session_start": self.metrics.current_session_metrics["session_start"].isoformat(),
                "total_processed": self.metrics.current_session_metrics["total_processed"]
            }
        }
        
        return summary
    
    async def export_audit_data(self, start_date: datetime, end_date: datetime, 
                              export_format: str = "json") -> str:
        """Export audit data for specified date range"""
        
        export_file = self.log_directory / f"aitl_export_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.{export_format}"
        
        try:
            if not self.audit_log_file.exists():
                raise FileNotFoundError("No audit log file found")
            
            exported_entries = []
            
            with open(self.audit_log_file, "r", encoding="utf-8") as f:
                for line in f:
                    entry = json.loads(line.strip())
                    entry_time = datetime.fromisoformat(entry["timestamp"])
                    
                    if start_date <= entry_time <= end_date:
                        exported_entries.append(entry)
            
            # Write export file
            if export_format == "json":
                with open(export_file, "w", encoding="utf-8") as f:
                    json.dump(exported_entries, f, indent=2)
            
            logger.info(f"Exported {len(exported_entries)} audit entries to {export_file}")
            return str(export_file)
            
        except Exception as e:
            logger.error(f"Failed to export audit data: {e}")
            raise


# Global audit logger instance
aitl_audit_logger = AITLAuditLogger()


async def log_aitl_decision(request: AITLRequest, result: AITLReviewResult, 
                          processing_time_ms: float, user_context: Optional[Dict] = None):
    """Global function to log AITL decisions"""
    await aitl_audit_logger.log_aitl_decision(request, result, processing_time_ms, user_context)


async def get_aitl_audit_summary(hours_back: int = 24) -> Dict[str, Any]:
    """Global function to get audit summary"""
    return await aitl_audit_logger.get_audit_summary(hours_back)


def get_aitl_metrics() -> Dict[str, Any]:
    """Global function to get real-time metrics"""
    return aitl_audit_logger.metrics.get_real_time_metrics()