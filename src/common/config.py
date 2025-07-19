"""
Configuration management for QLP
Uses pydantic-settings for environment variable management
"""

from typing import Optional, List, Dict, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"  # Allow extra fields from .env
    )
    
    # Application
    APP_NAME: str = "Quantum Layer Platform"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development", description="Environment (development, staging, production)")
    DEBUG: bool = Field(default=False)
    LOG_LEVEL: str = Field(default="INFO")
    
    # API Keys
    OPENAI_API_KEY: str = Field(default=None, description="OpenAI API key")
    ANTHROPIC_API_KEY: str = Field(default=None, description="Anthropic API key")
    GROQ_API_KEY: Optional[str] = Field(default=None, description="Groq API key")
    
    @field_validator('OPENAI_API_KEY', 'ANTHROPIC_API_KEY')
    @classmethod
    def validate_api_keys(cls, v: str, info) -> str:
        if not v or v == "your-openai-api-key" or v == "your-anthropic-api-key":
            print(f"⚠️  Warning: {info.field_name} is not set. Please set it in your .env file for full functionality")
            return v or ""  # Return empty string instead of failing
        return v
    
    # Azure OpenAI
    AZURE_OPENAI_ENDPOINT: Optional[str] = Field(default=None, description="Azure OpenAI endpoint URL")
    AZURE_OPENAI_API_KEY: Optional[str] = Field(default=None, description="Azure OpenAI API key")
    AZURE_OPENAI_API_VERSION: str = Field(default="2024-02-15-preview", description="Azure OpenAI API version")
    AZURE_OPENAI_DEPLOYMENT_NAME: Optional[str] = Field(default=None, description="Azure OpenAI deployment name")
    
    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://qlp:qlp@localhost:15432/qlp",
        description="PostgreSQL connection URL"
    )
    POSTGRES_HOST: str = Field(default="localhost")
    POSTGRES_PORT: int = Field(default=15432)
    POSTGRES_DB: str = Field(default="qlp_test")
    POSTGRES_USER: str = Field(default="test_user")
    POSTGRES_PASSWORD: str = Field(default="test_password")
    
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    REDIS_HOST: str = Field(default="redis", description="Redis host")
    REDIS_PORT: int = Field(default=6379, description="Redis port")
    
    # Temporal
    TEMPORAL_SERVER: str = Field(
        default="localhost:7233",
        description="Temporal server address"
    )
    TEMPORAL_NAMESPACE: str = Field(default="default")
    TEMPORAL_TASK_QUEUE: str = Field(default="qlp-main")
    TEMPORAL_HOST: str = Field(default="localhost:7233")
    HUMAN_REVIEW_THRESHOLD: float = Field(default=0.8)
    
    # Vector Database
    QDRANT_URL: str = Field(
        default="http://localhost:6333",
        description="Qdrant vector database URL"
    )
    QDRANT_API_KEY: Optional[str] = None
    WEAVIATE_URL: str = Field(
        default="http://localhost:8080",
        description="Weaviate vector database URL"
    )
    
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = Field(
        default="localhost:9092",
        description="Kafka bootstrap servers"
    )
    KAFKA_SECURITY_PROTOCOL: str = Field(default="PLAINTEXT")
    
    # Service URLs (for inter-service communication)
    ORCHESTRATOR_URL: str = Field(default="http://localhost:8000")
    AGENT_FACTORY_URL: str = Field(default="http://localhost:8001")
    VALIDATION_MESH_URL: str = Field(default="http://localhost:8002")
    VECTOR_MEMORY_URL: str = Field(default="http://localhost:8003")
    SANDBOX_SERVICE_URL: str = Field(default="http://localhost:8004")
    
    # Service Ports
    ORCHESTRATOR_PORT: int = Field(default=8000)
    AGENT_FACTORY_PORT: int = Field(default=8001)
    VALIDATION_MESH_PORT: int = Field(default=8002)
    VECTOR_MEMORY_PORT: int = Field(default=8003)
    SANDBOX_PORT: int = Field(default=8004)
    
    # Security
    SECRET_KEY: str = Field(
        default="your-secret-key-here-change-in-production",
        description="Secret key for JWT tokens"
    )
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True)
    RATE_LIMIT_PER_MINUTE: int = Field(default=60)
    
    # Provider-specific rate limits (requests per minute)
    OPENAI_RPM: int = Field(default=60, description="OpenAI requests per minute")
    OPENAI_TPM: int = Field(default=90000, description="OpenAI tokens per minute")
    AZURE_RPM: int = Field(default=240, description="Azure OpenAI requests per minute")
    AZURE_TPM: int = Field(default=240000, description="Azure OpenAI tokens per minute")
    ANTHROPIC_RPM: int = Field(default=50, description="Anthropic requests per minute")
    ANTHROPIC_TPM: int = Field(default=100000, description="Anthropic tokens per minute")
    GROQ_RPM: int = Field(default=30, description="Groq requests per minute")
    GROQ_TPM: int = Field(default=6000, description="Groq tokens per minute")
    AWS_BEDROCK_RPM: int = Field(default=200, description="AWS Bedrock requests per minute")
    AWS_BEDROCK_TPM: int = Field(default=400000, description="AWS Bedrock tokens per minute")
    
    # Storage
    STORAGE_BACKEND: str = Field(
        default="local",
        description="Storage backend (local, s3, gcs, azure)"
    )
    STORAGE_PATH: str = Field(default="/tmp/qlp-storage")
    S3_BUCKET: Optional[str] = None
    S3_REGION: str = Field(default="us-east-1")
    
    # Kubernetes
    K8S_IN_CLUSTER: bool = Field(
        default=False,
        description="Whether running inside Kubernetes cluster"
    )
    K8S_NAMESPACE: str = Field(default="qlp-system")
    
    # Docker
    DOCKER_REGISTRY: str = Field(default="localhost:5000")
    DOCKER_IMAGE_PREFIX: str = Field(default="qlp")
    
    # Sandbox Execution
    SANDBOX_TIMEOUT: int = Field(
        default=300,
        description="Default sandbox execution timeout in seconds"
    )
    SANDBOX_MEMORY_LIMIT: str = Field(default="512M")
    SANDBOX_CPU_LIMIT: str = Field(default="1.0")
    
    # LLM Configuration
    LLM_DEFAULT_MODEL: str = Field(default="gpt-4-turbo-preview")
    LLM_DEFAULT_TEMPERATURE: float = Field(default=0.3)
    LLM_MAX_TOKENS: int = Field(default=4000)
    LLM_TIMEOUT: int = Field(default=120)
    
    # Test-Driven Development
    TDD_ENABLED: bool = Field(
        default=True,
        description="Enable Test-Driven Development for code generation tasks"
    )
    TDD_MIN_INDICATORS: int = Field(
        default=2,
        description="Minimum number of TDD indicators required to trigger TDD workflow"
    )
    
    # AITL Configuration (AI-in-the-Loop)
    AITL_ENABLED: bool = Field(default=True, description="Enable AITL review system")
    AITL_AUTO_PROCESS: bool = Field(default=False, description="Auto-process AITL reviews")
    AITL_CONFIDENCE_THRESHOLD: float = Field(default=0.5, description="Confidence threshold for AITL approval")
    
    # HAP Configuration (Hate, Abuse, Profanity)
    HAP_ENABLED: bool = Field(default=True, description="Enable HAP content moderation")
    HAP_TECHNICAL_CONTEXT_AWARE: bool = Field(default=True, description="Enable technical context detection")
    HAP_REQUEST_BLOCKING_THRESHOLD: str = Field(default="HIGH", description="Severity threshold for blocking requests (LOW, MEDIUM, HIGH, CRITICAL)")
    HAP_OUTPUT_BLOCKING_THRESHOLD: str = Field(default="HIGH", description="Severity threshold for blocking outputs (LOW, MEDIUM, HIGH, CRITICAL)")
    HAP_PROFANITY_SENSITIVITY: str = Field(default="LOW", description="Profanity detection sensitivity (LOW, MEDIUM, HIGH)")
    
    # LLM Provider Selection by Tier
    LLM_T0_PROVIDER: str = Field(default="azure", description="Provider for T0 agents")
    LLM_T1_PROVIDER: str = Field(default="azure", description="Provider for T1 agents")
    LLM_T2_PROVIDER: str = Field(default="azure", description="Provider for T2 agents")
    LLM_T3_PROVIDER: str = Field(default="azure", description="Provider for T3 agents")
    
    # Azure OpenAI Model Selection by Tier
    AZURE_T0_MODEL: str = Field(default="gpt-35-turbo", description="Azure model for T0 agents (simple tasks)")
    AZURE_T1_MODEL: str = Field(default="gpt-4.1-mini", description="Azure model for T1 agents (medium tasks)")
    AZURE_T2_MODEL: str = Field(default="gpt-4", description="Azure model for T2 agents (complex tasks)")
    AZURE_T3_MODEL: str = Field(default="gpt-4.1", description="Azure model for T3 agents (meta-agents)")
    
    # Azure OpenAI Deployment Names by Tier
    AZURE_T0_DEPLOYMENT: str = Field(default="gpt-35-turbo", description="Azure deployment for T0")
    AZURE_T1_DEPLOYMENT: str = Field(default="gpt-4.1-mini", description="Azure deployment for T1")
    AZURE_T2_DEPLOYMENT: str = Field(default="gpt-4", description="Azure deployment for T2")
    AZURE_T3_DEPLOYMENT: str = Field(default="gpt-4.1", description="Azure deployment for T3")
    
    # AWS Bedrock Configuration
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None, description="AWS Access Key ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None, description="AWS Secret Access Key")
    
    # Workflow Configuration - Enterprise Scale
    WORKFLOW_MAX_BATCH_SIZE: int = Field(default=50, description="Maximum tasks per batch for parallel execution")
    WORKFLOW_MAX_CONCURRENT_ACTIVITIES: int = Field(default=100, description="Max concurrent activities per worker")
    WORKFLOW_MAX_CONCURRENT_WORKFLOWS: int = Field(default=50, description="Max concurrent workflow tasks")
    WORKFLOW_ACTIVITY_TIMEOUT_MINUTES: int = Field(default=60, description="Default activity timeout in minutes")
    WORKFLOW_LONG_ACTIVITY_TIMEOUT_MINUTES: int = Field(default=180, description="Long activity timeout in minutes")
    WORKFLOW_HEARTBEAT_TIMEOUT_MINUTES: int = Field(default=20, description="Heartbeat timeout in minutes")
    WORKFLOW_HEARTBEAT_INTERVAL_SECONDS: int = Field(default=10, description="Heartbeat interval in seconds")
    WORKFLOW_MAX_DURATION_HOURS: int = Field(default=6, description="Maximum workflow duration in hours")
    
    # Dynamic Scaling Configuration
    ENABLE_DYNAMIC_SCALING: bool = Field(default=True, description="Enable dynamic resource scaling")
    MIN_BATCH_SIZE: int = Field(default=5, description="Minimum batch size for parallel execution")
    MAX_BATCH_SIZE: int = Field(default=100, description="Maximum batch size for parallel execution")
    CPU_THRESHOLD_HIGH: float = Field(default=80.0, description="CPU threshold for scaling down")
    CPU_THRESHOLD_LOW: float = Field(default=50.0, description="CPU threshold for scaling up")
    MEMORY_THRESHOLD_HIGH: float = Field(default=80.0, description="Memory threshold for scaling down")
    MEMORY_THRESHOLD_LOW: float = Field(default=50.0, description="Memory threshold for scaling up")
    
    # Retry Configuration
    RETRY_MAX_ATTEMPTS: int = Field(default=5, description="Maximum retry attempts")
    RETRY_INITIAL_INTERVAL_SECONDS: int = Field(default=2, description="Initial retry interval")
    RETRY_BACKOFF_COEFFICIENT: float = Field(default=2.5, description="Retry backoff coefficient")
    RETRY_MAX_INTERVAL_MINUTES: int = Field(default=5, description="Maximum retry interval")
    
    # Circuit Breaker Configuration
    CIRCUIT_BREAKER_ENABLED: bool = Field(default=True, description="Enable circuit breaker")
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = Field(default=5, description="Failure threshold before opening")
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = Field(default=60, description="Recovery timeout in seconds")
    CIRCUIT_BREAKER_EXPECTED_EXCEPTION_TYPES: List[str] = Field(
        default=["TimeoutError", "ConnectionError"], 
        description="Exception types that trigger circuit breaker"
    )
    
    # Monitoring Configuration
    ENABLE_METRICS: bool = Field(default=True, description="Enable metrics collection")
    ENABLE_DISTRIBUTED_TRACING: bool = Field(default=True, description="Enable distributed tracing")
    METRICS_EXPORT_INTERVAL: int = Field(default=60, description="Metrics export interval in seconds")
    JAEGER_ENDPOINT: Optional[str] = Field(default="http://localhost:14268/api/traces", description="Jaeger endpoint")
    
    # Enterprise Features
    ENTERPRISE_FEATURES_ENABLED: bool = Field(default=True, description="Enable enterprise features")
    ENABLE_TASK_PRIORITY_QUEUE: bool = Field(default=True, description="Enable priority-based task scheduling")
    ENABLE_RESOURCE_MONITORING: bool = Field(default=True, description="Enable resource usage monitoring")
    ENABLE_ADAPTIVE_TIMEOUTS: bool = Field(default=True, description="Enable adaptive timeout calculation")
    ENABLE_INTELLIGENT_RETRY: bool = Field(default=True, description="Enable intelligent retry with exponential backoff")
    
    # GitHub Configuration
    GITHUB_TOKEN: Optional[str] = Field(default=None, description="GitHub personal access token")
    GITHUB_DEFAULT_BRANCH: str = Field(default="main", description="Default branch for GitHub repos")
    GITHUB_AUTO_CREATE_REPO: bool = Field(default=True, description="Auto-create GitHub repository")
    
    # Universal Language Support
    DETECT_LANGUAGE_FROM_REQUIREMENTS: bool = Field(default=True, description="Auto-detect programming language")
    SUPPORTED_LANGUAGES: List[str] = Field(
        default=["python", "javascript", "typescript", "java", "go", "rust", "cpp", "csharp", "ruby", "php", "swift", "kotlin", "scala", "r", "julia", "dart", "lua", "perl", "shell", "powershell", "sql", "html", "css", "yaml", "json", "xml", "markdown"],
        description="List of supported programming languages"
    )
    AWS_SESSION_TOKEN: Optional[str] = Field(default=None, description="AWS Session Token (for temporary credentials)")
    AWS_REGION: str = Field(default="us-east-1", description="AWS region for Bedrock services")
    AWS_BEDROCK_ENDPOINT: Optional[str] = Field(default=None, description="Custom AWS Bedrock endpoint (for VPC/private endpoints)")
    
    # AWS Bedrock Model Selection by Tier
    AWS_T0_MODEL: str = Field(default="anthropic.claude-3-haiku-20240307-v1:0", description="AWS Bedrock model for T0 agents")
    AWS_T1_MODEL: str = Field(default="anthropic.claude-3-sonnet-20240229-v1:0", description="AWS Bedrock model for T1 agents")
    AWS_T2_MODEL: str = Field(default="anthropic.claude-3-5-sonnet-20240620-v1:0", description="AWS Bedrock model for T2 agents")
    AWS_T3_MODEL: str = Field(default="anthropic.claude-3-opus-20240229-v1:0", description="AWS Bedrock model for T3 agents")
    
    # AWS Bedrock Advanced Configuration
    AWS_BEDROCK_RETRY_ATTEMPTS: int = Field(default=3, description="Number of retry attempts for Bedrock API calls")
    AWS_BEDROCK_TIMEOUT: int = Field(default=60, description="Timeout in seconds for Bedrock API calls")
    AWS_BEDROCK_MAX_CONCURRENT: int = Field(default=10, description="Maximum concurrent Bedrock requests")
    AWS_BEDROCK_ENABLE_LOGGING: bool = Field(default=True, description="Enable detailed logging for Bedrock requests")
    
    # Multi-Provider Ensemble Configuration
    ENSEMBLE_ENABLED: bool = Field(default=False, description="Enable ensemble validation for critical tasks")
    ENSEMBLE_MIN_CONSENSUS: float = Field(default=0.7, description="Minimum consensus score for ensemble acceptance")
    ENSEMBLE_PROVIDERS: List[str] = Field(default=["aws_bedrock", "azure_openai"], description="Providers to use in ensemble")
    
    # Provider Health Monitoring
    PROVIDER_HEALTH_CHECK_INTERVAL: int = Field(default=60, description="Provider health check interval in seconds")
    PROVIDER_CIRCUIT_BREAKER_THRESHOLD: int = Field(default=5, description="Failure count to trigger circuit breaker")
    PROVIDER_CIRCUIT_BREAKER_TIMEOUT: int = Field(default=300, description="Circuit breaker timeout in seconds")
    
    # Regional Optimization
    REGIONAL_OPTIMIZATION_ENABLED: bool = Field(default=True, description="Enable regional provider optimization")
    PREFERRED_REGIONS: List[str] = Field(default=["us-east-1", "eu-west-1", "ap-southeast-1"], description="Preferred AWS regions in order")
    
    # Multi-tenancy
    MULTI_TENANT_ENABLED: bool = Field(default=True)
    DEFAULT_TENANT_ID: str = Field(default="default")
    
    # Workflow Configuration
    WORKFLOW_ACTIVITY_TIMEOUT_MINUTES: int = Field(default=30, description="Default activity timeout in minutes")
    WORKFLOW_LONG_ACTIVITY_TIMEOUT_MINUTES: int = Field(default=60, description="Long activity timeout in minutes")
    WORKFLOW_HEARTBEAT_TIMEOUT_MINUTES: int = Field(default=5, description="Heartbeat timeout in minutes")
    WORKFLOW_HEARTBEAT_INTERVAL_SECONDS: int = Field(default=30, description="Heartbeat interval in seconds")
    WORKFLOW_MAX_DURATION_HOURS: int = Field(default=24, description="Maximum workflow duration in hours")
    WORKFLOW_MAX_BATCH_SIZE: int = Field(default=10, description="Maximum batch size for parallel execution")
    WORKFLOW_MAX_CONCURRENT_ACTIVITIES: int = Field(default=20, description="Maximum concurrent activities")
    WORKFLOW_MAX_CONCURRENT_WORKFLOWS: int = Field(default=10, description="Maximum concurrent workflows")
    
    # Enterprise Worker Configuration
    ENABLE_DYNAMIC_SCALING: bool = Field(default=True, description="Enable dynamic batch size scaling")
    ENABLE_ADAPTIVE_TIMEOUTS: bool = Field(default=True, description="Enable adaptive timeout calculation")
    CIRCUIT_BREAKER_ENABLED: bool = Field(default=True, description="Enable circuit breaker for services")
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = Field(default=5, description="Failures before circuit opens")
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = Field(default=60, description="Recovery timeout in seconds")
    
    # Resource Monitoring Thresholds
    CPU_THRESHOLD_HIGH: float = Field(default=80.0, description="High CPU threshold percentage")
    CPU_THRESHOLD_LOW: float = Field(default=30.0, description="Low CPU threshold percentage")
    MEMORY_THRESHOLD_HIGH: float = Field(default=80.0, description="High memory threshold percentage")
    MEMORY_THRESHOLD_LOW: float = Field(default=30.0, description="Low memory threshold percentage")
    MIN_BATCH_SIZE: int = Field(default=2, description="Minimum batch size")
    MAX_BATCH_SIZE: int = Field(default=50, description="Maximum batch size")
    
    # Retry Configuration
    RETRY_INITIAL_INTERVAL_SECONDS: int = Field(default=2, description="Initial retry interval")
    RETRY_BACKOFF_COEFFICIENT: float = Field(default=2.0, description="Retry backoff coefficient")
    RETRY_MAX_INTERVAL_MINUTES: int = Field(default=5, description="Maximum retry interval")
    RETRY_MAX_ATTEMPTS: int = Field(default=3, description="Maximum retry attempts")
    
    # Language Detection
    DETECT_LANGUAGE_FROM_REQUIREMENTS: bool = Field(default=True, description="Auto-detect programming language")
    SUPPORTED_LANGUAGES: List[str] = Field(default=["python", "javascript", "typescript", "java", "go", "rust", "csharp"], description="Supported programming languages")
    
    # GitHub Integration
    GITHUB_DEFAULT_BRANCH: str = Field(default="main", description="Default GitHub branch")
    
    # Feature Flags
    FEATURE_ADVANCED_VALIDATION: bool = Field(default=True)
    FEATURE_AUTO_SCALING: bool = Field(default=False)
    FEATURE_SEMANTIC_SEARCH: bool = Field(default=True)
    FEATURE_CHAOS_TESTING: bool = Field(default=False)
    
    # Monitoring
    METRICS_ENABLED: bool = Field(default=True)
    TRACING_ENABLED: bool = Field(default=True)
    JAEGER_AGENT_HOST: str = Field(default="localhost")
    JAEGER_AGENT_PORT: int = Field(default=6831)
    
    # CORS
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:3001"
    )
    
    # Social Media API Keys (for marketing auto-publish)
    TWITTER_API_KEY: Optional[str] = None
    TWITTER_API_SECRET: Optional[str] = None
    TWITTER_ACCESS_TOKEN: Optional[str] = None
    TWITTER_ACCESS_SECRET: Optional[str] = None
    TWITTER_BEARER_TOKEN: Optional[str] = None
    
    LINKEDIN_EMAIL: Optional[str] = None
    LINKEDIN_PASSWORD: Optional[str] = None
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(',')]
    
    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}")
        return v
    
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}")
        return v.upper()
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"
    
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"
    
    def get_llm_config(self, model: Optional[str] = None) -> Dict[str, Any]:
        """Get LLM configuration"""
        return {
            "model": model or self.LLM_DEFAULT_MODEL,
            "temperature": self.LLM_DEFAULT_TEMPERATURE,
            "max_tokens": self.LLM_MAX_TOKENS,
            "timeout": self.LLM_TIMEOUT
        }
    
    def get_tenant_limits(self, tier: str) -> Dict[str, Any]:
        """Get resource limits for tenant tier"""
        limits = {
            "free": {
                "requests_per_day": 10,
                "max_execution_time": 300,
                "max_tasks_per_request": 5,
                "storage_gb": 1
            },
            "standard": {
                "requests_per_day": 100,
                "max_execution_time": 1800,
                "max_tasks_per_request": 20,
                "storage_gb": 10
            },
            "enterprise": {
                "requests_per_day": -1,  # unlimited
                "max_execution_time": 7200,
                "max_tasks_per_request": 100,
                "storage_gb": 100
            }
        }
        return limits.get(tier, limits["free"])
    
    def validate_aws_config(self) -> Dict[str, bool]:
        """Validate AWS configuration"""
        validation = {
            "has_credentials": bool(self.AWS_ACCESS_KEY_ID and self.AWS_SECRET_ACCESS_KEY),
            "has_region": bool(self.AWS_REGION),
            "valid_region": self.AWS_REGION in [
                "us-east-1", "us-west-2", "eu-west-1", "eu-central-1", 
                "ap-southeast-1", "ap-northeast-1"
            ],
            "valid_timeout": 10 <= self.AWS_BEDROCK_TIMEOUT <= 300,
            "valid_concurrent": 1 <= self.AWS_BEDROCK_MAX_CONCURRENT <= 50
        }
        validation["is_valid"] = all(validation.values())
        return validation
    
    def get_aws_bedrock_config(self) -> Dict[str, Any]:
        """Get AWS Bedrock configuration"""
        return {
            "region": self.AWS_REGION,
            "endpoint_url": self.AWS_BEDROCK_ENDPOINT,
            "retry_attempts": self.AWS_BEDROCK_RETRY_ATTEMPTS,
            "timeout": self.AWS_BEDROCK_TIMEOUT,
            "max_concurrent": self.AWS_BEDROCK_MAX_CONCURRENT,
            "enable_logging": self.AWS_BEDROCK_ENABLE_LOGGING,
            "tier_models": {
                "T0": self.AWS_T0_MODEL,
                "T1": self.AWS_T1_MODEL,
                "T2": self.AWS_T2_MODEL,
                "T3": self.AWS_T3_MODEL
            }
        }


# Global settings instance
settings = Settings()


# Helper function to get settings
def get_settings() -> Settings:
    """Get application settings instance"""
    return settings
