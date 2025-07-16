"""
Rate limiting utilities for LLM API calls
Provides token bucket algorithm and sliding window rate limiting
"""

import asyncio
import time
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from collections import deque
import structlog

logger = structlog.get_logger()


class TokenBucket:
    """Token bucket rate limiter for controlling API request rates"""
    
    def __init__(self, capacity: int, refill_rate: float, refill_period: float = 60.0):
        """
        Initialize token bucket
        
        Args:
            capacity: Maximum number of tokens
            refill_rate: Number of tokens to add per refill period
            refill_period: Time period in seconds for refilling tokens (default: 60s)
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.refill_period = refill_period
        self.tokens = capacity
        self.last_refill = time.time()
        self._lock = asyncio.Lock()
        
    async def acquire(self, tokens: int = 1) -> bool:
        """Attempt to acquire tokens, returns True if successful"""
        async with self._lock:
            await self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    async def wait_and_acquire(self, tokens: int = 1, max_wait: float = 60.0) -> bool:
        """Wait for tokens to become available, with timeout"""
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            if await self.acquire(tokens):
                return True
            
            # Calculate wait time until next refill
            time_since_refill = time.time() - self.last_refill
            time_until_refill = self.refill_period - time_since_refill
            
            # Wait for a fraction of the refill period or 1 second, whichever is smaller
            wait_time = min(1.0, time_until_refill / 10)
            await asyncio.sleep(wait_time)
        
        return False
    
    async def _refill(self):
        """Refill tokens based on elapsed time"""
        current_time = time.time()
        time_elapsed = current_time - self.last_refill
        
        if time_elapsed >= self.refill_period:
            # Full refill
            tokens_to_add = self.refill_rate * (time_elapsed / self.refill_period)
            self.tokens = min(self.capacity, self.tokens + tokens_to_add)
            self.last_refill = current_time
            
            logger.debug(f"Token bucket refilled: {self.tokens}/{self.capacity} tokens")


class SlidingWindowRateLimiter:
    """Sliding window rate limiter for precise rate control"""
    
    def __init__(self, max_requests: int, window_seconds: int):
        """
        Initialize sliding window rate limiter
        
        Args:
            max_requests: Maximum requests allowed in the window
            window_seconds: Size of the sliding window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> bool:
        """Check if request can proceed"""
        async with self._lock:
            current_time = time.time()
            
            # Remove old requests outside the window
            while self.requests and self.requests[0] < current_time - self.window_seconds:
                self.requests.popleft()
            
            # Check if we can make a new request
            if len(self.requests) < self.max_requests:
                self.requests.append(current_time)
                return True
            
            return False
    
    async def wait_and_acquire(self, max_wait: float = 60.0) -> bool:
        """Wait for rate limit to allow request"""
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            if await self.acquire():
                return True
            
            # Calculate minimum wait time
            if self.requests:
                oldest_request = self.requests[0]
                wait_time = max(0.1, (oldest_request + self.window_seconds) - time.time())
                wait_time = min(wait_time, 1.0)  # Cap at 1 second
            else:
                wait_time = 0.1
            
            await asyncio.sleep(wait_time)
        
        return False


class ProviderRateLimiter:
    """Rate limiter that manages limits for different LLM providers"""
    
    def __init__(self):
        # Import settings here to avoid circular imports
        from src.common.config import settings
        
        # Configure rate limits per provider from settings
        self.provider_limits = {
            "openai": {"rpm": settings.OPENAI_RPM, "tpm": settings.OPENAI_TPM},
            "azure_openai": {"rpm": settings.AZURE_RPM, "tpm": settings.AZURE_TPM},
            "anthropic": {"rpm": settings.ANTHROPIC_RPM, "tpm": settings.ANTHROPIC_TPM},
            "groq": {"rpm": settings.GROQ_RPM, "tpm": settings.GROQ_TPM},
            "aws_bedrock": {"rpm": settings.AWS_BEDROCK_RPM, "tpm": settings.AWS_BEDROCK_TPM}
        }
        
        # Initialize rate limiters
        self.request_limiters: Dict[str, SlidingWindowRateLimiter] = {}
        self.token_buckets: Dict[str, TokenBucket] = {}
        
        for provider, limits in self.provider_limits.items():
            # Request rate limiter (sliding window)
            self.request_limiters[provider] = SlidingWindowRateLimiter(
                max_requests=limits["rpm"],
                window_seconds=60
            )
            
            # Token bucket for token-based limiting
            self.token_buckets[provider] = TokenBucket(
                capacity=limits["tpm"],
                refill_rate=limits["tpm"],
                refill_period=60.0
            )
    
    async def acquire(self, provider: str, estimated_tokens: int = 1000) -> bool:
        """Acquire permission to make a request"""
        if provider not in self.request_limiters:
            logger.warning(f"Unknown provider {provider}, allowing request")
            return True
        
        # Check both request rate and token limits
        request_allowed = await self.request_limiters[provider].acquire()
        tokens_allowed = await self.token_buckets[provider].acquire(estimated_tokens)
        
        if not request_allowed or not tokens_allowed:
            logger.info(f"Rate limit hit for {provider}: requests={request_allowed}, tokens={tokens_allowed}")
            return False
        
        return True
    
    async def wait_and_acquire(
        self, 
        provider: str, 
        estimated_tokens: int = 1000,
        max_wait: float = 30.0
    ) -> bool:
        """Wait for rate limit to clear and acquire permission"""
        if provider not in self.request_limiters:
            logger.warning(f"Unknown provider {provider}, allowing request")
            return True
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            # Try to acquire both limits
            if await self.acquire(provider, estimated_tokens):
                return True
            
            # Wait a bit before retrying
            await asyncio.sleep(0.5)
        
        logger.warning(f"Rate limit wait timeout for {provider} after {max_wait}s")
        return False
    
    def update_limits(self, provider: str, rpm: Optional[int] = None, tpm: Optional[int] = None):
        """Update rate limits for a provider dynamically"""
        if provider not in self.provider_limits:
            logger.warning(f"Unknown provider {provider}")
            return
        
        if rpm is not None:
            self.provider_limits[provider]["rpm"] = rpm
            self.request_limiters[provider] = SlidingWindowRateLimiter(
                max_requests=rpm,
                window_seconds=60
            )
            logger.info(f"Updated {provider} RPM limit to {rpm}")
        
        if tpm is not None:
            self.provider_limits[provider]["tpm"] = tpm
            self.token_buckets[provider] = TokenBucket(
                capacity=tpm,
                refill_rate=tpm,
                refill_period=60.0
            )
            logger.info(f"Updated {provider} TPM limit to {tpm}")


# Global rate limiter instance
global_rate_limiter = ProviderRateLimiter()


class RateLimitBackoff:
    """Exponential backoff strategy for rate limit errors"""
    
    def __init__(
        self,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.attempt = 0
    
    def next_delay(self) -> float:
        """Calculate next delay with exponential backoff"""
        delay = min(
            self.initial_delay * (self.exponential_base ** self.attempt),
            self.max_delay
        )
        
        if self.jitter:
            # Add jitter to prevent thundering herd
            import random
            delay = delay * (0.5 + random.random() * 0.5)
        
        self.attempt += 1
        return delay
    
    def reset(self):
        """Reset backoff counter"""
        self.attempt = 0


async def rate_limit_handler(
    func,
    provider: str,
    estimated_tokens: int = 1000,
    max_retries: int = 3,
    backoff: Optional[RateLimitBackoff] = None
):
    """
    Handle rate limiting for async functions
    
    Args:
        func: Async function to call
        provider: LLM provider name
        estimated_tokens: Estimated tokens for the request
        max_retries: Maximum retry attempts
        backoff: Backoff strategy (creates default if None)
    """
    if backoff is None:
        backoff = RateLimitBackoff()
    
    for attempt in range(max_retries):
        try:
            # Wait for rate limit clearance
            acquired = await global_rate_limiter.wait_and_acquire(
                provider, 
                estimated_tokens,
                max_wait=30.0
            )
            
            if not acquired:
                raise Exception(f"Rate limit timeout for {provider}")
            
            # Execute function
            result = await func()
            backoff.reset()  # Reset on success
            return result
            
        except Exception as e:
            error_message = str(e).lower()
            if "rate" in error_message and "limit" in error_message:
                # Rate limit error - wait and retry
                delay = backoff.next_delay()
                logger.warning(
                    f"Rate limit hit for {provider}, attempt {attempt + 1}/{max_retries}. "
                    f"Waiting {delay:.1f}s before retry"
                )
                await asyncio.sleep(delay)
                
                # Optionally reduce provider limits if we keep hitting them
                if attempt > 1:
                    current_rpm = global_rate_limiter.provider_limits[provider]["rpm"]
                    reduced_rpm = int(current_rpm * 0.8)  # Reduce by 20%
                    global_rate_limiter.update_limits(provider, rpm=reduced_rpm)
            else:
                # Non-rate-limit error, re-raise
                raise
    
    raise Exception(f"Max retries ({max_retries}) exceeded for {provider}")