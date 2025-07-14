"""
Production-Grade AWS Bedrock Client for QLP
Provides enterprise-level reliability, monitoring, and error handling
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

import boto3
import botocore
from botocore.exceptions import ClientError, BotoCoreError
from botocore.config import Config as BotoConfig
import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)

from src.common.config import settings

logger = structlog.get_logger()


class BedrockError(Exception):
    """Base exception for Bedrock client errors"""
    pass


class BedrockRateLimitError(BedrockError):
    """Raised when rate limit is exceeded"""
    pass


class BedrockTimeoutError(BedrockError):
    """Raised when request times out"""
    pass


class BedrockModelNotFoundError(BedrockError):
    """Raised when model is not available"""
    pass


@dataclass
class BedrockMetrics:
    """Metrics for Bedrock client performance"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_latency: float = 0.0
    average_latency: float = 0.0
    throttled_requests: int = 0
    timeouts: int = 0
    last_error: Optional[str] = None
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    
    def update_success(self, latency: float):
        """Update metrics for successful request"""
        self.total_requests += 1
        self.successful_requests += 1
        self.total_latency += latency
        self.average_latency = self.total_latency / self.total_requests
        self.last_success = datetime.now(timezone.utc)
    
    def update_failure(self, error: str, error_type: str = "general"):
        """Update metrics for failed request"""
        self.total_requests += 1
        self.failed_requests += 1
        self.last_error = error
        self.last_failure = datetime.now(timezone.utc)
        
        if error_type == "throttle":
            self.throttled_requests += 1
        elif error_type == "timeout":
            self.timeouts += 1
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate"""
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests


class BedrockModelFamily(str, Enum):
    """Supported Bedrock model families"""
    CLAUDE = "anthropic"
    TITAN = "amazon"
    JURASSIC = "ai21"
    COHERE = "cohere"
    LLAMA = "meta"


@dataclass
class BedrockModel:
    """Bedrock model configuration"""
    model_id: str
    family: BedrockModelFamily
    max_tokens: int
    supports_streaming: bool = True
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0


class BedrockModelRegistry:
    """Registry of available Bedrock models with their configurations"""
    
    MODELS = {
        # Claude 3 Family
        "anthropic.claude-3-haiku-20240307-v1:0": BedrockModel(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            family=BedrockModelFamily.CLAUDE,
            max_tokens=4096,
            cost_per_1k_input=0.00025,
            cost_per_1k_output=0.00125
        ),
        "anthropic.claude-3-sonnet-20240229-v1:0": BedrockModel(
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            family=BedrockModelFamily.CLAUDE,
            max_tokens=4096,
            cost_per_1k_input=0.003,
            cost_per_1k_output=0.015
        ),
        "anthropic.claude-3-5-sonnet-20240620-v1:0": BedrockModel(
            model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
            family=BedrockModelFamily.CLAUDE,
            max_tokens=4096,
            cost_per_1k_input=0.003,
            cost_per_1k_output=0.015
        ),
        "anthropic.claude-3-opus-20240229-v1:0": BedrockModel(
            model_id="anthropic.claude-3-opus-20240229-v1:0",
            family=BedrockModelFamily.CLAUDE,
            max_tokens=4096,
            cost_per_1k_input=0.015,
            cost_per_1k_output=0.075
        ),
        "anthropic.claude-3-7-sonnet-20250219-v1:0": BedrockModel(
            model_id="anthropic.claude-3-7-sonnet-20250219-v1:0",
            family=BedrockModelFamily.CLAUDE,
            max_tokens=4096,
            cost_per_1k_input=0.003,
            cost_per_1k_output=0.015
        ),
        
        # Titan Family
        "amazon.titan-text-premier-v1:0": BedrockModel(
            model_id="amazon.titan-text-premier-v1:0",
            family=BedrockModelFamily.TITAN,
            max_tokens=3000,
            cost_per_1k_input=0.0005,
            cost_per_1k_output=0.0015
        ),
        
        # Cohere Command Family
        "cohere.command-text-v14": BedrockModel(
            model_id="cohere.command-text-v14",
            family=BedrockModelFamily.COHERE,
            max_tokens=4096,
            cost_per_1k_input=0.0015,
            cost_per_1k_output=0.002
        ),
    }
    
    @classmethod
    def get_model(cls, model_id: str) -> Optional[BedrockModel]:
        """Get model configuration by ID"""
        return cls.MODELS.get(model_id)
    
    @classmethod
    def list_models_by_family(cls, family: BedrockModelFamily) -> List[BedrockModel]:
        """List models by family"""
        return [model for model in cls.MODELS.values() if model.family == family]


class ProductionBedrockClient:
    """
    Production-grade AWS Bedrock client with enterprise features:
    - Comprehensive error handling and retries
    - Health monitoring and circuit breaker
    - Cost tracking and optimization
    - Regional failover
    - Detailed metrics and logging
    """
    
    def __init__(self, region: Optional[str] = None):
        """
        Initialize Bedrock client
        
        Args:
            region: AWS region (defaults to config setting)
        """
        self.region = region or settings.AWS_REGION
        self.metrics = BedrockMetrics()
        self._client = None
        self._semaphore = None  # Lazy init to avoid event loop issues
        self._circuit_breaker_failures = 0
        self._circuit_breaker_last_failure = None
        self._is_circuit_open = False
        
        # Initialize client
        self._initialize_client()
        
        logger.info(
            "AWS Bedrock client initialized",
            region=self.region,
            max_concurrent=settings.AWS_BEDROCK_MAX_CONCURRENT
        )
    
    @property
    def semaphore(self):
        """Lazy initialize semaphore to avoid event loop issues"""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(settings.AWS_BEDROCK_MAX_CONCURRENT)
        return self._semaphore
    
    def _initialize_client(self):
        """Initialize boto3 Bedrock client with production config"""
        try:
            # Create session with credentials
            session = boto3.Session(
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                aws_session_token=settings.AWS_SESSION_TOKEN,
                region_name=self.region
            )
            
            # Production-grade boto config
            boto_config = BotoConfig(
                region_name=self.region,
                retries={
                    'max_attempts': settings.AWS_BEDROCK_RETRY_ATTEMPTS,
                    'mode': 'adaptive'
                },
                max_pool_connections=settings.AWS_BEDROCK_MAX_CONCURRENT,
                read_timeout=settings.AWS_BEDROCK_TIMEOUT,
                connect_timeout=30,
                tcp_keepalive=True
            )
            
            # Initialize bedrock-runtime client
            self._client = session.client(
                'bedrock-runtime',
                config=boto_config,
                endpoint_url=settings.AWS_BEDROCK_ENDPOINT
            )
            
            logger.info("Bedrock client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {e}")
            raise BedrockError(f"Client initialization failed: {e}")
    
    def _check_circuit_breaker(self) -> bool:
        """Check if circuit breaker is open"""
        if not self._is_circuit_open:
            return False
        
        # Check if timeout has passed
        if (self._circuit_breaker_last_failure and 
            time.time() - self._circuit_breaker_last_failure > settings.PROVIDER_CIRCUIT_BREAKER_TIMEOUT):
            self._is_circuit_open = False
            self._circuit_breaker_failures = 0
            logger.info("Circuit breaker reset")
            return False
        
        return True
    
    def _update_circuit_breaker(self, success: bool):
        """Update circuit breaker state"""
        if success:
            self._circuit_breaker_failures = 0
            if self._is_circuit_open:
                self._is_circuit_open = False
                logger.info("Circuit breaker closed after successful request")
        else:
            self._circuit_breaker_failures += 1
            self._circuit_breaker_last_failure = time.time()
            
            if self._circuit_breaker_failures >= settings.PROVIDER_CIRCUIT_BREAKER_THRESHOLD:
                self._is_circuit_open = True
                logger.warning(
                    "Circuit breaker opened",
                    failures=self._circuit_breaker_failures,
                    threshold=settings.PROVIDER_CIRCUIT_BREAKER_THRESHOLD
                )
    
    def _format_messages_for_bedrock(self, messages: List[Dict[str, str]], model_family: BedrockModelFamily) -> Dict[str, Any]:
        """Format messages for specific model families"""
        if model_family == BedrockModelFamily.CLAUDE:
            # Claude format
            formatted_messages = []
            for msg in messages:
                if msg["role"] in ["user", "assistant"]:
                    formatted_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            return {
                "anthropic_version": "bedrock-2023-05-31",
                "messages": formatted_messages
            }
        
        elif model_family == BedrockModelFamily.TITAN:
            # Titan format
            prompt = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
            return {
                "inputText": prompt
            }
        
        elif model_family == BedrockModelFamily.COHERE:
            # Cohere format
            prompt = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
            return {
                "prompt": prompt,
                "temperature": 0.3,
                "p": 0.9,
                "k": 0
            }
        
        else:
            # Default format
            prompt = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
            return {"prompt": prompt}
    
    def _parse_bedrock_response(self, response: Dict[str, Any], model_family: BedrockModelFamily) -> Dict[str, Any]:
        """Parse response from specific model families"""
        if model_family == BedrockModelFamily.CLAUDE:
            # Claude response format
            content = response.get("content", [])
            if content and len(content) > 0:
                text = content[0].get("text", "")
            else:
                text = ""
            
            usage = response.get("usage", {})
            return {
                "content": text,
                "usage": {
                    "prompt_tokens": usage.get("input_tokens", 0),
                    "completion_tokens": usage.get("output_tokens", 0),
                    "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                },
                "finish_reason": response.get("stop_reason", "stop")
            }
        
        elif model_family == BedrockModelFamily.TITAN:
            # Titan response format
            results = response.get("results", [])
            if results and len(results) > 0:
                text = results[0].get("outputText", "")
            else:
                text = ""
            
            return {
                "content": text,
                "usage": {
                    "prompt_tokens": response.get("inputTextTokenCount", 0),
                    "completion_tokens": len(text.split()),  # Approximate
                    "total_tokens": response.get("inputTextTokenCount", 0) + len(text.split())
                },
                "finish_reason": "stop"
            }
        
        elif model_family == BedrockModelFamily.COHERE:
            # Cohere response format
            generations = response.get("generations", [])
            if generations and len(generations) > 0:
                text = generations[0].get("text", "")
            else:
                text = ""
            
            return {
                "content": text,
                "usage": {
                    "prompt_tokens": 0,  # Not provided by Cohere
                    "completion_tokens": len(text.split()),  # Approximate
                    "total_tokens": len(text.split())
                },
                "finish_reason": "stop"
            }
        
        else:
            # Default parsing
            return {
                "content": str(response),
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "finish_reason": "stop"
            }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ClientError, BotoCoreError, BedrockTimeoutError)),
        before_sleep=before_sleep_log(logger, logging.INFO),
        after=after_log(logger, logging.INFO)
    )
    async def _invoke_model_with_retry(
        self,
        model_id: str,
        body: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Invoke model with retry logic"""
        try:
            # Run in thread pool since boto3 is synchronous
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._client.invoke_model(
                    modelId=model_id,
                    body=json.dumps(body),
                    contentType='application/json',
                    accept='application/json',
                    **kwargs
                )
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            return response_body
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            if error_code == 'ThrottlingException':
                raise BedrockRateLimitError(f"Rate limit exceeded: {error_message}")
            elif error_code == 'ValidationException':
                raise BedrockModelNotFoundError(f"Model validation error: {error_message}")
            elif error_code == 'TimeoutError':
                raise BedrockTimeoutError(f"Request timeout: {error_message}")
            else:
                raise BedrockError(f"Bedrock API error ({error_code}): {error_message}")
        
        except BotoCoreError as e:
            raise BedrockError(f"Boto core error: {e}")
        
        except Exception as e:
            raise BedrockError(f"Unexpected error: {e}")
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.3,
        max_tokens: int = 2000,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a chat completion using AWS Bedrock
        
        Args:
            messages: List of message dictionaries
            model: Bedrock model ID
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional model-specific parameters
            
        Returns:
            Completion response dict with 'content' and metadata
        """
        start_time = time.time()
        
        # Check circuit breaker
        if self._check_circuit_breaker():
            raise BedrockError("Circuit breaker is open")
        
        # Get model configuration
        model_config = BedrockModelRegistry.get_model(model)
        if not model_config:
            raise BedrockModelNotFoundError(f"Model {model} not found in registry")
        
        # Limit concurrent requests
        async with self.semaphore:
            try:
                # Format request body for model family
                body = self._format_messages_for_bedrock(messages, model_config.family)
                body.update({
                    "max_tokens": min(max_tokens, model_config.max_tokens),
                    "temperature": temperature,
                    **kwargs
                })
                
                # Invoke model
                response = await self._invoke_model_with_retry(model, body)
                
                # Parse response
                parsed_response = self._parse_bedrock_response(response, model_config.family)
                
                # Calculate latency and update metrics
                latency = time.time() - start_time
                self.metrics.update_success(latency)
                self._update_circuit_breaker(True)
                
                # Calculate cost
                usage = parsed_response["usage"]
                input_cost = (usage["prompt_tokens"] / 1000) * model_config.cost_per_1k_input
                output_cost = (usage["completion_tokens"] / 1000) * model_config.cost_per_1k_output
                total_cost = input_cost + output_cost
                
                if settings.AWS_BEDROCK_ENABLE_LOGGING:
                    logger.info(
                        "Bedrock completion successful",
                        model=model,
                        region=self.region,
                        latency=f"{latency:.3f}s",
                        prompt_tokens=usage["prompt_tokens"],
                        completion_tokens=usage["completion_tokens"],
                        cost_usd=f"${total_cost:.6f}"
                    )
                
                return {
                    "content": parsed_response["content"],
                    "usage": parsed_response["usage"],
                    "model": model,
                    "provider": "aws_bedrock",
                    "region": self.region,
                    "finish_reason": parsed_response["finish_reason"],
                    "latency": latency,
                    "cost": {
                        "input_cost_usd": input_cost,
                        "output_cost_usd": output_cost,
                        "total_cost_usd": total_cost
                    }
                }
                
            except Exception as e:
                # Update metrics and circuit breaker
                latency = time.time() - start_time
                error_type = "general"
                
                if isinstance(e, BedrockRateLimitError):
                    error_type = "throttle"
                elif isinstance(e, BedrockTimeoutError):
                    error_type = "timeout"
                
                self.metrics.update_failure(str(e), error_type)
                self._update_circuit_breaker(False)
                
                logger.error(
                    "Bedrock completion failed",
                    model=model,
                    region=self.region,
                    error=str(e),
                    error_type=error_type,
                    latency=f"{latency:.3f}s"
                )
                
                raise
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        return {
            "region": self.region,
            "circuit_breaker_open": self._is_circuit_open,
            "circuit_breaker_failures": self._circuit_breaker_failures,
            "metrics": {
                "total_requests": self.metrics.total_requests,
                "success_rate": self.metrics.success_rate,
                "error_rate": self.metrics.error_rate,
                "average_latency": self.metrics.average_latency,
                "throttled_requests": self.metrics.throttled_requests,
                "timeouts": self.metrics.timeouts,
                "last_success": self.metrics.last_success.isoformat() if self.metrics.last_success else None,
                "last_failure": self.metrics.last_failure.isoformat() if self.metrics.last_failure else None,
                "last_error": self.metrics.last_error
            }
        }
    
    async def health_check(self) -> bool:
        """Perform health check by making a simple request"""
        try:
            test_messages = [{"role": "user", "content": "Hello"}]
            result = await self.chat_completion(
                messages=test_messages,
                model=settings.AWS_T0_MODEL,
                max_tokens=10
            )
            return bool(result.get("content"))
        except Exception as e:
            logger.warning(f"Bedrock health check failed: {e}")
            return False


# Global client instance
bedrock_client = ProductionBedrockClient()