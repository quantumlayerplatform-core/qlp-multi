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

logger = structlog.get_logger()

# Azure deployment name mapping
# Maps OpenAI model names to Azure deployment names
AZURE_DEPLOYMENT_MAPPING = {
    "gpt-3.5-turbo": os.getenv("AZURE_GPT35_DEPLOYMENT", "gpt-35-turbo"),
    "gpt-4-turbo-preview": os.getenv("AZURE_GPT4_DEPLOYMENT", "gpt-4"),  # Your deployment name
    "gpt-4-turbo": os.getenv("AZURE_GPT4_DEPLOYMENT", "gpt-4"),  # Your deployment name
    "gpt-4": os.getenv("AZURE_GPT4_DEPLOYMENT", "gpt-4"),  # Your deployment name
    "gpt-4o": os.getenv("AZURE_GPT4O_DEPLOYMENT", "gpt-4o"),
    "gpt-4o-mini": os.getenv("AZURE_GPT4O_DEPLOYMENT", "gpt-4o-mini"),
    "text-embedding-ada-002": os.getenv("AZURE_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002"),
}


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"


class LLMClient:
    """Unified LLM client that supports multiple providers"""
    
    def __init__(self):
        self.clients = {}
        self._initialize_clients()
        self.request_semaphore = asyncio.Semaphore(20)  # Global rate limiting
        self.metrics = {
            "requests": 0,
            "errors": 0,
            "retries": 0,
            "total_latency": 0
        }
        
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
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((RateLimitError, APITimeoutError)),
        before_sleep=before_sleep_log(logger, structlog.INFO)
    )
    async def _make_request_with_retry(
        self,
        client: Any,
        provider: LLMProvider,
        model: str,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Any:
        """Make request with retry logic"""
        self.metrics["retries"] += 1
        
        if provider in [LLMProvider.OPENAI, LLMProvider.AZURE_OPENAI, LLMProvider.GROQ]:
            return await client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs
            )
        elif provider == LLMProvider.ANTHROPIC:
            return await client.messages.create(
                model=model,
                messages=messages,
                **kwargs
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        provider: Optional[LLMProvider] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
        timeout: float = 30.0,
        use_optimized: bool = True,
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
                result = await optimized_azure_client.chat_completion(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                self.metrics["total_latency"] += time.time() - start_time
                return result
            except Exception as e:
                logger.warning(f"Optimized client failed, falling back: {e}")
        
        if provider not in self.clients:
            raise ValueError(f"Provider {provider} not initialized. Check API keys.")
        
        client = self.clients[provider]
        
        async with self.request_semaphore:
            try:
            if provider in [LLMProvider.OPENAI, LLMProvider.AZURE_OPENAI, LLMProvider.GROQ]:
                # For Azure, map model names to deployment names
                if provider == LLMProvider.AZURE_OPENAI:
                    deployment_name = AZURE_DEPLOYMENT_MAPPING.get(model, model)
                    logger.debug(f"Azure OpenAI: mapping {model} to deployment {deployment_name}")
                    model = deployment_name
                
                # OpenAI-compatible API with retry
                response = await self._make_request_with_retry(
                    client=client,
                    provider=provider,
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout,
                    **kwargs
                )
                
                return {
                    "content": response.choices[0].message.content,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                        "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                        "total_tokens": response.usage.total_tokens if response.usage else 0
                    },
                    "model": response.model,
                    "provider": provider.value,
                    "finish_reason": response.choices[0].finish_reason,
                    "latency": time.time() - start_time
                }
                
            elif provider == LLMProvider.ANTHROPIC:
                # Anthropic API with retry
                response = await self._make_request_with_retry(
                    client=client,
                    provider=provider,
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                
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
                    "latency": time.time() - start_time
                }
                
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
        
        # Claude models -> Anthropic
        if "claude" in model.lower():
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
        
        return {
            "total_requests": self.metrics["requests"],
            "total_errors": self.metrics["errors"],
            "total_retries": self.metrics["retries"],
            "average_latency": avg_latency,
            "error_rate": self.metrics["errors"] / max(self.metrics["requests"], 1)
        }
    
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
    
    # Check available providers
    has_azure = llm_client.is_provider_available(LLMProvider.AZURE_OPENAI)
    has_openai = llm_client.is_provider_available(LLMProvider.OPENAI)
    has_anthropic = llm_client.is_provider_available(LLMProvider.ANTHROPIC)
    has_groq = llm_client.is_provider_available(LLMProvider.GROQ)
    
    tier_mapping = {
        "T0": [
            (has_groq, ("llama3-8b-8192", LLMProvider.GROQ)),  # Updated Groq model name
            (has_azure, ("gpt-3.5-turbo", LLMProvider.AZURE_OPENAI)),
            (has_openai, ("gpt-3.5-turbo", LLMProvider.OPENAI)),
        ],
        "T1": [
            (has_azure, ("gpt-4o-mini", LLMProvider.AZURE_OPENAI)),
            (has_openai, ("gpt-4o-mini", LLMProvider.OPENAI)),
            (has_azure, ("gpt-3.5-turbo", LLMProvider.AZURE_OPENAI)),
            (has_openai, ("gpt-3.5-turbo", LLMProvider.OPENAI)),
        ],
        "T2": [
            (has_azure, ("gpt-4-turbo-preview", LLMProvider.AZURE_OPENAI)),
            (has_openai, ("gpt-4-turbo-preview", LLMProvider.OPENAI)),
            (has_anthropic, ("claude-3-opus-20240229", LLMProvider.ANTHROPIC)),
        ],
        "T3": [
            (has_azure, ("gpt-4-turbo-preview", LLMProvider.AZURE_OPENAI)),
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
        return "gpt-3.5-turbo", LLMProvider.AZURE_OPENAI
    else:
        raise ValueError("No LLM providers available")