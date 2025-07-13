#!/usr/bin/env python3
"""
Cost Calculator for LLM Usage
Tracks and calculates costs for different LLM providers and models
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from decimal import Decimal
import json

import structlog

logger = structlog.get_logger()

# Cost per 1M tokens (as of 2024)
# Prices in USD
LLM_PRICING = {
    # OpenAI Models
    "gpt-4-turbo": {
        "input": 10.00,   # $10 per 1M input tokens
        "output": 30.00,  # $30 per 1M output tokens
    },
    "gpt-4": {
        "input": 30.00,   # $30 per 1M input tokens
        "output": 60.00,  # $60 per 1M output tokens
    },
    "gpt-4-32k": {
        "input": 60.00,   # $60 per 1M input tokens
        "output": 120.00, # $120 per 1M output tokens
    },
    "gpt-3.5-turbo": {
        "input": 0.50,    # $0.50 per 1M input tokens
        "output": 1.50,   # $1.50 per 1M output tokens
    },
    "gpt-3.5-turbo-16k": {
        "input": 3.00,    # $3 per 1M input tokens
        "output": 4.00,   # $4 per 1M output tokens
    },
    
    # Azure OpenAI (same as OpenAI)
    "gpt-35-turbo": {
        "input": 0.50,
        "output": 1.50,
    },
    "gpt-4o": {
        "input": 5.00,    # $5 per 1M input tokens
        "output": 15.00,  # $15 per 1M output tokens
    },
    "gpt-4o-mini": {
        "input": 0.15,    # $0.15 per 1M input tokens
        "output": 0.60,   # $0.60 per 1M output tokens
    },
    
    # Anthropic Claude Models
    "claude-3-opus-20240229": {
        "input": 15.00,   # $15 per 1M input tokens
        "output": 75.00,  # $75 per 1M output tokens
    },
    "claude-3-sonnet-20240229": {
        "input": 3.00,    # $3 per 1M input tokens
        "output": 15.00,  # $15 per 1M output tokens
    },
    "claude-3-haiku-20240307": {
        "input": 0.25,    # $0.25 per 1M input tokens
        "output": 1.25,   # $1.25 per 1M output tokens
    },
    "claude-2.1": {
        "input": 8.00,    # $8 per 1M input tokens
        "output": 24.00,  # $24 per 1M output tokens
    },
    "claude-2": {
        "input": 8.00,    # $8 per 1M input tokens
        "output": 24.00,  # $24 per 1M output tokens
    },
    
    # Groq Models (very competitive pricing)
    "llama3-70b-8192": {
        "input": 0.59,    # $0.59 per 1M input tokens
        "output": 0.79,   # $0.79 per 1M output tokens
    },
    "llama3-8b-8192": {
        "input": 0.05,    # $0.05 per 1M input tokens
        "output": 0.10,   # $0.10 per 1M output tokens
    },
    "mixtral-8x7b-32768": {
        "input": 0.27,    # $0.27 per 1M input tokens
        "output": 0.27,   # $0.27 per 1M output tokens
    },
    "gemma-7b-it": {
        "input": 0.10,    # $0.10 per 1M input tokens
        "output": 0.10,   # $0.10 per 1M output tokens
    },
}

# Additional costs
EMBEDDING_PRICING = {
    "text-embedding-ada-002": 0.10,  # $0.10 per 1M tokens
    "text-embedding-3-small": 0.02,  # $0.02 per 1M tokens
    "text-embedding-3-large": 0.13,  # $0.13 per 1M tokens
}

# Image generation costs
IMAGE_GENERATION_PRICING = {
    "dall-e-3": {
        "1024x1024": 0.040,  # $0.04 per image
        "1024x1792": 0.080,  # $0.08 per image
        "1792x1024": 0.080,  # $0.08 per image
    },
    "dall-e-2": {
        "1024x1024": 0.020,  # $0.02 per image
        "512x512": 0.018,    # $0.018 per image
        "256x256": 0.016,    # $0.016 per image
    },
}


class CostCalculator:
    """Calculate and track LLM usage costs"""
    
    def __init__(self):
        self.usage_history: List[Dict[str, Any]] = []
        self.total_cost = Decimal("0.00")
        
    def calculate_llm_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate the cost for LLM usage
        
        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            provider: Optional provider name for logging
            
        Returns:
            Cost breakdown dictionary
        """
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
        input_cost = Decimal(str(input_tokens * pricing["input"] / 1_000_000))
        output_cost = Decimal(str(output_tokens * pricing["output"] / 1_000_000))
        total_cost = input_cost + output_cost
        
        cost_breakdown = {
            "model": model,
            "provider": provider,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "input_cost_usd": float(input_cost.quantize(Decimal("0.000001"))),
            "output_cost_usd": float(output_cost.quantize(Decimal("0.000001"))),
            "total_cost_usd": float(total_cost.quantize(Decimal("0.000001"))),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pricing_used": {
                "input_per_1m": pricing["input"],
                "output_per_1m": pricing["output"]
            }
        }
        
        # Track usage
        self.usage_history.append(cost_breakdown)
        self.total_cost += total_cost
        
        logger.info(
            "LLM cost calculated",
            model=model,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=float(total_cost)
        )
        
        return cost_breakdown
    
    def calculate_embedding_cost(
        self,
        model: str,
        tokens: int
    ) -> Dict[str, Any]:
        """Calculate cost for embedding generation"""
        
        pricing = EMBEDDING_PRICING.get(model, 0.10)  # Default to ada-002 pricing
        cost = Decimal(str(tokens * pricing / 1_000_000))
        
        cost_breakdown = {
            "model": model,
            "tokens": tokens,
            "cost_usd": float(cost.quantize(Decimal("0.000001"))),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pricing_per_1m": pricing
        }
        
        self.total_cost += cost
        
        return cost_breakdown
    
    def calculate_image_cost(
        self,
        model: str,
        size: str,
        count: int = 1
    ) -> Dict[str, Any]:
        """Calculate cost for image generation"""
        
        model_pricing = IMAGE_GENERATION_PRICING.get(model, IMAGE_GENERATION_PRICING["dall-e-3"])
        price_per_image = model_pricing.get(size, 0.04)  # Default to standard size
        total_cost = Decimal(str(price_per_image * count))
        
        cost_breakdown = {
            "model": model,
            "size": size,
            "count": count,
            "cost_per_image": price_per_image,
            "total_cost_usd": float(total_cost.quantize(Decimal("0.01"))),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        self.total_cost += total_cost
        
        return cost_breakdown
    
    def get_workflow_summary(self, workflow_id: str) -> Dict[str, Any]:
        """Get cost summary for a workflow"""
        
        workflow_usage = [u for u in self.usage_history if u.get("workflow_id") == workflow_id]
        
        total_input_tokens = sum(u.get("input_tokens", 0) for u in workflow_usage)
        total_output_tokens = sum(u.get("output_tokens", 0) for u in workflow_usage)
        total_cost = sum(Decimal(str(u.get("total_cost_usd", 0))) for u in workflow_usage)
        
        # Group by model
        model_breakdown = {}
        for usage in workflow_usage:
            model = usage.get("model", "unknown")
            if model not in model_breakdown:
                model_breakdown[model] = {
                    "count": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0
                }
            
            model_breakdown[model]["count"] += 1
            model_breakdown[model]["input_tokens"] += usage.get("input_tokens", 0)
            model_breakdown[model]["output_tokens"] += usage.get("output_tokens", 0)
            model_breakdown[model]["cost_usd"] += usage.get("total_cost_usd", 0)
        
        return {
            "workflow_id": workflow_id,
            "total_requests": len(workflow_usage),
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_tokens": total_input_tokens + total_output_tokens,
            "total_cost_usd": float(total_cost.quantize(Decimal("0.01"))),
            "model_breakdown": model_breakdown,
            "average_cost_per_request": float((total_cost / len(workflow_usage)).quantize(Decimal("0.0001"))) if workflow_usage else 0
        }
    
    def get_tenant_summary(self, tenant_id: str, period_days: int = 30) -> Dict[str, Any]:
        """Get cost summary for a tenant over a period"""
        
        cutoff_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Filter by tenant and period
        tenant_usage = []
        for usage in self.usage_history:
            usage_date = datetime.fromisoformat(usage["timestamp"].replace("Z", "+00:00"))
            if (usage.get("tenant_id") == tenant_id and 
                (cutoff_date - usage_date).days <= period_days):
                tenant_usage.append(usage)
        
        # Calculate totals
        total_cost = sum(Decimal(str(u.get("total_cost_usd", 0))) for u in tenant_usage)
        
        # Daily breakdown
        daily_costs = {}
        for usage in tenant_usage:
            date = usage["timestamp"][:10]  # YYYY-MM-DD
            if date not in daily_costs:
                daily_costs[date] = 0.0
            daily_costs[date] += usage.get("total_cost_usd", 0)
        
        return {
            "tenant_id": tenant_id,
            "period_days": period_days,
            "total_requests": len(tenant_usage),
            "total_cost_usd": float(total_cost.quantize(Decimal("0.01"))),
            "average_daily_cost": float((total_cost / period_days).quantize(Decimal("0.01"))),
            "daily_breakdown": daily_costs,
            "projected_monthly_cost": float((total_cost / period_days * 30).quantize(Decimal("0.01")))
        }
    
    def estimate_capsule_cost(self, complexity: str, tech_stack: List[str]) -> Dict[str, Any]:
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
            ("claude-3-sonnet", LLM_PRICING["claude-3-sonnet-20240229"]),
            ("llama3-70b", LLM_PRICING["llama3-70b-8192"])
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


# Global cost calculator instance
cost_calculator = CostCalculator()


def track_llm_cost(
    model: str,
    provider: str,
    prompt_tokens: int,
    completion_tokens: int,
    workflow_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Track LLM usage cost with metadata
    
    This is the main function to call from other parts of the system
    """
    cost_data = cost_calculator.calculate_llm_cost(
        model=model,
        input_tokens=prompt_tokens,
        output_tokens=completion_tokens,
        provider=provider
    )
    
    # Add metadata
    cost_data.update({
        "workflow_id": workflow_id,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "metadata": metadata or {}
    })
    
    return cost_data


def get_cost_report(
    tenant_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    period_days: int = 30
) -> Dict[str, Any]:
    """Get cost report for tenant or workflow"""
    
    if workflow_id:
        return cost_calculator.get_workflow_summary(workflow_id)
    elif tenant_id:
        return cost_calculator.get_tenant_summary(tenant_id, period_days)
    else:
        # Overall summary
        return {
            "total_requests": len(cost_calculator.usage_history),
            "total_cost_usd": float(cost_calculator.total_cost.quantize(Decimal("0.01"))),
            "usage_count": len(cost_calculator.usage_history)
        }