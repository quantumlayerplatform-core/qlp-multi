"""
Temporal Workflow for Marketing Campaign System
Handles campaign generation, content creation, optimization, and analytics
"""
import asyncio
import logging
import json
from datetime import timedelta, datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.common import RetryPolicy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Activity timeout configurations
ACTIVITY_TIMEOUT = timedelta(minutes=10)
LONG_ACTIVITY_TIMEOUT = timedelta(minutes=30)
HEARTBEAT_TIMEOUT = timedelta(seconds=60)

# Retry policy for activities
DEFAULT_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=1),
    maximum_attempts=3,
)

# Workflow-safe data classes
@dataclass
class MarketingWorkflowRequest:
    """Marketing campaign workflow request"""
    request_id: str
    tenant_id: str
    user_id: str
    objective: str  # launch_awareness, technical_evangelism, etc.
    product_description: str
    key_features: List[str]
    target_audience: str
    unique_value_prop: str
    duration_days: int
    channels: List[str]  # twitter, linkedin, etc.
    tone_preferences: List[str]  # technical, visionary, etc.
    launch_date: Optional[str] = None
    constraints: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ContentPiece:
    """Individual marketing content piece"""
    content_id: str
    type: str  # tweet_thread, blog_post, etc.
    channel: str
    title: Optional[str]
    content: str
    tone: str
    keywords: List[str]
    hashtags: List[str]
    cta: Optional[str]
    scheduled_time: Optional[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CampaignResult:
    """Campaign generation result"""
    campaign_id: str
    status: str  # completed, failed, partial
    content_pieces: List[ContentPiece]
    content_calendar: Dict[str, List[str]]  # date -> content_ids
    strategy_summary: str
    kpis: Dict[str, Any]
    total_pieces: int
    channels_used: List[str]
    execution_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class OptimizationResult:
    """Campaign optimization result"""
    campaign_id: str
    optimizations_applied: int
    improvements: List[str]
    updated_content: List[ContentPiece]
    performance_prediction: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AnalyticsResult:
    """Campaign analytics result"""
    campaign_id: str
    total_impressions: int
    total_clicks: int
    total_conversions: int
    avg_engagement_rate: float
    best_performing_content: List[str]
    worst_performing_content: List[str]
    channel_performance: Dict[str, Dict[str, Any]]
    recommendations: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


# Activity implementations
@activity.defn
async def generate_campaign_strategy(request: MarketingWorkflowRequest) -> Dict[str, Any]:
    """Generate overall campaign strategy"""
    import httpx
    import os
    
    activity.logger.info(f"Generating campaign strategy for {request.objective}")
    
    try:
        # Use marketing orchestrator to generate strategy
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "http://agent-factory:8001/marketing/strategy",
                json={
                    "objective": request.objective,
                    "product_description": request.product_description,
                    "key_features": request.key_features,
                    "target_audience": request.target_audience,
                    "unique_value_prop": request.unique_value_prop,
                    "duration_days": request.duration_days,
                    "channels": request.channels
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to generate strategy: {response.text}")
            
            strategy_data = response.json()
            
            return {
                "strategy": strategy_data["strategy"],
                "content_themes": strategy_data["content_themes"],
                "messaging_pillars": strategy_data["messaging_pillars"],
                "channel_strategies": strategy_data["channel_strategies"]
            }
            
    except Exception as e:
        activity.logger.error(f"Strategy generation failed: {e}")
        raise


@activity.defn
async def create_content_calendar(request: MarketingWorkflowRequest, strategy: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Create content calendar based on strategy"""
    import httpx
    
    activity.logger.info(f"Creating content calendar for {request.duration_days} days")
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "http://agent-factory:8001/marketing/calendar",
                json={
                    "duration_days": request.duration_days,
                    "channels": request.channels,
                    "strategy": strategy,
                    "launch_date": request.launch_date
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to create calendar: {response.text}")
            
            return response.json()["calendar"]
            
    except Exception as e:
        activity.logger.error(f"Calendar creation failed: {e}")
        raise


@activity.defn
async def generate_content_piece(
    request: MarketingWorkflowRequest,
    content_spec: Dict[str, Any],
    strategy: Dict[str, Any]
) -> ContentPiece:
    """Generate individual content piece"""
    import httpx
    
    activity.logger.info(f"Generating {content_spec['type']} for {content_spec['channel']}")
    
    try:
        # Heartbeat for long-running content generation
        activity.heartbeat({"status": "generating", "type": content_spec["type"]})
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "http://agent-factory:8001/marketing/content",
                json={
                    "content_type": content_spec["type"],
                    "channel": content_spec["channel"],
                    "product_info": request.product_description,
                    "features": request.key_features,
                    "target_audience": request.target_audience,
                    "strategy": strategy,
                    "tone_preferences": request.tone_preferences
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to generate content: {response.text}")
            
            content_data = response.json()
            
            return ContentPiece(
                content_id=content_data["content_id"],
                type=content_spec["type"],
                channel=content_spec["channel"],
                title=content_data.get("title"),
                content=content_data["content"],
                tone=content_data["tone"],
                keywords=content_data.get("keywords", []),
                hashtags=content_data.get("hashtags", []),
                cta=content_data.get("cta"),
                scheduled_time=content_spec.get("scheduled_time"),
                metadata=content_data.get("metadata", {})
            )
            
    except Exception as e:
        activity.logger.error(f"Content generation failed: {e}")
        raise


@activity.defn
async def optimize_content_batch(
    content_pieces: List[ContentPiece],
    target_audience: str,
    tone_preferences: List[str]
) -> List[ContentPiece]:
    """Optimize content for tone and consistency"""
    import httpx
    
    activity.logger.info(f"Optimizing {len(content_pieces)} content pieces")
    
    try:
        activity.heartbeat({"status": "optimizing", "total": len(content_pieces)})
        
        optimized_pieces = []
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Batch optimize for efficiency
            for i in range(0, len(content_pieces), 5):
                batch = content_pieces[i:i+5]
                
                response = await client.post(
                    "http://agent-factory:8001/marketing/optimize",
                    json={
                        "content_pieces": [asdict(piece) for piece in batch],
                        "target_audience": target_audience,
                        "tone_preferences": tone_preferences
                    }
                )
                
                if response.status_code != 200:
                    raise Exception(f"Failed to optimize content: {response.text}")
                
                optimized_data = response.json()
                for opt_content in optimized_data["optimized_content"]:
                    optimized_pieces.append(ContentPiece(**opt_content))
                
                activity.heartbeat({"status": "optimizing", "completed": len(optimized_pieces)})
        
        return optimized_pieces
        
    except Exception as e:
        activity.logger.error(f"Content optimization failed: {e}")
        raise


@activity.defn
async def collect_campaign_analytics(campaign_id: str) -> AnalyticsResult:
    """Collect analytics for campaign"""
    import httpx
    
    activity.logger.info(f"Collecting analytics for campaign {campaign_id}")
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                f"http://orchestrator:8000/marketing/campaigns/{campaign_id}/analytics"
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to collect analytics: {response.text}")
            
            analytics_data = response.json()["analytics"]
            
            return AnalyticsResult(
                campaign_id=campaign_id,
                total_impressions=analytics_data["total_impressions"],
                total_clicks=analytics_data["total_clicks"],
                total_conversions=analytics_data["total_conversions"],
                avg_engagement_rate=analytics_data["avg_engagement_rate"],
                best_performing_content=analytics_data["best_performing_content"],
                worst_performing_content=analytics_data["worst_performing_content"],
                channel_performance=analytics_data["channel_performance"],
                recommendations=analytics_data["recommendations"]
            )
            
    except Exception as e:
        activity.logger.error(f"Analytics collection failed: {e}")
        raise


@activity.defn
async def apply_campaign_optimizations(
    campaign_id: str,
    analytics: AnalyticsResult
) -> OptimizationResult:
    """Apply optimizations based on analytics"""
    import httpx
    
    activity.logger.info(f"Applying optimizations for campaign {campaign_id}")
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"http://orchestrator:8000/marketing/campaigns/{campaign_id}/optimize",
                json=asdict(analytics)
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to apply optimizations: {response.text}")
            
            opt_data = response.json()
            
            return OptimizationResult(
                campaign_id=campaign_id,
                optimizations_applied=opt_data["optimizations_applied"],
                improvements=opt_data["improvements"],
                updated_content=[ContentPiece(**c) for c in opt_data.get("updated_content", [])],
                performance_prediction=opt_data.get("performance_prediction", {})
            )
            
    except Exception as e:
        activity.logger.error(f"Optimization application failed: {e}")
        raise


@activity.defn
async def create_marketing_capsule(
    request: MarketingWorkflowRequest,
    campaign_result: CampaignResult
) -> Dict[str, Any]:
    """Create marketing capsule with all campaign assets"""
    import httpx
    
    activity.logger.info(f"Creating marketing capsule for campaign {campaign_result.campaign_id}")
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "http://agent-factory:8001/marketing/capsule",
                json={
                    "request_id": request.request_id,
                    "tenant_id": request.tenant_id,
                    "user_id": request.user_id,
                    "campaign_data": asdict(campaign_result),
                    "metadata": {
                        "objective": request.objective,
                        "duration": request.duration_days,
                        "channels": request.channels,
                        "generated_at": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to create capsule: {response.text}")
            
            return response.json()
            
    except Exception as e:
        activity.logger.error(f"Capsule creation failed: {e}")
        raise


# Workflow implementation
@workflow.defn
class MarketingWorkflow:
    """Temporal workflow for marketing campaign generation"""
    
    @workflow.run
    async def run(self, request: MarketingWorkflowRequest) -> CampaignResult:
        """Execute marketing campaign workflow"""
        workflow.logger.info(f"Starting marketing workflow for {request.request_id}")
        
        start_time = workflow.now()
        
        try:
            # Step 1: Generate campaign strategy
            strategy = await workflow.execute_activity(
                generate_campaign_strategy,
                request,
                start_to_close_timeout=ACTIVITY_TIMEOUT,
                retry_policy=DEFAULT_RETRY_POLICY,
                heartbeat_timeout=HEARTBEAT_TIMEOUT
            )
            
            # Step 2: Create content calendar
            calendar = await workflow.execute_activity(
                create_content_calendar,
                args=[request, strategy],
                start_to_close_timeout=ACTIVITY_TIMEOUT,
                retry_policy=DEFAULT_RETRY_POLICY
            )
            
            # Step 3: Generate content pieces in parallel
            content_pieces = []
            content_tasks = []
            
            for date, content_specs in calendar.items():
                for spec in content_specs:
                    spec["scheduled_time"] = date
                    task = workflow.execute_activity(
                        generate_content_piece,
                        args=[request, spec, strategy],
                        start_to_close_timeout=LONG_ACTIVITY_TIMEOUT,
                        retry_policy=DEFAULT_RETRY_POLICY,
                        heartbeat_timeout=HEARTBEAT_TIMEOUT
                    )
                    content_tasks.append(task)
            
            # Execute content generation in batches to avoid overwhelming the system
            batch_size = 10
            for i in range(0, len(content_tasks), batch_size):
                batch = content_tasks[i:i+batch_size]
                batch_results = await asyncio.gather(*batch)
                content_pieces.extend(batch_results)
                
                workflow.logger.info(f"Generated {len(content_pieces)} content pieces so far")
            
            # Step 4: Optimize content for tone and consistency
            optimized_content = await workflow.execute_activity(
                optimize_content_batch,
                args=[content_pieces, request.target_audience, request.tone_preferences],
                start_to_close_timeout=LONG_ACTIVITY_TIMEOUT,
                retry_policy=DEFAULT_RETRY_POLICY,
                heartbeat_timeout=HEARTBEAT_TIMEOUT
            )
            
            # Step 5: Build content calendar mapping
            content_calendar = {}
            for piece in optimized_content:
                if piece.scheduled_time:
                    if piece.scheduled_time not in content_calendar:
                        content_calendar[piece.scheduled_time] = []
                    content_calendar[piece.scheduled_time].append(piece.content_id)
            
            # Calculate execution time
            execution_time = (workflow.now() - start_time).total_seconds()
            
            # Create campaign result
            campaign_result = CampaignResult(
                campaign_id=f"campaign_{request.request_id}",
                status="completed",
                content_pieces=optimized_content,
                content_calendar=content_calendar,
                strategy_summary=strategy["strategy"],
                kpis={
                    "target_impressions": len(optimized_content) * 1000,
                    "target_engagement_rate": 0.05,
                    "target_conversions": 50
                },
                total_pieces=len(optimized_content),
                channels_used=list(set(p.channel for p in optimized_content)),
                execution_time=execution_time,
                metadata={
                    "generated_at": workflow.now().isoformat(),
                    "workflow_id": workflow.info().workflow_id
                }
            )
            
            # Step 6: Create marketing capsule
            await workflow.execute_activity(
                create_marketing_capsule,
                args=[request, campaign_result],
                start_to_close_timeout=ACTIVITY_TIMEOUT,
                retry_policy=DEFAULT_RETRY_POLICY
            )
            
            workflow.logger.info(
                f"Marketing workflow completed successfully - campaign_id={campaign_result.campaign_id}, total_pieces={campaign_result.total_pieces}, execution_time={execution_time}"
            )
            
            return campaign_result
            
        except Exception as e:
            workflow.logger.error(f"Marketing workflow failed: {e}")
            
            # Return partial result on failure
            return CampaignResult(
                campaign_id=f"campaign_{request.request_id}",
                status="failed",
                content_pieces=[],
                content_calendar={},
                strategy_summary="",
                kpis={},
                total_pieces=0,
                channels_used=[],
                execution_time=(workflow.now() - start_time).total_seconds(),
                metadata={
                    "error": str(e),
                    "workflow_id": workflow.info().workflow_id
                }
            )


@workflow.defn
class ContentGenerationWorkflow:
    """Workflow for generating individual content pieces"""
    
    @workflow.run
    async def run(
        self,
        content_type: str,
        channel: str,
        product_info: str,
        features: List[str],
        target_audience: str,
        tone_preferences: List[str]
    ) -> ContentPiece:
        """Generate a single content piece"""
        workflow.logger.info(f"Generating {content_type} for {channel}")
        
        # Create minimal request for content generation
        request = MarketingWorkflowRequest(
            request_id=f"content_{workflow.now().timestamp()}",
            tenant_id="default",
            user_id="system",
            objective="content_generation",
            product_description=product_info,
            key_features=features,
            target_audience=target_audience,
            unique_value_prop="",
            duration_days=1,
            channels=[channel],
            tone_preferences=tone_preferences
        )
        
        # Generate content
        content = await workflow.execute_activity(
            generate_content_piece,
            args=[request, {"type": content_type, "channel": channel}, {}],
            start_to_close_timeout=LONG_ACTIVITY_TIMEOUT,
            retry_policy=DEFAULT_RETRY_POLICY,
            heartbeat_timeout=HEARTBEAT_TIMEOUT
        )
        
        return content


@workflow.defn
class CampaignOptimizationWorkflow:
    """Workflow for optimizing existing campaigns"""
    
    @workflow.run
    async def run(self, campaign_id: str) -> OptimizationResult:
        """Optimize a campaign based on performance"""
        workflow.logger.info(f"Optimizing campaign {campaign_id}")
        
        # Step 1: Collect analytics
        analytics = await workflow.execute_activity(
            collect_campaign_analytics,
            campaign_id,
            start_to_close_timeout=ACTIVITY_TIMEOUT,
            retry_policy=DEFAULT_RETRY_POLICY
        )
        
        # Step 2: Apply optimizations
        optimization_result = await workflow.execute_activity(
            apply_campaign_optimizations,
            args=[campaign_id, analytics],
            start_to_close_timeout=LONG_ACTIVITY_TIMEOUT,
            retry_policy=DEFAULT_RETRY_POLICY
        )
        
        workflow.logger.info(
            f"Campaign optimization completed",
            campaign_id=campaign_id,
            optimizations_applied=optimization_result.optimizations_applied
        )
        
        return optimization_result


# Worker setup
async def start_marketing_worker():
    """Start the marketing workflow worker"""
    import os
    
    # Connect to Temporal
    client = await Client.connect(
        os.getenv("TEMPORAL_HOST", "localhost:7233"),
        namespace=os.getenv("TEMPORAL_NAMESPACE", "default")
    )
    
    # Create worker
    worker = Worker(
        client,
        task_queue="marketing-queue",
        workflows=[
            MarketingWorkflow,
            ContentGenerationWorkflow,
            CampaignOptimizationWorkflow
        ],
        activities=[
            generate_campaign_strategy,
            create_content_calendar,
            generate_content_piece,
            optimize_content_batch,
            collect_campaign_analytics,
            apply_campaign_optimizations,
            create_marketing_capsule
        ]
    )
    
    logger.info("Starting marketing workflow worker...")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(start_marketing_worker())