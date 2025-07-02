"""
QLCapsule Versioning and History Tracking System
Production-ready versioning infrastructure with Git-like semantics
"""

from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import json
import hashlib
import asyncio
import aiofiles
from enum import Enum
import structlog

from src.common.models import QLCapsule
from src.common.error_handling import (
    QLPError,
    handle_errors,
    ErrorSeverity
)

logger = structlog.get_logger()


class VersioningError(QLPError):
    """Error in versioning operations"""
    pass


class ChangeType(Enum):
    """Types of changes in a version"""
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"
    MERGED = "merged"


@dataclass
class FileChange:
    """Represents a change to a file"""
    path: str
    change_type: ChangeType
    old_hash: Optional[str] = None
    new_hash: Optional[str] = None
    diff: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CapsuleVersion:
    """Represents a version of a capsule"""
    version_id: str
    parent_version: Optional[str]
    timestamp: datetime
    author: str
    message: str
    changes: List[FileChange]
    capsule_hash: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


@dataclass
class VersionHistory:
    """Complete version history of a capsule"""
    capsule_id: str
    versions: List[CapsuleVersion]
    branches: Dict[str, str]  # branch_name -> version_id
    current_branch: str = "main"
    head: Optional[str] = None


class CapsuleVersionManager:
    """Manages versioning and history for QLCapsules"""
    
    def __init__(self, storage_path: Path):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.histories: Dict[str, VersionHistory] = {}
        self._lock = asyncio.Lock()
    
    @handle_errors
    async def create_initial_version(
        self,
        capsule: QLCapsule,
        author: str = "system",
        message: str = "Initial version"
    ) -> CapsuleVersion:
        """Create the first version of a capsule"""
        async with self._lock:
            # Calculate capsule hash
            capsule_hash = await self._calculate_capsule_hash(capsule)
            
            # Create file changes for all files
            changes = []
            # Process source code files
            for file_path, content in capsule.source_code.items():
                file_hash = hashlib.sha256(content.encode()).hexdigest()
                changes.append(FileChange(
                    path=file_path,
                    change_type=ChangeType.CREATED,
                    new_hash=file_hash,
                    metadata={"size": len(content), "type": "source"}
                ))
            
            # Process test files
            for file_path, content in capsule.tests.items():
                file_hash = hashlib.sha256(content.encode()).hexdigest()
                changes.append(FileChange(
                    path=file_path,
                    change_type=ChangeType.CREATED,
                    new_hash=file_hash,
                    metadata={"size": len(content), "type": "test"}
                ))
            
            # Create version
            version = CapsuleVersion(
                version_id=self._generate_version_id(),
                parent_version=None,
                timestamp=datetime.now(timezone.utc),
                author=author,
                message=message,
                changes=changes,
                capsule_hash=capsule_hash,
                metadata={
                    "files_count": len(changes),
                    "confidence_score": capsule.metadata.get('confidence_score', 0)
                }
            )
            
            # Initialize history
            history = VersionHistory(
                capsule_id=capsule.id,
                versions=[version],
                branches={"main": version.version_id},
                current_branch="main",
                head=version.version_id
            )
            
            self.histories[capsule.id] = history
            await self._persist_history(history)
            
            logger.info(
                "Created initial version",
                capsule_id=capsule.id,
                version_id=version.version_id
            )
            
            return version
    
    @handle_errors
    async def create_version(
        self,
        capsule: QLCapsule,
        parent_version_id: Optional[str] = None,
        author: str = "system",
        message: str = "",
        branch: Optional[str] = None
    ) -> CapsuleVersion:
        """Create a new version of a capsule"""
        async with self._lock:
            history = self.histories.get(capsule.id)
            if not history:
                raise VersioningError(
                    f"No version history found for capsule {capsule.id}",
                    severity=ErrorSeverity.HIGH
                )
            
            # Determine parent version
            if not parent_version_id:
                parent_version_id = history.head
            
            parent = self._find_version(history, parent_version_id)
            if not parent:
                raise VersioningError(
                    f"Parent version {parent_version_id} not found",
                    severity=ErrorSeverity.HIGH
                )
            
            # Calculate changes
            changes = await self._calculate_changes(capsule, parent)
            if not changes:
                logger.warning(
                    "No changes detected",
                    capsule_id=capsule.id,
                    parent_version=parent_version_id
                )
                return parent
            
            # Create new version
            capsule_hash = await self._calculate_capsule_hash(capsule)
            version = CapsuleVersion(
                version_id=self._generate_version_id(),
                parent_version=parent_version_id,
                timestamp=datetime.now(timezone.utc),
                author=author,
                message=message or f"Update from {parent_version_id[:8]}",
                changes=changes,
                capsule_hash=capsule_hash,
                metadata={
                    "files_count": len(changes),
                    "confidence_score": capsule.metadata.get('confidence_score', 0),
                    "branch": branch or history.current_branch
                }
            )
            
            # Update history
            history.versions.append(version)
            if branch:
                history.branches[branch] = version.version_id
                if branch == history.current_branch:
                    history.head = version.version_id
            else:
                history.head = version.version_id
                history.branches[history.current_branch] = version.version_id
            
            await self._persist_history(history)
            
            logger.info(
                "Created new version",
                capsule_id=capsule.id,
                version_id=version.version_id,
                parent_version=parent_version_id,
                changes_count=len(changes)
            )
            
            return version
    
    @handle_errors
    async def get_version(
        self,
        capsule_id: str,
        version_id: Optional[str] = None
    ) -> Optional[CapsuleVersion]:
        """Get a specific version or the latest version"""
        history = self.histories.get(capsule_id)
        if not history:
            history = await self._load_history(capsule_id)
            if not history:
                return None
        
        if version_id:
            return self._find_version(history, version_id)
        else:
            # Return HEAD version
            return self._find_version(history, history.head) if history.head else None
    
    @handle_errors
    async def get_history(
        self,
        capsule_id: str,
        branch: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[CapsuleVersion]:
        """Get version history for a capsule"""
        history = self.histories.get(capsule_id)
        if not history:
            history = await self._load_history(capsule_id)
            if not history:
                return []
        
        # Filter by branch if specified
        if branch:
            branch_head = history.branches.get(branch)
            if not branch_head:
                return []
            
            # Walk the history from branch head
            versions = []
            current_id = branch_head
            while current_id and (not limit or len(versions) < limit):
                version = self._find_version(history, current_id)
                if version:
                    versions.append(version)
                    current_id = version.parent_version
                else:
                    break
            
            return versions
        else:
            # Return all versions
            versions = sorted(
                history.versions,
                key=lambda v: v.timestamp,
                reverse=True
            )
            if limit:
                versions = versions[:limit]
            return versions
    
    @handle_errors
    async def create_branch(
        self,
        capsule_id: str,
        branch_name: str,
        from_version: Optional[str] = None
    ) -> str:
        """Create a new branch"""
        async with self._lock:
            history = self.histories.get(capsule_id)
            if not history:
                raise VersioningError(
                    f"No version history found for capsule {capsule_id}",
                    severity=ErrorSeverity.HIGH
                )
            
            if branch_name in history.branches:
                raise VersioningError(
                    f"Branch {branch_name} already exists",
                    severity=ErrorSeverity.MEDIUM
                )
            
            # Use HEAD if no version specified
            if not from_version:
                from_version = history.head
            
            if not from_version:
                raise VersioningError(
                    "No version to branch from",
                    severity=ErrorSeverity.HIGH
                )
            
            # Create branch
            history.branches[branch_name] = from_version
            await self._persist_history(history)
            
            logger.info(
                "Created branch",
                capsule_id=capsule_id,
                branch_name=branch_name,
                from_version=from_version
            )
            
            return from_version
    
    @handle_errors
    async def merge_versions(
        self,
        capsule_id: str,
        source_version: str,
        target_version: str,
        author: str = "system",
        message: Optional[str] = None
    ) -> CapsuleVersion:
        """Merge two versions (three-way merge)"""
        async with self._lock:
            history = self.histories.get(capsule_id)
            if not history:
                raise VersioningError(
                    f"No version history found for capsule {capsule_id}",
                    severity=ErrorSeverity.HIGH
                )
            
            source = self._find_version(history, source_version)
            target = self._find_version(history, target_version)
            
            if not source or not target:
                raise VersioningError(
                    "Source or target version not found",
                    severity=ErrorSeverity.HIGH
                )
            
            # Find common ancestor
            common_ancestor = await self._find_common_ancestor(
                history, source_version, target_version
            )
            
            # Perform three-way merge
            merged_changes = await self._three_way_merge(
                common_ancestor, source, target
            )
            
            # Create merge version
            merge_version = CapsuleVersion(
                version_id=self._generate_version_id(),
                parent_version=target_version,  # Primary parent
                timestamp=datetime.now(timezone.utc),
                author=author,
                message=message or f"Merge {source_version[:8]} into {target_version[:8]}",
                changes=merged_changes,
                capsule_hash=self._generate_version_id(),  # Placeholder
                metadata={
                    "merge": True,
                    "source_version": source_version,
                    "target_version": target_version,
                    "common_ancestor": common_ancestor.version_id if common_ancestor else None
                }
            )
            
            history.versions.append(merge_version)
            await self._persist_history(history)
            
            logger.info(
                "Created merge version",
                capsule_id=capsule_id,
                merge_version=merge_version.version_id,
                source=source_version,
                target=target_version
            )
            
            return merge_version
    
    @handle_errors
    async def tag_version(
        self,
        capsule_id: str,
        version_id: str,
        tag: str,
        message: Optional[str] = None
    ) -> None:
        """Add a tag to a version"""
        async with self._lock:
            history = self.histories.get(capsule_id)
            if not history:
                raise VersioningError(
                    f"No version history found for capsule {capsule_id}",
                    severity=ErrorSeverity.HIGH
                )
            
            version = self._find_version(history, version_id)
            if not version:
                raise VersioningError(
                    f"Version {version_id} not found",
                    severity=ErrorSeverity.HIGH
                )
            
            # Add tag
            if tag not in version.tags:
                version.tags.append(tag)
                if message:
                    version.metadata[f"tag_{tag}_message"] = message
                
                await self._persist_history(history)
                
                logger.info(
                    "Tagged version",
                    capsule_id=capsule_id,
                    version_id=version_id,
                    tag=tag
                )
    
    @handle_errors
    async def get_diff(
        self,
        capsule_id: str,
        version1: str,
        version2: str
    ) -> List[FileChange]:
        """Get differences between two versions"""
        history = self.histories.get(capsule_id)
        if not history:
            history = await self._load_history(capsule_id)
            if not history:
                return []
        
        v1 = self._find_version(history, version1)
        v2 = self._find_version(history, version2)
        
        if not v1 or not v2:
            raise VersioningError(
                "One or both versions not found",
                severity=ErrorSeverity.HIGH
            )
        
        # Calculate diff
        return await self._calculate_diff(v1, v2)
    
    # Helper methods
    
    async def _calculate_capsule_hash(self, capsule: QLCapsule) -> str:
        """Calculate hash for entire capsule"""
        hasher = hashlib.sha256()
        
        # Hash source code files in deterministic order
        for file_path in sorted(capsule.source_code.keys()):
            hasher.update(file_path.encode())
            hasher.update(capsule.source_code[file_path].encode())
        
        # Hash test files in deterministic order
        for file_path in sorted(capsule.tests.keys()):
            hasher.update(file_path.encode())
            hasher.update(capsule.tests[file_path].encode())
        
        # Include metadata (serializable only)
        metadata_str = json.dumps(capsule.metadata, sort_keys=True, default=str)
        hasher.update(metadata_str.encode())
        
        return hasher.hexdigest()
    
    async def _calculate_changes(
        self,
        capsule: QLCapsule,
        parent_version: CapsuleVersion
    ) -> List[FileChange]:
        """Calculate changes between capsule and parent version"""
        changes = []
        
        # Build parent file map
        parent_files = {
            change.path: change.new_hash
            for change in parent_version.changes
            if change.change_type != ChangeType.DELETED
        }
        
        # Check current files
        current_files = {}
        # Process source code files
        for file_path, content in capsule.source_code.items():
            file_hash = hashlib.sha256(content.encode()).hexdigest()
            current_files[file_path] = file_hash
        
        # Process test files
        for file_path, content in capsule.tests.items():
            file_hash = hashlib.sha256(content.encode()).hexdigest()
            current_files[file_path] = file_hash
        
        # Compare files
        for file_path, file_hash in current_files.items():
            if file_path not in parent_files:
                # New file
                changes.append(FileChange(
                    path=file_path,
                    change_type=ChangeType.CREATED,
                    new_hash=file_hash
                ))
            elif parent_files[file_path] != file_hash:
                # Modified file
                changes.append(FileChange(
                    path=file_path,
                    change_type=ChangeType.MODIFIED,
                    old_hash=parent_files[file_path],
                    new_hash=file_hash
                ))
        
        # Check for deleted files
        for path, old_hash in parent_files.items():
            if path not in current_files:
                changes.append(FileChange(
                    path=path,
                    change_type=ChangeType.DELETED,
                    old_hash=old_hash
                ))
        
        return changes
    
    async def _find_common_ancestor(
        self,
        history: VersionHistory,
        version1: str,
        version2: str
    ) -> Optional[CapsuleVersion]:
        """Find common ancestor of two versions"""
        # Build ancestor sets
        ancestors1 = set()
        current = version1
        while current:
            ancestors1.add(current)
            version = self._find_version(history, current)
            current = version.parent_version if version else None
        
        # Walk second lineage until we find common ancestor
        current = version2
        while current:
            if current in ancestors1:
                return self._find_version(history, current)
            version = self._find_version(history, current)
            current = version.parent_version if version else None
        
        return None
    
    async def _three_way_merge(
        self,
        ancestor: Optional[CapsuleVersion],
        source: CapsuleVersion,
        target: CapsuleVersion
    ) -> List[FileChange]:
        """Perform three-way merge of changes"""
        merged_changes = []
        
        # Build file maps
        ancestor_files = {}
        if ancestor:
            for change in ancestor.changes:
                if change.change_type != ChangeType.DELETED:
                    ancestor_files[change.path] = change.new_hash
        
        source_files = {}
        for change in source.changes:
            if change.change_type != ChangeType.DELETED:
                source_files[change.path] = change.new_hash
        
        target_files = {}
        for change in target.changes:
            if change.change_type != ChangeType.DELETED:
                target_files[change.path] = change.new_hash
        
        # Merge logic
        all_paths = set(source_files.keys()) | set(target_files.keys())
        
        for path in all_paths:
            ancestor_hash = ancestor_files.get(path)
            source_hash = source_files.get(path)
            target_hash = target_files.get(path)
            
            if source_hash == target_hash:
                # No conflict
                if source_hash:
                    merged_changes.append(FileChange(
                        path=path,
                        change_type=ChangeType.MODIFIED if ancestor_hash else ChangeType.CREATED,
                        old_hash=ancestor_hash,
                        new_hash=source_hash
                    ))
            elif source_hash and not target_hash:
                # Deleted in target, modified in source - conflict
                merged_changes.append(FileChange(
                    path=path,
                    change_type=ChangeType.MERGED,
                    old_hash=ancestor_hash,
                    new_hash=source_hash,
                    metadata={"conflict": "delete-modify"}
                ))
            elif not source_hash and target_hash:
                # Deleted in source, keep target
                merged_changes.append(FileChange(
                    path=path,
                    change_type=ChangeType.MODIFIED,
                    old_hash=ancestor_hash,
                    new_hash=target_hash
                ))
            else:
                # Both modified - conflict
                merged_changes.append(FileChange(
                    path=path,
                    change_type=ChangeType.MERGED,
                    old_hash=ancestor_hash,
                    new_hash=source_hash,  # Prefer source
                    metadata={
                        "conflict": "modify-modify",
                        "target_hash": target_hash
                    }
                ))
        
        return merged_changes
    
    async def _calculate_diff(
        self,
        version1: CapsuleVersion,
        version2: CapsuleVersion
    ) -> List[FileChange]:
        """Calculate diff between two versions"""
        diff = []
        
        # Build file maps
        files1 = {
            change.path: change.new_hash
            for change in version1.changes
            if change.change_type != ChangeType.DELETED
        }
        
        files2 = {
            change.path: change.new_hash
            for change in version2.changes
            if change.change_type != ChangeType.DELETED
        }
        
        # Compare files
        all_paths = set(files1.keys()) | set(files2.keys())
        
        for path in all_paths:
            hash1 = files1.get(path)
            hash2 = files2.get(path)
            
            if hash1 and not hash2:
                diff.append(FileChange(
                    path=path,
                    change_type=ChangeType.DELETED,
                    old_hash=hash1
                ))
            elif not hash1 and hash2:
                diff.append(FileChange(
                    path=path,
                    change_type=ChangeType.CREATED,
                    new_hash=hash2
                ))
            elif hash1 != hash2:
                diff.append(FileChange(
                    path=path,
                    change_type=ChangeType.MODIFIED,
                    old_hash=hash1,
                    new_hash=hash2
                ))
        
        return diff
    
    def _find_version(
        self,
        history: VersionHistory,
        version_id: str
    ) -> Optional[CapsuleVersion]:
        """Find a version in history"""
        for version in history.versions:
            if version.version_id == version_id:
                return version
        return None
    
    def _generate_version_id(self) -> str:
        """Generate unique version ID"""
        return hashlib.sha256(
            f"{datetime.now().isoformat()}-{id(self)}".encode()
        ).hexdigest()[:16]
    
    async def _persist_history(self, history: VersionHistory) -> None:
        """Persist version history to storage"""
        history_file = self.storage_path / f"{history.capsule_id}_history.json"
        
        # Convert to dict for serialization
        history_dict = {
            "capsule_id": history.capsule_id,
            "versions": [
                {
                    "version_id": v.version_id,
                    "parent_version": v.parent_version,
                    "timestamp": v.timestamp.isoformat(),
                    "author": v.author,
                    "message": v.message,
                    "changes": [
                        {
                            "path": c.path,
                            "change_type": c.change_type.value,
                            "old_hash": c.old_hash,
                            "new_hash": c.new_hash,
                            "diff": c.diff,
                            "metadata": c.metadata
                        }
                        for c in v.changes
                    ],
                    "capsule_hash": v.capsule_hash,
                    "metadata": v.metadata,
                    "tags": v.tags
                }
                for v in history.versions
            ],
            "branches": history.branches,
            "current_branch": history.current_branch,
            "head": history.head
        }
        
        async with aiofiles.open(history_file, 'w') as f:
            await f.write(json.dumps(history_dict, indent=2))
    
    async def _load_history(self, capsule_id: str) -> Optional[VersionHistory]:
        """Load version history from storage"""
        history_file = self.storage_path / f"{capsule_id}_history.json"
        
        if not history_file.exists():
            return None
        
        try:
            async with aiofiles.open(history_file, 'r') as f:
                history_dict = json.loads(await f.read())
            
            # Convert back to objects
            versions = []
            for v_dict in history_dict["versions"]:
                changes = [
                    FileChange(
                        path=c["path"],
                        change_type=ChangeType(c["change_type"]),
                        old_hash=c["old_hash"],
                        new_hash=c["new_hash"],
                        diff=c["diff"],
                        metadata=c["metadata"]
                    )
                    for c in v_dict["changes"]
                ]
                
                version = CapsuleVersion(
                    version_id=v_dict["version_id"],
                    parent_version=v_dict["parent_version"],
                    timestamp=datetime.fromisoformat(v_dict["timestamp"]),
                    author=v_dict["author"],
                    message=v_dict["message"],
                    changes=changes,
                    capsule_hash=v_dict["capsule_hash"],
                    metadata=v_dict["metadata"],
                    tags=v_dict["tags"]
                )
                versions.append(version)
            
            history = VersionHistory(
                capsule_id=history_dict["capsule_id"],
                versions=versions,
                branches=history_dict["branches"],
                current_branch=history_dict["current_branch"],
                head=history_dict["head"]
            )
            
            self.histories[capsule_id] = history
            return history
            
        except Exception as e:
            logger.error(
                "Failed to load version history",
                capsule_id=capsule_id,
                error=str(e)
            )
            return None