"""
Marketing Campaign API Endpoints

Provides API access to the AI-powered marketing campaign system.
Now integrated with Temporal workflows for better orchestration.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
import io
import zipfile
import os
from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy

from src.agents.marketing.orchestrator import MarketingOrchestrator
from src.agents.marketing.models import (
    CampaignRequest, MarketingCampaign, ContentPerformance,
    CampaignAnalytics, Channel, ContentType, ToneStyle, CampaignObjective
)
from src.common.marketing_capsule import MarketingCapsule
from src.common.auth import get_current_user
from src.orchestrator.capsule_storage import CapsuleStorageService, get_capsule_storage
from src.orchestrator.marketing_workflow import (
    MarketingWorkflowRequest, MarketingWorkflow, 
    ContentGenerationWorkflow, CampaignOptimizationWorkflow
)
import structlog
from typing import Dict, Any

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v2/marketing", tags=["marketing"])

# Initialize services
orchestrator = MarketingOrchestrator()

async def get_temporal_client():
    """Create Temporal client"""
    from src.common.config import settings
    return await Client.connect(
        settings.TEMPORAL_SERVER,
        namespace=settings.TEMPORAL_NAMESPACE
    )


@router.post("/campaigns", response_model=Dict[str, Any])
async def create_campaign(
    request: CampaignRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user),
    capsule_storage: CapsuleStorageService = Depends(get_capsule_storage)
):
    """Generate a complete marketing campaign using Temporal workflow"""
    try:
        logger.info(
            "Creating marketing campaign via Temporal",
            user_id=current_user["user_id"],
            objective=request.objective
        )
        
        # Create Temporal client directly without helper function
        from src.common.config import settings
        temporal_client = await Client.connect(
            settings.TEMPORAL_SERVER,
            namespace=settings.TEMPORAL_NAMESPACE
        )
        
        # Create workflow request
        workflow_request = MarketingWorkflowRequest(
            request_id=f"marketing_{datetime.now().timestamp()}",
            tenant_id=current_user["tenant_id"],
            user_id=current_user["user_id"],
            objective=request.objective.value,
            product_description=request.product_description,
            key_features=request.key_features,
            target_audience=request.target_audience,
            unique_value_prop=request.unique_value_prop,
            duration_days=request.duration_days,
            channels=[c.value for c in request.channels],
            tone_preferences=[t.value for t in request.tone_preferences],
            launch_date=request.launch_date.isoformat() if request.launch_date else None,
            constraints=request.constraints
        )
        
        # Start workflow
        workflow_id = f"marketing-campaign-{workflow_request.request_id}"
        handle = await temporal_client.start_workflow(
            MarketingWorkflow.run,
            workflow_request,
            id=workflow_id,
            task_queue="marketing-queue",  # Use dedicated marketing queue
            id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE_FAILED_ONLY
        )
        
        # Wait for workflow completion (with timeout)
        try:
            campaign_result = await handle.result(timeout=300)  # 5 minute timeout
            
            return {
                "workflow_id": workflow_id,
                "campaign_id": campaign_result.campaign_id,
                "status": campaign_result.status,
                "total_content": campaign_result.total_pieces,
                "channels": campaign_result.channels_used,
                "duration_days": request.duration_days,
                "execution_time": campaign_result.execution_time,
                "message": "Campaign generated successfully via Temporal workflow"
            }
        
        except Exception as workflow_error:
            # Workflow failed, but we can still return partial info
            logger.error("Workflow execution failed", error=str(workflow_error))
            return {
                "workflow_id": workflow_id,
                "status": "failed",
                "error": str(workflow_error),
                "message": "Campaign generation failed"
            }
        
    except Exception as e:
        logger.error("Campaign generation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/campaigns/{campaign_id}")
async def get_campaign(
    campaign_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get campaign details"""
    try:
        # In production, retrieve from storage
        # For now, return sample data
        return {
            "campaign_id": campaign_id,
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "message": "Campaign details would be retrieved from storage"
        }
    except Exception as e:
        logger.error("Failed to retrieve campaign", error=str(e))
        raise HTTPException(status_code=404, detail="Campaign not found")


@router.post("/campaigns/{campaign_id}/export")
async def export_campaign(
    campaign_id: str,
    format: str = "zip",
    platform: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Export campaign in various formats"""
    try:
        # Retrieve campaign (in production from storage)
        # For demo, create sample
        campaign = MarketingCampaign(
            campaign_id=campaign_id,
            objective=CampaignObjective.LAUNCH_AWARENESS,
            target_audience="Developers",
            duration_days=30,
            content_pieces=[],
            content_calendar={},
            strategy_summary="Sample strategy"
        )
        
        marketing_capsule = MarketingCapsule(
            request_id=f"export_{campaign_id}",
            user_id=current_user["user_id"],
            tenant_id=current_user["tenant_id"],
            campaign_data=campaign
        )
        
        if format == "zip":
            # Create zip file
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for file_path, content in marketing_capsule.to_file_structure().items():
                    if content:  # Skip directory markers
                        zip_file.writestr(file_path, content)
            
            zip_buffer.seek(0)
            return StreamingResponse(
                zip_buffer,
                media_type="application/zip",
                headers={
                    "Content-Disposition": f"attachment; filename=campaign_{campaign_id}.zip"
                }
            )
            
        elif format == "json":
            return campaign.dict()
            
        elif format == "markdown":
            content = await orchestrator.export_campaign(campaign, "markdown")
            return StreamingResponse(
                io.StringIO(content),
                media_type="text/markdown",
                headers={
                    "Content-Disposition": f"attachment; filename=campaign_{campaign_id}.md"
                }
            )
            
        elif platform:
            # Platform-specific export
            return marketing_capsule.export_for_platform(platform)
            
        else:
            raise HTTPException(status_code=400, detail="Invalid export format")
            
    except Exception as e:
        logger.error("Export failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/campaigns/{campaign_id}/analytics")
async def track_analytics(
    campaign_id: str,
    performance_data: List[ContentPerformance],
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Track performance analytics for a campaign"""
    try:
        # Store performance data
        for perf in performance_data:
            await orchestrator.engagement_monitor.track_performance(
                content_id=perf.content_id,
                channel=perf.channel,
                metrics=perf.dict()
            )
        
        # Get updated analytics
        analytics = await orchestrator.engagement_monitor.get_campaign_analytics(
            campaign_id
        )
        
        return {
            "campaign_id": campaign_id,
            "metrics_tracked": len(performance_data),
            "total_impressions": analytics.total_impressions,
            "avg_engagement_rate": analytics.avg_engagement_rate,
            "message": "Analytics tracked successfully"
        }
        
    except Exception as e:
        logger.error("Analytics tracking failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/campaigns/{campaign_id}/analytics")
async def get_analytics(
    campaign_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get campaign analytics and recommendations"""
    try:
        analytics = await orchestrator.engagement_monitor.get_campaign_analytics(
            campaign_id
        )
        
        # Get improvement suggestions
        improvements = await orchestrator.iteration_agent.suggest_improvements(
            analytics
        )
        
        return {
            "analytics": analytics.dict(),
            "improvements": improvements,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to get analytics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/campaigns/{campaign_id}/optimize")
async def optimize_campaign(
    campaign_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Optimize campaign based on performance using Temporal workflow"""
    try:
        logger.info(
            "Optimizing campaign via Temporal",
            campaign_id=campaign_id,
            user_id=current_user["user_id"]
        )
        
        # Create Temporal client directly
        from src.common.config import settings
        temporal_client = await Client.connect(
            settings.TEMPORAL_SERVER,
            namespace=settings.TEMPORAL_NAMESPACE
        )
        
        # Start optimization workflow
        workflow_id = f"marketing-optimize-{campaign_id}-{datetime.now().timestamp()}"
        handle = await temporal_client.start_workflow(
            CampaignOptimizationWorkflow.run,
            campaign_id,
            id=workflow_id,
            task_queue="marketing-queue",  # Use dedicated marketing queue
            id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE_FAILED_ONLY
        )
        
        # Wait for workflow completion
        try:
            optimization_result = await handle.result(timeout=120)  # 2 minute timeout
            
            return {
                "workflow_id": workflow_id,
                "campaign_id": campaign_id,
                "optimizations_applied": optimization_result.optimizations_applied,
                "improvements": optimization_result.improvements,
                "message": "Campaign optimized successfully via Temporal workflow"
            }
            
        except Exception as workflow_error:
            logger.error("Optimization workflow failed", error=str(workflow_error))
            return {
                "workflow_id": workflow_id,
                "campaign_id": campaign_id,
                "status": "failed",
                "error": str(workflow_error),
                "message": "Campaign optimization failed"
            }
        
    except Exception as e:
        logger.error("Optimization failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/content/generate")
async def generate_content(
    content_type: ContentType,
    channel: Channel,
    tone: ToneStyle,
    topic: str,
    features: List[str] = ["AI-powered", "Fast", "Reliable"],
    target_audience: str = "Developers",
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Generate individual content piece using Temporal workflow"""
    try:
        logger.info(
            "Generating content via Temporal",
            content_type=content_type.value,
            channel=channel.value,
            user_id=current_user["user_id"]
        )
        
        # Create Temporal client directly
        from src.common.config import settings
        temporal_client = await Client.connect(
            settings.TEMPORAL_SERVER,
            namespace=settings.TEMPORAL_NAMESPACE
        )
        
        # Start content generation workflow
        workflow_id = f"marketing-content-{datetime.now().timestamp()}"
        handle = await temporal_client.start_workflow(
            ContentGenerationWorkflow.run,
            args=[
                content_type.value,
                channel.value,
                topic,
                features,
                target_audience,
                [tone.value]
            ],
            id=workflow_id,
            task_queue="marketing-queue",  # Use dedicated marketing queue
            id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE_FAILED_ONLY
        )
        
        # Wait for workflow completion
        try:
            content_piece = await handle.result(timeout=60)  # 1 minute timeout
            
            return {
                "workflow_id": workflow_id,
                "content_id": content_piece.content_id,
                "content": content_piece.content,
                "type": content_piece.type,
                "channel": content_piece.channel,
                "tone": content_piece.tone,
                "keywords": content_piece.keywords,
                "hashtags": content_piece.hashtags,
                "generated_at": datetime.now().isoformat(),
                "message": "Content generated successfully via Temporal workflow"
            }
            
        except Exception as workflow_error:
            logger.error("Content generation workflow failed", error=str(workflow_error))
            raise HTTPException(
                status_code=500, 
                detail=f"Content generation failed: {str(workflow_error)}"
            )
        
    except Exception as e:
        logger.error("Content generation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates")
async def get_templates(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get available campaign templates"""
    templates = [
        {
            "name": "Product Launch",
            "description": "30-day product launch campaign",
            "channels": ["twitter", "linkedin", "email", "producthunt"],
            "duration_days": 30,
            "content_pieces": 45
        },
        {
            "name": "Technical Blog Series",
            "description": "Weekly technical deep-dives",
            "channels": ["medium", "devto", "twitter"],
            "duration_days": 60,
            "content_pieces": 20
        },
        {
            "name": "Founder Thought Leadership",
            "description": "Build founder authority",
            "channels": ["linkedin", "twitter", "medium"],
            "duration_days": 90,
            "content_pieces": 60
        },
        {
            "name": "Developer Outreach",
            "description": "Engage developer community",
            "channels": ["reddit", "hackernews", "twitter", "devto"],
            "duration_days": 30,
            "content_pieces": 35
        }
    ]
    
    return {"templates": templates}


@router.get("/channels")
async def get_channels():
    """Get available marketing channels"""
    return {
        "channels": [
            {
                "id": channel.value,
                "name": channel.value.title(),
                "optimal_times": ["9 AM EST", "1 PM EST", "5 PM EST"],
                "content_types": ["tweet_thread", "image", "poll"],
                "character_limit": 280 if channel == Channel.TWITTER else None
            }
            for channel in Channel
        ]
    }


@router.get("/objectives")
async def get_objectives():
    """Get available campaign objectives"""
    return {
        "objectives": [
            {
                "id": obj.value,
                "name": obj.value.replace("_", " ").title(),
                "description": f"Focus on {obj.value}",
                "recommended_duration": 30,
                "recommended_channels": ["twitter", "linkedin", "email"]
            }
            for obj in CampaignObjective
        ]
    }


@router.get("/workflows/{workflow_id}")
async def get_workflow_status(
    workflow_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get status of a marketing workflow"""
    try:
        # Create Temporal client directly
        from src.common.config import settings
        temporal_client = await Client.connect(
            settings.TEMPORAL_SERVER,
            namespace=settings.TEMPORAL_NAMESPACE
        )
        
        # Get workflow handle
        handle = temporal_client.get_workflow_handle(workflow_id)
        
        # Describe workflow to get status
        description = await handle.describe()
        
        return {
            "workflow_id": workflow_id,
            "status": description.status.name,
            "start_time": description.start_time.isoformat() if description.start_time else None,
            "close_time": description.close_time.isoformat() if description.close_time else None,
            "execution_time": (
                (description.close_time - description.start_time).total_seconds()
                if description.close_time and description.start_time
                else None
            ),
            "task_queue": description.task_queue,
            "workflow_type": description.workflow_type
        }
        
    except Exception as e:
        logger.error("Failed to get workflow status", error=str(e))
        raise HTTPException(status_code=404, detail=f"Workflow not found: {str(e)}")


@router.post("/workflows/{workflow_id}/cancel")
async def cancel_workflow(
    workflow_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Cancel a marketing workflow"""
    try:
        # Create Temporal client directly
        from src.common.config import settings
        temporal_client = await Client.connect(
            settings.TEMPORAL_SERVER,
            namespace=settings.TEMPORAL_NAMESPACE
        )
        
        # Get workflow handle
        handle = temporal_client.get_workflow_handle(workflow_id)
        
        # Cancel workflow
        await handle.cancel()
        
        return {
            "workflow_id": workflow_id,
            "status": "cancelled",
            "message": "Workflow cancelled successfully"
        }
        
    except Exception as e:
        logger.error("Failed to cancel workflow", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to cancel workflow: {str(e)}")