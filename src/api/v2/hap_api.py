"""
HAP (Hate, Abuse, Profanity) API endpoints
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pydantic import BaseModel, Field

from src.moderation.hap_service import (
    hap_service, HAPCheckRequest, HAPCheckResult,
    CheckContext, Severity, Category
)
from src.common.auth import get_current_user
from src.common.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/hap", tags=["HAP"])


class BatchCheckRequest(BaseModel):
    """Batch content check request"""
    items: List[Dict[str, Union[str, Dict]]] = Field(
        description="List of items to check",
        min_items=1,
        max_items=100
    )
    context: CheckContext = CheckContext.USER_REQUEST


class HAPConfig(BaseModel):
    """HAP configuration model"""
    sensitivity: str = Field(
        default="moderate",
        description="Sensitivity level: strict, moderate, lenient"
    )
    categories: Dict[str, bool] = Field(
        default_factory=lambda: {
            "hate_speech": True,
            "abuse": True,
            "profanity": True,
            "violence": True,
            "self_harm": True,
            "sexual": True,
            "spam": False
        }
    )
    custom_rules: List[Dict[str, Union[str, bool, int]]] = Field(default_factory=list)
    whitelist: List[str] = Field(default_factory=list)


class ViolationReport(BaseModel):
    """Violation report for a user/tenant"""
    total_violations: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    categories: List[str] = Field(default_factory=list)
    risk_score: float = 0.0
    last_violation: Optional[datetime] = None


@router.post("/check", response_model=HAPCheckResult)
async def check_content(
    request: HAPCheckRequest,
    user: Dict[str, Any] = Depends(get_current_user)
) -> HAPCheckResult:
    """
    Check content for hate, abuse, and profanity
    
    Args:
        request: Content to check with context
        user: Authenticated user
        
    Returns:
        HAP check result with severity and categories
    """
    try:
        # Add user context to request
        request.user_id = user.get("user_id", user.get("sub"))
        request.tenant_id = user.get("organization_id", "default")
        
        # Initialize service if needed
        if not hap_service.initialized:
            await hap_service.initialize()
        
        # Perform check
        result = await hap_service.check_content(request)
        
        # Log high severity violations
        if result.severity in [Severity.HIGH, Severity.CRITICAL]:
            logger.warning(
                f"High severity content detected - User: {request.user_id}, "
                f"Severity: {result.severity}, Categories: {result.categories}"
            )
        
        return result
        
    except Exception as e:
        logger.error(f"HAP check failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Content check failed: {str(e)}"
        )


@router.post("/check-batch", response_model=List[HAPCheckResult])
async def check_batch(
    batch_request: BatchCheckRequest,
    user: Dict[str, Any] = Depends(get_current_user)
) -> List[HAPCheckResult]:
    """
    Check multiple content items in batch
    
    Args:
        batch_request: Batch of items to check
        user: Authenticated user
        
    Returns:
        List of HAP check results
    """
    try:
        if not hap_service.initialized:
            await hap_service.initialize()
        
        results = []
        user_id = user.get("user_id", user.get("sub"))
        tenant_id = user.get("organization_id", "default")
        
        for item in batch_request.items:
            request = HAPCheckRequest(
                content=item.get("content", ""),
                context=batch_request.context,
                user_id=user_id,
                tenant_id=tenant_id,
                metadata=item.get("metadata", {})
            )
            
            result = await hap_service.check_content(request)
            results.append(result)
        
        return results
        
    except Exception as e:
        logger.error(f"Batch HAP check failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Batch check failed: {str(e)}"
        )


@router.get("/violations", response_model=ViolationReport)
async def get_violations(
    days: int = Query(default=30, ge=1, le=365),
    user_id: Optional[str] = Query(default=None),
    user: Dict[str, Any] = Depends(get_current_user)
) -> ViolationReport:
    """
    Get violation report for a user or tenant
    
    Args:
        days: Number of days to look back
        user_id: Specific user to check (optional)
        user: Authenticated user
        
    Returns:
        Violation report with counts and risk score
    """
    try:
        tenant_id = user.get("organization_id", "default")
        target_user = user_id or user.get("user_id", user.get("sub"))
        
        # Get violations from service
        violations = await hap_service.get_user_violations(
            user_id=target_user,
            tenant_id=tenant_id,
            days=days
        )
        
        # Calculate risk score based on violations
        total = violations.get("total_violations", 0)
        critical = violations.get("critical", 0)
        high = violations.get("high", 0)
        
        risk_score = min(1.0, (critical * 0.5 + high * 0.3 + total * 0.01))
        
        return ViolationReport(
            total_violations=total,
            critical=critical,
            high=high,
            medium=violations.get("medium", 0),
            low=violations.get("low", 0),
            categories=violations.get("categories", []),
            risk_score=round(risk_score, 2)
        )
        
    except Exception as e:
        logger.error(f"Failed to get violations: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve violations: {str(e)}"
        )


@router.get("/config", response_model=HAPConfig)
async def get_config(
    user: Dict[str, Any] = Depends(get_current_user)
) -> HAPConfig:
    """
    Get HAP configuration for the tenant
    
    Args:
        user: Authenticated user
        
    Returns:
        Current HAP configuration
    """
    # In production, load from database per tenant
    return HAPConfig()


@router.put("/config", response_model=HAPConfig)
async def update_config(
    config: HAPConfig,
    user: Dict[str, Any] = Depends(get_current_user)
) -> HAPConfig:
    """
    Update HAP configuration for the tenant
    
    Args:
        config: New configuration
        user: Authenticated user (must be admin)
        
    Returns:
        Updated configuration
    """
    # Check admin permissions
    permissions = user.get("permissions", [])
    if "admin" not in permissions and "hap:write" not in permissions:
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions to update HAP config"
        )
    
    # In production, save to database
    logger.info(f"HAP config updated for tenant {user.get('organization_id')}")
    
    return config


@router.post("/report-false-positive")
async def report_false_positive(
    content_hash: str = Body(..., description="Hash of flagged content"),
    reason: str = Body(..., description="Reason for false positive"),
    user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, str]:
    """
    Report a false positive detection
    
    Args:
        content_hash: Hash of the incorrectly flagged content
        reason: Explanation of why it's a false positive
        user: Authenticated user
        
    Returns:
        Confirmation message
    """
    # In production, log to database for review
    logger.info(
        f"False positive reported - User: {user.get('user_id')}, "
        f"Hash: {content_hash}, Reason: {reason}"
    )
    
    return {
        "status": "reported",
        "message": "Thank you for reporting. We'll review this case."
    }


@router.get("/stats")
async def get_statistics(
    period: str = Query(default="day", regex="^(hour|day|week|month)$"),
    user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get HAP statistics for the tenant
    
    Args:
        period: Time period for statistics
        user: Authenticated user
        
    Returns:
        Statistics including violation trends
    """
    # Check permissions
    permissions = user.get("permissions", [])
    if "admin" not in permissions and "hap:stats" not in permissions:
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions to view HAP statistics"
        )
    
    # In production, query from hap_statistics table
    # For now, return sample data
    return {
        "period": period,
        "total_checks": 1523,
        "total_violations": 47,
        "violation_rate": 0.031,
        "by_severity": {
            "critical": 2,
            "high": 8,
            "medium": 15,
            "low": 22
        },
        "by_category": {
            "profanity": 18,
            "abuse": 12,
            "hate_speech": 5,
            "violence": 7,
            "spam": 5
        },
        "trending": "decreasing",
        "top_contexts": [
            {"context": "user_request", "count": 28},
            {"context": "agent_output", "count": 19}
        ]
    }


@router.get("/high-risk-users")
async def get_high_risk_users(
    limit: int = Query(default=10, ge=1, le=100),
    user: Dict[str, Any] = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Get list of high-risk users for review
    
    Args:
        limit: Maximum number of users to return
        user: Authenticated user (must be admin)
        
    Returns:
        List of high-risk users with violation details
    """
    # Check admin permissions
    permissions = user.get("permissions", [])
    if "admin" not in permissions:
        raise HTTPException(
            status_code=403,
            detail="Admin permissions required"
        )
    
    # In production, query from hap_high_risk_users view
    # For now, return empty list
    return []


# Health check endpoint
@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Check HAP service health"""
    try:
        if not hap_service.initialized:
            await hap_service.initialize()
        
        return {
            "status": "healthy",
            "service": "HAP Detection",
            "initialized": hap_service.initialized
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }