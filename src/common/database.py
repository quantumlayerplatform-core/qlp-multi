"""
Production Database Models and Connection Management
Handles persistent storage for capsules, versions, and delivery metadata
"""

import os
from sqlalchemy import create_engine, Column, String, Text, DateTime, Boolean, Float, Integer, JSON, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import uuid
import json
from contextlib import asynccontextmanager

from src.common.config import settings

Base = declarative_base()


class CapsuleModel(Base):
    """Database model for QLCapsules"""
    __tablename__ = "capsules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(String(255), nullable=False, index=True)
    tenant_id = Column(String(255), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    
    # Core content
    manifest = Column(JSON, nullable=False, default={})
    source_code = Column(JSON, nullable=False, default={})  # filename -> content
    tests = Column(JSON, nullable=False, default={})  # filename -> content
    documentation = Column(Text, default="")
    
    # Validation and deployment
    validation_report = Column(JSON, nullable=True)
    deployment_config = Column(JSON, nullable=False, default={})
    
    # Status and metrics
    confidence_score = Column(Float, default=0.0)
    execution_duration = Column(Float, default=0.0)  # seconds
    file_count = Column(Integer, default=0)
    total_size_bytes = Column(Integer, default=0)
    
    # Metadata and timestamps
    meta_data = Column(JSON, nullable=False, default={})
    status = Column(String(50), default="created", index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    versions = relationship("CapsuleVersionModel", back_populates="capsule", cascade="all, delete-orphan")
    deliveries = relationship("CapsuleDeliveryModel", back_populates="capsule", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_capsule_tenant_user', 'tenant_id', 'user_id'),
        Index('idx_capsule_created', 'created_at'),
        Index('idx_capsule_status', 'status'),
    )


class CapsuleVersionModel(Base):
    """Database model for capsule versions"""
    __tablename__ = "capsule_versions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    capsule_id = Column(UUID(as_uuid=True), ForeignKey('capsules.id'), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    version_hash = Column(String(64), nullable=False, unique=True, index=True)
    
    # Version metadata
    author = Column(String(255), nullable=False)
    message = Column(Text, default="")
    branch = Column(String(255), default="main", index=True)
    parent_version_id = Column(UUID(as_uuid=True), ForeignKey('capsule_versions.id'), nullable=True)
    
    # Changes tracking
    changes = Column(JSON, nullable=False, default=[])  # List of file changes
    files_added = Column(Integer, default=0)
    files_modified = Column(Integer, default=0)
    files_deleted = Column(Integer, default=0)
    
    # Tags and labels
    tags = Column(JSON, nullable=False, default=[])
    is_release = Column(Boolean, default=False)
    is_draft = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    capsule = relationship("CapsuleModel", back_populates="versions")
    parent_version = relationship("CapsuleVersionModel", remote_side=[id], back_populates="child_versions")
    child_versions = relationship("CapsuleVersionModel", back_populates="parent_version", overlaps="parent_version")
    
    # Indexes
    __table_args__ = (
        Index('idx_version_capsule_number', 'capsule_id', 'version_number'),
        Index('idx_version_branch', 'capsule_id', 'branch'),
        Index('idx_version_created', 'created_at'),
    )


class CapsuleDeliveryModel(Base):
    """Database model for capsule deliveries"""
    __tablename__ = "capsule_deliveries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    capsule_id = Column(UUID(as_uuid=True), ForeignKey('capsules.id'), nullable=False, index=True)
    version_id = Column(UUID(as_uuid=True), ForeignKey('capsule_versions.id'), nullable=True, index=True)
    
    # Delivery configuration
    provider = Column(String(50), nullable=False, index=True)  # s3, azure, github, etc.
    destination = Column(String(500), nullable=False)
    delivery_config = Column(JSON, nullable=False, default={})
    
    # Delivery results
    status = Column(String(50), default="pending", index=True)  # pending, success, failed, expired
    url = Column(String(1000), nullable=True)
    signed_url = Column(String(1000), nullable=True)
    signed_url_expires = Column(DateTime(timezone=True), nullable=True)
    checksum = Column(String(128), nullable=True)
    file_size = Column(Integer, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Metadata and timestamps
    meta_data = Column(JSON, nullable=False, default={})
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    capsule = relationship("CapsuleModel", back_populates="deliveries")
    version = relationship("CapsuleVersionModel")
    
    # Indexes
    __table_args__ = (
        Index('idx_delivery_capsule_provider', 'capsule_id', 'provider'),
        Index('idx_delivery_status', 'status'),
        Index('idx_delivery_created', 'created_at'),
    )


class CapsuleSignatureModel(Base):
    """Database model for capsule digital signatures"""
    __tablename__ = "capsule_signatures"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    capsule_id = Column(UUID(as_uuid=True), ForeignKey('capsules.id'), nullable=False, index=True)
    version_id = Column(UUID(as_uuid=True), ForeignKey('capsule_versions.id'), nullable=True, index=True)
    
    # Signature details
    signature = Column(Text, nullable=False)
    algorithm = Column(String(50), default="HMAC-SHA256")
    key_id = Column(String(255), nullable=False)
    signer = Column(String(255), nullable=False)
    
    # Verification
    is_verified = Column(Boolean, default=False)
    verification_timestamp = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    capsule = relationship("CapsuleModel")
    version = relationship("CapsuleVersionModel")


class DatabaseManager:
    """Production database connection and session management"""
    
    def __init__(self):
        self.database_url = self._build_database_url()
        self.engine = create_engine(
            self.database_url,
            echo=settings.DEBUG,
            pool_size=20,
            max_overflow=30,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def _build_database_url(self) -> str:
        """Build PostgreSQL connection URL from environment"""
        # Use environment variable if set
        if os.environ.get('DATABASE_URL'):
            return os.environ['DATABASE_URL']
        
        # Build from settings, replacing localhost with 127.0.0.1 for IPv4
        host = settings.POSTGRES_HOST
        if host == 'localhost':
            host = '127.0.0.1'
        
        return (
            f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
            f"@{host}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
        )
    
    def create_tables(self):
        """Create all database tables"""
        Base.metadata.create_all(bind=self.engine)
    
    def drop_tables(self):
        """Drop all database tables (use with caution)"""
        Base.metadata.drop_all(bind=self.engine)
    
    def get_session(self) -> Session:
        """Get a database session"""
        return self.SessionLocal()
    
    @asynccontextmanager
    async def session_scope(self):
        """Async context manager for database sessions with automatic cleanup"""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


# Global database manager instance
db_manager = DatabaseManager()


# Dependency for FastAPI
def get_db() -> Session:
    """Database dependency for FastAPI"""
    db = db_manager.get_session()
    try:
        yield db
    finally:
        db.close()


# Helper functions for common database operations
class CapsuleRepository:
    """Repository for capsule database operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_capsule(self, capsule_data: Dict[str, Any]) -> CapsuleModel:
        """Create a new capsule in database"""
        capsule = CapsuleModel(**capsule_data)
        self.db.add(capsule)
        self.db.commit()
        self.db.refresh(capsule)
        return capsule
    
    def get_capsule(self, capsule_id: str) -> Optional[CapsuleModel]:
        """Get capsule by ID"""
        return self.db.query(CapsuleModel).filter(CapsuleModel.id == capsule_id).first()
    
    def get_capsules_by_user(self, tenant_id: str, user_id: str, limit: int = 50) -> List[CapsuleModel]:
        """Get capsules for a specific user"""
        return (
            self.db.query(CapsuleModel)
            .filter(CapsuleModel.tenant_id == tenant_id, CapsuleModel.user_id == user_id)
            .order_by(CapsuleModel.created_at.desc())
            .limit(limit)
            .all()
        )
    
    def update_capsule(self, capsule_id: str, updates: Dict[str, Any]) -> Optional[CapsuleModel]:
        """Update capsule with new data"""
        capsule = self.get_capsule(capsule_id)
        if capsule:
            for key, value in updates.items():
                setattr(capsule, key, value)
            capsule.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(capsule)
        return capsule
    
    def delete_capsule(self, capsule_id: str) -> bool:
        """Delete capsule and all related data"""
        capsule = self.get_capsule(capsule_id)
        if capsule:
            self.db.delete(capsule)
            self.db.commit()
            return True
        return False
    
    def create_version(self, version_data: Dict[str, Any]) -> CapsuleVersionModel:
        """Create a new capsule version"""
        version = CapsuleVersionModel(**version_data)
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)
        return version
    
    def get_version(self, version_id: str) -> Optional[CapsuleVersionModel]:
        """Get version by ID"""
        return self.db.query(CapsuleVersionModel).filter(CapsuleVersionModel.id == version_id).first()
    
    def get_capsule_versions(self, capsule_id: str, branch: Optional[str] = None, limit: int = 50) -> List[CapsuleVersionModel]:
        """Get versions for a capsule"""
        query = self.db.query(CapsuleVersionModel).filter(CapsuleVersionModel.capsule_id == capsule_id)
        
        if branch:
            query = query.filter(CapsuleVersionModel.branch == branch)
        
        return query.order_by(CapsuleVersionModel.created_at.desc()).limit(limit).all()
    
    def create_delivery(self, delivery_data: Dict[str, Any]) -> CapsuleDeliveryModel:
        """Create a new delivery record"""
        delivery = CapsuleDeliveryModel(**delivery_data)
        self.db.add(delivery)
        self.db.commit()
        self.db.refresh(delivery)
        return delivery
    
    def get_delivery(self, delivery_id: str) -> Optional[CapsuleDeliveryModel]:
        """Get delivery by ID"""
        return self.db.query(CapsuleDeliveryModel).filter(CapsuleDeliveryModel.id == delivery_id).first()
    
    def get_capsule_deliveries(self, capsule_id: str) -> List[CapsuleDeliveryModel]:
        """Get all deliveries for a capsule"""
        return (
            self.db.query(CapsuleDeliveryModel)
            .filter(CapsuleDeliveryModel.capsule_id == capsule_id)
            .order_by(CapsuleDeliveryModel.created_at.desc())
            .all()
        )
    
    def update_delivery_status(self, delivery_id: str, status: str, **kwargs) -> Optional[CapsuleDeliveryModel]:
        """Update delivery status and metadata"""
        delivery = self.get_delivery(delivery_id)
        if delivery:
            delivery.status = status
            for key, value in kwargs.items():
                setattr(delivery, key, value)
            if status == "success":
                delivery.delivered_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(delivery)
        return delivery