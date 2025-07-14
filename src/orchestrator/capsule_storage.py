"""
Production Capsule Storage Service
Handles persistent storage and retrieval of QLCapsules with proper database integration
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import hashlib
import json
from uuid import uuid4
import structlog

from sqlalchemy.orm import Session
from src.common.database import CapsuleRepository, CapsuleModel, CapsuleVersionModel, get_db
from src.common.models import QLCapsule, ExecutionRequest, ValidationReport
from src.common.error_handling import QLPError, ErrorSeverity, handle_errors

logger = structlog.get_logger()


class CapsuleStorageService:
    """Production service for capsule storage and retrieval"""
    
    def __init__(self, db: Session):
        self.db = db
        self.repository = CapsuleRepository(db)
    
    @handle_errors
    async def store_capsule(
        self,
        capsule: QLCapsule,
        request: ExecutionRequest,
        overwrite: bool = False
    ) -> str:
        """Store a capsule in the database"""
        
        # Check if capsule already exists
        existing = self.repository.get_capsule(str(capsule.id))
        if existing and not overwrite:
            raise QLPError(
                f"Capsule {capsule.id} already exists. Use overwrite=True to replace.",
                severity=ErrorSeverity.MEDIUM
            )
        
        # Calculate metadata
        file_count = len(capsule.source_code) + len(capsule.tests)
        total_size = sum(len(content.encode('utf-8')) for content in capsule.source_code.values())
        total_size += sum(len(content.encode('utf-8')) for content in capsule.tests.values())
        total_size += len(capsule.documentation.encode('utf-8'))
        
        # Prepare capsule data for database
        capsule_data = {
            'id': capsule.id,
            'request_id': capsule.request_id,
            'tenant_id': request.tenant_id,
            'user_id': request.user_id,
            'manifest': capsule.manifest,
            'source_code': capsule.source_code,
            'tests': capsule.tests,
            'documentation': capsule.documentation,
            'validation_report': json.loads(capsule.validation_report.model_dump_json()) if capsule.validation_report else None,
            'deployment_config': capsule.deployment_config,
            'confidence_score': capsule.metadata.get('confidence_score', 0.0),
            'execution_duration': capsule.metadata.get('execution_duration', 0.0),
            'file_count': file_count,
            'total_size_bytes': total_size,
            'meta_data': capsule.metadata,
            'status': 'stored'
        }
        
        if existing and overwrite:
            # Update existing capsule
            stored_capsule = self.repository.update_capsule(str(capsule.id), capsule_data)
            logger.info(
                "Updated existing capsule",
                capsule_id=capsule.id,
                file_count=file_count,
                total_size=total_size
            )
        else:
            # Create new capsule
            stored_capsule = self.repository.create_capsule(capsule_data)
            logger.info(
                "Stored new capsule",
                capsule_id=capsule.id,
                file_count=file_count,
                total_size=total_size
            )
        
        return str(stored_capsule.id)
    
    @handle_errors
    async def get_capsule(self, capsule_id: str) -> Optional[QLCapsule]:
        """Retrieve a capsule from storage"""
        
        capsule_model = self.repository.get_capsule(capsule_id)
        if not capsule_model:
            logger.warning("Capsule not found", capsule_id=capsule_id)
            return None
        
        # Convert database model to QLCapsule
        validation_report = None
        if capsule_model.validation_report:
            try:
                # Create a copy of the validation report data
                vr_data = dict(capsule_model.validation_report)
                logger.info(f"ValidationReport data: {vr_data}")
                logger.info(f"created_at in vr_data: {'created_at' in vr_data}")
                if 'created_at' in vr_data:
                    logger.info(f"created_at type: {type(vr_data['created_at'])}, value: {vr_data['created_at']}")
                validation_report = ValidationReport(**vr_data)
            except Exception as e:
                logger.error(f"Failed to create ValidationReport: {str(e)}")
                logger.error(f"ValidationReport data: {capsule_model.validation_report}")
                raise
        
        # Parse JSON fields if they're strings
        source_code = capsule_model.source_code
        if isinstance(source_code, str):
            try:
                source_code = json.loads(source_code)
            except:
                source_code = {}
        
        tests = capsule_model.tests
        if isinstance(tests, str):
            try:
                tests = json.loads(tests)
            except:
                tests = {}
        
        manifest = capsule_model.manifest
        if isinstance(manifest, str):
            try:
                manifest = json.loads(manifest)
            except:
                manifest = {}
        
        deployment_config = capsule_model.deployment_config
        if isinstance(deployment_config, str):
            try:
                deployment_config = json.loads(deployment_config)
            except:
                deployment_config = {}
        
        metadata = capsule_model.meta_data
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
        
        # Handle created_at - convert datetime to string if needed
        created_at_str = None
        if capsule_model.created_at:
            if isinstance(capsule_model.created_at, str):
                created_at_str = capsule_model.created_at
            else:
                created_at_str = capsule_model.created_at.isoformat()
        
        capsule = QLCapsule(
            id=str(capsule_model.id),
            request_id=capsule_model.request_id,
            manifest=manifest or {},
            source_code=source_code or {},
            tests=tests or {},
            documentation=capsule_model.documentation or "",
            validation_report=validation_report,
            deployment_config=deployment_config or {},
            metadata=metadata or {},
            created_at=created_at_str or datetime.utcnow().isoformat()
        )
        
        logger.info("Retrieved capsule", capsule_id=capsule_id)
        return capsule
    
    @handle_errors
    async def list_capsules(
        self,
        tenant_id: str,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List capsules for a user"""
        
        capsules = self.repository.get_capsules_by_user(tenant_id, user_id, limit)
        
        result = []
        for capsule in capsules:
            result.append({
                'id': str(capsule.id),
                'request_id': capsule.request_id,
                'status': capsule.status,
                'file_count': capsule.file_count,
                'total_size_bytes': capsule.total_size_bytes,
                'confidence_score': capsule.confidence_score,
                'created_at': capsule.created_at.isoformat(),
                'updated_at': capsule.updated_at.isoformat(),
                'metadata': capsule.meta_data
            })
        
        logger.info(
            "Listed capsules",
            tenant_id=tenant_id,
            user_id=user_id,
            count=len(result)
        )
        
        return result
    
    @handle_errors
    async def delete_capsule(self, capsule_id: str, user_id: str, tenant_id: str) -> bool:
        """Delete a capsule (with authorization check)"""
        
        # First verify ownership
        capsule = self.repository.get_capsule(capsule_id)
        if not capsule:
            logger.warning("Capsule not found for deletion", capsule_id=capsule_id)
            return False
        
        if capsule.user_id != user_id or capsule.tenant_id != tenant_id:
            raise QLPError(
                "Unauthorized: Cannot delete capsule owned by another user",
                severity=ErrorSeverity.HIGH
            )
        
        success = self.repository.delete_capsule(capsule_id)
        
        if success:
            logger.info("Deleted capsule", capsule_id=capsule_id, user_id=user_id)
        else:
            logger.error("Failed to delete capsule", capsule_id=capsule_id)
        
        return success
    
    @handle_errors
    async def create_version(
        self,
        capsule_id: str,
        capsule: QLCapsule,
        author: str,
        message: str,
        branch: str = "main"
    ) -> str:
        """Create a new version of a capsule"""
        
        # Get the latest version number for this capsule
        existing_versions = self.repository.get_capsule_versions(capsule_id, branch, 1)
        next_version = 1
        if existing_versions:
            next_version = existing_versions[0].version_number + 1
        
        # Calculate version hash based on content
        content_hash = self._calculate_content_hash(capsule)
        
        # Calculate changes (simplified for now - could be enhanced with diff)
        changes = []
        for file_path in capsule.source_code.keys():
            changes.append({
                'path': file_path,
                'type': 'modified',
                'size': len(capsule.source_code[file_path])
            })
        
        version_data = {
            'capsule_id': capsule_id,
            'version_number': next_version,
            'version_hash': content_hash,
            'author': author,
            'message': message,
            'branch': branch,
            'changes': changes,
            'files_added': len([c for c in changes if c['type'] == 'added']),
            'files_modified': len([c for c in changes if c['type'] == 'modified']),
            'files_deleted': len([c for c in changes if c['type'] == 'deleted']),
            'tags': [],
            'is_release': False,
            'is_draft': False
        }
        
        version = self.repository.create_version(version_data)
        
        logger.info(
            "Created capsule version",
            capsule_id=capsule_id,
            version_id=str(version.id),
            version_number=next_version,
            branch=branch
        )
        
        return str(version.id)
    
    @handle_errors
    async def get_version(self, version_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific version"""
        
        version = self.repository.get_version(version_id)
        if not version:
            return None
        
        return {
            'id': str(version.id),
            'capsule_id': str(version.capsule_id),
            'version_number': version.version_number,
            'version_hash': version.version_hash,
            'author': version.author,
            'message': version.message,
            'branch': version.branch,
            'parent_version_id': str(version.parent_version_id) if version.parent_version_id else None,
            'changes': version.changes,
            'files_added': version.files_added,
            'files_modified': version.files_modified,
            'files_deleted': version.files_deleted,
            'tags': version.tags,
            'is_release': version.is_release,
            'is_draft': version.is_draft,
            'created_at': version.created_at.isoformat()
        }
    
    @handle_errors
    async def get_version_history(
        self,
        capsule_id: str,
        branch: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get version history for a capsule"""
        
        versions = self.repository.get_capsule_versions(capsule_id, branch, limit)
        
        result = []
        for version in versions:
            result.append({
                'id': str(version.id),
                'version_number': version.version_number,
                'version_hash': version.version_hash,
                'author': version.author,
                'message': version.message,
                'branch': version.branch,
                'parent_version_id': str(version.parent_version_id) if version.parent_version_id else None,
                'files_added': version.files_added,
                'files_modified': version.files_modified,
                'files_deleted': version.files_deleted,
                'tags': version.tags,
                'is_release': version.is_release,
                'created_at': version.created_at.isoformat()
            })
        
        logger.info(
            "Retrieved version history",
            capsule_id=capsule_id,
            branch=branch,
            count=len(result)
        )
        
        return result
    
    @handle_errors
    async def tag_version(
        self,
        version_id: str,
        tag: str,
        is_release: bool = False
    ) -> bool:
        """Add a tag to a version"""
        
        version = self.repository.get_version(version_id)
        if not version:
            return False
        
        if tag not in version.tags:
            version.tags.append(tag)
            if is_release:
                version.is_release = True
            
            self.db.commit()
            
            logger.info(
                "Tagged version",
                version_id=version_id,
                tag=tag,
                is_release=is_release
            )
            
            return True
        
        return False
    
    def _calculate_content_hash(self, capsule: QLCapsule) -> str:
        """Calculate hash of capsule content for versioning"""
        hasher = hashlib.sha256()
        
        # Hash source code in deterministic order
        for file_path in sorted(capsule.source_code.keys()):
            hasher.update(file_path.encode('utf-8'))
            hasher.update(capsule.source_code[file_path].encode('utf-8'))
        
        # Hash test files
        for file_path in sorted(capsule.tests.keys()):
            hasher.update(file_path.encode('utf-8'))
            hasher.update(capsule.tests[file_path].encode('utf-8'))
        
        # Hash documentation
        hasher.update(capsule.documentation.encode('utf-8'))
        
        return hasher.hexdigest()
    
    @handle_errors
    async def get_capsule_statistics(self, capsule_id: str) -> Dict[str, Any]:
        """Get detailed statistics for a capsule"""
        
        capsule = self.repository.get_capsule(capsule_id)
        if not capsule:
            return {}
        
        versions = self.repository.get_capsule_versions(capsule_id)
        deliveries = self.repository.get_capsule_deliveries(capsule_id)
        
        # Calculate language breakdown
        languages = {}
        for file_path, content in capsule.source_code.items():
            ext = file_path.split('.')[-1].lower()
            if ext not in languages:
                languages[ext] = {'files': 0, 'lines': 0}
            languages[ext]['files'] += 1
            languages[ext]['lines'] += len(content.split('\n'))
        
        return {
            'capsule_id': str(capsule.id),
            'file_count': capsule.file_count,
            'total_size_bytes': capsule.total_size_bytes,
            'confidence_score': capsule.confidence_score,
            'execution_duration': capsule.execution_duration,
            'version_count': len(versions),
            'delivery_count': len(deliveries),
            'successful_deliveries': len([d for d in deliveries if d.status == 'success']),
            'languages': languages,
            'created_at': capsule.created_at.isoformat(),
            'updated_at': capsule.updated_at.isoformat()
        }
    
    @handle_errors
    async def update_capsule_metadata(self, capsule_id: str, metadata: Dict[str, Any]) -> bool:
        """Update capsule metadata"""
        try:
            capsule = self.repository.get_capsule(capsule_id)
            if not capsule:
                return False
            
            # Update metadata
            capsule.meta_data = metadata
            capsule.updated_at = datetime.now(timezone.utc)
            
            self.db.commit()
            logger.info(f"Updated capsule metadata for {capsule_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update capsule metadata: {str(e)}")
            self.db.rollback()
            return False


# Factory function for dependency injection
def get_capsule_storage(db: Session = get_db()) -> CapsuleStorageService:
    """Get capsule storage service instance"""
    return CapsuleStorageService(db)