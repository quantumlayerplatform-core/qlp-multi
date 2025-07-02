"""
Optimized Azure OpenAI client with retry logic, caching, and performance enhancements
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import asyncio
import hashlib
import json
from functools import lru_cache
import time

import logging
import structlog
from openai import AsyncAzureOpenAI, RateLimitError, APITimeoutError, APIError
import redis.asyncio as redis
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from src.common.config import settings

logger = structlog.get_logger()


class ResponseCache:
    """Redis-based response cache for LLM completions"""
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self.redis_client = None
        self.ttl = 3600  # 1 hour default TTL
        
    async def connect(self):
        """Initialize Redis connection"""
        if not self.redis_client:
            self.redis_client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("Redis cache connected")
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
    
    def _generate_cache_key(self, messages: List[Dict], model: str, **kwargs) -> str:
        """Generate consistent cache key from request parameters"""
        cache_data = {
            "messages": messages,
            "model": model,
            "temperature": kwargs.get("temperature", 0.3),
            "max_tokens": kwargs.get("max_tokens", 2000)
        }
        cache_str = json.dumps(cache_data, sort_keys=True)
        return f"llm_cache:{hashlib.md5(cache_str.encode()).hexdigest()}"
    
    async def get(self, messages: List[Dict], model: str, **kwargs) -> Optional[Dict]:
        """Get cached response if available"""
        if not self.redis_client:
            await self.connect()
        
        cache_key = self._generate_cache_key(messages, model, **kwargs)
        try:
            cached = await self.redis_client.get(cache_key)
            if cached:
                logger.debug("Cache hit", cache_key=cache_key[:16])
                return json.loads(cached)
        except Exception as e:
            logger.warning("Cache get failed", error=str(e))
        
        return None
    
    async def set(self, messages: List[Dict], model: str, response: Dict, **kwargs):
        """Cache response"""
        if not self.redis_client:
            await self.connect()
        
        cache_key = self._generate_cache_key(messages, model, **kwargs)
        try:
            await self.redis_client.setex(
                cache_key,
                self.ttl,
                json.dumps(response)
            )
            logger.debug("Response cached", cache_key=cache_key[:16])
        except Exception as e:
            logger.warning("Cache set failed", error=str(e))


class OptimizedAzureLLMClient:
    """Azure OpenAI client with performance optimizations"""
    
    def __init__(self):
        self.client = None
        self.cache = ResponseCache()
        self.deployment_config = self._load_deployment_config()
        self.request_semaphore = asyncio.Semaphore(10)  # Limit concurrent requests
        self.metrics = {
            "requests": 0,
            "cache_hits": 0,
            "retries": 0,
            "errors": 0,
            "total_latency": 0
        }
        
    def _load_deployment_config(self) -> Dict[str, Dict[str, Any]]:
        """Load Azure deployment configuration with scaling parameters"""
        return {
            "gpt-4": {
                "deployment_name": getattr(settings, 'AZURE_OPENAI_DEPLOYMENT_NAME', None) or "gpt-4",
                "max_concurrent": 5,
                "timeout": 60,
                "max_retries": 3,
                "rpm_limit": 60,  # Requests per minute
                "tpm_limit": 90000  # Tokens per minute
            },
            "gpt-4-turbo-preview": {
                "deployment_name": getattr(settings, 'AZURE_OPENAI_DEPLOYMENT_NAME', None) or "gpt-4",
                "max_concurrent": 8,
                "timeout": 45,
                "max_retries": 3,
                "rpm_limit": 100,
                "tpm_limit": 150000
            },
            "gpt-3.5-turbo": {
                "deployment_name": getattr(settings, 'AZURE_OPENAI_DEPLOYMENT_NAME', None) or "gpt-35-turbo",
                "max_concurrent": 20,
                "timeout": 30,
                "max_retries": 3,
                "rpm_limit": 300,
                "tpm_limit": 250000
            }
        }
    
    async def initialize(self):
        """Initialize Azure OpenAI client and cache"""
        if not self.client:
            self.client = AsyncAzureOpenAI(
                api_key=settings.AZURE_OPENAI_API_KEY,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                max_retries=0  # We handle retries ourselves
            )
            await self.cache.connect()
            logger.info("Optimized Azure OpenAI client initialized")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((RateLimitError, APITimeoutError)),
        before_sleep=before_sleep_log(logger, logging.INFO)
    )
    async def _make_request_with_retry(
        self,
        model: str,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Any:
        """Make request with exponential backoff retry"""
        self.metrics["retries"] += 1
        
        deployment_config = self.deployment_config.get(model, {})
        deployment_name = deployment_config.get("deployment_name", model)
        timeout = kwargs.pop("timeout", deployment_config.get("timeout", 30))
        
        try:
            response = await self.client.chat.completions.create(
                model=deployment_name,
                messages=messages,
                timeout=timeout,
                **kwargs
            )
            return response
        except RateLimitError as e:
            logger.warning(f"Rate limit hit for {model}, retrying...", error=str(e))
            # Add jitter to avoid thundering herd
            await asyncio.sleep(0.5 + (hash(str(messages)) % 1000) / 1000)
            raise
        except APITimeoutError as e:
            logger.warning(f"Timeout for {model}, retrying...", error=str(e))
            raise
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4-turbo-preview",
        temperature: float = 0.3,
        max_tokens: int = 2000,
        use_cache: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create chat completion with caching and retry logic
        
        Args:
            messages: Chat messages
            model: Model name
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            use_cache: Whether to use response cache
            **kwargs: Additional parameters
            
        Returns:
            Response dict with content and metadata
        """
        if not self.client:
            await self.initialize()
        
        start_time = time.time()
        self.metrics["requests"] += 1
        
        # Check cache first
        if use_cache and temperature <= 0.3:  # Only cache deterministic responses
            cached_response = await self.cache.get(messages, model, 
                                                   temperature=temperature, 
                                                   max_tokens=max_tokens)
            if cached_response:
                self.metrics["cache_hits"] += 1
                cached_response["cached"] = True
                return cached_response
        
        # Apply rate limiting using semaphore
        deployment_config = self.deployment_config.get(model, {})
        max_concurrent = deployment_config.get("max_concurrent", 10)
        
        async with self.request_semaphore:
            try:
                response = await self._make_request_with_retry(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                
                result = {
                    "content": response.choices[0].message.content,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                        "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                        "total_tokens": response.usage.total_tokens if response.usage else 0
                    },
                    "model": response.model,
                    "provider": "azure_openai",
                    "finish_reason": response.choices[0].finish_reason,
                    "cached": False,
                    "latency": time.time() - start_time
                }
                
                # Cache successful responses
                if use_cache and temperature <= 0.3:
                    await self.cache.set(messages, model, result,
                                       temperature=temperature,
                                       max_tokens=max_tokens)
                
                # Update metrics
                self.metrics["total_latency"] += result["latency"]
                
                return result
                
            except Exception as e:
                self.metrics["errors"] += 1
                logger.error(f"Azure OpenAI request failed", 
                           model=model, 
                           error=str(e))
                raise
    
    async def batch_completion(
        self,
        requests: List[Dict[str, Any]],
        max_concurrent: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Process multiple completions in parallel with rate limiting
        
        Args:
            requests: List of request dicts with messages, model, etc.
            max_concurrent: Max concurrent requests
            
        Returns:
            List of responses in same order as requests
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_single(request: Dict[str, Any], index: int) -> Tuple[int, Dict]:
            async with semaphore:
                try:
                    response = await self.chat_completion(**request)
                    return index, response
                except Exception as e:
                    logger.error(f"Batch request {index} failed", error=str(e))
                    return index, {"error": str(e)}
        
        # Process all requests concurrently
        tasks = [
            process_single(request, i) 
            for i, request in enumerate(requests)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Sort results by original index
        sorted_results = sorted(results, key=lambda x: x[0])
        return [result[1] for result in sorted_results]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        avg_latency = (
            self.metrics["total_latency"] / self.metrics["requests"]
            if self.metrics["requests"] > 0 else 0
        )
        
        cache_hit_rate = (
            self.metrics["cache_hits"] / self.metrics["requests"]
            if self.metrics["requests"] > 0 else 0
        )
        
        return {
            "total_requests": self.metrics["requests"],
            "cache_hits": self.metrics["cache_hits"],
            "cache_hit_rate": cache_hit_rate,
            "total_retries": self.metrics["retries"],
            "total_errors": self.metrics["errors"],
            "average_latency": avg_latency,
            "error_rate": self.metrics["errors"] / max(self.metrics["requests"], 1)
        }
    
    async def close(self):
        """Cleanup resources"""
        await self.cache.disconnect()
        if self.client:
            await self.client.close()


# Global optimized client instance
optimized_azure_client = OptimizedAzureLLMClient()


# Utility functions for easy migration
async def create_optimized_completion(
    messages: List[Dict[str, str]],
    model: str = "gpt-4-turbo-preview",
    **kwargs
) -> str:
    """
    Create completion and return just the content
    Backward compatible wrapper
    """
    response = await optimized_azure_client.chat_completion(
        messages=messages,
        model=model,
        **kwargs
    )
    return response["content"]