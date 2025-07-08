"""
AITL API Endpoints
FastAPI endpoints for the AI-in-the-Loop system
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime
import structlog

from src.orchestrator.aitl_system import (
    aitl_orchestrator, 
    AITLRequest, 
    AITLReviewResult,
    AITLDecision,
    convert_hitl_to_aitl
)
from src.common.models import ValidationReport

logger = structlog.get_logger()

# Create router
aitl_router = APIRouter(prefix="/aitl", tags=["aitl"])


class AITLSubmissionRequest(BaseModel):
    """Request model for AITL submission"""
    task_id: str
    code: str
    validation_result: Dict[str, Any]
    task_context: Dict[str, Any]
    priority: str = "normal"


class AITLResponse(BaseModel):
    """Response model for AITL results"""
    request_id: str
    decision: str
    confidence: float
    reasoning: str
    feedback: str
    modifications_required: List[str]
    security_issues: List[str]
    quality_score: float
    estimated_fix_time: int
    reviewer_tier: str
    timestamp: datetime


class HITLToAITLConversion(BaseModel):
    """Request to convert HITL to AITL"""
    hitl_request_data: Dict[str, Any]


@aitl_router.post("/submit", response_model=Dict[str, str])
async def submit_aitl_request(request: AITLSubmissionRequest, background_tasks: BackgroundTasks):
    """
    Submit a request for AITL review
    """
    try:
        # Generate unique request ID
        request_id = f"aitl_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{request.task_id}"
        
        # Convert validation result
        validation_result = ValidationReport(
            id=request.validation_result.get("id", f"val_{request.task_id}"),
            execution_id=request.validation_result.get("execution_id", ""),
            checks=request.validation_result.get("checks", []),
            confidence_score=request.validation_result.get("confidence_score", 0.5),
            overall_status=request.validation_result.get("overall_status", "unknown"),
            requires_human_review=request.validation_result.get("requires_human_review", True)
        )
        
        # Create AITL request
        aitl_request = AITLRequest(
            request_id=request_id,
            task_id=request.task_id,
            code=request.code,
            validation_result=validation_result,
            task_context=request.task_context,
            priority=request.priority
        )
        
        # Submit for review
        submitted_id = await aitl_orchestrator.submit_for_aitl_review(aitl_request)
        
        # Process in background if not high priority
        if request.priority != "high":
            background_tasks.add_task(aitl_orchestrator.process_aitl_request, submitted_id)
        else:
            # Process immediately for high priority
            await aitl_orchestrator.process_aitl_request(submitted_id)
        
        logger.info(f"AITL request submitted: {submitted_id}")
        
        return {
            "status": "submitted", 
            "request_id": submitted_id,
            "message": f"AITL review {'started' if request.priority == 'high' else 'queued'}"
        }
        
    except Exception as e:
        logger.error(f"Failed to submit AITL request: {e}")
        raise HTTPException(status_code=500, detail=f"Submission failed: {str(e)}")


@aitl_router.get("/status/{request_id}", response_model=Dict[str, Any])
async def get_aitl_status(request_id: str):
    """
    Get the status of an AITL request
    """
    try:
        # Check if completed
        result = aitl_orchestrator.get_aitl_result(request_id)
        if result:
            return {
                "status": "completed",
                "request_id": request_id,
                "decision": result.decision.value,
                "confidence": result.confidence,
                "quality_score": result.quality_score,
                "completed_at": datetime.utcnow().isoformat()
            }
        
        # Check if pending
        if request_id in aitl_orchestrator.pending_requests:
            pending_request = aitl_orchestrator.pending_requests[request_id]
            return {
                "status": "pending",
                "request_id": request_id,
                "priority": pending_request.priority,
                "submitted_at": pending_request.created_at.isoformat(),
                "expires_at": pending_request.expires_at.isoformat() if pending_request.expires_at else None
            }
        
        # Check if escalated
        if request_id in aitl_orchestrator.escalation_queue:
            return {
                "status": "escalated",
                "request_id": request_id,
                "reason": "Requires human review or senior oversight"
            }
        
        # Not found
        raise HTTPException(status_code=404, detail=f"Request {request_id} not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get AITL status: {e}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


@aitl_router.get("/result/{request_id}", response_model=AITLResponse)
async def get_aitl_result(request_id: str):
    """
    Get the detailed result of an AITL review
    """
    try:
        result = aitl_orchestrator.get_aitl_result(request_id)
        if not result:
            raise HTTPException(status_code=404, detail=f"Result for {request_id} not found or not yet completed")
        
        return AITLResponse(
            request_id=request_id,
            decision=result.decision.value,
            confidence=result.confidence,
            reasoning=result.reasoning,
            feedback=result.feedback,
            modifications_required=result.modifications_required,
            security_issues=result.security_issues,
            quality_score=result.quality_score,
            estimated_fix_time=result.estimated_fix_time,
            reviewer_tier=result.reviewer_tier,
            timestamp=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get AITL result: {e}")
        raise HTTPException(status_code=500, detail=f"Result retrieval failed: {str(e)}")


@aitl_router.post("/process/{request_id}", response_model=Dict[str, str])
async def process_aitl_request(request_id: str):
    """
    Manually trigger processing of a specific AITL request
    """
    try:
        result_status = await aitl_orchestrator.process_aitl_request(request_id)
        
        return {
            "status": "processed",
            "request_id": request_id,
            "result": result_status,
            "processed_at": datetime.utcnow().isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to process AITL request: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@aitl_router.post("/process-all", response_model=Dict[str, Any])
async def process_all_pending():
    """
    Process all pending AITL requests
    """
    try:
        results = await aitl_orchestrator.process_all_pending()
        
        return {
            "status": "completed",
            "processed_count": len(results),
            "results": results,
            "processed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to process all pending: {e}")
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(e)}")


@aitl_router.get("/statistics", response_model=Dict[str, Any])
async def get_aitl_statistics():
    """
    Get comprehensive AITL system statistics
    """
    try:
        stats = await aitl_orchestrator.get_aitl_statistics()
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "statistics": stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get AITL statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Statistics retrieval failed: {str(e)}")


@aitl_router.get("/pending", response_model=Dict[str, Any])
async def get_pending_requests():
    """
    Get all pending AITL requests
    """
    try:
        status = aitl_orchestrator.get_aitl_status()
        
        # Get detailed pending requests
        pending_details = []
        for request_id in status["pending_ids"]:
            if request_id in aitl_orchestrator.pending_requests:
                request = aitl_orchestrator.pending_requests[request_id]
                pending_details.append({
                    "request_id": request_id,
                    "task_id": request.task_id,
                    "priority": request.priority,
                    "created_at": request.created_at.isoformat(),
                    "expires_at": request.expires_at.isoformat() if request.expires_at else None,
                    "code_length": len(request.code),
                    "validation_checks": len(request.validation_result.checks) if request.validation_result.checks else 0
                })
        
        return {
            "pending_count": status["pending_requests"],
            "pending_requests": pending_details,
            "escalated_count": status["escalation_queue"],
            "system_status": status["system_status"]
        }
        
    except Exception as e:
        logger.error(f"Failed to get pending requests: {e}")
        raise HTTPException(status_code=500, detail=f"Pending requests retrieval failed: {str(e)}")


@aitl_router.post("/convert-hitl", response_model=AITLResponse)
async def convert_hitl_to_aitl_endpoint(conversion_request: HITLToAITLConversion):
    """
    Convert a HITL request to AITL and process it
    """
    try:
        result = await convert_hitl_to_aitl(conversion_request.hitl_request_data)
        
        if not result:
            raise HTTPException(status_code=500, detail="HITL to AITL conversion failed")
        
        return AITLResponse(
            request_id=conversion_request.hitl_request_data["request_id"],
            decision=result.decision.value,
            confidence=result.confidence,
            reasoning=result.reasoning,
            feedback=result.feedback,
            modifications_required=result.modifications_required,
            security_issues=result.security_issues,
            quality_score=result.quality_score,
            estimated_fix_time=result.estimated_fix_time,
            reviewer_tier=result.reviewer_tier,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to convert HITL to AITL: {e}")
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")


@aitl_router.get("/health", response_model=Dict[str, str])
async def aitl_health_check():
    """
    Health check for AITL system
    """
    try:
        status = aitl_orchestrator.get_aitl_status()
        
        return {
            "status": "healthy",
            "system_status": status["system_status"],
            "pending_count": str(status["pending_requests"]),
            "completed_count": str(status["completed_reviews"]),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"AITL health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


# Advanced features

@aitl_router.post("/batch-submit", response_model=Dict[str, Any])
async def batch_submit_aitl_requests(requests: List[AITLSubmissionRequest], background_tasks: BackgroundTasks):
    """
    Submit multiple requests for AITL review in batch
    """
    try:
        submitted_requests = []
        
        for request in requests:
            # Generate unique request ID
            request_id = f"aitl_batch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{request.task_id}"
            
            # Convert validation result
            validation_result = ValidationReport(
                id=request.validation_result.get("id", f"val_batch_{request.task_id}"),
                execution_id=request.validation_result.get("execution_id", ""),
                checks=request.validation_result.get("checks", []),
                confidence_score=request.validation_result.get("confidence_score", 0.5),
                overall_status=request.validation_result.get("overall_status", "unknown"),
                requires_human_review=request.validation_result.get("requires_human_review", True)
            )
            
            # Create AITL request
            aitl_request = AITLRequest(
                request_id=request_id,
                task_id=request.task_id,
                code=request.code,
                validation_result=validation_result,
                task_context=request.task_context,
                priority=request.priority
            )
            
            # Submit for review
            submitted_id = await aitl_orchestrator.submit_for_aitl_review(aitl_request)
            submitted_requests.append(submitted_id)
        
        # Process all in background
        background_tasks.add_task(aitl_orchestrator.process_all_pending)
        
        logger.info(f"Batch AITL submission: {len(submitted_requests)} requests")
        
        return {
            "status": "batch_submitted",
            "request_count": len(submitted_requests),
            "request_ids": submitted_requests,
            "message": "Batch processing started in background"
        }
        
    except Exception as e:
        logger.error(f"Failed batch AITL submission: {e}")
        raise HTTPException(status_code=500, detail=f"Batch submission failed: {str(e)}")


@aitl_router.get("/escalated", response_model=Dict[str, Any])
async def get_escalated_requests():
    """
    Get requests that were escalated to human review
    """
    try:
        escalated_ids = aitl_orchestrator.escalation_queue
        escalated_details = []
        
        for request_id in escalated_ids[-20:]:  # Last 20 escalations
            result = aitl_orchestrator.get_aitl_result(request_id)
            if result:
                escalated_details.append({
                    "request_id": request_id,
                    "decision": result.decision.value,
                    "reasoning": result.reasoning,
                    "confidence": result.confidence,
                    "reviewer_tier": result.reviewer_tier,
                    "security_issues_count": len(result.security_issues),
                    "escalated_at": datetime.utcnow().isoformat()  # Approximate
                })
        
        return {
            "escalated_count": len(escalated_ids),
            "recent_escalations": escalated_details,
            "escalation_rate": len(escalated_ids) / max(len(aitl_orchestrator.completed_reviews), 1),
            "requires_attention": len(escalated_ids) > 0
        }
        
    except Exception as e:
        logger.error(f"Failed to get escalated requests: {e}")
        raise HTTPException(status_code=500, detail=f"Escalated requests retrieval failed: {str(e)}")


# Include router in main application
def include_aitl_routes(app):
    """Include AITL routes in the FastAPI application"""
    app.include_router(aitl_router)
    logger.info("AITL routes included in application")