"""Billing service for managing subscriptions and usage"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.billing.models import (
    Organization, User, Subscription, UsageTracking, UsageQuota,
    SubscriptionTier, SubscriptionStatus, ActionType
)
from src.common.logger import get_logger

logger = get_logger(__name__)


# Pricing configuration
PRICING = {
    SubscriptionTier.FREE: {
        "monthly_price": 0,
        "included": {
            "generations": 10,
            "storage_gb": 1,
            "api_calls": 1000,
        },
        "overage_rates": None  # No overages on free tier
    },
    SubscriptionTier.STARTER: {
        "monthly_price": 99,
        "included": {
            "generations": 100,
            "storage_gb": 10,
            "api_calls": 10000,
        },
        "overage_rates": {
            "generation": 1.00,
            "storage_gb": 0.10,
            "api_call": 0.001,
        }
    },
    SubscriptionTier.PROFESSIONAL: {
        "monthly_price": 499,
        "included": {
            "generations": 1000,
            "storage_gb": 100,
            "api_calls": 100000,
        },
        "overage_rates": {
            "generation": 0.75,
            "storage_gb": 0.08,
            "api_call": 0.0008,
        }
    },
    SubscriptionTier.ENTERPRISE: {
        "monthly_price": 2499,
        "included": {
            "generations": -1,  # Unlimited
            "storage_gb": 1000,
            "api_calls": -1,  # Unlimited
        },
        "overage_rates": {
            "storage_gb": 0.05,
        }
    }
}

# Cost per action type and resource
ACTION_COSTS = {
    ActionType.CODE_GENERATION: {
        "T0": 0.03,  # Llama/GPT-3.5
        "T1": 0.10,  # Enhanced GPT-3.5
        "T2": 0.25,  # Claude
        "T3": 0.50,  # GPT-4
    },
    ActionType.VALIDATION: 0.02,
    ActionType.EXPORT: 0.01,
    ActionType.API_CALL: 0.001,
    ActionType.STORAGE: 0.0001,  # Per GB per day
}


class BillingService:
    """Service for managing billing and usage"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def track_usage(
        self,
        organization_id: UUID,
        user_id: UUID,
        action_type: ActionType,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        tokens_used: int = 0,
        compute_time_ms: int = 0,
        storage_bytes: int = 0,
        metadata: Optional[Dict] = None
    ) -> UsageTracking:
        """Track a billable action"""
        
        # Calculate cost
        cost = self._calculate_cost(
            action_type, 
            resource_type, 
            tokens_used, 
            compute_time_ms,
            storage_bytes
        )
        
        # Create usage record
        usage = UsageTracking(
            organization_id=organization_id,
            user_id=user_id,
            action_type=action_type,
            resource_type=resource_type,
            resource_id=resource_id,
            tokens_used=tokens_used,
            compute_time_ms=compute_time_ms,
            storage_bytes=storage_bytes,
            cost=cost,
            meta_data=metadata or {}
        )
        
        self.db.add(usage)
        
        # Update quotas
        await self._update_quotas(organization_id, action_type)
        
        await self.db.commit()
        
        logger.info(
            "Tracked usage",
            organization_id=str(organization_id),
            action_type=action_type.value,
            cost=float(cost)
        )
        
        return usage
    
    async def check_quota(
        self,
        organization_id: UUID,
        action_type: ActionType
    ) -> Tuple[bool, Optional[str]]:
        """Check if organization has quota for action"""
        
        # Get organization's subscription tier
        org = await self.db.get(Organization, organization_id)
        if not org:
            return False, "Organization not found"
        
        # Free tier quotas
        if org.subscription_tier == SubscriptionTier.FREE:
            quota_map = {
                ActionType.CODE_GENERATION: "generations",
                ActionType.API_CALL: "api_calls",
            }
            
            quota_type = quota_map.get(action_type)
            if not quota_type:
                return True, None  # No quota for this action
            
            # Check current usage
            quota = await self._get_or_create_quota(organization_id, quota_type)
            limit = PRICING[SubscriptionTier.FREE]["included"][quota_type]
            
            if quota.used >= limit:
                return False, f"Free tier limit reached ({limit} {quota_type}/month)"
        
        # Paid tiers - check if subscription is active
        if org.subscription_status != SubscriptionStatus.ACTIVE:
            return False, f"Subscription is {org.subscription_status.value}"
        
        return True, None
    
    async def get_usage_summary(
        self,
        organization_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """Get usage summary for organization"""
        
        if not start_date:
            start_date = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Query usage
        stmt = select(
            UsageTracking.action_type,
            func.count(UsageTracking.id).label("count"),
            func.sum(UsageTracking.cost).label("total_cost"),
            func.sum(UsageTracking.tokens_used).label("total_tokens"),
            func.sum(UsageTracking.compute_time_ms).label("total_compute_ms")
        ).where(
            UsageTracking.organization_id == organization_id,
            UsageTracking.timestamp >= start_date,
            UsageTracking.timestamp <= end_date
        ).group_by(UsageTracking.action_type)
        
        result = await self.db.execute(stmt)
        usage_by_type = result.all()
        
        # Format summary
        summary = {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "by_action": {},
            "totals": {
                "cost": Decimal("0"),
                "count": 0,
                "tokens": 0,
                "compute_ms": 0
            }
        }
        
        for row in usage_by_type:
            action_type = row.action_type.value
            summary["by_action"][action_type] = {
                "count": row.count,
                "cost": float(row.total_cost or 0),
                "tokens": row.total_tokens or 0,
                "compute_ms": row.total_compute_ms or 0
            }
            
            summary["totals"]["cost"] += row.total_cost or 0
            summary["totals"]["count"] += row.count
            summary["totals"]["tokens"] += row.total_tokens or 0
            summary["totals"]["compute_ms"] += row.total_compute_ms or 0
        
        summary["totals"]["cost"] = float(summary["totals"]["cost"])
        
        return summary
    
    async def estimate_monthly_bill(
        self,
        organization_id: UUID
    ) -> Dict:
        """Estimate current month's bill"""
        
        org = await self.db.get(Organization, organization_id)
        if not org:
            raise ValueError("Organization not found")
        
        # Get current month usage
        start_date = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
        usage_summary = await self.get_usage_summary(organization_id, start_date)
        
        # Base subscription cost
        base_cost = PRICING[org.subscription_tier]["monthly_price"]
        
        # Calculate overages
        overage_cost = 0
        overages = {}
        
        if org.subscription_tier != SubscriptionTier.FREE:
            included = PRICING[org.subscription_tier]["included"]
            overage_rates = PRICING[org.subscription_tier]["overage_rates"]
            
            # Check generations overage
            generations = usage_summary["by_action"].get(
                ActionType.CODE_GENERATION.value, {}
            ).get("count", 0)
            
            if included["generations"] != -1 and generations > included["generations"]:
                overage_count = generations - included["generations"]
                overage_cost += overage_count * overage_rates["generation"]
                overages["generations"] = {
                    "count": overage_count,
                    "cost": overage_count * overage_rates["generation"]
                }
        
        return {
            "subscription_tier": org.subscription_tier.value,
            "base_cost": base_cost,
            "usage_cost": float(usage_summary["totals"]["cost"]),
            "overage_cost": overage_cost,
            "total_estimated": base_cost + overage_cost,
            "overages": overages,
            "usage_summary": usage_summary
        }
    
    def _calculate_cost(
        self,
        action_type: ActionType,
        resource_type: Optional[str],
        tokens_used: int,
        compute_time_ms: int,
        storage_bytes: int
    ) -> Decimal:
        """Calculate cost for an action"""
        
        cost = Decimal("0")
        
        if action_type == ActionType.CODE_GENERATION:
            # Cost based on model tier
            tier_cost = ACTION_COSTS[action_type].get(resource_type, 0.10)
            cost = Decimal(str(tier_cost))
            
            # Add token-based cost if significant
            if tokens_used > 10000:
                cost += Decimal(str(tokens_used * 0.00001))
                
        elif action_type == ActionType.STORAGE:
            # Storage cost per GB per day
            gb_days = (storage_bytes / 1_073_741_824)  # Convert to GB
            cost = Decimal(str(gb_days * ACTION_COSTS[action_type]))
            
        else:
            # Fixed cost per action
            cost = Decimal(str(ACTION_COSTS.get(action_type, 0.001)))
        
        return cost
    
    async def _update_quotas(
        self,
        organization_id: UUID,
        action_type: ActionType
    ):
        """Update usage quotas"""
        
        quota_map = {
            ActionType.CODE_GENERATION: "generations",
            ActionType.API_CALL: "api_calls",
        }
        
        quota_type = quota_map.get(action_type)
        if not quota_type:
            return
        
        quota = await self._get_or_create_quota(organization_id, quota_type)
        quota.used += 1
        
        # Check if quota needs reset
        if datetime.utcnow() >= quota.reset_at:
            quota.used = 1
            quota.reset_at = self._next_reset_date(quota.period)
    
    async def _get_or_create_quota(
        self,
        organization_id: UUID,
        quota_type: str
    ) -> UsageQuota:
        """Get or create quota record"""
        
        stmt = select(UsageQuota).where(
            UsageQuota.organization_id == organization_id,
            UsageQuota.quota_type == quota_type
        )
        result = await self.db.execute(stmt)
        quota = result.scalar_one_or_none()
        
        if not quota:
            # Create new quota
            org = await self.db.get(Organization, organization_id)
            limit = PRICING[org.subscription_tier]["included"].get(quota_type, 0)
            
            quota = UsageQuota(
                organization_id=organization_id,
                quota_type=quota_type,
                period="month",
                limit=limit,
                used=0,
                reset_at=self._next_reset_date("month")
            )
            self.db.add(quota)
        
        return quota
    
    def _next_reset_date(self, period: str) -> datetime:
        """Calculate next reset date based on period"""
        
        now = datetime.utcnow()
        
        if period == "month":
            # First day of next month
            if now.month == 12:
                return now.replace(year=now.year + 1, month=1, day=1, 
                                 hour=0, minute=0, second=0, microsecond=0)
            else:
                return now.replace(month=now.month + 1, day=1,
                                 hour=0, minute=0, second=0, microsecond=0)
        elif period == "day":
            # Next day at midnight
            return (now + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        else:
            # Default to monthly
            return self._next_reset_date("month")