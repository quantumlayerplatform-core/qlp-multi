"""
Azure OpenAI client wrapper for QLP
Provides a unified interface for both OpenAI and Azure OpenAI
"""

from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import asyncio
import os
from enum import Enum
import time
from functools import lru_cache

import logging
import structlog
from openai import AsyncOpenAI, AsyncAzureOpenAI, RateLimitError, APITimeoutError
from anthropic import AsyncAnthropic
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from src.common.config import settings
from src.agents.azure_llm_optimized import optimized_azure_client
from src.common.cost_calculator_persistent import track_llm_cost
from src.agents.rate_limiter import global_rate_limiter, rate_limit_handler, RateLimitBackoff

logger = structlog.get_logger()

# Debug log to confirm cost tracking is imported
logger.info("Azure LLM Client: Cost tracking imported successfully")

# Azure deployment name mapping
# Maps OpenAI model names to Azure deployment names
AZURE_DEPLOYMENT_MAPPING = {
    # T0 - Simple tasks (gpt-35-turbo)
    "gpt-3.5-turbo": os.getenv("AZURE_GPT35_DEPLOYMENT", "gpt-35-turbo"),
    "gpt-35-turbo": "gpt-35-turbo",
    
    # T1 - Medium tasks (gpt-4.1-mini or gpt-4.1-nano)
    "gpt-4o-mini": os.getenv("AZURE_GPT4_MINI_DEPLOYMENT", "gpt-4.1-mini"),
    "gpt-4.1-mini": "gpt-4.1-mini",
    "gpt-4.1-nano": "gpt-4.1-nano",
    
    # T2 - Complex tasks (gpt-4 or o4-mini)
    "gpt-4-turbo-preview": os.getenv("AZURE_GPT4_DEPLOYMENT", "gpt-4"),
    "gpt-4-turbo": os.getenv("AZURE_GPT4_DEPLOYMENT", "gpt-4"),
    "gpt-4": "gpt-4",
    "o4-mini": "o4-mini",
    
    # T3 - Meta tasks (gpt-4.1)
    "gpt-4.1": "gpt-4.1",
    
    # Embeddings
    "text-embedding-ada-002": os.getenv("AZURE_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002"),
}


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    AWS_BEDROCK = "aws_bedrock"


class LLMClient:
    """Unified LLM client that supports multiple providers"""
    
    def __init__(self):
        self.clients = {}
        self._initialize_clients()
        self._request_semaphore = None  # Lazy initialize to avoid event loop issues
        self.metrics = {
            "requests": 0,
            "errors": 0,
            "retries": 0,
            "total_latency": 0
        }
    
    @property
    def request_semaphore(self):
        """Lazy initialize semaphore to avoid event loop issues"""
        if self._request_semaphore is None:
            self._request_semaphore = asyncio.Semaphore(20)
        return self._request_semaphore
        
    def _initialize_clients(self):
        """Initialize available LLM clients based on configuration"""
        
        # OpenAI client
        if settings.OPENAI_API_KEY:
            self.clients[LLMProvider.OPENAI] = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY
            )
            logger.info("OpenAI client initialized")
        
        # Azure OpenAI client
        if settings.AZURE_OPENAI_API_KEY and settings.AZURE_OPENAI_ENDPOINT:
            self.clients[LLMProvider.AZURE_OPENAI] = AsyncAzureOpenAI(
                api_key=settings.AZURE_OPENAI_API_KEY,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_version=settings.AZURE_OPENAI_API_VERSION
            )
            logger.info("Azure OpenAI client initialized", 
                       endpoint=settings.AZURE_OPENAI_ENDPOINT)
        
        # Anthropic client
        if settings.ANTHROPIC_API_KEY:
            self.clients[LLMProvider.ANTHROPIC] = AsyncAnthropic(
                api_key=settings.ANTHROPIC_API_KEY
            )
            logger.info("Anthropic client initialized")
        
        # Groq client (if available)
        if settings.GROQ_API_KEY:
            try:
                from groq import AsyncGroq
                self.clients[LLMProvider.GROQ] = AsyncGroq(
                    api_key=settings.GROQ_API_KEY
                )
                logger.info("Groq client initialized")
            except ImportError:
                logger.warning("Groq library not installed")
        
        # AWS Bedrock client
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            try:
                from src.agents.aws_bedrock_client import bedrock_client
                self.clients[LLMProvider.AWS_BEDROCK] = bedrock_client
                logger.info("AWS Bedrock client initialized", region=settings.AWS_REGION)
            except Exception as e:
                logger.warning(f"Failed to initialize AWS Bedrock client: {e}")
    
    async def _make_request_with_retry(
        self,
        client: Any,
        provider: LLMProvider,
        model: str,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Any:
        """Make request with intelligent retry logic"""
        backoff = RateLimitBackoff(initial_delay=2.0, max_delay=60.0)
        max_retries = 5  # Increased from 3
        
        for attempt in range(max_retries):
            try:
                if provider in [LLMProvider.OPENAI, LLMProvider.AZURE_OPENAI, LLMProvider.GROQ]:
                    response = await client.chat.completions.create(
                        model=model,
                        messages=messages,
                        **kwargs
                    )
                elif provider == LLMProvider.ANTHROPIC:
                    response = await client.messages.create(
                        model=model,
                        messages=messages,
                        **kwargs
                    )
                else:
                    raise ValueError(f"Unknown provider: {provider}")
                
                # Success - reset metrics
                return response
                
            except (RateLimitError, APITimeoutError) as e:
                self.metrics["retries"] += 1
                
                if attempt >= max_retries - 1:
                    # Last attempt failed
                    logger.error(
                        f"Max retries exceeded for {provider.value}",
                        model=model,
                        attempt=attempt + 1,
                        error=str(e)
                    )
                    raise
                
                # Calculate backoff delay
                delay = backoff.next_delay()
                
                # Extract retry-after header if available
                if hasattr(e, 'response') and e.response:
                    retry_after = e.response.headers.get('retry-after')
                    if retry_after:
                        try:
                            delay = max(delay, float(retry_after))
                        except:
                            pass
                
                logger.warning(
                    f"Rate limit hit for {provider.value}, retrying in {delay:.1f}s",
                    model=model,
                    attempt=attempt + 1,
                    max_retries=max_retries
                )
                
                await asyncio.sleep(delay)
                
                # Optionally reduce rate limits if we keep hitting them
                if attempt >= 2:
                    current_rpm = global_rate_limiter.provider_limits.get(provider.value, {}).get("rpm", 60)
                    reduced_rpm = int(current_rpm * 0.8)
                    global_rate_limiter.update_limits(provider.value, rpm=reduced_rpm)
                    logger.info(f"Reduced {provider.value} rate limit to {reduced_rpm} RPM")
                
            except Exception as e:
                # Non-retryable error
                logger.error(
                    f"Non-retryable error for {provider.value}",
                    model=model,
                    error=str(e)
                )
                raise
        
        # Should not reach here
        raise Exception(f"Unexpected retry loop exit for {provider.value}")
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        provider: Optional[LLMProvider] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
        timeout: float = 600.0,  # 10 minutes for enterprise-scale tasks
        use_optimized: bool = True,
        workflow_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a chat completion using the specified provider
        
        Args:
            messages: List of message dictionaries
            model: Model name (provider-specific)
            provider: LLM provider to use (auto-detected if None)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Completion response dict with 'content' and metadata
        """
        
        start_time = time.time()
        self.metrics["requests"] += 1
        
        # Auto-detect provider if not specified
        if provider is None:
            provider = self._detect_provider(model)
        
        # Use optimized Azure client if available and requested
        if (use_optimized and 
            provider == LLMProvider.AZURE_OPENAI and 
            hasattr(optimized_azure_client, 'chat_completion')):
            try:
                # Don't pass cost tracking params to optimized client
                optimized_kwargs = {k: v for k, v in kwargs.items() 
                                  if k not in ['workflow_id', 'tenant_id', 'user_id', 'task_id', 'metadata']}
                result = await optimized_azure_client.chat_completion(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **optimized_kwargs
                )
                self.metrics["total_latency"] += time.time() - start_time
                
                # Track cost for optimized client too
                if "usage" in result and result["usage"]:
                    usage = result["usage"]
                    logger.info(
                        "Creating cost tracking task (optimized path)",
                        model=result.get("model", model),
                        provider=provider.value,
                        workflow_id=workflow_id,
                        prompt_tokens=usage.get("prompt_tokens", 0),
                        completion_tokens=usage.get("completion_tokens", 0)
                    )
                    cost_task = asyncio.create_task(
                        track_llm_cost(
                            model=result.get("model", model),
                            provider=provider.value,
                            prompt_tokens=usage.get("prompt_tokens", 0),
                            completion_tokens=usage.get("completion_tokens", 0),
                            workflow_id=workflow_id,
                            tenant_id=tenant_id,
                            user_id=user_id,
                            task_id=task_id,
                            metadata=metadata or {},
                            latency_ms=int((time.time() - start_time) * 1000)
                        ),
                        name=f"track_cost_{workflow_id}_{task_id}"
                    )
                    def handle_cost_error(task):
                        try:
                            task.result()
                        except Exception as e:
                            logger.error(f"Cost tracking failed: {e}")
                    cost_task.add_done_callback(handle_cost_error)
                
                return result
            except Exception as e:
                logger.warning(f"Optimized client failed, falling back: {e}")
        
        if provider not in self.clients:
            raise ValueError(f"Provider {provider} not initialized. Check API keys.")
        
        client = self.clients[provider]
        
        # Estimate tokens for rate limiting (rough approximation)
        estimated_tokens = sum(len(m.get("content", "").split()) * 1.3 for m in messages) + max_tokens
        
        # Wait for rate limit clearance
        acquired = await global_rate_limiter.wait_and_acquire(
            provider.value,
            int(estimated_tokens),
            max_wait=30.0
        )
        
        if not acquired:
            raise RateLimitError(f"Rate limit timeout for {provider.value}")
        
        async with self.request_semaphore:
            try:
                if provider in [LLMProvider.OPENAI, LLMProvider.AZURE_OPENAI, LLMProvider.GROQ]:
                    # For Azure, map model names to deployment names
                    if provider == LLMProvider.AZURE_OPENAI:
                        deployment_name = AZURE_DEPLOYMENT_MAPPING.get(model, model)
                        logger.debug(f"Azure OpenAI: mapping {model} to deployment {deployment_name}")
                        model = deployment_name
                
                    # OpenAI-compatible API with retry
                    # Filter out cost tracking params that OpenAI doesn't accept
                    openai_kwargs = {k: v for k, v in kwargs.items() 
                                   if k not in ['workflow_id', 'tenant_id', 'user_id', 'task_id', 'metadata']}
                    
                    response = await self._make_request_with_retry(
                        client=client,
                        provider=provider,
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        timeout=timeout,
                        **openai_kwargs
                    )
                    
                    # Track cost asynchronously
                    usage = response.usage if response.usage else None
                    cost_data = {}
                    if usage:
                        logger.info(
                            "Creating cost tracking task",
                            model=response.model,
                            provider=provider.value,
                            workflow_id=workflow_id,
                            prompt_tokens=usage.prompt_tokens,
                            completion_tokens=usage.completion_tokens
                        )
                        # Create the task with a name for debugging
                        cost_task = asyncio.create_task(
                            track_llm_cost(
                                model=response.model,
                                provider=provider.value,
                                prompt_tokens=usage.prompt_tokens,
                                completion_tokens=usage.completion_tokens,
                                workflow_id=workflow_id,
                                tenant_id=tenant_id,
                                user_id=user_id,
                                task_id=task_id,
                                metadata=metadata or {},
                                latency_ms=int((time.time() - start_time) * 1000)
                            ),
                            name=f"track_cost_{workflow_id}_{task_id}"
                        )
                        # Add error handler to prevent unhandled exceptions
                        def handle_cost_error(task):
                            try:
                                task.result()
                            except Exception as e:
                                logger.error(f"Cost tracking failed: {e}")
                        cost_task.add_done_callback(handle_cost_error)
                        
                        # For immediate response, calculate cost synchronously
                        cost_data = {
                            "input_cost_usd": usage.prompt_tokens * 0.00001,  # Approximate
                            "output_cost_usd": usage.completion_tokens * 0.00003,
                            "total_cost_usd": (usage.prompt_tokens * 0.00001) + (usage.completion_tokens * 0.00003),
                            "async_tracking": True
                        }
                    
                    return {
                        "content": response.choices[0].message.content,
                        "usage": {
                            "prompt_tokens": usage.prompt_tokens if usage else 0,
                            "completion_tokens": usage.completion_tokens if usage else 0,
                            "total_tokens": usage.total_tokens if usage else 0
                        },
                        "model": response.model,
                        "provider": provider.value,
                        "finish_reason": response.choices[0].finish_reason,
                        "latency": time.time() - start_time,
                        "cost": cost_data
                    }
                    
                elif provider == LLMProvider.ANTHROPIC:
                    # Anthropic API with retry
                    # Filter out cost tracking params that Anthropic doesn't accept
                    anthropic_kwargs = {k: v for k, v in kwargs.items() 
                                      if k not in ['workflow_id', 'tenant_id', 'user_id', 'task_id', 'metadata']}
                    
                    response = await self._make_request_with_retry(
                        client=client,
                        provider=provider,
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        **anthropic_kwargs
                    )
                    
                    # Track cost asynchronously
                    cost_task = asyncio.create_task(
                        track_llm_cost(
                            model=response.model,
                            provider=provider.value,
                            prompt_tokens=response.usage.input_tokens,
                            completion_tokens=response.usage.output_tokens,
                            workflow_id=workflow_id,
                            tenant_id=tenant_id,
                            user_id=user_id,
                            task_id=task_id,
                            metadata=metadata or {},
                            latency_ms=int((time.time() - start_time) * 1000)
                        ),
                        name=f"track_cost_{workflow_id}_{task_id}"
                    )
                    # Add error handler
                    def handle_cost_error(task):
                        try:
                            task.result()
                        except Exception as e:
                            logger.error(f"Cost tracking failed: {e}")
                    cost_task.add_done_callback(handle_cost_error)
                    
                    # For immediate response, calculate cost synchronously
                    cost_data = {
                        "input_cost_usd": response.usage.input_tokens * 0.00003,  # Approximate for Claude
                        "output_cost_usd": response.usage.output_tokens * 0.00015,
                        "total_cost_usd": (response.usage.input_tokens * 0.00003) + (response.usage.output_tokens * 0.00015),
                        "async_tracking": True
                    }
                    
                    return {
                        "content": response.content[0].text,
                        "usage": {
                            "prompt_tokens": response.usage.input_tokens,
                            "completion_tokens": response.usage.output_tokens,
                            "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                        },
                        "model": response.model,
                        "provider": provider.value,
                        "finish_reason": response.stop_reason,
                        "latency": time.time() - start_time,
                        "cost": cost_data
                    }
                
                elif provider == LLMProvider.AWS_BEDROCK:
                    # AWS Bedrock API - use our production client
                    # Filter out cost tracking params for Bedrock client
                    bedrock_kwargs = {k: v for k, v in kwargs.items() 
                                    if k not in ['workflow_id', 'tenant_id', 'user_id', 'task_id', 'metadata']}
                    
                    response = await client.chat_completion(
                        messages=messages,
                        model=model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        **bedrock_kwargs
                    )
                    
                    # Track cost asynchronously (cost already calculated in bedrock client)
                    if response.get("cost"):
                        cost_task = asyncio.create_task(
                            track_llm_cost(
                                model=response["model"],
                                provider=provider.value,
                                prompt_tokens=response["usage"]["prompt_tokens"],
                                completion_tokens=response["usage"]["completion_tokens"],
                                workflow_id=workflow_id,
                                tenant_id=tenant_id,
                                user_id=user_id,
                                task_id=task_id,
                                metadata=metadata or {},
                                latency_ms=int(response["latency"] * 1000)
                            ),
                            name=f"track_cost_{workflow_id}_{task_id}"
                        )
                        # Add error handler
                        def handle_cost_error(task):
                            try:
                                task.result()
                            except Exception as e:
                                logger.error(f"Cost tracking failed: {e}")
                        cost_task.add_done_callback(handle_cost_error)
                    
                    # Return the response (already properly formatted by bedrock client)
                    return response
                
            except Exception as e:
                self.metrics["errors"] += 1
                logger.error(f"LLM completion failed", 
                            provider=provider.value, 
                            model=model, 
                            error=str(e))
                raise
            finally:
                self.metrics["total_latency"] += time.time() - start_time
    
    def _detect_provider(self, model: str) -> LLMProvider:
        """Auto-detect provider based on model name"""
        
        # Bedrock models (identified by "anthropic.", "amazon.", etc.)
        if any(prefix in model.lower() for prefix in ["anthropic.", "amazon.", "ai21.", "cohere.", "meta."]):
            if LLMProvider.AWS_BEDROCK in self.clients:
                return LLMProvider.AWS_BEDROCK
        
        # Claude models -> Prefer Bedrock if available, otherwise Anthropic
        if "claude" in model.lower():
            if LLMProvider.AWS_BEDROCK in self.clients:
                return LLMProvider.AWS_BEDROCK
            return LLMProvider.ANTHROPIC
        
        # Mixtral/Llama models -> Groq (if available)
        if any(m in model.lower() for m in ["mixtral", "llama", "groq"]):
            if LLMProvider.GROQ in self.clients:
                return LLMProvider.GROQ
        
        # GPT models -> Prefer Azure if available, otherwise OpenAI
        if "gpt" in model.lower():
            if LLMProvider.AZURE_OPENAI in self.clients:
                return LLMProvider.AZURE_OPENAI
            return LLMProvider.OPENAI
        
        # Default to OpenAI
        return LLMProvider.OPENAI
    
    def get_available_providers(self) -> List[str]:
        """Get list of available providers"""
        return [provider.value for provider in self.clients.keys()]
    
    def is_provider_available(self, provider: LLMProvider) -> bool:
        """Check if a provider is available"""
        return provider in self.clients
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        avg_latency = (
            self.metrics["total_latency"] / self.metrics["requests"]
            if self.metrics["requests"] > 0 else 0
        )
        
        # Import cost calculator to get cost metrics
        from src.common.cost_calculator import cost_calculator
        
        return {
            "total_requests": self.metrics["requests"],
            "total_errors": self.metrics["errors"],
            "total_retries": self.metrics["retries"],
            "average_latency": avg_latency,
            "error_rate": self.metrics["errors"] / max(self.metrics["requests"], 1),
            "total_cost_usd": float(cost_calculator.total_cost),
            "cost_breakdown": {
                "total_usage_count": len(cost_calculator.usage_history),
                "by_provider": self._get_cost_by_provider()
            }
        }
    
    def _get_cost_by_provider(self) -> Dict[str, float]:
        """Get cost breakdown by provider"""
        from src.common.cost_calculator import cost_calculator
        
        provider_costs = {}
        for usage in cost_calculator.usage_history:
            provider = usage.get("provider", "unknown")
            if provider not in provider_costs:
                provider_costs[provider] = 0.0
            provider_costs[provider] += usage.get("total_cost_usd", 0)
        
        return provider_costs
    
    @property
    def azure_endpoint(self) -> Optional[str]:
        """Get Azure endpoint if configured"""
        return settings.AZURE_OPENAI_ENDPOINT


# Global instance
llm_client = LLMClient()


# Convenience functions for backward compatibility
async def create_chat_completion(
    messages: List[Dict[str, str]],
    model: str = "gpt-4-turbo-preview",
    **kwargs
) -> str:
    """
    Create a chat completion and return just the content
    Backward compatible wrapper
    """
    response = await llm_client.chat_completion(
        messages=messages,
        model=model,
        **kwargs
    )
    return response["content"]


def get_model_for_tier(tier: str) -> tuple[str, LLMProvider]:
    """
    Get recommended model and provider for a given tier
    Returns (model_name, provider)
    """
    
    # Check if we should use Azure models from config
    provider_config = {
        "T0": settings.LLM_T0_PROVIDER,
        "T1": settings.LLM_T1_PROVIDER,
        "T2": settings.LLM_T2_PROVIDER,
        "T3": settings.LLM_T3_PROVIDER
    }
    
    azure_model_config = {
        "T0": settings.AZURE_T0_MODEL,
        "T1": settings.AZURE_T1_MODEL,
        "T2": settings.AZURE_T2_MODEL,
        "T3": settings.AZURE_T3_MODEL
    }
    
    # Get provider preference for this tier
    preferred_provider = provider_config.get(tier, "azure")
    
    # If Azure is preferred and available, use configured Azure model
    if preferred_provider == "azure" and llm_client.is_provider_available(LLMProvider.AZURE_OPENAI):
        azure_model = azure_model_config.get(tier, "gpt-35-turbo")
        return azure_model, LLMProvider.AZURE_OPENAI
    
    # Check AWS Bedrock preference
    aws_model_config = {
        "T0": settings.AWS_T0_MODEL,
        "T1": settings.AWS_T1_MODEL,
        "T2": settings.AWS_T2_MODEL,
        "T3": settings.AWS_T3_MODEL
    }
    
    # If AWS Bedrock is preferred and available, use configured Bedrock model
    if preferred_provider == "aws_bedrock" and llm_client.is_provider_available(LLMProvider.AWS_BEDROCK):
        aws_model = aws_model_config.get(tier, settings.AWS_T0_MODEL)
        return aws_model, LLMProvider.AWS_BEDROCK
    
    # Otherwise, check available providers
    has_azure = llm_client.is_provider_available(LLMProvider.AZURE_OPENAI)
    has_openai = llm_client.is_provider_available(LLMProvider.OPENAI)
    has_anthropic = llm_client.is_provider_available(LLMProvider.ANTHROPIC)
    has_groq = llm_client.is_provider_available(LLMProvider.GROQ)
    has_aws_bedrock = llm_client.is_provider_available(LLMProvider.AWS_BEDROCK)
    
    # Intelligent tier mapping with AWS Bedrock prioritized for code generation
    tier_mapping = {
        "T0": [
            (has_azure, (settings.AZURE_T0_MODEL, LLMProvider.AZURE_OPENAI)),
            (has_aws_bedrock, (settings.AWS_T0_MODEL, LLMProvider.AWS_BEDROCK)),  # Claude Haiku - fast & cheap
            (has_groq, ("llama3-8b-8192", LLMProvider.GROQ)),
            (has_openai, ("gpt-3.5-turbo", LLMProvider.OPENAI)),
        ],
        "T1": [
            (has_azure, (settings.AZURE_T1_MODEL, LLMProvider.AZURE_OPENAI)),
            (has_aws_bedrock, (settings.AWS_T1_MODEL, LLMProvider.AWS_BEDROCK)),  # Claude Sonnet - balanced
            (has_openai, ("gpt-4o-mini", LLMProvider.OPENAI)),
            (has_anthropic, ("claude-3-sonnet-20240229", LLMProvider.ANTHROPIC)),
        ],
        "T2": [
            (has_aws_bedrock, (settings.AWS_T2_MODEL, LLMProvider.AWS_BEDROCK)),  # Claude 3.5 Sonnet - best for code
            (has_azure, (settings.AZURE_T2_MODEL, LLMProvider.AZURE_OPENAI)),
            (has_openai, ("gpt-4-turbo-preview", LLMProvider.OPENAI)),
            (has_anthropic, ("claude-3-5-sonnet-20240620", LLMProvider.ANTHROPIC)),
        ],
        "T3": [
            (has_aws_bedrock, (settings.AWS_T3_MODEL, LLMProvider.AWS_BEDROCK)),  # Claude Opus - most capable
            (has_azure, (settings.AZURE_T3_MODEL, LLMProvider.AZURE_OPENAI)),
            (has_openai, ("gpt-4-turbo-preview", LLMProvider.OPENAI)),
            (has_anthropic, ("claude-3-opus-20240229", LLMProvider.ANTHROPIC)),
        ]
    }
    
    # Find first available option for tier
    for available, (model, provider) in tier_mapping.get(tier, []):
        if available:
            return model, provider
    
    # Fallback
    if has_openai:
        return "gpt-3.5-turbo", LLMProvider.OPENAI
    elif has_azure:
        return "gpt-35-turbo", LLMProvider.AZURE_OPENAI
    else:
        raise ValueError("No LLM providers available")