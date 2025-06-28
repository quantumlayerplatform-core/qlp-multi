"""
Tenant service for managing organizations and users
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4
from decimal import Decimal

from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.base import (
    BaseService, ServiceError, NotFoundError, ValidationError,
    AuthorizationError, DomainEvent
)
from src.services.events import (
    TenantCreated, TenantUpdated, TenantDeleted,
    UserInvited, UserJoined, UserRemoved, RoleChanged,
    PlanUpgraded, publish_event
)
from src.services.usage_tracking_service import get_usage_service
from src.models.tenant import (
    Tenant, User, TenantUser, Workspace,
    TenantPlan, UserRole, ResourceType
)
from src.common.logger import get_logger

logger = get_logger(__name__)


class TenantUpdate:
    """DTO for tenant updates"""
    def __init__(
        self,
        name: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None,
        is_active: Optional[bool] = None
    ):
        self.name = name
        self.settings = settings
        self.is_active = is_active


class Invitation:
    """User invitation details"""
    def __init__(
        self,
        id: str,
        tenant_id: str,
        email: str,
        role: UserRole,
        invitation_code: str,
        invited_by: str,
        expires_at: datetime,
        created_at: datetime
    ):
        self.id = id
        self.tenant_id = tenant_id
        self.email = email
        self.role = role
        self.invitation_code = invitation_code
        self.invited_by = invited_by
        self.expires_at = expires_at
        self.created_at = created_at


class TenantStats:
    """Tenant statistics"""
    def __init__(self):
        self.user_count = 0
        self.active_user_count = 0
        self.workspace_count = 0
        self.storage_used = Decimal(0)
        self.api_calls_today = 0
        self.code_generations_month = 0
        self.last_activity = None


class TenantService(BaseService):
    """
    Service for managing tenants and their users
    
    Features:
    - Tenant lifecycle management
    - User invitation and management
    - Plan upgrades/downgrades
    - Settings management
    - Analytics and reporting
    """
    
    def __init__(self):
        super().__init__()
        self._invitations: Dict[str, Invitation] = {}  # In-memory for now
    
    # Tenant Lifecycle Management
    
    async def create_tenant(
        self,
        name: str,
        owner_email: str,
        plan: TenantPlan = TenantPlan.FREE,
        settings: Optional[Dict[str, Any]] = None
    ) -> Tenant:
        """
        Create a new tenant with owner
        
        Args:
            name: Tenant name
            owner_email: Email of the owner
            plan: Subscription plan
            settings: Initial settings
        
        Returns:
            Created tenant
        """
        # Validate inputs
        self.validate_required_fields(
            {"name": name, "owner_email": owner_email},
            ["name", "owner_email"]
        )
        
        if "@" not in owner_email:
            raise ValidationError("Invalid email address", field="owner_email")
        
        async with await self.get_db() as db:
            # Check if tenant name is unique
            existing = await db.execute(
                select(Tenant).where(Tenant.name == name)
            )
            if existing.scalar_one_or_none():
                raise ValidationError(
                    f"Tenant name '{name}' already exists",
                    field="name"
                )
            
            # Start transaction
            async with db.begin():
                # Create tenant
                tenant = Tenant(
                    name=name,
                    plan=plan,
                    settings=settings or {},
                    is_active=True
                )
                db.add(tenant)
                await db.flush()
                
                # Find or create owner user
                user_result = await db.execute(
                    select(User).where(User.email == owner_email.lower())
                )
                owner = user_result.scalar_one_or_none()
                
                if not owner:
                    owner = User(
                        email=owner_email.lower(),
                        profile={"name": owner_email.split("@")[0]},
                        is_active=True
                    )
                    db.add(owner)
                    await db.flush()
                
                # Create tenant-user relationship
                tenant_user = TenantUser(
                    tenant_id=tenant.id,
                    user_id=owner.id,
                    role=UserRole.OWNER,
                    is_active=True
                )
                db.add(tenant_user)
                
                # Create default workspace
                workspace = Workspace(
                    tenant_id=tenant.id,
                    name="Default Workspace",
                    description="Default workspace for all projects",
                    is_active=True
                )
                db.add(workspace)
                
                await db.commit()
            
            # Emit events
            await publish_event(TenantCreated(
                tenant_id=str(tenant.id),
                name=name,
                plan=plan.value,
                owner_email=owner_email
            ))
            
            # Log audit
            await self.log_audit(
                action="create",
                entity_type="tenant",
                entity_id=str(tenant.id),
                changes={"name": name, "plan": plan.value}
            )
            
            logger.info(
                f"Tenant created",
                tenant_id=str(tenant.id),
                name=name,
                plan=plan.value
            )
            
            return tenant
    
    async def update_tenant(
        self,
        tenant_id: str,
        updates: TenantUpdate
    ) -> Tenant:
        """Update tenant details"""
        tenant = await self.get_current_tenant()
        if not tenant or str(tenant.id) != tenant_id:
            raise AuthorizationError("Cannot update other tenants")
        
        # Check permissions
        tenant_user = await self.get_current_tenant_user()
        if not tenant_user or tenant_user.role not in [UserRole.OWNER, UserRole.ADMIN]:
            raise AuthorizationError("Only owners and admins can update tenant")
        
        changes = {}
        
        async with await self.get_db() as db:
            # Get fresh tenant instance
            result = await db.execute(
                select(Tenant).where(Tenant.id == tenant_id)
            )
            tenant = result.scalar_one_or_none()
            
            if not tenant:
                raise NotFoundError("tenant", tenant_id)
            
            # Apply updates
            if updates.name and updates.name != tenant.name:
                # Check name uniqueness
                existing = await db.execute(
                    select(Tenant).where(
                        and_(
                            Tenant.name == updates.name,
                            Tenant.id != tenant_id
                        )
                    )
                )
                if existing.scalar_one_or_none():
                    raise ValidationError(
                        f"Tenant name '{updates.name}' already exists",
                        field="name"
                    )
                
                changes["name"] = {"old": tenant.name, "new": updates.name}
                tenant.name = updates.name
            
            if updates.settings is not None:
                changes["settings"] = {"old": tenant.settings, "new": updates.settings}
                tenant.settings = updates.settings
            
            if updates.is_active is not None and updates.is_active != tenant.is_active:
                changes["is_active"] = {"old": tenant.is_active, "new": updates.is_active}
                tenant.is_active = updates.is_active
            
            await db.commit()
        
        if changes:
            # Emit event
            await publish_event(TenantUpdated(
                tenant_id=tenant_id,
                changes=changes
            ))
            
            # Log audit
            await self.log_audit(
                action="update",
                entity_type="tenant",
                entity_id=tenant_id,
                changes=changes
            )
        
        return tenant
    
    async def delete_tenant(self, tenant_id: str) -> None:
        """
        Soft delete tenant with 30-day retention
        
        Only tenant owner can delete
        """
        tenant = await self.get_current_tenant()
        if not tenant or str(tenant.id) != tenant_id:
            raise AuthorizationError("Cannot delete other tenants")
        
        # Check if current user is owner
        tenant_user = await self.get_current_tenant_user()
        if not tenant_user or tenant_user.role != UserRole.OWNER:
            raise AuthorizationError("Only tenant owner can delete tenant")
        
        user = await self.get_current_user()
        
        async with await self.get_db() as db:
            result = await db.execute(
                select(Tenant).where(Tenant.id == tenant_id)
            )
            tenant = result.scalar_one_or_none()
            
            if not tenant:
                raise NotFoundError("tenant", tenant_id)
            
            # Soft delete
            tenant.is_active = False
            tenant.settings["deleted_at"] = datetime.now(timezone.utc).isoformat()
            tenant.settings["deleted_by"] = str(user.id)
            tenant.settings["retention_until"] = (
                datetime.now(timezone.utc) + timedelta(days=30)
            ).isoformat()
            
            await db.commit()
        
        # Emit event
        await publish_event(TenantDeleted(
            tenant_id=tenant_id,
            deleted_by=str(user.id)
        ))
        
        # Log audit
        await self.log_audit(
            action="delete",
            entity_type="tenant",
            entity_id=tenant_id
        )
        
        logger.info(f"Tenant marked for deletion", tenant_id=tenant_id)
    
    # User Management
    
    async def invite_user(
        self,
        email: str,
        role: UserRole,
        workspace_ids: Optional[List[str]] = None
    ) -> Invitation:
        """
        Invite user to tenant
        
        Args:
            email: User email
            role: Role to assign
            workspace_ids: Optional workspace access
        
        Returns:
            Invitation details
        """
        # Validate permissions
        tenant_user = await self.get_current_tenant_user()
        if not tenant_user or not tenant_user.can_invite_users():
            raise AuthorizationError("You don't have permission to invite users")
        
        tenant = await self.get_current_tenant()
        user = await self.get_current_user()
        
        # Check tenant user limit
        if not tenant.can_add_users():
            raise ValidationError(
                "Tenant has reached user limit for current plan"
            )
        
        # Validate email
        if "@" not in email:
            raise ValidationError("Invalid email address", field="email")
        
        # Check if user already exists in tenant
        async with await self.get_db() as db:
            existing = await db.execute(
                select(TenantUser).join(User).where(
                    and_(
                        User.email == email.lower(),
                        TenantUser.tenant_id == tenant.id,
                        TenantUser.is_active == True
                    )
                )
            )
            if existing.scalar_one_or_none():
                raise ValidationError(
                    f"User {email} is already a member of this tenant"
                )
        
        # Create invitation
        invitation = Invitation(
            id=str(uuid4()),
            tenant_id=str(tenant.id),
            email=email.lower(),
            role=role,
            invitation_code=secrets.token_urlsafe(32),
            invited_by=str(user.id),
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            created_at=datetime.now(timezone.utc)
        )
        
        # Store invitation (in production, would use database)
        self._invitations[invitation.invitation_code] = invitation
        
        # Emit event
        await publish_event(UserInvited(
            tenant_id=str(tenant.id),
            email=email,
            role=role.value,
            invited_by=str(user.id),
            invitation_code=invitation.invitation_code
        ))
        
        # Log audit
        await self.log_audit(
            action="invite",
            entity_type="user",
            entity_id=email,
            metadata={
                "role": role.value,
                "invitation_code": invitation.invitation_code
            }
        )
        
        logger.info(
            f"User invited",
            email=email,
            tenant_id=str(tenant.id),
            role=role.value
        )
        
        return invitation
    
    async def accept_invitation(
        self,
        invitation_code: str,
        user_id: str
    ) -> TenantUser:
        """Accept invitation and join tenant"""
        # Get invitation
        invitation = self._invitations.get(invitation_code)
        if not invitation:
            raise NotFoundError("invitation", invitation_code)
        
        # Check expiration
        if datetime.now(timezone.utc) > invitation.expires_at:
            raise ValidationError("Invitation has expired")
        
        async with await self.get_db() as db:
            # Get user
            result = await db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                raise NotFoundError("user", user_id)
            
            # Verify email matches
            if user.email != invitation.email:
                raise ValidationError(
                    "Invitation email doesn't match user email"
                )
            
            # Check if already member
            existing = await db.execute(
                select(TenantUser).where(
                    and_(
                        TenantUser.tenant_id == invitation.tenant_id,
                        TenantUser.user_id == user_id
                    )
                )
            )
            tenant_user = existing.scalar_one_or_none()
            
            if tenant_user and tenant_user.is_active:
                raise ValidationError("User is already a member")
            
            # Create or reactivate membership
            if tenant_user:
                tenant_user.is_active = True
                tenant_user.role = invitation.role
                tenant_user.joined_at = datetime.now(timezone.utc)
            else:
                tenant_user = TenantUser(
                    tenant_id=UUID(invitation.tenant_id),
                    user_id=user.id,
                    role=invitation.role,
                    invited_by=UUID(invitation.invited_by),
                    is_active=True
                )
                db.add(tenant_user)
            
            await db.commit()
        
        # Remove used invitation
        del self._invitations[invitation_code]
        
        # Emit event
        await publish_event(UserJoined(
            tenant_id=invitation.tenant_id,
            user_id=str(user.id),
            role=invitation.role.value
        ))
        
        # Log audit
        await self.log_audit(
            action="join",
            entity_type="tenant",
            entity_id=invitation.tenant_id,
            metadata={"user_id": str(user.id), "role": invitation.role.value}
        )
        
        return tenant_user
    
    async def update_user_role(
        self,
        user_id: str,
        new_role: UserRole
    ) -> TenantUser:
        """Update user's role in tenant"""
        # Check permissions
        current_tenant_user = await self.get_current_tenant_user()
        if not current_tenant_user or current_tenant_user.role != UserRole.OWNER:
            raise AuthorizationError("Only owners can change user roles")
        
        tenant = await self.get_current_tenant()
        current_user = await self.get_current_user()
        
        async with await self.get_db() as db:
            # Get tenant user
            result = await db.execute(
                select(TenantUser).where(
                    and_(
                        TenantUser.tenant_id == tenant.id,
                        TenantUser.user_id == user_id,
                        TenantUser.is_active == True
                    )
                )
            )
            tenant_user = result.scalar_one_or_none()
            
            if not tenant_user:
                raise NotFoundError("tenant_user", user_id)
            
            # Cannot change owner role if they're the only owner
            if tenant_user.role == UserRole.OWNER:
                owner_count = await db.execute(
                    select(func.count()).select_from(TenantUser).where(
                        and_(
                            TenantUser.tenant_id == tenant.id,
                            TenantUser.role == UserRole.OWNER,
                            TenantUser.is_active == True
                        )
                    )
                )
                if owner_count.scalar() == 1:
                    raise ValidationError(
                        "Cannot change role of the only owner"
                    )
            
            old_role = tenant_user.role
            tenant_user.role = new_role
            
            await db.commit()
        
        # Emit event
        await publish_event(RoleChanged(
            tenant_id=str(tenant.id),
            user_id=user_id,
            old_role=old_role.value,
            new_role=new_role.value,
            changed_by=str(current_user.id)
        ))
        
        # Log audit
        await self.log_audit(
            action="role_change",
            entity_type="user",
            entity_id=user_id,
            changes={
                "role": {"old": old_role.value, "new": new_role.value}
            }
        )
        
        return tenant_user
    
    async def remove_user(self, user_id: str) -> None:
        """Remove user from tenant"""
        # Check permissions
        current_tenant_user = await self.get_current_tenant_user()
        if not current_tenant_user or current_tenant_user.role not in [
            UserRole.OWNER, UserRole.ADMIN
        ]:
            raise AuthorizationError(
                "Only owners and admins can remove users"
            )
        
        tenant = await self.get_current_tenant()
        current_user = await self.get_current_user()
        
        # Cannot remove yourself
        if str(current_user.id) == user_id:
            raise ValidationError("Cannot remove yourself from tenant")
        
        async with await self.get_db() as db:
            # Get tenant user
            result = await db.execute(
                select(TenantUser).where(
                    and_(
                        TenantUser.tenant_id == tenant.id,
                        TenantUser.user_id == user_id,
                        TenantUser.is_active == True
                    )
                )
            )
            tenant_user = result.scalar_one_or_none()
            
            if not tenant_user:
                raise NotFoundError("tenant_user", user_id)
            
            # Cannot remove last owner
            if tenant_user.role == UserRole.OWNER:
                owner_count = await db.execute(
                    select(func.count()).select_from(TenantUser).where(
                        and_(
                            TenantUser.tenant_id == tenant.id,
                            TenantUser.role == UserRole.OWNER,
                            TenantUser.is_active == True
                        )
                    )
                )
                if owner_count.scalar() == 1:
                    raise ValidationError("Cannot remove the only owner")
            
            # Soft delete
            tenant_user.is_active = False
            
            await db.commit()
        
        # Emit event
        await publish_event(UserRemoved(
            tenant_id=str(tenant.id),
            user_id=user_id,
            removed_by=str(current_user.id)
        ))
        
        # Log audit
        await self.log_audit(
            action="remove",
            entity_type="user",
            entity_id=user_id,
            metadata={"removed_by": str(current_user.id)}
        )
    
    # Plan Management
    
    async def upgrade_plan(
        self,
        new_plan: TenantPlan,
        payment_method: Optional[str] = None
    ) -> Tenant:
        """Upgrade tenant plan"""
        # Check permissions
        tenant_user = await self.get_current_tenant_user()
        if not tenant_user or tenant_user.role != UserRole.OWNER:
            raise AuthorizationError("Only owners can change plans")
        
        tenant = await self.get_current_tenant()
        user = await self.get_current_user()
        
        if tenant.plan == new_plan:
            raise ValidationError("Already on this plan")
        
        if new_plan.value < tenant.plan.value:
            # This is a downgrade, use downgrade_plan instead
            return await self.downgrade_plan(new_plan)
        
        old_plan = tenant.plan
        
        async with await self.get_db() as db:
            # Update plan
            result = await db.execute(
                select(Tenant).where(Tenant.id == tenant.id)
            )
            tenant = result.scalar_one()
            
            tenant.plan = new_plan
            tenant.settings["plan_changed_at"] = datetime.now(timezone.utc).isoformat()
            tenant.settings["plan_changed_by"] = str(user.id)
            
            if payment_method:
                tenant.settings["payment_method"] = payment_method
            
            await db.commit()
        
        # Update quotas for new plan
        usage_service = await get_usage_service()
        # This would update all resource quotas based on new plan
        
        # Emit event
        await publish_event(PlanUpgraded(
            tenant_id=str(tenant.id),
            old_plan=old_plan.value,
            new_plan=new_plan.value,
            upgraded_by=str(user.id)
        ))
        
        # Log audit
        await self.log_audit(
            action="plan_upgrade",
            entity_type="tenant",
            entity_id=str(tenant.id),
            changes={
                "plan": {"old": old_plan.value, "new": new_plan.value}
            }
        )
        
        logger.info(
            f"Plan upgraded",
            tenant_id=str(tenant.id),
            old_plan=old_plan.value,
            new_plan=new_plan.value
        )
        
        return tenant
    
    async def downgrade_plan(self, new_plan: TenantPlan) -> Tenant:
        """Downgrade tenant plan after checking resource usage"""
        tenant = await self.get_current_tenant()
        
        # Check current usage against new plan limits
        usage_service = await get_usage_service()
        
        # Get current usage for all resources
        for resource_type in ResourceType:
            usage_summary = await usage_service.get_usage_summary()
            # Check if current usage exceeds new plan limits
            # This is simplified - would need actual limit checking
        
        # If checks pass, proceed with downgrade
        return await self.upgrade_plan(new_plan)
    
    # Settings & Features
    
    async def update_settings(
        self,
        settings: Dict[str, Any]
    ) -> Tenant:
        """Update tenant settings"""
        updates = TenantUpdate(settings=settings)
        return await self.update_tenant(
            str((await self.get_current_tenant()).id),
            updates
        )
    
    async def enable_feature(self, feature: str) -> None:
        """Enable a feature for tenant"""
        tenant = await self.get_current_tenant()
        
        # Check if feature is available for plan
        plan_features = {
            TenantPlan.FREE: ["basic_api", "basic_generation"],
            TenantPlan.TEAM: ["basic_api", "basic_generation", "collaboration", "webhooks"],
            TenantPlan.ENTERPRISE: ["all"]
        }
        
        available_features = plan_features.get(tenant.plan, [])
        if "all" not in available_features and feature not in available_features:
            raise ValidationError(
                f"Feature '{feature}' not available for {tenant.plan.value} plan"
            )
        
        # Enable feature
        if "features" not in tenant.settings:
            tenant.settings["features"] = {}
        
        tenant.settings["features"][feature] = {
            "enabled": True,
            "enabled_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.update_settings(tenant.settings)
    
    async def disable_feature(self, feature: str) -> None:
        """Disable a feature for tenant"""
        tenant = await self.get_current_tenant()
        
        if "features" in tenant.settings and feature in tenant.settings["features"]:
            tenant.settings["features"][feature]["enabled"] = False
            tenant.settings["features"][feature]["disabled_at"] = (
                datetime.now(timezone.utc).isoformat()
            )
            
            await self.update_settings(tenant.settings)
    
    # Analytics & Reporting
    
    async def get_tenant_statistics(self) -> TenantStats:
        """Get tenant statistics"""
        tenant = await self.get_current_tenant()
        stats = TenantStats()
        
        async with await self.get_db() as db:
            # User counts
            user_count = await db.execute(
                select(func.count()).select_from(TenantUser).where(
                    and_(
                        TenantUser.tenant_id == tenant.id,
                        TenantUser.is_active == True
                    )
                )
            )
            stats.user_count = user_count.scalar()
            
            # Active users (logged in last 30 days)
            # This would check login timestamps
            stats.active_user_count = stats.user_count  # Simplified
            
            # Workspace count
            workspace_count = await db.execute(
                select(func.count()).select_from(Workspace).where(
                    and_(
                        Workspace.tenant_id == tenant.id,
                        Workspace.is_active == True
                    )
                )
            )
            stats.workspace_count = workspace_count.scalar()
        
        # Get usage data
        usage_service = await get_usage_service()
        usage_summary = await usage_service.get_usage_summary()
        
        # Extract key metrics
        resources = usage_summary.get("resources", {})
        
        if ResourceType.API_CALLS.value in resources:
            stats.api_calls_today = int(
                resources[ResourceType.API_CALLS.value].get("total_usage", 0)
            )
        
        if ResourceType.CODE_GENERATIONS.value in resources:
            stats.code_generations_month = int(
                resources[ResourceType.CODE_GENERATIONS.value].get("total_usage", 0)
            )
        
        return stats
    
    async def get_user_activity(
        self,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get user activity for the tenant"""
        # This would query activity logs
        # For now, return empty list
        return []
    
    async def export_tenant_data(self) -> Dict[str, Any]:
        """Export all tenant data for GDPR compliance"""
        tenant = await self.get_current_tenant()
        user = await self.get_current_user()
        
        # Check permissions
        tenant_user = await self.get_current_tenant_user()
        if not tenant_user or tenant_user.role != UserRole.OWNER:
            raise AuthorizationError("Only owners can export tenant data")
        
        export_data = {
            "export_id": str(uuid4()),
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "exported_by": str(user.id),
            "tenant": {
                "id": str(tenant.id),
                "name": tenant.name,
                "plan": tenant.plan.value,
                "created_at": tenant.created_at.isoformat(),
                "settings": tenant.settings
            },
            "users": [],
            "workspaces": [],
            "usage_data": {}
        }
        
        async with await self.get_db() as db:
            # Export users
            users_result = await db.execute(
                select(User).join(TenantUser).where(
                    TenantUser.tenant_id == tenant.id
                ).options(selectinload(User.tenants))
            )
            for user in users_result.scalars():
                export_data["users"].append({
                    "id": str(user.id),
                    "email": user.email,
                    "profile": user.profile,
                    "created_at": user.created_at.isoformat()
                })
            
            # Export workspaces
            workspaces_result = await db.execute(
                select(Workspace).where(
                    Workspace.tenant_id == tenant.id
                )
            )
            for workspace in workspaces_result.scalars():
                export_data["workspaces"].append({
                    "id": str(workspace.id),
                    "name": workspace.name,
                    "description": workspace.description,
                    "created_at": workspace.created_at.isoformat()
                })
        
        # Export usage data
        usage_service = await get_usage_service()
        export_data["usage_data"] = await usage_service.get_usage_summary()
        
        # Log audit
        await self.log_audit(
            action="export",
            entity_type="tenant",
            entity_id=str(tenant.id),
            metadata={"export_id": export_data["export_id"]}
        )
        
        return export_data


# Singleton instance
_tenant_service: Optional[TenantService] = None


def get_tenant_service() -> TenantService:
    """Get or create tenant service instance"""
    global _tenant_service
    if not _tenant_service:
        _tenant_service = TenantService()
    return _tenant_service