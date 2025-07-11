"""
Patch for CapsuleStorageService to handle missing request_ids
Apply this patch to fix the issue with capsules missing request_id
"""

from typing import Optional
from uuid import uuid4
from datetime import datetime
import json
import structlog

from src.common.models import QLCapsule, ValidationReport
from src.common.error_handling import handle_errors

logger = structlog.get_logger()


class PatchedCapsuleStorageService:
    """Patched version of CapsuleStorageService that handles missing request_ids"""
    
    @handle_errors
    async def get_capsule_patched(self, capsule_id: str) -> Optional[QLCapsule]:
        """Retrieve a capsule from storage with request_id handling"""
        
        # Call the original repository method
        capsule_model = self.repository.get_capsule(capsule_id)
        if not capsule_model:
            logger.warning("Capsule not found", capsule_id=capsule_id)
            return None
        
        # Convert database model to QLCapsule
        validation_report = None
        if capsule_model.validation_report:
            validation_report = ValidationReport(**capsule_model.validation_report)
        
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
        
        # PATCH: Handle missing request_id
        request_id = getattr(capsule_model, 'request_id', None)
        if not request_id:
            # Generate a new request_id
            request_id = str(uuid4())
            logger.warning(
                "Capsule missing request_id, generating temporary one",
                capsule_id=capsule_id,
                generated_request_id=request_id
            )
            
            # Try to update the model (if possible)