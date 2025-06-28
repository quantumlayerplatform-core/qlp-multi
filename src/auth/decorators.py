"""
Authorization decorators for role-based access control and usage tracking
"""

import asyncio
import functools
import time
from typing import List, Optional, Callable, Any, Union
from datetime import datetime

from fastapi import HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.azure_ad_b2c import UserClaims
from src.auth.middleware import require_auth, require_tenant, get_current_user, get_current_tenant_id
from src.models.tenant import UserRole, WorkspaceRole, TenantPlan, ResourceType
from src.common.logger import get_logger

logger = get_logger(__name__)


class ForbiddenError(HTTPException):
    """Raised when user lacks required permissions"""
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


class QuotaExceededError(HTTPException):
    """Raised when tenant exceeds resource quota"""
    def __init__(self, resource_type: str, detail: str = "Quota exceeded"):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers={"X-RateLimit-Resource": resource_type}
        )


def require_auth_decorator(func: Callable) -> Callable:
    """
    Basic authentication decorator
    
    Usage:
        @require_auth_decorator
        async def my_endpoint(user: UserClaims = Depends(require_auth)):
            ...
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # The actual auth check is done by the middleware
        # This decorator is mainly for documentation
        return await func(*args, **kwargs)
    
    # Add FastAPI dependency
    wrapper.__annotations__['user'] = UserClaims
    wrapper.__defaults__ = (Depends(require_auth),) if func.__defaults__ else (Depends(require_auth),)
    
    return wrapper


def require_tenant_role(roles: Union[UserRole, List[UserRole]]) -> Callable:
    """
    Decorator to require specific tenant-level roles
    
    Args:
        roles: Single role or list of allowed roles
    
    Usage:
        @require_tenant_role([UserRole.OWNER, UserRole.ADMIN])
        async def admin_endpoint(user: UserClaims = Depends(require_auth)):
            ...
    """
    if isinstance(roles, UserRole):
        allowed_roles = [roles]
    else:
        allowed_roles = roles
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user and tenant from context
            user = get_current_user()
            tenant_id = get_current_tenant_id()
            
            # Check user's role in tenant
            # In a real implementation, this would query the database
            user_role = user.role  # This would come from DB lookup
            
            if user_role not in [role.value for role in allowed_roles]:
                logger.warning(
                    f"Access denied: user {user.sub} with role {user_role} "
                    f"attempted to access {func.__name__} requiring {allowed_roles}"
                )
                raise ForbiddenError(
                    f"This action requires one of these roles: {', '.join(r.value for r in allowed_roles)}"
                )
            
            logger.info(
                f"Access granted: user {user.sub} with role {user_role} "
                f"accessing {func.__name__}"
            )
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def require_workspace_role(roles: Union[WorkspaceRole, List[WorkspaceRole]]) -> Callable:
    """
    Decorator to require specific workspace-level roles
    
    Args:
        roles: Single role or list of allowed roles
    
    Usage:
        @require_workspace_role(WorkspaceRole.CONTRIBUTOR)
        async def update_project(workspace_id: str, user: UserClaims = Depends(require_auth)):
            ...
    """
    if isinstance(roles, WorkspaceRole):
        allowed_roles = [roles]
    else:
        allowed_roles = roles
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract workspace_id from kwargs or args
            workspace_id = kwargs.get('workspace_id')
            if not workspace_id and len(args) > 1:
                # Try to find workspace_id in positional args
                # This is fragile and should be improved
                workspace_id = args[1] if isinstance(args[1], str) else None
            
            if not workspace_id:
                raise ValueError("workspace_id not found in function arguments")
            
            user = get_current_user()
            
            # Check if user has access to workspace
            if workspace_id not in user.workspace_ids:
                logger.warning(
                    f"Access denied: user {user.sub} lacks access to workspace {workspace_id}"
                )
                raise ForbiddenError("You don't have access to this workspace")
            
            # In real implementation, check user's role in workspace from DB
            # For now, we'll assume it's in the claims
            user_workspace_role = WorkspaceRole.CONTRIBUTOR  # This would come from DB
            
            if user_workspace_role not in allowed_roles:
                logger.warning(
                    f"Access denied: user {user.sub} with role {user_workspace_role} "
                    f"in workspace {workspace_id} attempted {func.__name__}"
                )
                raise ForbiddenError(
                    f"This action requires one of these workspace roles: "
                    f"{', '.join(r.value for r in allowed_roles)}"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def require_tenant_plan(plans: Union[TenantPlan, List[TenantPlan]]) -> Callable:
    """
    Decorator to require specific tenant plans (feature gating)
    
    Args:
        plans: Single plan or list of allowed plans
    
    Usage:
        @require_tenant_plan([TenantPlan.TEAM, TenantPlan.ENTERPRISE])
        async def advanced_feature(user: UserClaims = Depends(require_auth)):
            ...
    """
    if isinstance(plans, TenantPlan):
        allowed_plans = [plans]
    else:
        allowed_plans = plans
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            tenant_id = get_current_tenant_id()
            
            # In real implementation, get tenant plan from DB
            # For now, we'll use a placeholder
            tenant_plan = TenantPlan.FREE  # This would come from DB
            
            if tenant_plan not in allowed_plans:
                logger.warning(
                    f"Feature access denied: tenant {tenant_id} with plan {tenant_plan} "
                    f"attempted to use {func.__name__}"
                )
                raise ForbiddenError(
                    f"This feature requires one of these plans: "
                    f"{', '.join(p.value for p in allowed_plans)}. "
                    f"Please upgrade your subscription."
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def track_usage(
    resource_type: ResourceType,
    quantity: Union[int, Callable[..., int]] = 1,
    check_quota: bool = True
) -> Callable:
    """
    Decorator to track resource usage and optionally check quotas
    
    Args:
        resource_type: Type of resource being consumed
        quantity: Fixed quantity or callable to compute quantity
        check_quota: Whether to check quota before allowing action
    
    Usage:
        @track_usage(ResourceType.API_CALLS)
        async def api_endpoint():
            ...
        
        @track_usage(ResourceType.CODE_GENERATIONS, quantity=lambda result: len(result.files))
        async def generate_code() -> GenerationResult:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            user = get_current_user()
            tenant_id = get_current_tenant_id()
            
            # Calculate quantity if it's a callable
            if callable(quantity):
                # For pre-execution quantity calculation, we'll use 1
                # Post-execution calculation happens after the function runs
                pre_quantity = 1
            else:
                pre_quantity = quantity
            
            # Check quota if required
            if check_quota:
                # In real implementation, check against database
                # For now, we'll simulate quota checking
                logger.info(
                    f"Checking quota for tenant {tenant_id}, "
                    f"resource {resource_type}, quantity {pre_quantity}"
                )
                
                # Simulate quota check
                quota_ok = True  # This would be actual quota check
                if not quota_ok:
                    logger.warning(
                        f"Quota exceeded: tenant {tenant_id}, resource {resource_type}"
                    )
                    raise QuotaExceededError(
                        resource_type.value,
                        f"Quota exceeded for {resource_type.value}. "
                        "Please upgrade your plan or wait for quota reset."
                    )
            
            # Execute the function
            try:
                result = await func(*args, **kwargs)
                
                # Calculate actual quantity if needed
                if callable(quantity):
                    try:
                        actual_quantity = quantity(result)
                    except Exception as e:
                        logger.error(f"Error calculating usage quantity: {e}")
                        actual_quantity = 1
                else:
                    actual_quantity = quantity
                
                # Track successful usage
                execution_time = time.time() - start_time
                logger.info(
                    f"Usage tracked: tenant {tenant_id}, user {user.sub}, "
                    f"resource {resource_type}, quantity {actual_quantity}, "
                    f"execution_time {execution_time:.2f}s"
                )
                
                # In real implementation, write to database
                # await track_usage_event(tenant_id, user.sub, resource_type, actual_quantity)
                
                return result
                
            except Exception as e:
                # Track failed usage (might still consume some resources)
                logger.error(
                    f"Function failed but usage tracked: {func.__name__}, error: {e}"
                )
                # Could track partial usage here
                raise
        
        return wrapper
    
    return decorator


def require_permission(permission: str) -> Callable:
    """
    Decorator to require specific permission
    
    Args:
        permission: Required permission string
    
    Usage:
        @require_permission("projects.delete")
        async def delete_project(project_id: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            user = get_current_user()
            
            if not user.has_permission(permission):
                logger.warning(
                    f"Permission denied: user {user.sub} lacks permission {permission}"
                )
                raise ForbiddenError(f"Missing required permission: {permission}")
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def combine_decorators(*decorators) -> Callable:
    """
    Combine multiple decorators into one
    
    Usage:
        @combine_decorators(
            require_tenant_role(UserRole.ADMIN),
            track_usage(ResourceType.API_CALLS),
            require_tenant_plan(TenantPlan.TEAM)
        )
        async def admin_api():
            ...
    """
    def decorator(func: Callable) -> Callable:
        for dec in reversed(decorators):
            func = dec(func)
        return func
    
    return decorator


# Convenience decorators for common patterns
owner_only = require_tenant_role(UserRole.OWNER)
admin_only = require_tenant_role([UserRole.OWNER, UserRole.ADMIN])
member_only = require_tenant_role([UserRole.OWNER, UserRole.ADMIN, UserRole.MEMBER])

workspace_admin_only = require_workspace_role([WorkspaceRole.OWNER, WorkspaceRole.ADMIN])
workspace_contributor = require_workspace_role([
    WorkspaceRole.OWNER, 
    WorkspaceRole.ADMIN, 
    WorkspaceRole.CONTRIBUTOR
])

paid_plans_only = require_tenant_plan([TenantPlan.TEAM, TenantPlan.ENTERPRISE])
enterprise_only = require_tenant_plan(TenantPlan.ENTERPRISE)


# Example usage patterns
if __name__ == "__main__":
    # Example 1: Simple role check
    @admin_only
    async def delete_user(user_id: str):
        """Only admins can delete users"""
        pass
    
    # Example 2: Workspace access with usage tracking
    @workspace_contributor
    @track_usage(ResourceType.CODE_GENERATIONS)
    async def generate_code(workspace_id: str, prompt: str):
        """Contributors can generate code, usage is tracked"""
        pass
    
    # Example 3: Feature gating with quota check
    @paid_plans_only
    @track_usage(ResourceType.API_CALLS, check_quota=True)
    async def advanced_api_endpoint():
        """Only available for paid plans, with quota enforcement"""
        pass
    
    # Example 4: Complex authorization
    @combine_decorators(
        require_tenant_role(UserRole.ADMIN),
        require_tenant_plan([TenantPlan.TEAM, TenantPlan.ENTERPRISE]),
        track_usage(ResourceType.API_CALLS, quantity=10),  # Expensive operation
        require_permission("analytics.export")
    )
    async def export_analytics():
        """Multiple authorization checks"""
        pass