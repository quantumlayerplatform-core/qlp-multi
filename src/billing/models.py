"""Billing and subscription models"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Column, String, DateTime, DECIMAL as SQLDecimal, 
    Integer, ForeignKey, Enum as SQLEnum, Boolean,
    UniqueConstraint, Index, JSON
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from src.common.database import Base


class SubscriptionTier(str, Enum):
    """Subscription tier levels"""
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, Enum):
    """Subscription status"""
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    TRIALING = "trialing"


class UserRole(str, Enum):
    """User roles within organization"""
    OWNER = "owner"
    ADMIN = "admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"


class ActionType(str, Enum):
    """Billable action types"""
    CODE_GENERATION = "code_generation"
    VALIDATION = "validation"
    EXPORT = "export"
    API_CALL = "api_call"
    STORAGE = "storage"


class Organization(Base):
    """Organization (tenant) model"""
    __tablename__ = "organizations"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False)
    
    # Subscription info
    subscription_tier = Column(SQLEnum(SubscriptionTier), default=SubscriptionTier.FREE)
    subscription_status = Column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE)
    stripe_customer_id = Column(String(255), unique=True, nullable=True)
    
    # Settings
    settings = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("User", back_populates="organization")
    subscriptions = relationship("Subscription", back_populates="organization")
    usage_tracking = relationship("UsageTracking", back_populates="organization")
    
    __table_args__ = (
        Index("idx_org_stripe_customer", "stripe_customer_id"),
    )


class User(Base):
    """User model with organization relationship"""
    __tablename__ = "users"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    
    # Organization relationship
    organization_id = Column(PGUUID(as_uuid=True), ForeignKey("organizations.id"))
    role = Column(SQLEnum(UserRole), default=UserRole.DEVELOPER)
    
    # Profile
    full_name = Column(String(255))
    avatar_url = Column(String(500))
    
    # Status
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime)
    
    # Relationships
    organization = relationship("Organization", back_populates="users")
    api_keys = relationship("APIKey", back_populates="user")
    
    __table_args__ = (
        Index("idx_user_email", "email"),
        Index("idx_user_org", "organization_id"),
    )


class Subscription(Base):
    """Subscription details"""
    __tablename__ = "subscriptions"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id = Column(PGUUID(as_uuid=True), ForeignKey("organizations.id"))
    
    # Stripe info
    stripe_subscription_id = Column(String(255), unique=True)
    stripe_price_id = Column(String(255))
    
    # Status
    status = Column(SQLEnum(SubscriptionStatus))
    current_period_start = Column(DateTime)
    current_period_end = Column(DateTime)
    cancel_at_period_end = Column(Boolean, default=False)
    
    # Billing
    amount = Column(SQLDecimal(10, 2))
    currency = Column(String(3), default="USD")
    interval = Column(String(20))  # month, year
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization", back_populates="subscriptions")
    
    __table_args__ = (
        Index("idx_sub_stripe", "stripe_subscription_id"),
    )


class UsageTracking(Base):
    """Track all billable usage"""
    __tablename__ = "usage_tracking"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id = Column(PGUUID(as_uuid=True), ForeignKey("organizations.id"))
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    
    # What was done
    action_type = Column(SQLEnum(ActionType), nullable=False)
    resource_type = Column(String(50))  # T0, T1, T2, T3, etc.
    resource_id = Column(String(255))  # capsule_id, etc.
    
    # Usage metrics
    tokens_used = Column(Integer, default=0)
    compute_time_ms = Column(Integer, default=0)
    storage_bytes = Column(Integer, default=0)
    
    # Cost
    cost = Column(SQLDecimal(10, 4), nullable=False)
    
    # Metadata
    meta_data = Column(JSON, default=dict)
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    organization = relationship("Organization", back_populates="usage_tracking")
    user = relationship("User")
    
    __table_args__ = (
        Index("idx_usage_org_time", "organization_id", "timestamp"),
        Index("idx_usage_user_time", "user_id", "timestamp"),
    )


class UsageQuota(Base):
    """Usage quotas per organization"""
    __tablename__ = "usage_quotas"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id = Column(PGUUID(as_uuid=True), ForeignKey("organizations.id"))
    
    # Quota type
    quota_type = Column(String(50), nullable=False)  # generations, storage, api_calls
    period = Column(String(20), default="month")  # month, day, hour
    
    # Limits
    limit = Column(Integer, nullable=False)
    used = Column(Integer, default=0)
    
    # Reset
    reset_at = Column(DateTime, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("organization_id", "quota_type", name="uq_org_quota"),
        Index("idx_quota_reset", "reset_at"),
    )


class APIKey(Base):
    """API keys for programmatic access"""
    __tablename__ = "api_keys"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    
    # Key info
    name = Column(String(255), nullable=False)
    key_hash = Column(String(255), nullable=False)  # Only store hash
    key_prefix = Column(String(10), nullable=False)  # For display: "qlp_..."
    
    # Permissions
    scopes = Column(JSON, default=list)  # ["read", "write", "admin"]
    
    # Status
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime)
    expires_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    revoked_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    
    __table_args__ = (
        Index("idx_api_key_prefix", "key_prefix"),
    )


