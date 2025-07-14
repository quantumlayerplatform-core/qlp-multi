#!/usr/bin/env python3
"""
Clerk Authentication Integration
Provides authentication and authorization using Clerk for the QLP platform.
"""

from typing import Dict, Any, Optional, List
from functools import wraps
import os
import httpx
from datetime import datetime, timezone
from jose import jwt, JWTError

from fastapi import HTTPException, Depends, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import structlog

from src.common.config import settings

logger = structlog.get_logger()

# Clerk configuration
CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY", "")
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY", "")
CLERK_API_URL = "https://api.clerk.com/v1"
CLERK_JWKS_URL = os.getenv("CLERK_JWKS_URL", "")

# Security scheme
security = HTTPBearer()

# Cache for JWKS keys
_jwks_cache = None
_jwks_cache_time = None
JWKS_CACHE_DURATION = 3600  # 1 hour


class ClerkAuth:
    """Clerk authentication handler"""
    
    def __init__(self):
        self.publishable_key = CLERK_PUBLISHABLE_KEY
        self.secret_key = CLERK_SECRET_KEY
        self.api_url = CLERK_API_URL
        self.jwks_url = CLERK_JWKS_URL or f"https://{self._get_clerk_domain()}.clerk.accounts.dev/.well-known/jwks.json"
        
        if not self.secret_key:
            logger.warning("Clerk secret key not configured - using development mode")
    
    def _get_clerk_domain(self) -> str:
        """Extract Clerk domain from publishable key"""
        if self.publishable_key and self.publishable_key.startswith("pk_"):
            # Extract domain from publishable key
            parts = self.publishable_key.split("_")
            if len(parts) >= 3:
                return parts[2]
        return "clerk"
    
    async def get_jwks(self) -> Dict[str, Any]:
        """Get JWKS keys from Clerk with caching"""
        global _jwks_cache, _jwks_cache_time
        
        # Check cache
        if _jwks_cache and _jwks_cache_time:
            if (datetime.now(timezone.utc) - _jwks_cache_time).total_seconds() < JWKS_CACHE_DURATION:
                return _jwks_cache
        
        # Fetch new JWKS
        async with httpx.AsyncClient() as client:
            response = await client.get(self.jwks_url)
            response.raise_for_status()
            
            _jwks_cache = response.json()
            _jwks_cache_time = datetime.now(timezone.utc)
            
            return _jwks_cache
    
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode Clerk JWT token"""
        try:
            # In development mode, return mock user
            if not self.secret_key:
                return {
                    "user_id": "dev_user_123",
                    "email": "dev@quantumlayer.com",
                    "organizations": ["org_dev_456"],
                    "role": "admin",
                    "permissions": ["*"]
                }
            
            # Get JWKS keys
            jwks = await self.get_jwks()
            
            # Decode token header to get kid
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            
            # Find the correct key
            key = None
            for k in jwks.get("keys", []):
                if k.get("kid") == kid:
                    key = k
                    break
            
            if not key:
                raise ValueError("Unable to find matching key")
            
            # Verify and decode token
            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                options={"verify_aud": False}  # Clerk doesn't always include audience
            )
            
            # Extract user information
            return {
                "user_id": payload.get("sub"),
                "email": payload.get("email"),
                "organizations": payload.get("org_id", []),
                "role": payload.get("org_role", "member"),
                "permissions": payload.get("org_permissions", []),
                "metadata": payload.get("metadata", {})
            }
            
        except JWTError as e:
            logger.error("JWT verification failed", error=str(e))
            raise HTTPException(status_code=401, detail="Invalid token")
        except Exception as e:
            logger.error("Token verification error", error=str(e))
            raise HTTPException(status_code=401, detail="Authentication failed")
    
    async def get_user_details(self, user_id: str) -> Dict[str, Any]:
        """Get user details from Clerk API"""
        if not self.secret_key:
            # Development mode
            return {
                "id": user_id,
                "email": "dev@quantumlayer.com",
                "first_name": "Dev",
                "last_name": "User",
                "organizations": ["org_dev_456"]
            }
        
        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/users/{user_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error("Failed to get user details", 
                           status_code=response.status_code,
                           user_id=user_id)
                return None
    
    async def get_organization_details(self, org_id: str) -> Dict[str, Any]:
        """Get organization details from Clerk API"""
        if not self.secret_key:
            # Development mode
            return {
                "id": org_id,
                "name": "Dev Organization",
                "slug": "dev-org"
            }
        
        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/organizations/{org_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error("Failed to get organization details",
                           status_code=response.status_code,
                           org_id=org_id)
                return None


# Global Clerk instance
clerk = ClerkAuth()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    request: Request = None
) -> Dict[str, Any]:
    """Get current authenticated user from Clerk token"""
    
    try:
        # Verify token
        user_data = await clerk.verify_token(credentials.credentials)
        
        # Get the first organization if available
        organization_id = None
        if user_data.get("organizations"):
            organization_id = user_data["organizations"][0] if isinstance(user_data["organizations"], list) else user_data["organizations"]
        
        # Build user context
        user_context = {
            "user_id": user_data["user_id"],
            "email": user_data.get("email"),
            "organization_id": organization_id,
            "tenant_id": organization_id,  # For backward compatibility
            "role": user_data.get("role", "member"),
            "permissions": user_data.get("permissions", []),
            "authenticated": True,
            "auth_provider": "clerk"
        }
        
        # Add to request state if available
        if request:
            request.state.user = user_context
        
        logger.info("User authenticated", 
                   user_id=user_context["user_id"],
                   org_id=user_context["organization_id"])
        
        return user_context
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Authentication error", error=str(e))
        raise HTTPException(status_code=401, detail="Authentication failed")


def require_role(allowed_roles: List[str]):
    """Dependency to require specific roles"""
    async def role_checker(user: Dict[str, Any] = Depends(get_current_user)):
        user_role = user.get("role", "member")
        
        if user_role not in allowed_roles:
            logger.warning("Access denied - insufficient role",
                         user_id=user["user_id"],
                         user_role=user_role,
                         required_roles=allowed_roles)
            raise HTTPException(
                status_code=403,
                detail=f"Requires one of roles: {', '.join(allowed_roles)}"
            )
        
        return user
    
    return role_checker


def require_permission(required_permissions: List[str]):
    """Dependency to require specific permissions"""
    async def permission_checker(user: Dict[str, Any] = Depends(get_current_user)):
        user_permissions = set(user.get("permissions", []))
        
        # Admin has all permissions
        if user.get("role") == "admin" or "*" in user_permissions:
            return user
        
        # Check if user has all required permissions
        missing_permissions = set(required_permissions) - user_permissions
        
        if missing_permissions:
            logger.warning("Access denied - missing permissions",
                         user_id=user["user_id"],
                         missing_permissions=list(missing_permissions))
            raise HTTPException(
                status_code=403,
                detail=f"Missing permissions: {', '.join(missing_permissions)}"
            )
        
        return user
    
    return permission_checker


def optional_auth():
    """Optional authentication - returns user if authenticated, None otherwise"""
    async def auth_checker(
        authorization: Optional[str] = Header(None),
        request: Request = None
    ):
        if not authorization or not authorization.startswith("Bearer "):
            return None
        
        try:
            token = authorization.split(" ")[1]
            user_data = await clerk.verify_token(token)
            
            # Get the first organization if available
            organization_id = None
            if user_data.get("organizations"):
                organization_id = user_data["organizations"][0] if isinstance(user_data["organizations"], list) else user_data["organizations"]
            
            user_context = {
                "user_id": user_data["user_id"],
                "email": user_data.get("email"),
                "organization_id": organization_id,
                "tenant_id": organization_id,
                "role": user_data.get("role", "member"),
                "permissions": user_data.get("permissions", []),
                "authenticated": True,
                "auth_provider": "clerk"
            }
            
            if request:
                request.state.user = user_context
            
            return user_context
            
        except Exception:
            return None
    
    return auth_checker


# Backward compatibility with existing code
def get_current_user_sync() -> Dict[str, Any]:
    """Synchronous version for backward compatibility - returns development user"""
    logger.warning("Using synchronous auth function - should be replaced with async version")
    return {
        "user_id": "default-user",
        "tenant_id": "default-tenant",
        "organization_id": "default-tenant",
        "email": "user@example.com",
        "role": "admin",
        "authenticated": True,
        "auth_provider": "development"
    }


# Export the old function name for backward compatibility
from src.common.auth import get_current_user as old_get_current_user