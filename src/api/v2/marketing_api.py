"""
Marketing Campaign API Endpoints

Provides API access to the AI-powered marketing campaign system.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
import io
import zipfile

from src.agents.marketing.orchestrator import MarketingOrchestrator
from src.agents.marketing.models import (
    CampaignRequest, MarketingCampaign, ContentPerformance,
    CampaignAnalytics, Channel, ContentType, ToneStyle, CampaignObjective
)
from src.common.marketing_capsule import MarketingCapsule
from src.common.auth import get_current_user
from src.orchestrator.capsule_storage import CapsuleStorageService, get_capsule_storage
import structlog
from typing import Dict, Any

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v2/marketing", tags=["marketing"])

# Initialize services
orchestrator = MarketingOrchestrator()


@router.post("/campaigns", response_model=Dict[str, Any])
async def create_campaign(
    request: CampaignRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user),
    capsule_storage: CapsuleStorageService = Depends(get_capsule_storage)
):
    """Generate a complete marketing campaign"""
    try:
        logger.info(
            "Creating marketing campaign",
            user_id=current_user["user_id"],
            objective=request.objective
        )
        
        # Generate campaign
        campaign = await orchestrator.generate_campaign(request)
        
        # Create marketing capsule
        marketing_capsule = MarketingCapsule(
            request_id=f"marketing_{datetime.now().timestamp()}",
            user_id=current_user["user_id"],
            tenant_id=current_user["tenant_id"],
            campaign_data=campaign,
            metadata={
                "objective": request.objective.value,
                "duration": request.duration_days,
                "channels": [c.value for c in request.channels]
            }
        )
        
        # Store capsule asynchronously
        background_tasks.add_task(
            capsule_storage.store_capsule,
            marketing_capsule
        )
        
        return {
            "campaign_id": campaign.campaign_id,
            "capsule_id": marketing_capsule.capsule_id,
            "objective": campaign.objective.value,
            "total_content": campaign.total_pieces,
            "channels": [c.value for c in campaign.channels_used],
            "duration_days": campaign.duration_days,
            "message": "Campaign generated successfully"
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
    """Optimize campaign based on performance"""
    try:
        # Get current performance
        analytics = await orchestrator.engagement_monitor.get_campaign_analytics(
            campaign_id
        )
        
        # Get optimization suggestions
        improvements = await orchestrator.iteration_agent.suggest_improvements(
            analytics
        )
        
        # Apply optimizations (in production would update stored campaign)
        
        return {
            "campaign_id": campaign_id,
            "optimizations_applied": len(improvements),
            "improvements": improvements,
            "message": "Campaign optimized successfully"
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
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Generate individual content piece"""
    try:
        # Quick content generation
        if content_type in [ContentType.TWEET_THREAD, ContentType.BLOG_POST]:
            content = await orchestrator.evangelism_agent.generate_content(
                content_type=content_type,
                channel=channel,
                product_info=topic,
                features=["AI-powered", "Fast", "Reliable"],
                target_audience="Developers",
                strategy="Technical evangelism"
            )
        else:
            content = await orchestrator.narrative_agent.generate_content(
                content_type=content_type,
                channel=channel,
                product_info=topic,
                value_prop="Revolutionary AI platform",
                target_audience="Tech leaders",
                tone_preferences=[tone]
            )
        
        return {
            "content": content,
            "type": content_type.value,
            "channel": channel.value,
            "tone": tone.value,
            "generated_at": datetime.now().isoformat()
        }
        
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