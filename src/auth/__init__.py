"""
Authentication and authorization module for multi-tenancy
"""

from .azure_ad_b2c import (
    AzureADB2CConfig,
    AzureADB2CClient,
    UserClaims,
    TokenResponse,
    get_azure_ad_client
)

from .middleware import (
    JWTAuthMiddleware,
    TenantContextMiddleware,
    AuthPerformanceMiddleware,
    AuthenticationError,
    AuthorizationError,
    require_auth,
    require_tenant,
    get_current_user,
    get_current_tenant_id
)

from .decorators import (
    require_auth_decorator,
    require_tenant_role,
    require_workspace_role,
    require_tenant_plan,
    track_usage,
    require_permission,
    combine_decorators,
    # Convenience decorators
    owner_only,
    admin_only,
    member_only,
    workspace_admin_only,
    workspace_contributor,
    paid_plans_only,
    enterprise_only,
    # Errors
    ForbiddenError,
    QuotaExceededError
)

__all__ = [
    # Azure AD B2C
    'AzureADB2CConfig',
    'AzureADB2CClient',
    'UserClaims',
    'TokenResponse',
    'get_azure_ad_client',
    
    # Middleware
    'JWTAuthMiddleware',
    'TenantContextMiddleware',
    'AuthPerformanceMiddleware',
    'AuthenticationError',
    'AuthorizationError',
    'require_auth',
    'require_tenant',
    'get_current_user',
    'get_current_tenant_id',
    
    # Decorators
    'require_auth_decorator',
    'require_tenant_role',
    'require_workspace_role',
    'require_tenant_plan',
    'track_usage',
    'require_permission',
    'combine_decorators',
    
    # Convenience decorators
    'owner_only',
    'admin_only',
    'member_only',
    'workspace_admin_only',
    'workspace_contributor',
    'paid_plans_only',
    'enterprise_only',
    
    # Errors
    'ForbiddenError',
    'QuotaExceededError'
]