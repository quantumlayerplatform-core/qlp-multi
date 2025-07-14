"""
Scheduled Publisher Workflow - Handles scheduled publishing of marketing content
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from temporalio import workflow, activity
from temporalio.client import Client
from temporalio.worker import Worker
import structlog

from src.orchestrator.marketing_workflow import ContentPiece, publish_content_piece

logger = structlog.get_logger()

# Activity timeout configurations
ACTIVITY_TIMEOUT = timedelta(minutes=5)


@dataclass
class ScheduledPublishRequest:
    """Request to publish scheduled content"""
    campaign_id: str
    check_interval_minutes: int = 60  # How often to check for content to publish


@dataclass
class PublishingStatus:
    """Status of publishing operations"""
    campaign_id: str
    total_scheduled: int
    total_published: int
    total_failed: int
    last_check: datetime
    next_check: datetime
    published_items: List[Dict[str, Any]]
    failed_items: List[Dict[str, Any]]


@activity.defn
async def get_scheduled_content(
    campaign_id: str,
    window_minutes: int = 60
) -> List[ContentPiece]:
    """Get content scheduled for publication in the next window"""
    import httpx
    
    activity.logger.info(
        f"Checking for scheduled content for campaign {campaign_id}",
        window_minutes=window_minutes
    )
    
    try:
        # Get campaign content from storage
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"http://orchestrator:8000/marketing/campaigns/{campaign_id}/scheduled",
                params={"window_minutes": window_minutes}
            )
            
            if response.status_code != 200:
                activity.logger.warning(f"No scheduled content found: {response.text}")
                return []
            
            data = response.json()
            
            # Convert to ContentPiece objects
            content_pieces = []
            now = datetime.now(timezone.utc)
            window_end = now + timedelta(minutes=window_minutes)
            
            for piece_data in data.get("content_pieces", []):
                piece = ContentPiece(**piece_data)
                
                # Check if it's time to publish
                if piece.scheduled_time:
                    scheduled_dt = datetime.fromisoformat(
                        piece.scheduled_time.replace('Z', '+00:00')
                    )
                    if now <= scheduled_dt <= window_end:
                        content_pieces.append(piece)
            
            return content_pieces
            
    except Exception as e:
        activity.logger.error(f"Failed to get scheduled content: {e}")
        return []


@activity.defn
async def update_publishing_status(
    campaign_id: str,
    content_id: str,
    status: str,
    platform_id: Optional[str] = None,
    url: Optional[str] = None,
    error: Optional[str] = None
) -> bool:
    """Update the publishing status of a content piece"""
    import httpx
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"http://orchestrator:8000/marketing/campaigns/{campaign_id}/content/{content_id}/status",
                json={
                    "status": status,
                    "platform_id": platform_id,
                    "url": url,
                    "error": error,
                    "published_at": datetime.now(timezone.utc).isoformat()
                }
            )
            
            return response.status_code == 200
            
    except Exception as e:
        activity.logger.error(f"Failed to update publishing status: {e}")
        return False


@workflow.defn
class ScheduledPublisherWorkflow:
    """Workflow that periodically checks and publishes scheduled content"""
    
    @workflow.run
    async def run(self, request: ScheduledPublishRequest) -> PublishingStatus:
        """Run the scheduled publisher workflow"""
        workflow.logger.info(
            f"Starting scheduled publisher for campaign {request.campaign_id}"
        )
        
        status = PublishingStatus(
            campaign_id=request.campaign_id,
            total_scheduled=0,
            total_published=0,
            total_failed=0,
            last_check=workflow.now(),
            next_check=workflow.now() + timedelta(minutes=request.check_interval_minutes),
            published_items=[],
            failed_items=[]
        )
        
        # Run continuously until cancelled
        while True:
            try:
                # Get content scheduled for the next window
                scheduled_content = await workflow.execute_activity(
                    get_scheduled_content,
                    args=[request.campaign_id, request.check_interval_minutes],
                    start_to_close_timeout=ACTIVITY_TIMEOUT
                )
                
                status.total_scheduled = len(scheduled_content)
                workflow.logger.info(
                    f"Found {len(scheduled_content)} items to publish"
                )
                
                # Publish each piece
                for piece in scheduled_content:
                    try:
                        # Publish the content
                        result = await workflow.execute_activity(
                            publish_content_piece,
                            args=[piece, False],  # Not immediate, respect schedule
                            start_to_close_timeout=ACTIVITY_TIMEOUT
                        )
                        
                        if result["status"] == "published":
                            status.total_published += 1
                            status.published_items.append({
                                "content_id": piece.content_id,
                                "channel": piece.channel,
                                "published_at": result.get("published_at"),
                                "url": result.get("url")
                            })
                            
                            # Update status in storage
                            await workflow.execute_activity(
                                update_publishing_status,
                                args=[
                                    request.campaign_id,
                                    piece.content_id,
                                    "published",
                                    result.get("platform_id"),
                                    result.get("url")
                                ],
                                start_to_close_timeout=ACTIVITY_TIMEOUT
                            )
                        else:
                            status.total_failed += 1
                            status.failed_items.append({
                                "content_id": piece.content_id,
                                "channel": piece.channel,
                                "error": result.get("error", "Unknown error")
                            })
                            
                            # Update failure status
                            await workflow.execute_activity(
                                update_publishing_status,
                                args=[
                                    request.campaign_id,
                                    piece.content_id,
                                    "failed",
                                    None,
                                    None,
                                    result.get("error")
                                ],
                                start_to_close_timeout=ACTIVITY_TIMEOUT
                            )
                        
                        # Small delay between publishes
                        await workflow.sleep(timedelta(seconds=5))
                        
                    except Exception as e:
                        workflow.logger.error(
                            f"Failed to publish {piece.content_id}: {e}"
                        )
                        status.total_failed += 1
                        status.failed_items.append({
                            "content_id": piece.content_id,
                            "channel": piece.channel,
                            "error": str(e)
                        })
                
                # Update status
                status.last_check = workflow.now()
                status.next_check = workflow.now() + timedelta(
                    minutes=request.check_interval_minutes
                )
                
                workflow.logger.info(
                    f"Publishing cycle complete. Published: {status.total_published}, "
                    f"Failed: {status.total_failed}"
                )
                
                # Wait for next check interval
                await workflow.sleep(timedelta(minutes=request.check_interval_minutes))
                
            except workflow.CancelledError:
                workflow.logger.info("Scheduled publisher cancelled")
                break
            except Exception as e:
                workflow.logger.error(f"Publisher cycle failed: {e}")
                # Wait before retrying
                await workflow.sleep(timedelta(minutes=5))
        
        return status


# Worker setup
async def start_publisher_worker():
    """Start the scheduled publisher worker"""
    import os
    
    # Connect to Temporal
    client = await Client.connect(
        os.getenv("TEMPORAL_HOST", "localhost:7233"),
        namespace=os.getenv("TEMPORAL_NAMESPACE", "default")
    )
    
    # Create worker
    worker = Worker(
        client,
        task_queue="publisher-queue",
        workflows=[ScheduledPublisherWorkflow],
        activities=[
            get_scheduled_content,
            publish_content_piece,
            update_publishing_status
        ]
    )
    
    logger.info("Starting scheduled publisher worker...")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(start_publisher_worker())