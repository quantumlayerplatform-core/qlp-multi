#!/usr/bin/env python3
"""
Authentication module for QLP endpoints
Supports both Clerk authentication (production) and development mode
"""

from typing import Dict, Any, Optional, List
import os

# Try to import Clerk auth, fall back to development auth if not available
try:
    from src.common.clerk_auth import (
        get_current_user as clerk_get_current_user,
        require_role as clerk_require_role,
        require_permission as clerk_require_permission,
        optional_auth as clerk_optional_auth,
        clerk
    )
    CLERK_AVAILABLE = bool(os.getenv("CLERK_SECRET_KEY"))
except ImportError:
    CLERK_AVAILABLE = False


def get_current_user() -> Dict[str, Any]:
    """
    Simple authentication function that returns a default user
    In production with Clerk configured, use get_current_user_async instead
    """
    if CLERK_AVAILABLE:
        # In sync context, return a warning user
        return {
            "user_id": "sync-context-user",
            "tenant_id": "sync-context-tenant",
            "organization_id": "sync-context-tenant",
            "role": "admin",
            "authenticated": True,
            "auth_provider": "clerk-sync-fallback"
        }
    
    # Development mode
    return {
        "user_id": "default-user",
        "tenant_id": "default-tenant",
        "organization_id": "default-tenant",
        "role": "admin",
        "authenticated": True,
        "auth_provider": "development"
    }


# Export async version for FastAPI dependencies
if CLERK_AVAILABLE:
    get_current_user_async = clerk_get_current_user
    require_role = clerk_require_role
    require_permission = clerk_require_permission
    optional_auth = clerk_optional_auth
else:
    # Provide fallback implementations for development
    from fastapi import Depends
    
    async def get_current_user_async(**kwargs) -> Dict[str, Any]:
        """Async version of get_current_user for FastAPI"""
        return {
            "user_id": "default-user",
            "tenant_id": "default-tenant",
            "organization_id": "default-tenant",
            "role": "admin",
            "permissions": ["*"],
            "authenticated": True,
            "auth_provider": "development"
        }
    
    def require_role(roles: List[str]):
        """Fallback role checker - always allows in dev mode"""
        async def checker(**kwargs):
            return await get_current_user_async()
        return checker
    
    def require_permission(permissions: List[str]):
        """Fallback permission checker - always allows in dev mode"""
        async def checker(**kwargs):
            return await get_current_user_async()
        return checker
    
    def optional_auth():
        """Fallback optional auth - always returns dev user"""
        async def checker(**kwargs):
            return await get_current_user_async()
        return checker