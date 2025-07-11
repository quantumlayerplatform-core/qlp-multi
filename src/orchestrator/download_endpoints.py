#!/usr/bin/env python3
"""
API endpoints for downloading and exporting capsules
"""

import io
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Response, Depends
from fastapi.responses import StreamingResponse, FileResponse
import zipfile
import tarfile

from src.common.models import QLCapsule
from src.common.auth import get_current_user
from src.orchestrator.capsule_storage import CapsuleStorageService as PostgresCapsuleStorage
from src.orchestrator.capsule_export import CapsuleExporter, CapsuleStreamer


router = APIRouter(prefix="/api/capsules", tags=["capsule-download"])


@router.get("")
async def list_capsules(
    limit: int = Query(10, description="Maximum number of capsules to return"),
    offset: int = Query(0, description="Number of capsules to skip"),
    user: dict = Depends(get_current_user)
):
    """List available capsules with pagination"""
    storage = PostgresCapsuleStorage()
    
    try:
        capsules = await storage.list_capsules(limit=limit, offset=offset)
        
        # Transform for API response
        results = []
        for capsule in capsules:
            manifest = capsule.get('manifest', {})
            metadata = capsule.get('metadata', {})
            
            results.append({
                "id": capsule['id'],
                "name": manifest.get('name', 'Unnamed'),
                "description": manifest.get('description', ''),
                "language": manifest.get('language', 'Unknown'),
                "framework": manifest.get('framework', 'Unknown'),
                "created_at": capsule.get('created_at'),
                "confidence_score": metadata.get('confidence_score', 0),
                "production_ready": metadata.get('production_ready', False),
                "file_count": len(capsule.get('source_code', {})) + len(capsule.get('tests', {}))
            })
        
        return {
            "capsules": results,
            "count": len(results),
            "limit": limit,
            "offset": offset
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list capsules: {str(e)}")


@router.get("/{capsule_id}")
async def get_capsule_details(
    capsule_id: str,
    user: dict = Depends(get_current_user)
):
    """Get detailed information about a specific capsule"""
    storage = PostgresCapsuleStorage()
    
    try:
        capsule_data = await storage.get_capsule(capsule_id)
        
        if not capsule_data:
            raise HTTPException(status_code=404, detail=f"Capsule {capsule_id} not found")
        
        # Transform for API response
        manifest = capsule_data.get('manifest', {})
        metadata = capsule_data.get('metadata', {})
        validation = capsule_data.get('validation_report', {})
        
        return {
            "id": capsule_data['id'],
            "request_id": capsule_data.get('request_id'),
            "created_at": capsule_data.get('created_at'),
            "manifest": manifest,
            "metadata": metadata,
            "validation_report": validation,
            "files": {
                "source_code": list(capsule_data.get('source_code', {}).keys()),
                "tests": list(capsule_data.get('tests', {}).keys()),
                "has_documentation": bool(capsule_data.get('documentation')),
                "has_deployment_config": bool(capsule_data.get('deployment_config'))
            },
            "stats": {
                "total_files": len(capsule_data.get('source_code', {})) + len(capsule_data.get('tests', {})),
                "total_lines": metadata.get('total_lines', 0),
                "languages": metadata.get('languages', []),
                "frameworks": metadata.get('frameworks', []),
                "features": metadata.get('features', [])
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get capsule: {str(e)}")


@router.get("/{capsule_id}/download")
async def download_capsule(
    capsule_id: str,
    format: str = Query("zip", description="Download format: zip, tar, tar.gz"),
    user: dict = Depends(get_current_user)
):
    """Download a capsule in the specified format"""
    storage = PostgresCapsuleStorage()
    exporter = CapsuleExporter()
    
    try:
        # Fetch capsule
        capsule_data = await storage.get_capsule(capsule_id)
        
        if not capsule_data:
            raise HTTPException(status_code=404, detail=f"Capsule {capsule_id} not found")
        
        capsule = QLCapsule(**capsule_data)
        manifest = capsule.manifest
        name = manifest.get('name', 'unnamed').lower().replace(' ', '-')
        
        if format == "zip":
            # Export as ZIP
            zip_data = await exporter.export_as_zip(capsule)
            
            return Response(
                content=zip_data,
                media_type="application/zip",
                headers={
                    "Content-Disposition": f'attachment; filename="{name}_capsule.zip"'
                }
            )
        
        elif format in ["tar", "tar.gz"]:
            # Export as TAR
            compression = "gz" if format == "tar.gz" else None
            tar_data = await exporter.export_as_tar(capsule, compression)
            
            media_type = "application/gzip" if compression else "application/x-tar"
            extension = ".tar.gz" if compression else ".tar"
            
            return Response(
                content=tar_data,
                media_type=media_type,
                headers={
                    "Content-Disposition": f'attachment; filename="{name}_capsule{extension}"'
                }
            )
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download capsule: {str(e)}")


@router.get("/{capsule_id}/stream")
async def stream_capsule(
    capsule_id: str,
    format: str = Query("tar.gz", description="Stream format: tar.gz"),
    chunk_size: int = Query(1024*1024, description="Chunk size in bytes"),
    user: dict = Depends(get_current_user)
):
    """Stream a large capsule in chunks"""
    storage = PostgresCapsuleStorage()
    streamer = CapsuleStreamer()
    
    try:
        # Fetch capsule
        capsule_data = await storage.get_capsule(capsule_id)
        
        if not capsule_data:
            raise HTTPException(status_code=404, detail=f"Capsule {capsule_id} not found")
        
        capsule = QLCapsule(**capsule_data)
        manifest = capsule.manifest
        name = manifest.get('name', 'unnamed').lower().replace(' ', '-')
        
        # Create async generator for streaming
        async def generate():
            async for chunk in streamer.stream_capsule(capsule, format, chunk_size):
                yield chunk
        
        return StreamingResponse(
            generate(),
            media_type="application/gzip",
            headers={
                "Content-Disposition": f'attachment; filename="{name}_capsule.tar.gz"'
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stream capsule: {str(e)}")


@router.get("/{capsule_id}/files/{file_path:path}")
async def get_capsule_file(
    capsule_id: str,
    file_path: str,
    user: dict = Depends(get_current_user)
):
    """Get a specific file from a capsule"""
    storage = PostgresCapsuleStorage()
    
    try:
        # Fetch capsule
        capsule_data = await storage.get_capsule(capsule_id)
        
        if not capsule_data:
            raise HTTPException(status_code=404, detail=f"Capsule {capsule_id} not found")
        
        capsule = QLCapsule(**capsule_data)
        
        # Look for file in source code and tests
        content = None
        if file_path in capsule.source_code:
            content = capsule.source_code[file_path]
        elif file_path in capsule.tests:
            content = capsule.tests[file_path]
        elif file_path == "README.md" and capsule.documentation:
            content = capsule.documentation
        elif file_path == "manifest.json":
            import json
            content = json.dumps(capsule.manifest, indent=2)
        elif file_path == "metadata.json":
            import json
            content = json.dumps(capsule.metadata, indent=2)
        elif file_path == "validation_report.json" and capsule.validation_report:
            import json
            content = json.dumps(capsule.validation_report.model_dump(), indent=2)
        elif file_path == "deployment_config.json" and capsule.deployment_config:
            import json
            content = json.dumps(capsule.deployment_config, indent=2)
        else:
            raise HTTPException(status_code=404, detail=f"File '{file_path}' not found in capsule")
        
        # Determine content type
        if file_path.endswith('.py'):
            media_type = "text/x-python"
        elif file_path.endswith('.json'):
            media_type = "application/json"
        elif file_path.endswith('.yaml') or file_path.endswith('.yml'):
            media_type = "text/yaml"
        elif file_path.endswith('.md'):
            media_type = "text/markdown"
        elif file_path.endswith('.txt'):
            media_type = "text/plain"
        else:
            media_type = "text/plain"
        
        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'inline; filename="{file_path}"'
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get file: {str(e)}")


@router.get("/{capsule_id}/export/helm")
async def export_as_helm(
    capsule_id: str,
    user: dict = Depends(get_current_user)
):
    """Export capsule as a Helm chart"""
    storage = PostgresCapsuleStorage()
    exporter = CapsuleExporter()
    
    try:
        # Fetch capsule
        capsule_data = await storage.get_capsule(capsule_id)
        
        if not capsule_data:
            raise HTTPException(status_code=404, detail=f"Capsule {capsule_id} not found")
        
        capsule = QLCapsule(**capsule_data)
        
        # Export as Helm chart
        helm_data = await exporter.export_as_helm_chart(capsule)
        
        return helm_data
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export as Helm: {str(e)}")


@router.get("/{capsule_id}/export/terraform")
async def export_as_terraform(
    capsule_id: str,
    user: dict = Depends(get_current_user)
):
    """Export capsule as Terraform configuration"""
    storage = PostgresCapsuleStorage()
    exporter = CapsuleExporter()
    
    try:
        # Fetch capsule
        capsule_data = await storage.get_capsule(capsule_id)
        
        if not capsule_data:
            raise HTTPException(status_code=404, detail=f"Capsule {capsule_id} not found")
        
        capsule = QLCapsule(**capsule_data)
        
        # Export as Terraform
        tf_data = await exporter.export_as_terraform(capsule)
        
        return tf_data
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export as Terraform: {str(e)}")