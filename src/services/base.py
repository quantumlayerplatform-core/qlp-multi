"""
Base service class providing common functionality for all services
"""

import asyncio
import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Dict, Any, Type, TypeVar, Generic
from uuid import UUID, uuid4
from contextvars import ContextVar

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select

from src.models.tenant import Tenant, User, TenantUser
from src.auth.middleware import current_user, current_tenant_id
from src.common.logger import get_logger
from src.common.config import settings

logger = get_logger(__name__)

# Type variable for generic model operations
T = TypeVar('T')

# Context variables for service layer
db_session_context: ContextVar[Optional[AsyncSession]] = ContextVar('db_session', default=None)
audit_context: ContextVar[Optional[Dict[str, Any]]] = ContextVar('audit_context', default=None)


class ServiceError(Exception):
    """Base exception for service layer errors"""
    def __init__(self, message: str, code: str = "SERVICE_ERROR", details: Optional[Dict] = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


class NotFoundError(ServiceError):
    """Raised when requested resource is not found"""
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            f"{resource_type} with id {resource_id} not found",
            code="NOT_FOUND",
            details={"resource_type": resource_type, "resource_id": resource_id}
        )


class ValidationError(ServiceError):
    """Raised when validation fails"""
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(
            message,
            code="VALIDATION_ERROR",
            details={"field": field} if field else {}
        )


class AuthorizationError(ServiceError):
    """Raised when user lacks required permissions"""
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, code="AUTHORIZATION_ERROR")


class QuotaExceededError(ServiceError):
    """Raised when resource quota is exceeded"""
    def __init__(self, resource_type: str, limit: int, current: int):
        super().__init__(
            f"Quota exceeded for {resource_type}. Limit: {limit}, Current: {current}",
            code="QUOTA_EXCEEDED",
            details={"resource_type": resource_type, "limit": limit, "current": current}
        )


class DomainEvent:
    """Base class for domain events"""
    def __init__(
        self,
        event_type: str,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ):
        self.id = str(uuid4())
        self.event_type = event_type
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.data = data or {}
        self.timestamp = datetime.utcnow()
        self.version = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            "id": self.id,
            "event_type": self.event_type,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version
        }


class BaseService(ABC):
    """
    Base service providing common functionality
    
    Features:
    - Database session management
    - Tenant context access
    - Audit logging
    - Domain event publishing
    - Common error handling
    """
    
    def __init__(self):
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[sessionmaker] = None
        self._event_handlers: Dict[str, list] = {}
    
    async def initialize(self):
        """Initialize database connection"""
        if not self._engine:
            self._engine = create_async_engine(
                settings.DATABASE_URL,
                echo=settings.DEBUG,
                pool_size=20,
                max_overflow=10,
                pool_pre_ping=True
            )
            self._session_factory = sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            logger.info(f"Initialized {self.__class__.__name__} with database connection")
    
    async def close(self):
        """Close database connection"""
        if self._engine:
            await self._engine.dispose()
            logger.info(f"Closed {self.__class__.__name__} database connection")
    
    async def get_db(self) -> AsyncSession:
        """Get database session from context or create new one"""
        # Check if we have a session in context
        session = db_session_context.get()
        if session:
            return session
        
        # Create new session
        if not self._session_factory:
            await self.initialize()
        
        return self._session_factory()
    
    async def get_current_tenant(self) -> Optional[Tenant]:
        """Get current tenant from context"""
        tenant_id = current_tenant_id.get()
        if not tenant_id:
            return None
        
        async with await self.get_db() as db:
            result = await db.execute(
                select(Tenant).where(Tenant.id == tenant_id)
            )
            return result.scalar_one_or_none()
    
    async def get_current_user(self) -> Optional[User]:
        """Get current user from context"""
        user_claims = current_user.get()
        if not user_claims:
            return None
        
        async with await self.get_db() as db:
            # Try to find by Azure AD object ID first
            if hasattr(user_claims, 'sub'):
                result = await db.execute(
                    select(User).where(User.azure_ad_object_id == user_claims.sub)
                )
                user = result.scalar_one_or_none()
                if user:
                    return user
            
            # Fallback to email
            if hasattr(user_claims, 'email') and user_claims.email:
                result = await db.execute(
                    select(User).where(User.email == user_claims.email)
                )
                return result.scalar_one_or_none()
        
        return None
    
    async def get_current_tenant_user(self) -> Optional[TenantUser]:
        """Get current user's tenant relationship"""
        user = await self.get_current_user()
        tenant = await self.get_current_tenant()
        
        if not user or not tenant:
            return None
        
        async with await self.get_db() as db:
            result = await db.execute(
                select(TenantUser).where(
                    TenantUser.tenant_id == tenant.id,
                    TenantUser.user_id == user.id,
                    TenantUser.is_active == True
                )
            )
            return result.scalar_one_or_none()
    
    async def emit_event(self, event: DomainEvent):
        """
        Emit a domain event
        
        Args:
            event: The domain event to emit
        """
        # Add context if not provided
        if not event.tenant_id:
            tenant = await self.get_current_tenant()
            if tenant:
                event.tenant_id = str(tenant.id)
        
        if not event.user_id:
            user = await self.get_current_user()
            if user:
                event.user_id = str(user.id)
        
        # Log the event
        logger.info(
            f"Domain event emitted",
            event_type=event.event_type,
            entity_type=event.entity_type,
            entity_id=event.entity_id,
            tenant_id=event.tenant_id
        )
        
        # Store event in database (could be async)
        await self._store_event(event)
        
        # Notify handlers
        await self._notify_handlers(event)
    
    async def _store_event(self, event: DomainEvent):
        """Store event in database for event sourcing"""
        # This would store in an events table
        # For now, just log it
        logger.debug(f"Event stored: {event.to_dict()}")
    
    async def _notify_handlers(self, event: DomainEvent):
        """Notify registered event handlers"""
        handlers = self._event_handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                # Run handlers in background
                asyncio.create_task(handler(event))
            except Exception as e:
                logger.error(f"Error in event handler: {e}", exc_info=True)
    
    def register_event_handler(self, event_type: str, handler: callable):
        """Register an event handler"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
    
    async def log_audit(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        changes: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log an audit entry
        
        Args:
            action: The action performed (e.g., "create", "update", "delete")
            entity_type: Type of entity (e.g., "tenant", "user", "workspace")
            entity_id: ID of the entity
            changes: Dictionary of changes made
            metadata: Additional metadata
        """
        user = await self.get_current_user()
        tenant = await self.get_current_tenant()
        
        audit_entry = {
            "id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "user_id": str(user.id) if user else None,
            "user_email": user.email if user else None,
            "tenant_id": str(tenant.id) if tenant else None,
            "changes": changes or {},
            "metadata": metadata or {},
            "ip_address": audit_context.get().get("ip_address") if audit_context.get() else None,
            "user_agent": audit_context.get().get("user_agent") if audit_context.get() else None
        }
        
        logger.info(
            "Audit log",
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=audit_entry["user_id"]
        )
        
        # In production, this would write to an audit log table
        # For now, we'll emit it as an event
        await self.emit_event(DomainEvent(
            event_type="audit.logged",
            entity_type=entity_type,
            entity_id=entity_id,
            data=audit_entry
        ))
    
    async def with_transaction(self, func: callable, *args, **kwargs):
        """
        Execute a function within a database transaction
        
        Args:
            func: The function to execute
            *args, **kwargs: Arguments for the function
        
        Returns:
            The function's return value
        
        Raises:
            Any exception from the function will cause rollback
        """
        async with await self.get_db() as db:
            async with db.begin():
                try:
                    # Set session in context
                    token = db_session_context.set(db)
                    result = await func(*args, **kwargs)
                    await db.commit()
                    return result
                except Exception as e:
                    await db.rollback()
                    logger.error(f"Transaction rolled back: {e}")
                    raise
                finally:
                    db_session_context.reset(token)
    
    async def get_by_id(self, model_class: Type[T], id: UUID) -> Optional[T]:
        """
        Get a model instance by ID
        
        Args:
            model_class: The SQLAlchemy model class
            id: The UUID of the instance
        
        Returns:
            The model instance or None
        """
        async with await self.get_db() as db:
            result = await db.execute(
                select(model_class).where(model_class.id == id)
            )
            return result.scalar_one_or_none()
    
    async def ensure_tenant_access(self, tenant_id: UUID):
        """
        Ensure current user has access to the specified tenant
        
        Args:
            tenant_id: The tenant ID to check
        
        Raises:
            AuthorizationError if access is denied
        """
        current_tenant = await self.get_current_tenant()
        if not current_tenant or str(current_tenant.id) != str(tenant_id):
            raise AuthorizationError("Access denied to this tenant")
    
    async def ensure_workspace_access(self, workspace_id: UUID):
        """
        Ensure current user has access to the specified workspace
        
        Args:
            workspace_id: The workspace ID to check
        
        Raises:
            AuthorizationError if access is denied
        """
        user_claims = current_user.get()
        if not user_claims:
            raise AuthorizationError("No authenticated user")
        
        # Check if workspace is in user's accessible workspaces
        if hasattr(user_claims, 'workspace_ids'):
            if str(workspace_id) not in user_claims.workspace_ids:
                raise AuthorizationError("Access denied to this workspace")
    
    def validate_required_fields(self, data: Dict[str, Any], required: list):
        """
        Validate required fields are present
        
        Args:
            data: The data dictionary
            required: List of required field names
        
        Raises:
            ValidationError if any required field is missing
        """
        missing = [field for field in required if field not in data or data[field] is None]
        if missing:
            raise ValidationError(
                f"Missing required fields: {', '.join(missing)}",
                field=missing[0]
            )
    
    async def check_unique_constraint(
        self,
        model_class: Type[T],
        field_name: str,
        value: Any,
        exclude_id: Optional[UUID] = None
    ) -> bool:
        """
        Check if a value is unique for a field
        
        Args:
            model_class: The model class to check
            field_name: The field name to check
            value: The value to check
            exclude_id: Optional ID to exclude from check (for updates)
        
        Returns:
            True if unique, False otherwise
        """
        async with await self.get_db() as db:
            query = select(model_class).where(
                getattr(model_class, field_name) == value
            )
            if exclude_id:
                query = query.where(model_class.id != exclude_id)
            
            result = await db.execute(query)
            return result.scalar_one_or_none() is None


# Singleton instances for common services
_service_instances: Dict[str, BaseService] = {}


def get_service(service_class: Type[BaseService]) -> BaseService:
    """Get or create a service instance"""
    class_name = service_class.__name__
    if class_name not in _service_instances:
        _service_instances[class_name] = service_class()
    return _service_instances[class_name]