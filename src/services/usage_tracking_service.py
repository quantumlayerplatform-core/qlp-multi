"""
Usage tracking service with real-time quota enforcement
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import time

import redis.asyncio as redis
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.base import BaseService, ServiceError, QuotaExceededError, DomainEvent
from src.models.tenant import (
    UsageEvent, TenantQuota, UsageSummary, Tenant,
    ResourceType, QuotaPeriod, TenantPlan
)
from src.common.logger import get_logger

logger = get_logger(__name__)


class QuotaCheck:
    """Result of quota check"""
    def __init__(
        self,
        allowed: bool,
        resource_type: ResourceType,
        current_usage: Decimal,
        limit: Decimal,
        period: QuotaPeriod,
        remaining: Decimal,
        reset_at: Optional[datetime] = None
    ):
        self.allowed = allowed
        self.resource_type = resource_type
        self.current_usage = current_usage
        self.limit = limit
        self.period = period
        self.remaining = remaining
        self.reset_at = reset_at
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "resource_type": self.resource_type.value,
            "current_usage": float(self.current_usage),
            "limit": float(self.limit),
            "period": self.period.value,
            "remaining": float(self.remaining),
            "reset_at": self.reset_at.isoformat() if self.reset_at else None
        }


class UsageSummaryData:
    """Usage summary data"""
    def __init__(self, resource_type: ResourceType, period: QuotaPeriod):
        self.resource_type = resource_type
        self.period = period
        self.total_usage = Decimal(0)
        self.event_count = 0
        self.by_user: Dict[str, Decimal] = defaultdict(Decimal)
        self.by_workspace: Dict[str, Decimal] = defaultdict(Decimal)
        self.peak_usage = Decimal(0)
        self.peak_time = None


class UsageTrackingService(BaseService):
    """
    Real-time usage tracking with quota enforcement
    
    Features:
    - Sub-millisecond quota checks with Redis
    - Sliding window rate limiting
    - Batch event processing
    - Automatic quota resets
    - Usage analytics and reporting
    """
    
    def __init__(self):
        super().__init__()
        self._redis_client: Optional[redis.Redis] = None
        self._batch_queue: List[UsageEvent] = []
        self._batch_lock = asyncio.Lock()
        self._batch_task: Optional[asyncio.Task] = None
        self._quota_cache: Dict[str, Tuple[TenantQuota, datetime]] = {}
        self._cache_ttl = 300  # 5 minutes
    
    async def initialize(self):
        """Initialize service with Redis connection"""
        await super().initialize()
        
        # Initialize Redis
        try:
            self._redis_client = await redis.from_url(
                "redis://localhost:6379/1",  # Use DB 1 for usage tracking
                decode_responses=True
            )
            await self._redis_client.ping()
            logger.info("Connected to Redis for usage tracking")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            # Service can work without Redis, just slower
        
        # Start batch processing task
        self._batch_task = asyncio.create_task(self._batch_processor())
    
    async def close(self):
        """Close connections and stop tasks"""
        if self._batch_task:
            self._batch_task.cancel()
            try:
                await self._batch_task
            except asyncio.CancelledError:
                pass
        
        if self._redis_client:
            await self._redis_client.close()
        
        await super().close()
    
    # Event Tracking Methods
    
    async def track_usage(
        self,
        resource_type: ResourceType,
        amount: Decimal = Decimal(1),
        metadata: Optional[Dict[str, Any]] = None,
        workspace_id: Optional[str] = None,
        check_quota: bool = True
    ) -> None:
        """
        Track resource usage
        
        Args:
            resource_type: Type of resource consumed
            amount: Amount consumed
            metadata: Additional tracking data
            workspace_id: Optional workspace context
            check_quota: Whether to check quota before tracking
        
        Raises:
            QuotaExceededError if quota would be exceeded
        """
        start_time = time.time()
        
        tenant = await self.get_current_tenant()
        user = await self.get_current_user()
        
        if not tenant:
            raise ServiceError("No tenant context for usage tracking")
        
        # Check quota if required
        if check_quota:
            quota_check = await self.check_quota(resource_type, amount)
            if not quota_check.allowed:
                await self.emit_event(DomainEvent(
                    event_type="usage.quota_exceeded",
                    entity_type="tenant",
                    entity_id=str(tenant.id),
                    data={
                        "resource_type": resource_type.value,
                        "requested": float(amount),
                        "current": float(quota_check.current_usage),
                        "limit": float(quota_check.limit)
                    }
                ))
                raise QuotaExceededError(
                    resource_type.value,
                    int(quota_check.limit),
                    int(quota_check.current_usage)
                )
        
        # Create usage event
        event = UsageEvent(
            tenant_id=tenant.id,
            user_id=user.id if user else None,
            workspace_id=workspace_id,
            event_type=resource_type,
            quantity=amount,
            metadata=metadata or {},
            timestamp=datetime.now(timezone.utc)
        )
        
        # Add to batch queue
        async with self._batch_lock:
            self._batch_queue.append(event)
        
        # Update Redis counters for real-time tracking
        if self._redis_client:
            await self._update_redis_counters(tenant.id, resource_type, amount)
        
        # Log performance
        elapsed = (time.time() - start_time) * 1000
        logger.info(
            f"Usage tracked in {elapsed:.2f}ms",
            tenant_id=str(tenant.id),
            resource_type=resource_type.value,
            amount=float(amount)
        )
    
    async def batch_track_usage(self, events: List[Dict[str, Any]]) -> None:
        """Track multiple usage events efficiently"""
        tenant = await self.get_current_tenant()
        user = await self.get_current_user()
        
        if not tenant:
            raise ServiceError("No tenant context for usage tracking")
        
        # Convert to UsageEvent objects
        usage_events = []
        for event_data in events:
            event = UsageEvent(
                tenant_id=tenant.id,
                user_id=user.id if user else None,
                workspace_id=event_data.get("workspace_id"),
                event_type=ResourceType(event_data["resource_type"]),
                quantity=Decimal(event_data.get("amount", 1)),
                metadata=event_data.get("metadata", {}),
                resource_id=event_data.get("resource_id"),
                timestamp=datetime.now(timezone.utc)
            )
            usage_events.append(event)
        
        # Add all to batch queue
        async with self._batch_lock:
            self._batch_queue.extend(usage_events)
        
        # Update Redis counters
        if self._redis_client:
            pipe = self._redis_client.pipeline()
            for event in usage_events:
                await self._update_redis_counters(
                    tenant.id, event.event_type, event.quantity, pipe
                )
            await pipe.execute()
    
    async def track_async(
        self,
        resource_type: ResourceType,
        amount: Decimal = Decimal(1)
    ) -> None:
        """Fire-and-forget usage tracking"""
        # Create task that won't block
        asyncio.create_task(
            self.track_usage(resource_type, amount, check_quota=False)
        )
    
    # Quota Management Methods
    
    async def check_quota(
        self,
        resource_type: ResourceType,
        amount: Decimal = Decimal(1)
    ) -> QuotaCheck:
        """
        Check if usage would exceed quota
        
        Returns:
            QuotaCheck with details
        """
        start_time = time.time()
        tenant = await self.get_current_tenant()
        
        if not tenant:
            raise ServiceError("No tenant context")
        
        # Get quota limits for tenant
        quotas = await self._get_tenant_quotas(tenant.id, resource_type)
        
        # Check each period (minute, hour, day, month)
        for quota in quotas:
            current_usage = await self._get_current_usage(
                tenant.id, resource_type, quota.period
            )
            
            new_usage = current_usage + amount
            allowed = new_usage <= quota.limit_value or not quota.is_hard_limit
            
            if not allowed:
                # Return the first exceeded quota
                return QuotaCheck(
                    allowed=False,
                    resource_type=resource_type,
                    current_usage=current_usage,
                    limit=quota.limit_value,
                    period=quota.period,
                    remaining=Decimal(0),
                    reset_at=self._get_period_reset_time(quota.period)
                )
        
        # All quotas OK, return the most restrictive
        if quotas:
            quota = quotas[0]  # Shortest period is most restrictive
            current_usage = await self._get_current_usage(
                tenant.id, resource_type, quota.period
            )
            
            elapsed = (time.time() - start_time) * 1000
            logger.debug(f"Quota check completed in {elapsed:.2f}ms")
            
            return QuotaCheck(
                allowed=True,
                resource_type=resource_type,
                current_usage=current_usage,
                limit=quota.limit_value,
                period=quota.period,
                remaining=max(Decimal(0), quota.limit_value - current_usage - amount),
                reset_at=self._get_period_reset_time(quota.period)
            )
        
        # No quotas defined, allow by default
        return QuotaCheck(
            allowed=True,
            resource_type=resource_type,
            current_usage=Decimal(0),
            limit=Decimal(999999),
            period=QuotaPeriod.MONTH,
            remaining=Decimal(999999),
            reset_at=None
        )
    
    async def get_remaining_quota(self, resource_type: ResourceType) -> Dict[str, Any]:
        """Get remaining quota for all periods"""
        tenant = await self.get_current_tenant()
        if not tenant:
            raise ServiceError("No tenant context")
        
        quotas = await self._get_tenant_quotas(tenant.id, resource_type)
        remaining = {}
        
        for quota in quotas:
            current = await self._get_current_usage(
                tenant.id, resource_type, quota.period
            )
            remaining[quota.period.value] = {
                "used": float(current),
                "limit": float(quota.limit_value),
                "remaining": float(max(Decimal(0), quota.limit_value - current)),
                "reset_at": self._get_period_reset_time(quota.period).isoformat()
            }
        
        return remaining
    
    async def set_custom_quota(
        self,
        resource_type: ResourceType,
        period: QuotaPeriod,
        limit: Decimal
    ) -> None:
        """Set custom quota for current tenant"""
        tenant = await self.get_current_tenant()
        if not tenant:
            raise ServiceError("No tenant context")
        
        async with await self.get_db() as db:
            # Check if quota exists
            result = await db.execute(
                select(TenantQuota).where(
                    and_(
                        TenantQuota.tenant_id == tenant.id,
                        TenantQuota.resource_type == resource_type,
                        TenantQuota.period == period
                    )
                )
            )
            quota = result.scalar_one_or_none()
            
            if quota:
                quota.limit_value = limit
                quota.updated_at = datetime.now(timezone.utc)
            else:
                quota = TenantQuota(
                    tenant_id=tenant.id,
                    resource_type=resource_type,
                    period=period,
                    limit_value=limit,
                    is_hard_limit=True
                )
                db.add(quota)
            
            await db.commit()
            
            # Clear cache
            self._clear_quota_cache(tenant.id)
            
            await self.log_audit(
                action="quota.updated",
                entity_type="tenant",
                entity_id=str(tenant.id),
                changes={
                    "resource_type": resource_type.value,
                    "period": period.value,
                    "limit": float(limit)
                }
            )
    
    # Reporting Methods
    
    async def get_usage_summary(
        self,
        period: Optional[QuotaPeriod] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get usage summary for current tenant"""
        tenant = await self.get_current_tenant()
        if not tenant:
            raise ServiceError("No tenant context")
        
        if not start_date:
            if period:
                start_date = self._get_period_start(period)
            else:
                start_date = self._get_period_start(QuotaPeriod.MONTH)
        
        if not end_date:
            end_date = datetime.now(timezone.utc)
        
        async with await self.get_db() as db:
            # Get usage events
            result = await db.execute(
                select(UsageEvent).where(
                    and_(
                        UsageEvent.tenant_id == tenant.id,
                        UsageEvent.timestamp >= start_date,
                        UsageEvent.timestamp <= end_date
                    )
                )
            )
            events = result.scalars().all()
            
            # Aggregate by resource type
            summary = defaultdict(lambda: UsageSummaryData(None, period or QuotaPeriod.MONTH))
            
            for event in events:
                data = summary[event.event_type]
                data.resource_type = event.event_type
                data.total_usage += event.quantity
                data.event_count += 1
                
                if event.user_id:
                    data.by_user[str(event.user_id)] += event.quantity
                
                if event.workspace_id:
                    data.by_workspace[str(event.workspace_id)] += event.quantity
                
                if event.quantity > data.peak_usage:
                    data.peak_usage = event.quantity
                    data.peak_time = event.timestamp
            
            # Convert to dict
            return {
                "tenant_id": str(tenant.id),
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "resources": {
                    resource_type.value: {
                        "total_usage": float(data.total_usage),
                        "event_count": data.event_count,
                        "average_per_event": float(
                            data.total_usage / data.event_count
                        ) if data.event_count > 0 else 0,
                        "peak_usage": float(data.peak_usage),
                        "peak_time": data.peak_time.isoformat() if data.peak_time else None,
                        "top_users": sorted(
                            [
                                {"user_id": uid, "usage": float(usage)}
                                for uid, usage in data.by_user.items()
                            ],
                            key=lambda x: x["usage"],
                            reverse=True
                        )[:10],
                        "top_workspaces": sorted(
                            [
                                {"workspace_id": wid, "usage": float(usage)}
                                for wid, usage in data.by_workspace.items()
                            ],
                            key=lambda x: x["usage"],
                            reverse=True
                        )[:10]
                    }
                    for resource_type, data in summary.items()
                }
            }
    
    async def get_detailed_usage(
        self,
        start_date: datetime,
        end_date: datetime,
        resource_type: Optional[ResourceType] = None
    ) -> List[Dict[str, Any]]:
        """Get detailed usage events"""
        tenant = await self.get_current_tenant()
        if not tenant:
            raise ServiceError("No tenant context")
        
        async with await self.get_db() as db:
            query = select(UsageEvent).where(
                and_(
                    UsageEvent.tenant_id == tenant.id,
                    UsageEvent.timestamp >= start_date,
                    UsageEvent.timestamp <= end_date
                )
            )
            
            if resource_type:
                query = query.where(UsageEvent.event_type == resource_type)
            
            query = query.order_by(UsageEvent.timestamp.desc()).limit(10000)
            
            result = await db.execute(query)
            events = result.scalars().all()
            
            return [
                {
                    "id": str(event.id),
                    "timestamp": event.timestamp.isoformat(),
                    "resource_type": event.event_type.value,
                    "quantity": float(event.quantity),
                    "user_id": str(event.user_id) if event.user_id else None,
                    "workspace_id": str(event.workspace_id) if event.workspace_id else None,
                    "resource_id": event.resource_id,
                    "metadata": event.metadata
                }
                for event in events
            ]
    
    # Private Helper Methods
    
    async def _get_tenant_quotas(
        self,
        tenant_id: str,
        resource_type: ResourceType
    ) -> List[TenantQuota]:
        """Get quota limits for tenant, with caching"""
        cache_key = f"{tenant_id}:{resource_type.value}"
        
        # Check cache
        if cache_key in self._quota_cache:
            cached_quotas, cached_at = self._quota_cache[cache_key]
            if datetime.now() - cached_at < timedelta(seconds=self._cache_ttl):
                return cached_quotas
        
        async with await self.get_db() as db:
            # Get custom quotas
            result = await db.execute(
                select(TenantQuota).where(
                    and_(
                        TenantQuota.tenant_id == tenant_id,
                        TenantQuota.resource_type == resource_type
                    )
                ).order_by(TenantQuota.period)
            )
            quotas = list(result.scalars().all())
            
            # If no custom quotas, use plan defaults
            if not quotas:
                tenant_result = await db.execute(
                    select(Tenant).where(Tenant.id == tenant_id)
                )
                tenant = tenant_result.scalar_one_or_none()
                
                if tenant:
                    # Create default quotas based on plan
                    quotas = await self._create_default_quotas(
                        tenant, resource_type, db
                    )
            
            # Cache the results
            self._quota_cache[cache_key] = (quotas, datetime.now())
            
            return quotas
    
    async def _create_default_quotas(
        self,
        tenant: Tenant,
        resource_type: ResourceType,
        db: AsyncSession
    ) -> List[TenantQuota]:
        """Create default quotas based on tenant plan"""
        # Default limits by plan
        plan_limits = {
            TenantPlan.FREE: {
                ResourceType.API_CALLS: {
                    QuotaPeriod.HOUR: 100,
                    QuotaPeriod.DAY: 1000
                },
                ResourceType.CODE_GENERATIONS: {
                    QuotaPeriod.DAY: 50,
                    QuotaPeriod.MONTH: 500
                },
                ResourceType.LLM_TOKENS: {
                    QuotaPeriod.DAY: 100000
                }
            },
            TenantPlan.TEAM: {
                ResourceType.API_CALLS: {
                    QuotaPeriod.HOUR: 1000,
                    QuotaPeriod.DAY: 10000
                },
                ResourceType.CODE_GENERATIONS: {
                    QuotaPeriod.DAY: 500,
                    QuotaPeriod.MONTH: 10000
                },
                ResourceType.LLM_TOKENS: {
                    QuotaPeriod.DAY: 1000000
                }
            },
            TenantPlan.ENTERPRISE: {
                ResourceType.API_CALLS: {
                    QuotaPeriod.HOUR: 10000,
                    QuotaPeriod.DAY: 100000
                },
                ResourceType.CODE_GENERATIONS: {
                    QuotaPeriod.DAY: 5000,
                    QuotaPeriod.MONTH: 100000
                },
                ResourceType.LLM_TOKENS: {
                    QuotaPeriod.DAY: 10000000
                }
            }
        }
        
        quotas = []
        limits = plan_limits.get(tenant.plan, {}).get(resource_type, {})
        
        for period, limit in limits.items():
            quota = TenantQuota(
                tenant_id=tenant.id,
                resource_type=resource_type,
                period=period,
                limit_value=Decimal(limit),
                is_hard_limit=tenant.plan != TenantPlan.ENTERPRISE
            )
            db.add(quota)
            quotas.append(quota)
        
        return quotas
    
    async def _get_current_usage(
        self,
        tenant_id: str,
        resource_type: ResourceType,
        period: QuotaPeriod
    ) -> Decimal:
        """Get current usage for a period"""
        # Try Redis first for real-time data
        if self._redis_client:
            try:
                key = self._get_redis_key(tenant_id, resource_type, period)
                value = await self._redis_client.get(key)
                if value:
                    return Decimal(value)
            except Exception as e:
                logger.error(f"Redis error: {e}")
        
        # Fallback to database
        period_start = self._get_period_start(period)
        
        async with await self.get_db() as db:
            result = await db.execute(
                select(func.sum(UsageEvent.quantity)).where(
                    and_(
                        UsageEvent.tenant_id == tenant_id,
                        UsageEvent.event_type == resource_type,
                        UsageEvent.timestamp >= period_start
                    )
                )
            )
            total = result.scalar_one_or_none()
            return Decimal(total or 0)
    
    async def _update_redis_counters(
        self,
        tenant_id: str,
        resource_type: ResourceType,
        amount: Decimal,
        pipe: Optional[redis.Redis] = None
    ):
        """Update Redis counters for all periods"""
        if not self._redis_client:
            return
        
        redis_client = pipe or self._redis_client
        
        for period in QuotaPeriod:
            key = self._get_redis_key(tenant_id, resource_type, period)
            ttl = self._get_period_ttl(period)
            
            try:
                # Increment counter
                await redis_client.incrbyfloat(key, float(amount))
                # Set expiry
                await redis_client.expire(key, ttl)
            except Exception as e:
                logger.error(f"Redis update error: {e}")
    
    def _get_redis_key(
        self,
        tenant_id: str,
        resource_type: ResourceType,
        period: QuotaPeriod
    ) -> str:
        """Generate Redis key for usage counter"""
        timestamp = self._get_period_start(period).strftime("%Y%m%d%H%M")
        return f"usage:{tenant_id}:{resource_type.value}:{period.value}:{timestamp}"
    
    def _get_period_start(self, period: QuotaPeriod) -> datetime:
        """Get start time for a period"""
        now = datetime.now(timezone.utc)
        
        if period == QuotaPeriod.MINUTE:
            return now.replace(second=0, microsecond=0)
        elif period == QuotaPeriod.HOUR:
            return now.replace(minute=0, second=0, microsecond=0)
        elif period == QuotaPeriod.DAY:
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == QuotaPeriod.MONTH:
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        return now
    
    def _get_period_reset_time(self, period: QuotaPeriod) -> datetime:
        """Get next reset time for a period"""
        start = self._get_period_start(period)
        
        if period == QuotaPeriod.MINUTE:
            return start + timedelta(minutes=1)
        elif period == QuotaPeriod.HOUR:
            return start + timedelta(hours=1)
        elif period == QuotaPeriod.DAY:
            return start + timedelta(days=1)
        elif period == QuotaPeriod.MONTH:
            # Next month
            if start.month == 12:
                return start.replace(year=start.year + 1, month=1)
            else:
                return start.replace(month=start.month + 1)
        
        return start
    
    def _get_period_ttl(self, period: QuotaPeriod) -> int:
        """Get TTL in seconds for Redis key"""
        if period == QuotaPeriod.MINUTE:
            return 120  # 2 minutes
        elif period == QuotaPeriod.HOUR:
            return 3700  # 1 hour + buffer
        elif period == QuotaPeriod.DAY:
            return 90000  # 25 hours
        elif period == QuotaPeriod.MONTH:
            return 2764800  # 32 days
        
        return 3600
    
    def _clear_quota_cache(self, tenant_id: str):
        """Clear quota cache for tenant"""
        keys_to_remove = [
            key for key in self._quota_cache.keys()
            if key.startswith(f"{tenant_id}:")
        ]
        for key in keys_to_remove:
            del self._quota_cache[key]
    
    async def _batch_processor(self):
        """Background task to process usage events in batches"""
        while True:
            try:
                await asyncio.sleep(1)  # Process every second
                
                if not self._batch_queue:
                    continue
                
                # Get events to process
                async with self._batch_lock:
                    events_to_process = self._batch_queue[:100]  # Process up to 100 at a time
                    self._batch_queue = self._batch_queue[100:]
                
                if events_to_process:
                    await self._save_events_to_db(events_to_process)
                    
            except asyncio.CancelledError:
                # Save any remaining events before shutting down
                if self._batch_queue:
                    await self._save_events_to_db(self._batch_queue)
                raise
            except Exception as e:
                logger.error(f"Batch processor error: {e}", exc_info=True)
    
    async def _save_events_to_db(self, events: List[UsageEvent]):
        """Save batch of events to database"""
        async with await self.get_db() as db:
            db.add_all(events)
            await db.commit()
            
            logger.info(f"Saved {len(events)} usage events to database")
            
            # Emit batch saved event
            if events:
                await self.emit_event(DomainEvent(
                    event_type="usage.batch_saved",
                    data={
                        "count": len(events),
                        "tenant_id": str(events[0].tenant_id)
                    }
                ))


# Singleton instance
_usage_service: Optional[UsageTrackingService] = None


async def get_usage_service() -> UsageTrackingService:
    """Get or create usage tracking service instance"""
    global _usage_service
    if not _usage_service:
        _usage_service = UsageTrackingService()
        await _usage_service.initialize()
    return _usage_service