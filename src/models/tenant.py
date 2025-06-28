"""
SQLAlchemy models for multi-tenancy
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from uuid import uuid4

from sqlalchemy import (
    Column, String, DateTime, Boolean, ForeignKey, 
    UniqueConstraint, Index, Enum as SQLEnum, DECIMAL
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func

Base = declarative_base()


class TenantPlan(str, Enum):
    """Tenant subscription plans"""
    FREE = "free"
    TEAM = "team"
    ENTERPRISE = "enterprise"


class UserRole(str, Enum):
    """Roles a user can have in a tenant"""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    GUEST = "guest"


class WorkspaceRole(str, Enum):
    """Roles a user can have in a workspace"""
    OWNER = "owner"
    ADMIN = "admin"
    CONTRIBUTOR = "contributor"
    VIEWER = "viewer"


class ResourceType(str, Enum):
    """Types of resources tracked for usage"""
    API_CALLS = "api_calls"
    CODE_GENERATIONS = "code_generations"
    STORAGE_BYTES = "storage_bytes"
    COMPUTE_SECONDS = "compute_seconds"
    VECTOR_SEARCHES = "vector_searches"
    LLM_TOKENS = "llm_tokens"


class QuotaPeriod(str, Enum):
    """Time periods for quota limits"""
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    MONTH = "month"


class Tenant(Base):
    """Organization using the platform"""
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    azure_ad_tenant_id = Column(String(255), unique=True, index=True)
    plan = Column(SQLEnum(TenantPlan), nullable=False, default=TenantPlan.FREE)
    settings = Column(JSONB, default={})
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    workspaces = relationship("Workspace", back_populates="tenant", cascade="all, delete-orphan")
    users = relationship("TenantUser", back_populates="tenant", cascade="all, delete-orphan")
    quotas = relationship("TenantQuota", back_populates="tenant", cascade="all, delete-orphan")
    usage_events = relationship("UsageEvent", back_populates="tenant", cascade="all, delete-orphan")

    @validates('name')
    def validate_name(self, key, name):
        if not name or len(name.strip()) < 2:
            raise ValueError("Tenant name must be at least 2 characters")
        return name.strip()

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value with default"""
        return self.settings.get(key, default) if self.settings else default

    def update_setting(self, key: str, value: Any):
        """Update a single setting"""
        if self.settings is None:
            self.settings = {}
        self.settings[key] = value

    def is_owner(self, user_id: str) -> bool:
        """Check if user is owner of tenant"""
        return any(tu.user_id == user_id and tu.role == UserRole.OWNER 
                  for tu in self.users if tu.is_active)

    def can_add_users(self) -> bool:
        """Check if tenant can add more users based on plan"""
        limits = {
            TenantPlan.FREE: 5,
            TenantPlan.TEAM: 50,
            TenantPlan.ENTERPRISE: None  # Unlimited
        }
        limit = limits.get(self.plan)
        if limit is None:
            return True
        active_users = sum(1 for tu in self.users if tu.is_active)
        return active_users < limit

    def __repr__(self):
        return f"<Tenant(id={self.id}, name='{self.name}', plan={self.plan})>"


class Workspace(Base):
    """Isolated work area within a tenant"""
    __tablename__ = "workspaces"
    __table_args__ = (
        UniqueConstraint('tenant_id', 'name'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String)
    settings = Column(JSONB, default={})
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    tenant = relationship("Tenant", back_populates="workspaces")
    members = relationship("WorkspaceMember", back_populates="workspace", cascade="all, delete-orphan")

    @validates('name')
    def validate_name(self, key, name):
        if not name or len(name.strip()) < 2:
            raise ValueError("Workspace name must be at least 2 characters")
        return name.strip()

    def has_member(self, user_id: str) -> bool:
        """Check if user is member of workspace"""
        return any(m.user_id == user_id and m.is_active for m in self.members)

    def get_member_role(self, user_id: str) -> Optional[WorkspaceRole]:
        """Get user's role in workspace"""
        member = next((m for m in self.members if m.user_id == user_id and m.is_active), None)
        return member.role if member else None

    def __repr__(self):
        return f"<Workspace(id={self.id}, name='{self.name}', tenant_id={self.tenant_id})>"


class User(Base):
    """Platform users that can belong to multiple tenants"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    azure_ad_object_id = Column(String(255), unique=True, index=True)
    profile = Column(JSONB, default={})
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    tenants = relationship("TenantUser", back_populates="user")
    workspaces = relationship("WorkspaceMember", back_populates="user")
    usage_events = relationship("UsageEvent", back_populates="user")

    @validates('email')
    def validate_email(self, key, email):
        if not email or '@' not in email:
            raise ValueError("Invalid email address")
        return email.lower().strip()

    def get_tenants(self) -> List['Tenant']:
        """Get all active tenants for user"""
        return [tu.tenant for tu in self.tenants if tu.is_active]

    def get_tenant_role(self, tenant_id: str) -> Optional[UserRole]:
        """Get user's role in a specific tenant"""
        tenant_user = next((tu for tu in self.tenants 
                           if tu.tenant_id == tenant_id and tu.is_active), None)
        return tenant_user.role if tenant_user else None

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"


class TenantUser(Base):
    """Maps users to tenants with roles"""
    __tablename__ = "tenant_users"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True, index=True)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.MEMBER)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    invited_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    is_active = Column(Boolean, default=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    user = relationship("User", back_populates="tenants")
    inviter = relationship("User", foreign_keys=[invited_by])

    def can_invite_users(self) -> bool:
        """Check if this user can invite others"""
        return self.role in [UserRole.OWNER, UserRole.ADMIN]

    def can_manage_workspaces(self) -> bool:
        """Check if this user can create/delete workspaces"""
        return self.role in [UserRole.OWNER, UserRole.ADMIN]

    def __repr__(self):
        return f"<TenantUser(tenant_id={self.tenant_id}, user_id={self.user_id}, role={self.role})>"


class WorkspaceMember(Base):
    """Maps users to workspaces with permissions"""
    __tablename__ = "workspace_members"

    workspace_id = Column(UUID(as_uuid=True), ForeignKey('workspaces.id', ondelete='CASCADE'), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True, index=True)
    role = Column(SQLEnum(WorkspaceRole), nullable=False, default=WorkspaceRole.VIEWER)
    permissions = Column(JSONB, default={})
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)

    # Relationships
    workspace = relationship("Workspace", back_populates="members")
    user = relationship("User", back_populates="workspaces")

    def has_permission(self, permission: str) -> bool:
        """Check if member has specific permission"""
        # Role-based defaults
        role_permissions = {
            WorkspaceRole.OWNER: {"read", "write", "delete", "admin"},
            WorkspaceRole.ADMIN: {"read", "write", "delete"},
            WorkspaceRole.CONTRIBUTOR: {"read", "write"},
            WorkspaceRole.VIEWER: {"read"}
        }
        
        default_perms = role_permissions.get(self.role, set())
        custom_perms = set(self.permissions.get("allowed", [])) if self.permissions else set()
        blocked_perms = set(self.permissions.get("blocked", [])) if self.permissions else set()
        
        return permission in (default_perms | custom_perms) - blocked_perms

    def __repr__(self):
        return f"<WorkspaceMember(workspace_id={self.workspace_id}, user_id={self.user_id}, role={self.role})>"


class UsageEvent(Base):
    """Detailed log of all resource usage events"""
    __tablename__ = "usage_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), index=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey('workspaces.id', ondelete='SET NULL'))
    event_type = Column(SQLEnum(ResourceType), nullable=False)
    quantity = Column(DECIMAL(20, 4), nullable=False, default=1)
    resource_id = Column(String(255))
    metadata = Column(JSONB, default={})
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="usage_events")
    user = relationship("User", back_populates="usage_events")
    workspace = relationship("Workspace")

    def __repr__(self):
        return f"<UsageEvent(id={self.id}, tenant_id={self.tenant_id}, type={self.event_type}, quantity={self.quantity})>"


class TenantQuota(Base):
    """Configured quotas per tenant"""
    __tablename__ = "tenant_quotas"
    __table_args__ = (
        UniqueConstraint('tenant_id', 'resource_type', 'period'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    resource_type = Column(SQLEnum(ResourceType), nullable=False)
    limit_value = Column(DECIMAL(20, 4), nullable=False)
    period = Column(SQLEnum(QuotaPeriod), nullable=False)
    reset_at = Column(DateTime(timezone=True))
    is_hard_limit = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    tenant = relationship("Tenant", back_populates="quotas")

    def is_exceeded(self, current_usage: float) -> bool:
        """Check if quota is exceeded"""
        return current_usage >= float(self.limit_value)

    def remaining(self, current_usage: float) -> float:
        """Calculate remaining quota"""
        return max(0, float(self.limit_value) - current_usage)

    def __repr__(self):
        return f"<TenantQuota(tenant_id={self.tenant_id}, type={self.resource_type}, limit={self.limit_value}, period={self.period})>"


class UsageSummary(Base):
    """Aggregated usage data for quick quota checks"""
    __tablename__ = "usage_summaries"
    __table_args__ = (
        UniqueConstraint('tenant_id', 'resource_type', 'period', 'period_start'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    resource_type = Column(SQLEnum(ResourceType), nullable=False)
    period = Column(SQLEnum(QuotaPeriod), nullable=False)
    count = Column(DECIMAL(20, 4), nullable=False, default=0)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    last_updated = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    tenant = relationship("Tenant")

    def __repr__(self):
        return f"<UsageSummary(tenant_id={self.tenant_id}, type={self.resource_type}, count={self.count}, period={self.period})>"


# Index definitions
Index('idx_usage_events_tenant_timestamp', UsageEvent.tenant_id, UsageEvent.timestamp.desc())
Index('idx_tenant_quotas_lookup', TenantQuota.tenant_id, TenantQuota.resource_type, TenantQuota.period)
Index('idx_usage_summaries_lookup', UsageSummary.tenant_id, UsageSummary.resource_type, UsageSummary.period, UsageSummary.period_start)