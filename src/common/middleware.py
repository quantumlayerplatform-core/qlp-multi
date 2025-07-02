"""Middleware for authentication, tenant isolation, and usage tracking"""

from contextvars import ContextVar
from typing import Optional
from uuid import UUID

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.service import AuthService
from src.billing.models import User, Organization, ActionType
from src.billing.service import BillingService
from src.common.database import get_db
from src.common.logger import get_logger

logger = get_logger(__name__)

# Context variables for request-scoped data
current_user: ContextVar[Optional[User]] = ContextVar("current_user", default=None)
current_organization: ContextVar[Optional[Organization]] = ContextVar("current_organization", default=None)
current_tenant_id: ContextVar[Optional[str]] = ContextVar("current_tenant_id", default=None)

security = HTTPBearer()


class AuthMiddleware:
    """Authentication middleware"""
    
    async def __call__(self, request: Request, credentials: HTTPAuthorizationCredentials = None):
        """Authenticate request using JWT or API key"""
        
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        token = credentials.credentials
        
        # Get database session
        async with get_db() as db:
            auth_service = AuthService(db)
            
            try:
                if token.startswith("qlp_"):
                    # API key authentication
                    user, api_key = await auth_service.verify_api_key(token)
                else:
                    # JWT authentication
                    payload = auth_service.verify_token(token)
                    user = await db.get(User, UUID(payload["user_id"]))
                    
                    if not user or not user.is_active:
                        raise ValueError("User not found or inactive")
                
                # Get organization
                org = await db.get(Organization, user.organization_id)
                
                # Set context
                current_user.set(user)
                current_organization.set(org)
                current_tenant_id.set(str(org.id))
                
                return user
                
            except Exception as e:
                logger.error(f"Authentication failed: {e}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=str(e)
                )


class TenantIsolationMiddleware:
    """Ensure tenant isolation in all queries"""
    
    @staticmethod
    def get_current_tenant_id() -> Optional[str]:
        """Get current tenant ID from context"""
        return current_tenant_id.get()
    
    @staticmethod
    def apply_tenant_filter(query, tenant_field="tenant_id"):
        """Apply tenant filter to SQLAlchemy query"""
        tenant_id = TenantIsolationMiddleware.get_current_tenant_id()
        if tenant_id:
            return query.filter_by(**{tenant_field: tenant_id})
        return query


class UsageTrackingMiddleware:
    """Track API usage for billing"""
    
    def __init__(self, action_type: ActionType):
        self.action_type = action_type
    
    async def __call__(self, request: Request):
        """Track usage for this request"""
        
        user = current_user.get()
        org = current_organization.get()
        
        if not user or not org:
            return
        
        async with get_db() as db:
            billing_service = BillingService(db)
            
            # Check quota
            allowed, reason = await billing_service.check_quota(
                org.id,
                self.action_type
            )
            
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=reason
                )
            
            # Track will happen after successful request
            request.state.track_usage = True
            request.state.action_type = self.action_type


async def track_usage_after_response(
    request: Request,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    tokens_used: int = 0,
    compute_time_ms: int = 0
):
    """Track usage after successful response"""
    
    if not hasattr(request.state, "track_usage") or not request.state.track_usage:
        return
    
    user = current_user.get()
    org = current_organization.get()
    
    if not user or not org:
        return
    
    async with get_db() as db:
        billing_service = BillingService(db)
        
        await billing_service.track_usage(
            organization_id=org.id,
            user_id=user.id,
            action_type=request.state.action_type,
            resource_type=resource_type,
            resource_id=resource_id,
            tokens_used=tokens_used,
            compute_time_ms=compute_time_ms
        )


# Dependency functions for FastAPI
async def get_current_user() -> User:
    """Get current authenticated user"""
    user = current_user.get()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return user


async def get_current_organization() -> Organization:
    """Get current organization"""
    org = current_organization.get()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Organization not found"
        )
    return org


def require_role(allowed_roles: list):
    """Require specific user roles"""
    
    async def role_checker(user: User = Depends(get_current_user)):
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return user
    
    return role_checker


# Add to imports
from fastapi import Depends