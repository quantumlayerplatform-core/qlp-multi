"""
Azure AD B2C configuration and client for multi-tenant authentication
"""

import os
import time
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, List, Any
from urllib.parse import urljoin
import asyncio
from functools import lru_cache

import httpx
import jwt
from jwt import PyJWKClient
from pydantic import BaseModel, Field, ValidationError
import redis.asyncio as redis
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from src.common.logger import get_logger

logger = get_logger(__name__)


class AzureADB2CConfig(BaseModel):
    """Azure AD B2C configuration settings"""
    tenant_name: str = Field(description="Azure AD B2C tenant name (without .onmicrosoft.com)")
    client_id: str = Field(description="Application (client) ID")
    client_secret: str = Field(description="Client secret for confidential clients")
    policy_name: str = Field(default="B2C_1_SignUpSignIn", description="User flow/policy name")
    
    # Optional settings
    authority_domain: str = Field(default="b2clogin.com", description="B2C domain")
    api_version: str = Field(default="v2.0", description="API version")
    scopes: List[str] = Field(default_factory=lambda: ["openid", "profile", "email"])
    
    # Token settings
    clock_skew_seconds: int = Field(default=300, description="Clock skew tolerance in seconds")
    token_cache_ttl: int = Field(default=300, description="Token cache TTL in seconds")
    jwks_cache_ttl: int = Field(default=3600, description="JWKS cache TTL in seconds")
    
    # Redis settings
    redis_url: str = Field(default="redis://localhost:6379/0")
    
    @classmethod
    def from_env(cls) -> "AzureADB2CConfig":
        """Create config from environment variables"""
        return cls(
            tenant_name=os.getenv("AZURE_AD_B2C_TENANT_NAME", ""),
            client_id=os.getenv("AZURE_AD_B2C_CLIENT_ID", ""),
            client_secret=os.getenv("AZURE_AD_B2C_CLIENT_SECRET", ""),
            policy_name=os.getenv("AZURE_AD_B2C_POLICY_NAME", "B2C_1_SignUpSignIn"),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            scopes=os.getenv("AZURE_AD_B2C_SCOPES", "openid,profile,email").split(",")
        )
    
    @property
    def authority(self) -> str:
        """Get the authority URL"""
        return f"https://{self.tenant_name}.{self.authority_domain}/{self.tenant_name}.onmicrosoft.com/{self.policy_name}"
    
    @property
    def issuer(self) -> str:
        """Get the expected token issuer"""
        return f"https://{self.tenant_name}.{self.authority_domain}/{self.tenant_name}.onmicrosoft.com/{self.policy_name}/{self.api_version}/"
    
    @property
    def jwks_uri(self) -> str:
        """Get the JWKS endpoint URL"""
        return f"{self.authority}/{self.api_version}/.well-known/openid-configuration"
    
    @property
    def token_endpoint(self) -> str:
        """Get the token endpoint URL"""
        return f"{self.authority}/oauth2/{self.api_version}/token"


class UserClaims(BaseModel):
    """Validated user claims from token"""
    # Standard claims
    sub: str = Field(description="Subject identifier (user ID)")
    email: Optional[str] = Field(None, description="User email")
    name: Optional[str] = Field(None, description="Display name")
    given_name: Optional[str] = Field(None)
    family_name: Optional[str] = Field(None)
    
    # Custom claims
    tenant_id: Optional[str] = Field(None, description="Current tenant ID")
    workspace_ids: List[str] = Field(default_factory=list, description="Accessible workspace IDs")
    role: Optional[str] = Field(None, description="User role in current context")
    permissions: List[str] = Field(default_factory=list, description="Granted permissions")
    
    # Token metadata
    iat: int = Field(description="Issued at timestamp")
    exp: int = Field(description="Expiration timestamp")
    aud: str = Field(description="Audience (client ID)")
    iss: str = Field(description="Issuer")
    
    # Additional metadata
    auth_time: Optional[int] = Field(None, description="Authentication time")
    acr: Optional[str] = Field(None, description="Authentication context reference")
    
    @property
    def user_id(self) -> str:
        """Get user ID (alias for sub)"""
        return self.sub
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired"""
        return datetime.now(timezone.utc).timestamp() > self.exp
    
    @property
    def time_until_expiry(self) -> timedelta:
        """Get time until token expires"""
        return datetime.fromtimestamp(self.exp, timezone.utc) - datetime.now(timezone.utc)
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        return permission in self.permissions
    
    def has_workspace_access(self, workspace_id: str) -> bool:
        """Check if user has access to workspace"""
        return workspace_id in self.workspace_ids


class TokenResponse(BaseModel):
    """Token response from Azure AD B2C"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None
    scope: Optional[str] = None
    
    @property
    def expires_at(self) -> datetime:
        """Calculate expiration time"""
        return datetime.now(timezone.utc) + timedelta(seconds=self.expires_in)


class AzureADB2CClient:
    """Azure AD B2C client for token validation and user management"""
    
    def __init__(self, config: Optional[AzureADB2CConfig] = None):
        self.config = config or AzureADB2CConfig.from_env()
        self._http_client: Optional[httpx.AsyncClient] = None
        self._redis_client: Optional[redis.Redis] = None
        self._jwks_client: Optional[PyJWKClient] = None
        self._jwks_data: Optional[Dict] = None
        self._jwks_fetched_at: float = 0
        self._initialization_lock = asyncio.Lock()
        
    async def initialize(self):
        """Initialize HTTP and Redis clients"""
        async with self._initialization_lock:
            if not self._http_client:
                self._http_client = httpx.AsyncClient(timeout=30.0)
                logger.info("Initialized HTTP client for Azure AD B2C")
            
            if not self._redis_client:
                try:
                    self._redis_client = await redis.from_url(
                        self.config.redis_url,
                        decode_responses=True
                    )
                    await self._redis_client.ping()
                    logger.info("Connected to Redis for token caching")
                except Exception as e:
                    logger.error(f"Failed to connect to Redis: {e}")
                    self._redis_client = None
    
    async def close(self):
        """Close connections"""
        if self._http_client:
            await self._http_client.aclose()
        if self._redis_client:
            await self._redis_client.close()
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    def _get_cache_key(self, key_type: str, key_id: str) -> str:
        """Generate Redis cache key"""
        return f"auth:b2c:{key_type}:{key_id}"
    
    async def _get_from_cache(self, key: str) -> Optional[Dict]:
        """Get value from Redis cache"""
        if not self._redis_client:
            return None
        
        try:
            value = await self._redis_client.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    async def _set_cache(self, key: str, value: Dict, ttl: int):
        """Set value in Redis cache with TTL"""
        if not self._redis_client:
            return
        
        try:
            await self._redis_client.setex(
                key, 
                ttl, 
                json.dumps(value)
            )
        except Exception as e:
            logger.error(f"Redis set error: {e}")
    
    async def _delete_from_cache(self, key: str):
        """Delete value from Redis cache"""
        if not self._redis_client:
            return
        
        try:
            await self._redis_client.delete(key)
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
    
    async def get_openid_configuration(self) -> Dict[str, Any]:
        """Get OpenID configuration from B2C"""
        cache_key = self._get_cache_key("config", self.config.policy_name)
        
        # Check cache first
        cached = await self._get_from_cache(cache_key)
        if cached:
            logger.debug("Using cached OpenID configuration")
            return cached
        
        # Fetch from B2C
        if not self._http_client:
            await self.initialize()
        
        try:
            response = await self._http_client.get(self.config.jwks_uri)
            response.raise_for_status()
            config = response.json()
            
            # Cache the configuration
            await self._set_cache(cache_key, config, self.config.jwks_cache_ttl)
            
            logger.info("Fetched OpenID configuration from Azure AD B2C")
            return config
        except Exception as e:
            logger.error(f"Failed to fetch OpenID configuration: {e}")
            raise
    
    async def get_jwks(self) -> Dict[str, Any]:
        """Get JSON Web Key Set with caching"""
        # Check if we have recent JWKS data
        if (self._jwks_data and 
            time.time() - self._jwks_fetched_at < self.config.jwks_cache_ttl):
            return self._jwks_data
        
        cache_key = self._get_cache_key("jwks", self.config.policy_name)
        
        # Check Redis cache
        cached = await self._get_from_cache(cache_key)
        if cached:
            self._jwks_data = cached
            self._jwks_fetched_at = time.time()
            logger.debug("Using cached JWKS")
            return cached
        
        # Get JWKS URI from OpenID configuration
        config = await self.get_openid_configuration()
        jwks_uri = config.get("jwks_uri")
        
        if not jwks_uri:
            raise ValueError("JWKS URI not found in OpenID configuration")
        
        # Fetch JWKS
        if not self._http_client:
            await self.initialize()
        
        try:
            response = await self._http_client.get(jwks_uri)
            response.raise_for_status()
            jwks = response.json()
            
            # Cache the JWKS
            await self._set_cache(cache_key, jwks, self.config.jwks_cache_ttl)
            
            self._jwks_data = jwks
            self._jwks_fetched_at = time.time()
            
            logger.info("Fetched JWKS from Azure AD B2C")
            return jwks
        except Exception as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            raise
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate and decode JWT token"""
        # Check cache first
        cache_key = self._get_cache_key("token", token[:50])  # Use token prefix as key
        cached = await self._get_from_cache(cache_key)
        if cached:
            logger.debug("Using cached token validation")
            return cached
        
        try:
            # Get JWKS for validation
            jwks = await self.get_jwks()
            
            # Decode token header to get kid
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            
            if not kid:
                raise ValueError("Token missing 'kid' header")
            
            # Find the signing key
            signing_key = None
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    signing_key = key
                    break
            
            if not signing_key:
                raise ValueError(f"Signing key with kid '{kid}' not found")
            
            # Build the public key
            public_key = jwt.PyJWK(signing_key).key
            
            # Decode and verify the token
            decoded = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=self.config.client_id,
                issuer=self.config.issuer,
                options={
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": True,
                    "require": ["exp", "iat", "aud", "iss", "sub"]
                },
                leeway=self.config.clock_skew_seconds
            )
            
            # Cache the validated token
            await self._set_cache(cache_key, decoded, self.config.token_cache_ttl)
            
            logger.info(f"Successfully validated token for user: {decoded.get('sub')}")
            return decoded
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            raise
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token: {e}")
            raise
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise
    
    async def get_user_claims(self, token: str) -> UserClaims:
        """Extract and validate user claims from token"""
        decoded = await self.validate_token(token)
        
        try:
            # Extract custom claims with defaults
            claims = UserClaims(
                # Standard claims
                sub=decoded["sub"],
                email=decoded.get("email") or decoded.get("emails", [None])[0],
                name=decoded.get("name") or decoded.get("displayName"),
                given_name=decoded.get("given_name"),
                family_name=decoded.get("family_name"),
                
                # Custom claims - these would be added via custom policies
                tenant_id=decoded.get("extension_TenantId") or decoded.get("tenant_id"),
                workspace_ids=decoded.get("extension_WorkspaceIds", []) or decoded.get("workspace_ids", []),
                role=decoded.get("extension_Role") or decoded.get("role"),
                permissions=decoded.get("extension_Permissions", []) or decoded.get("permissions", []),
                
                # Token metadata
                iat=decoded["iat"],
                exp=decoded["exp"],
                aud=decoded["aud"],
                iss=decoded["iss"],
                
                # Additional metadata
                auth_time=decoded.get("auth_time"),
                acr=decoded.get("acr")
            )
            
            logger.debug(f"Extracted claims for user: {claims.sub}")
            return claims
            
        except ValidationError as e:
            logger.error(f"Claims validation error: {e}")
            raise ValueError(f"Invalid token claims: {e}")
    
    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        """Exchange refresh token for new tokens"""
        if not self._http_client:
            await self.initialize()
        
        try:
            data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "scope": " ".join(self.config.scopes)
            }
            
            response = await self._http_client.post(
                self.config.token_endpoint,
                data=data
            )
            response.raise_for_status()
            
            token_data = response.json()
            token_response = TokenResponse(**token_data)
            
            logger.info("Successfully refreshed token")
            return token_response
            
        except httpx.HTTPError as e:
            logger.error(f"Token refresh HTTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            raise
    
    async def revoke_token(self, token: str):
        """Revoke token by removing from cache"""
        cache_key = self._get_cache_key("token", token[:50])
        await self._delete_from_cache(cache_key)
        logger.info("Token revoked from cache")
    
    async def validate_permissions(
        self, 
        claims: UserClaims, 
        required_permissions: List[str]
    ) -> bool:
        """Validate user has required permissions"""
        missing = set(required_permissions) - set(claims.permissions)
        if missing:
            logger.warning(f"User {claims.sub} missing permissions: {missing}")
            return False
        return True
    
    async def validate_tenant_access(
        self, 
        claims: UserClaims, 
        tenant_id: str
    ) -> bool:
        """Validate user has access to tenant"""
        if not claims.tenant_id:
            logger.warning(f"User {claims.sub} has no tenant claim")
            return False
        
        if claims.tenant_id != tenant_id:
            logger.warning(f"User {claims.sub} tenant mismatch: {claims.tenant_id} != {tenant_id}")
            return False
        
        return True
    
    async def validate_workspace_access(
        self, 
        claims: UserClaims, 
        workspace_id: str
    ) -> bool:
        """Validate user has access to workspace"""
        if workspace_id not in claims.workspace_ids:
            logger.warning(f"User {claims.sub} lacks access to workspace: {workspace_id}")
            return False
        return True


# Singleton instance
_client: Optional[AzureADB2CClient] = None


async def get_azure_ad_client() -> AzureADB2CClient:
    """Get or create Azure AD B2C client instance"""
    global _client
    if not _client:
        _client = AzureADB2CClient()
        await _client.initialize()
    return _client


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def test_client():
        """Test Azure AD B2C client"""
        # This would require actual Azure AD B2C setup
        config = AzureADB2CConfig(
            tenant_name="your-tenant",
            client_id="your-client-id",
            client_secret="your-secret"
        )
        
        async with AzureADB2CClient(config) as client:
            # Get OpenID configuration
            config = await client.get_openid_configuration()
            print(f"OpenID Config: {json.dumps(config, indent=2)}")
            
            # Get JWKS
            jwks = await client.get_jwks()
            print(f"JWKS: {json.dumps(jwks, indent=2)}")
    
    # asyncio.run(test_client())