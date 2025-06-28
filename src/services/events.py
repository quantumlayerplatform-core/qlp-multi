"""
Domain event system for multi-tenant platform
"""

import asyncio
import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any, Type, Callable
from uuid import uuid4
import traceback

from sqlalchemy import Column, String, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base

from src.common.logger import get_logger

logger = get_logger(__name__)

Base = declarative_base()


# Event Storage Model
class StoredEvent(Base):
    """Stored domain event for event sourcing"""
    __tablename__ = "domain_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    event_type = Column(String(100), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), index=True)
    user_id = Column(UUID(as_uuid=True), index=True)
    entity_type = Column(String(50), index=True)
    entity_id = Column(String(100), index=True)
    data = Column(JSON, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    version = Column(String(10), default="1.0")
    processed = Column(String(20), default="pending")  # pending, processing, completed, failed


# Base Event Classes

class DomainEvent:
    """Base class for all domain events"""
    
    event_type: str = "base.event"
    
    def __init__(
        self,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.id = str(uuid4())
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.data = data or {}
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()
        self.version = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for storage"""
        return {
            "id": self.id,
            "event_type": self.event_type,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "data": self.data,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DomainEvent":
        """Create event from dictionary"""
        event = cls(
            tenant_id=data.get("tenant_id"),
            user_id=data.get("user_id"),
            entity_type=data.get("entity_type"),
            entity_id=data.get("entity_id"),
            data=data.get("data", {}),
            metadata=data.get("metadata", {})
        )
        event.id = data.get("id", str(uuid4()))
        event.timestamp = datetime.fromisoformat(data["timestamp"])
        event.version = data.get("version", "1.0")
        return event


# Core Domain Events

class TenantCreated(DomainEvent):
    """Emitted when a new tenant is created"""
    event_type = "tenant.created"
    
    def __init__(self, tenant_id: str, name: str, plan: str, owner_email: str, **kwargs):
        super().__init__(
            entity_type="tenant",
            entity_id=tenant_id,
            data={
                "name": name,
                "plan": plan,
                "owner_email": owner_email
            },
            **kwargs
        )


class TenantUpdated(DomainEvent):
    """Emitted when tenant is updated"""
    event_type = "tenant.updated"
    
    def __init__(self, tenant_id: str, changes: Dict[str, Any], **kwargs):
        super().__init__(
            entity_type="tenant",
            entity_id=tenant_id,
            data={"changes": changes},
            **kwargs
        )


class TenantDeleted(DomainEvent):
    """Emitted when tenant is deleted"""
    event_type = "tenant.deleted"
    
    def __init__(self, tenant_id: str, deleted_by: str, **kwargs):
        super().__init__(
            entity_type="tenant",
            entity_id=tenant_id,
            data={"deleted_by": deleted_by},
            **kwargs
        )


class UserInvited(DomainEvent):
    """Emitted when user is invited to tenant"""
    event_type = "user.invited"
    
    def __init__(
        self,
        tenant_id: str,
        email: str,
        role: str,
        invited_by: str,
        invitation_code: str,
        **kwargs
    ):
        super().__init__(
            tenant_id=tenant_id,
            entity_type="invitation",
            entity_id=invitation_code,
            data={
                "email": email,
                "role": role,
                "invited_by": invited_by,
                "invitation_code": invitation_code
            },
            **kwargs
        )


class UserJoined(DomainEvent):
    """Emitted when user joins tenant"""
    event_type = "user.joined"
    
    def __init__(self, tenant_id: str, user_id: str, role: str, **kwargs):
        super().__init__(
            tenant_id=tenant_id,
            user_id=user_id,
            entity_type="user",
            entity_id=user_id,
            data={"role": role},
            **kwargs
        )


class UserRemoved(DomainEvent):
    """Emitted when user is removed from tenant"""
    event_type = "user.removed"
    
    def __init__(self, tenant_id: str, user_id: str, removed_by: str, **kwargs):
        super().__init__(
            tenant_id=tenant_id,
            entity_type="user",
            entity_id=user_id,
            data={"removed_by": removed_by},
            **kwargs
        )


class RoleChanged(DomainEvent):
    """Emitted when user role changes"""
    event_type = "role.changed"
    
    def __init__(
        self,
        tenant_id: str,
        user_id: str,
        old_role: str,
        new_role: str,
        changed_by: str,
        **kwargs
    ):
        super().__init__(
            tenant_id=tenant_id,
            user_id=user_id,
            entity_type="user",
            entity_id=user_id,
            data={
                "old_role": old_role,
                "new_role": new_role,
                "changed_by": changed_by
            },
            **kwargs
        )


class WorkspaceCreated(DomainEvent):
    """Emitted when workspace is created"""
    event_type = "workspace.created"
    
    def __init__(
        self,
        tenant_id: str,
        workspace_id: str,
        name: str,
        created_by: str,
        **kwargs
    ):
        super().__init__(
            tenant_id=tenant_id,
            entity_type="workspace",
            entity_id=workspace_id,
            data={
                "name": name,
                "created_by": created_by
            },
            **kwargs
        )


class WorkspaceUpdated(DomainEvent):
    """Emitted when workspace is updated"""
    event_type = "workspace.updated"
    
    def __init__(self, workspace_id: str, changes: Dict[str, Any], **kwargs):
        super().__init__(
            entity_type="workspace",
            entity_id=workspace_id,
            data={"changes": changes},
            **kwargs
        )


class MemberAdded(DomainEvent):
    """Emitted when member is added to workspace"""
    event_type = "member.added"
    
    def __init__(
        self,
        workspace_id: str,
        user_id: str,
        role: str,
        added_by: str,
        **kwargs
    ):
        super().__init__(
            entity_type="workspace",
            entity_id=workspace_id,
            data={
                "user_id": user_id,
                "role": role,
                "added_by": added_by
            },
            **kwargs
        )


class QuotaExceeded(DomainEvent):
    """Emitted when quota is exceeded"""
    event_type = "quota.exceeded"
    
    def __init__(
        self,
        tenant_id: str,
        resource_type: str,
        limit: float,
        current: float,
        requested: float,
        **kwargs
    ):
        super().__init__(
            tenant_id=tenant_id,
            entity_type="quota",
            entity_id=f"{tenant_id}:{resource_type}",
            data={
                "resource_type": resource_type,
                "limit": limit,
                "current": current,
                "requested": requested
            },
            **kwargs
        )


class UsageAlert(DomainEvent):
    """Emitted when usage reaches threshold"""
    event_type = "usage.alert"
    
    def __init__(
        self,
        tenant_id: str,
        resource_type: str,
        threshold_percent: int,
        current_usage: float,
        limit: float,
        **kwargs
    ):
        super().__init__(
            tenant_id=tenant_id,
            entity_type="usage",
            entity_id=f"{tenant_id}:{resource_type}",
            data={
                "resource_type": resource_type,
                "threshold_percent": threshold_percent,
                "current_usage": current_usage,
                "limit": limit
            },
            **kwargs
        )


class PlanUpgraded(DomainEvent):
    """Emitted when tenant plan is upgraded"""
    event_type = "plan.upgraded"
    
    def __init__(
        self,
        tenant_id: str,
        old_plan: str,
        new_plan: str,
        upgraded_by: str,
        **kwargs
    ):
        super().__init__(
            tenant_id=tenant_id,
            entity_type="tenant",
            entity_id=tenant_id,
            data={
                "old_plan": old_plan,
                "new_plan": new_plan,
                "upgraded_by": upgraded_by
            },
            **kwargs
        )


class SecurityEvent(DomainEvent):
    """Base class for security events"""
    event_type = "security.event"
    
    def __init__(
        self,
        event_subtype: str,
        severity: str,
        details: Dict[str, Any],
        **kwargs
    ):
        super().__init__(
            entity_type="security",
            data={
                "event_subtype": event_subtype,
                "severity": severity,
                "details": details
            },
            **kwargs
        )


class AuditEvent(DomainEvent):
    """Audit trail event"""
    event_type = "audit.event"
    
    def __init__(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        changes: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        super().__init__(
            entity_type=entity_type,
            entity_id=entity_id,
            data={
                "action": action,
                "changes": changes or {}
            },
            **kwargs
        )


# Event Handler Interface

class EventHandler(ABC):
    """Base class for event handlers"""
    
    @abstractmethod
    async def handle(self, event: DomainEvent) -> None:
        """Handle the event"""
        pass
    
    @abstractmethod
    def can_handle(self, event: DomainEvent) -> bool:
        """Check if handler can process this event"""
        pass


# Concrete Event Handlers

class EmailNotificationHandler(EventHandler):
    """Send email notifications for events"""
    
    def __init__(self, email_service=None):
        self.email_service = email_service
        self.event_templates = {
            "user.invited": "invitation_email",
            "quota.exceeded": "quota_alert_email",
            "usage.alert": "usage_warning_email",
            "plan.upgraded": "plan_upgrade_confirmation"
        }
    
    async def handle(self, event: DomainEvent) -> None:
        """Send email based on event type"""
        template = self.event_templates.get(event.event_type)
        if not template:
            return
        
        try:
            # In real implementation, would use email service
            logger.info(
                f"Would send email",
                event_type=event.event_type,
                template=template,
                tenant_id=event.tenant_id
            )
            
            # Example for user invitation
            if event.event_type == "user.invited":
                await self._send_invitation_email(event)
                
        except Exception as e:
            logger.error(f"Email handler error: {e}", exc_info=True)
    
    def can_handle(self, event: DomainEvent) -> bool:
        return event.event_type in self.event_templates
    
    async def _send_invitation_email(self, event: UserInvited):
        """Send invitation email"""
        # Implementation would use actual email service
        logger.info(
            f"Sending invitation email",
            email=event.data["email"],
            tenant_id=event.tenant_id
        )


class AuditLogHandler(EventHandler):
    """Record all events for audit trail"""
    
    def __init__(self, db_service=None):
        self.db_service = db_service
    
    async def handle(self, event: DomainEvent) -> None:
        """Store event in audit log"""
        try:
            # Store in database
            logger.info(
                f"Audit log recorded",
                event_id=event.id,
                event_type=event.event_type,
                entity_type=event.entity_type,
                entity_id=event.entity_id
            )
        except Exception as e:
            logger.error(f"Audit handler error: {e}", exc_info=True)
    
    def can_handle(self, event: DomainEvent) -> bool:
        # Handle all events for audit
        return True


class UsageAlertHandler(EventHandler):
    """Handle usage alerts and quota warnings"""
    
    def __init__(self, notification_service=None):
        self.notification_service = notification_service
        self.thresholds = [50, 80, 90, 100]  # Percentage thresholds
    
    async def handle(self, event: DomainEvent) -> None:
        """Process usage alerts"""
        if event.event_type == "usage.alert":
            threshold = event.data.get("threshold_percent", 0)
            
            if threshold >= 90:
                # Critical alert
                await self._send_critical_alert(event)
            elif threshold >= 80:
                # Warning
                await self._send_warning(event)
            else:
                # Info
                logger.info(
                    f"Usage threshold reached",
                    tenant_id=event.tenant_id,
                    threshold=threshold
                )
    
    def can_handle(self, event: DomainEvent) -> bool:
        return event.event_type in ["usage.alert", "quota.exceeded"]
    
    async def _send_critical_alert(self, event: DomainEvent):
        """Send critical usage alert"""
        logger.warning(
            f"Critical usage alert",
            tenant_id=event.tenant_id,
            resource=event.data.get("resource_type"),
            usage=event.data.get("current_usage")
        )
    
    async def _send_warning(self, event: DomainEvent):
        """Send usage warning"""
        logger.info(
            f"Usage warning",
            tenant_id=event.tenant_id,
            resource=event.data.get("resource_type")
        )


class WebhookHandler(EventHandler):
    """Call external webhooks for events"""
    
    def __init__(self, webhook_service=None):
        self.webhook_service = webhook_service
    
    async def handle(self, event: DomainEvent) -> None:
        """Send event to registered webhooks"""
        try:
            # In real implementation, would look up tenant webhooks
            # and send HTTP POST with event data
            logger.info(
                f"Webhook notification",
                event_type=event.event_type,
                tenant_id=event.tenant_id
            )
        except Exception as e:
            logger.error(f"Webhook handler error: {e}", exc_info=True)
    
    def can_handle(self, event: DomainEvent) -> bool:
        # Only handle events for tenants with webhooks configured
        return True  # Simplified for now


# Event Bus Implementation

class EventBus:
    """
    Central event bus for publishing and handling events
    """
    
    def __init__(self):
        self.handlers: List[EventHandler] = []
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.processing_task: Optional[asyncio.Task] = None
        self.retry_queue: List[Tuple[DomainEvent, EventHandler, int]] = []
        self.max_retries = 3
    
    def register_handler(self, handler: EventHandler):
        """Register an event handler"""
        self.handlers.append(handler)
        logger.info(f"Registered handler: {handler.__class__.__name__}")
    
    async def publish(self, event: DomainEvent):
        """Publish an event to the bus"""
        await self.event_queue.put(event)
        logger.debug(
            f"Event published",
            event_type=event.event_type,
            event_id=event.id
        )
    
    async def start(self):
        """Start processing events"""
        self.processing_task = asyncio.create_task(self._process_events())
        logger.info("Event bus started")
    
    async def stop(self):
        """Stop processing events"""
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        logger.info("Event bus stopped")
    
    async def _process_events(self):
        """Process events from the queue"""
        while True:
            try:
                # Get event from queue
                event = await self.event_queue.get()
                
                # Find handlers that can process this event
                eligible_handlers = [
                    h for h in self.handlers if h.can_handle(event)
                ]
                
                # Process with each handler
                for handler in eligible_handlers:
                    asyncio.create_task(
                        self._handle_with_retry(event, handler)
                    )
                
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Event processing error: {e}", exc_info=True)
    
    async def _handle_with_retry(
        self,
        event: DomainEvent,
        handler: EventHandler,
        retry_count: int = 0
    ):
        """Handle event with retry logic"""
        try:
            await handler.handle(event)
            logger.debug(
                f"Event handled successfully",
                event_id=event.id,
                handler=handler.__class__.__name__
            )
        except Exception as e:
            logger.error(
                f"Handler error",
                event_id=event.id,
                handler=handler.__class__.__name__,
                error=str(e),
                retry_count=retry_count
            )
            
            if retry_count < self.max_retries:
                # Exponential backoff
                delay = 2 ** retry_count
                await asyncio.sleep(delay)
                
                # Retry
                await self._handle_with_retry(
                    event, handler, retry_count + 1
                )
            else:
                # Max retries exceeded, log and move on
                logger.error(
                    f"Handler failed after {self.max_retries} retries",
                    event_id=event.id,
                    handler=handler.__class__.__name__
                )


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get or create event bus instance"""
    global _event_bus
    if not _event_bus:
        _event_bus = EventBus()
        
        # Register default handlers
        _event_bus.register_handler(EmailNotificationHandler())
        _event_bus.register_handler(AuditLogHandler())
        _event_bus.register_handler(UsageAlertHandler())
        _event_bus.register_handler(WebhookHandler())
    
    return _event_bus


# Helper function for easy event publishing
async def publish_event(event: DomainEvent):
    """Publish an event to the global event bus"""
    bus = get_event_bus()
    await bus.publish(event)