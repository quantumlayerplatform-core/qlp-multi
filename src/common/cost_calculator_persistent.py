#!/usr/bin/env python3
"""
Persistent Cost Calculator for LLM Usage
Tracks and stores costs in PostgreSQL database
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import json
import asyncio
from contextlib import asynccontextmanager

import asyncpg
import structlog
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text

from src.common.config import settings
from src.common.cost_calculator import LLM_PRICING, EMBEDDING_PRICING, IMAGE_GENERATION_PRICING

logger = structlog.get_logger()

class PersistentCostCalculator:
    """Cost calculator with PostgreSQL persistence"""
    
    def __init__(self, database_url: Optional[str] = None):
        # Try to get DATABASE_URL from environment first, then settings
        import os
        env_db_url = os.getenv('DATABASE_URL')
        self.database_url = database_url or env_db_url or settings.DATABASE_URL
        
        # Ensure we use asyncpg for async operations
        if "+asyncpg" not in self.database_url:
            self.database_url = self.database_url.replace("postgresql://", "postgresql+asyncpg://")
        
        logger.info(f"PersistentCostCalculator using database URL: {self.database_url.split('@')[1] if '@' in self.database_url else 'N/A'}")
        
        self.engine = create_async_engine(
            self.database_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            echo=False
        )
        self.async_session = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        
        # In-memory cache for recent costs (last 1000 entries)
        self._recent_costs = []
        self._max_cache_size = 1000
        
    @asynccontextmanager
    async def get_db(self):
        """Get database session"""
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def track_llm_cost_async(
        self,
        model: str,
        provider: str,
        prompt_tokens: int,
        completion_tokens: int,
        workflow_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        task_id: Optional[str] = None,
        latency_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Track LLM cost and persist to database asynchronously"""
        
        logger.info(
            "track_llm_cost_async called",
            model=model,
            provider=provider,
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens
        )
        
        # Calculate costs
        cost_data = self._calculate_cost(
            model=model,
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            provider=provider
        )
        
        # Add additional fields
        cost_data.update({
            "workflow_id": workflow_id,
            "tenant_id": tenant_id or "default",
            "user_id": user_id,
            "task_id": task_id,
            "latency_ms": latency_ms,
            "metadata": metadata or {}
        })
        
        # Save to database
        try:
            async with self.get_db() as session:
                await session.execute(
                    text("""
                        INSERT INTO llm_usage (
                            workflow_id, tenant_id, user_id, task_id,
                            provider, model, input_tokens, output_tokens,
                            input_cost_usd, output_cost_usd,
                            latency_ms, metadata
                        ) VALUES (
                            :workflow_id, :tenant_id, :user_id, :task_id,
                            :provider, :model, :input_tokens, :output_tokens,
                            :input_cost_usd, :output_cost_usd,
                            :latency_ms, :metadata
                        )
                    """),
                    {
                        "workflow_id": workflow_id,
                        "tenant_id": tenant_id or "default",
                        "user_id": user_id,
                        "task_id": task_id,
                        "provider": provider,
                        "model": model,
                        "input_tokens": prompt_tokens,
                        "output_tokens": completion_tokens,
                        "input_cost_usd": cost_data["input_cost_usd"],
                        "output_cost_usd": cost_data["output_cost_usd"],
                        "latency_ms": latency_ms,
                        "metadata": json.dumps(metadata or {})
                    }
                )
            
            logger.info(
                "LLM cost tracked to database",
                workflow_id=workflow_id,
                tenant_id=tenant_id,
                model=model,
                cost_usd=cost_data["total_cost_usd"]
            )
            
            # Add to cache
            self._add_to_cache(cost_data)
            
        except Exception as e:
            logger.error(f"Failed to save cost to database: {e}", exc_info=True)
            # Don't fail the LLM call if cost tracking fails
        
        return cost_data
    
    def _calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calculate the cost for LLM usage"""
        
        # Normalize model name
        model_lower = model.lower()
        
        # Find pricing for model
        pricing = None
        for model_key, prices in LLM_PRICING.items():
            if model_key in model_lower:
                pricing = prices
                break
        
        if not pricing:
            logger.warning(f"No pricing found for model: {model}, using GPT-3.5 pricing as fallback")
            pricing = LLM_PRICING["gpt-3.5-turbo"]
        
        # Calculate costs (convert from per 1M tokens to actual cost)
        input_cost = float(Decimal(str(input_tokens * pricing["input"] / 1_000_000)))
        output_cost = float(Decimal(str(output_tokens * pricing["output"] / 1_000_000)))
        total_cost = input_cost + output_cost
        
        return {
            "model": model,
            "provider": provider,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "input_cost_usd": input_cost,
            "output_cost_usd": output_cost,
            "total_cost_usd": total_cost,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pricing_used": {
                "input_per_1m": pricing["input"],
                "output_per_1m": pricing["output"]
            }
        }
    
    def _add_to_cache(self, cost_data: Dict[str, Any]):
        """Add cost data to in-memory cache"""
        self._recent_costs.append(cost_data)
        if len(self._recent_costs) > self._max_cache_size:
            self._recent_costs.pop(0)
    
    async def get_workflow_cost(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get cost for a specific workflow from database"""
        async with self.get_db() as session:
            # Get aggregate data
            result = await session.execute(
                text("""
                    SELECT 
                        COUNT(*) as request_count,
                        COALESCE(SUM(input_tokens), 0) as total_input_tokens,
                        COALESCE(SUM(output_tokens), 0) as total_output_tokens,
                        COALESCE(SUM(total_cost_usd), 0) as total_cost_usd,
                        MIN(created_at) as first_request,
                        MAX(created_at) as last_request
                    FROM llm_usage
                    WHERE workflow_id = :workflow_id
                """),
                {"workflow_id": workflow_id}
            )
            
            row = result.first()
            if not row or row.request_count == 0:
                return None
            
            # Get breakdown by model
            model_result = await session.execute(
                text("""
                    SELECT 
                        model,
                        provider,
                        COUNT(*) as count,
                        SUM(input_tokens) as input_tokens,
                        SUM(output_tokens) as output_tokens,
                        SUM(total_cost_usd) as cost_usd
                    FROM llm_usage
                    WHERE workflow_id = :workflow_id
                    GROUP BY model, provider
                """),
                {"workflow_id": workflow_id}
            )
            
            model_breakdown = {}
            for m in model_result:
                key = f"{m.provider}/{m.model}"
                model_breakdown[key] = {
                    "count": m.count,
                    "input_tokens": m.input_tokens,
                    "output_tokens": m.output_tokens,
                    "cost_usd": float(m.cost_usd)
                }
            
            return {
                "workflow_id": workflow_id,
                "total_requests": row.request_count,
                "total_input_tokens": row.total_input_tokens,
                "total_output_tokens": row.total_output_tokens,
                "total_tokens": row.total_input_tokens + row.total_output_tokens,
                "total_cost_usd": float(row.total_cost_usd),
                "first_request": row.first_request.isoformat() if row.first_request else None,
                "last_request": row.last_request.isoformat() if row.last_request else None,
                "model_breakdown": model_breakdown,
                "average_cost_per_request": float(row.total_cost_usd / row.request_count) if row.request_count > 0 else 0
            }
    
    async def get_tenant_costs(
        self, 
        tenant_id: str, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get costs for a tenant in date range"""
        if not start_date:
            start_date = datetime.now(timezone.utc) - timedelta(days=30)
        if not end_date:
            end_date = datetime.now(timezone.utc)
        
        async with self.get_db() as session:
            # Get aggregate data
            result = await session.execute(
                text("""
                    SELECT 
                        COUNT(*) as request_count,
                        COALESCE(SUM(input_tokens), 0) as total_input_tokens,
                        COALESCE(SUM(output_tokens), 0) as total_output_tokens,
                        COALESCE(SUM(total_cost_usd), 0) as total_cost_usd
                    FROM llm_usage
                    WHERE tenant_id = :tenant_id 
                    AND created_at >= :start_date 
                    AND created_at <= :end_date
                """),
                {
                    "tenant_id": tenant_id,
                    "start_date": start_date,
                    "end_date": end_date
                }
            )
            
            row = result.first()
            
            # Get daily breakdown
            daily_result = await session.execute(
                text("""
                    SELECT 
                        DATE(created_at) as usage_date,
                        SUM(total_cost_usd) as daily_cost
                    FROM llm_usage
                    WHERE tenant_id = :tenant_id 
                    AND created_at >= :start_date 
                    AND created_at <= :end_date
                    GROUP BY DATE(created_at)
                    ORDER BY usage_date
                """),
                {
                    "tenant_id": tenant_id,
                    "start_date": start_date,
                    "end_date": end_date
                }
            )
            
            daily_costs = {
                row.usage_date.isoformat(): float(row.daily_cost)
                for row in daily_result
            }
            
            total_days = (end_date - start_date).days or 1
            total_cost = float(row.total_cost_usd) if row else 0
            
            return {
                "tenant_id": tenant_id,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "total_requests": row.request_count if row else 0,
                "total_input_tokens": row.total_input_tokens if row else 0,
                "total_output_tokens": row.total_output_tokens if row else 0,
                "total_tokens": (row.total_input_tokens + row.total_output_tokens) if row else 0,
                "total_cost_usd": total_cost,
                "average_daily_cost": total_cost / total_days,
                "daily_breakdown": daily_costs,
                "projected_monthly_cost": (total_cost / total_days * 30) if total_days > 0 else 0
            }
    
    async def estimate_capsule_cost(self, complexity: str, tech_stack: List[str]) -> Dict[str, Any]:
        """Estimate cost for generating a capsule based on complexity"""
        
        # Base estimates for token usage
        complexity_multipliers = {
            "trivial": 1.0,
            "simple": 2.0,
            "medium": 5.0,
            "complex": 10.0,
            "very_complex": 20.0
        }
        
        # Base token estimates
        base_input_tokens = 2000   # Prompts, context, etc.
        base_output_tokens = 5000  # Generated code
        
        multiplier = complexity_multipliers.get(complexity, 5.0)
        
        # Adjust for tech stack size
        stack_multiplier = 1.0 + (len(tech_stack) * 0.2)
        
        estimated_input = int(base_input_tokens * multiplier * stack_multiplier)
        estimated_output = int(base_output_tokens * multiplier * stack_multiplier)
        
        # Calculate for different models
        estimates = {}
        for model_name, pricing in [
            ("gpt-3.5-turbo", LLM_PRICING["gpt-3.5-turbo"]),
            ("gpt-4-turbo", LLM_PRICING["gpt-4-turbo"]),
            ("claude-3-sonnet", LLM_PRICING.get("claude-3-sonnet-20240229", LLM_PRICING["gpt-4-turbo"])),
            ("llama3-70b", LLM_PRICING.get("llama3-70b-8192", LLM_PRICING["gpt-3.5-turbo"]))
        ]:
            input_cost = estimated_input * pricing["input"] / 1_000_000
            output_cost = estimated_output * pricing["output"] / 1_000_000
            total = input_cost + output_cost
            
            estimates[model_name] = {
                "estimated_cost_usd": round(total, 4),
                "estimated_tokens": estimated_input + estimated_output
            }
        
        return {
            "complexity": complexity,
            "tech_stack": tech_stack,
            "estimated_input_tokens": estimated_input,
            "estimated_output_tokens": estimated_output,
            "model_estimates": estimates,
            "recommended_model": "gpt-3.5-turbo" if complexity in ["trivial", "simple"] else "gpt-4-turbo"
        }
    
    async def close(self):
        """Close database connections"""
        await self.engine.dispose()


# Global instance
persistent_cost_calculator = PersistentCostCalculator()


# Convenience functions for backward compatibility
async def track_llm_cost(
    model: str,
    provider: str,
    prompt_tokens: int,
    completion_tokens: int,
    workflow_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    task_id: Optional[str] = None,
    latency_ms: Optional[int] = None
) -> Dict[str, Any]:
    """Track LLM usage cost with metadata"""
    logger.info(
        "track_llm_cost wrapper called",
        model=model,
        provider=provider,
        workflow_id=workflow_id
    )
    return await persistent_cost_calculator.track_llm_cost_async(
        model=model,
        provider=provider,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        user_id=user_id,
        task_id=task_id,
        latency_ms=latency_ms,
        metadata=metadata
    )


async def get_cost_report(
    tenant_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Optional[Dict[str, Any]]:
    """Get cost report for tenant or workflow"""
    
    if workflow_id:
        return await persistent_cost_calculator.get_workflow_cost(workflow_id)
    elif tenant_id:
        return await persistent_cost_calculator.get_tenant_costs(
            tenant_id, start_date, end_date
        )
    else:
        return None