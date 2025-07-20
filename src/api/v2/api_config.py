"""
API-specific configuration for dynamic URL handling
"""

import os
from typing import Optional
from pydantic import Field
from src.common.config import Settings


class APISettings(Settings):
    """Extended settings for API configuration"""
    
    # API URLs
    API_BASE_URL: Optional[str] = Field(
        default=None, 
        description="Custom API base URL (overrides environment-based URLs)"
    )
    PRODUCTION_API_URL: str = Field(
        default="https://api.quantumlayerplatform.com",
        description="Production API URL"
    )
    STAGING_API_URL: str = Field(
        default="https://staging-api.quantumlayerplatform.com",
        description="Staging API URL"
    )
    LOCAL_API_URL: str = Field(
        default="http://localhost:8000",
        description="Local development API URL"
    )
    
    # CSP Configuration
    ADDITIONAL_ALLOWED_ORIGINS: str = Field(
        default="",
        description="Comma-separated list of additional allowed origins for CORS/CSP"
    )
    
    # Documentation
    SWAGGER_CDN_URL: str = Field(
        default="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0",
        description="CDN URL for Swagger UI assets"
    )
    REDOC_CDN_URL: str = Field(
        default="https://cdn.jsdelivr.net/npm/redoc@2.0.0",
        description="CDN URL for ReDoc assets"
    )
    
    # Feature flags
    AUTO_DETECT_HOST: bool = Field(
        default=True,
        description="Auto-detect host from request in development mode"
    )
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def is_staging(self) -> bool:
        """Check if running in staging environment"""
        return self.ENVIRONMENT.lower() == "staging"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.ENVIRONMENT.lower() in ["development", "dev", "local"]


# Create a singleton instance
api_settings = APISettings()