"""
Enhanced QLCapsule Delivery System
Production-ready delivery infrastructure with multiple providers and security
"""

from typing import Dict, Any, List, Optional, BinaryIO
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import asyncio
import json
import tarfile
import zipfile
import tempfile
import hashlib
import hmac
from io import BytesIO
import structlog

from src.common.models import QLCapsule
from src.common.error_handling import (
    QLPError,
    handle_errors,
    CircuitBreaker,
    ErrorSeverity
)

logger = structlog.get_logger()

# Circuit breakers for external services
s3_circuit_breaker = CircuitBreaker("s3", failure_threshold=5, recovery_timeout=60)
azure_circuit_breaker = CircuitBreaker("azure", failure_threshold=5, recovery_timeout=60)
gcs_circuit_breaker = CircuitBreaker("gcs", failure_threshold=5, recovery_timeout=60)
git_circuit_breaker = CircuitBreaker("git", failure_threshold=3, recovery_timeout=120)


@dataclass
class DeliveryConfig:
    """Configuration for capsule delivery"""
    mode: str  # s3, azure, gcs, git, local, stream
    destination: str  # bucket/container/repo
    options: Dict[str, Any]
    credentials: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class DeliveryResult:
    """Result of capsule delivery"""
    success: bool
    mode: str
    destination: str
    url: Optional[str] = None
    signed_url: Optional[str] = None
    version: Optional[str] = None
    checksum: Optional[str] = None
    metadata: Dict[str, Any] = None
    error: Optional[str] = None


class DeliveryProvider(ABC):
    """Base class for delivery providers"""
    
    @abstractmethod
    async def deliver(self, capsule: QLCapsule, config: DeliveryConfig) -> DeliveryResult:
        """Deliver capsule to destination"""
        pass
    
    @abstractmethod
    async def verify(self, delivery_result: DeliveryResult) -> bool:
        """Verify successful delivery"""
        pass
    
    def calculate_checksum(self, data: bytes) -> str:
        """Calculate SHA256 checksum"""
        return hashlib.sha256(data).hexdigest()
    
    def create_archive(self, capsule: QLCapsule, format: str = "tar.gz") -> bytes:
        """Create archive from capsule files"""
        output = BytesIO()
        
        if format == "tar.gz":
            with tarfile.open(fileobj=output, mode='w:gz') as tar:
                # Add all source files
                for path, content in capsule.source_code.items():
                    info = tarfile.TarInfo(name=path)
                    info.size = len(content.encode())
                    tar.addfile(info, BytesIO(content.encode()))
                
                # Add all test files
                for path, content in capsule.tests.items():
                    info = tarfile.TarInfo(name=path)
                    info.size = len(content.encode())
                    tar.addfile(info, BytesIO(content.encode()))
                
                # Add documentation
                info = tarfile.TarInfo(name="README.md")
                info.size = len(capsule.documentation.encode())
                tar.addfile(info, BytesIO(capsule.documentation.encode()))
                
                # Add manifest
                manifest_data = json.dumps(capsule.manifest, indent=2).encode()
                info = tarfile.TarInfo(name="manifest.json")
                info.size = len(manifest_data)
                tar.addfile(info, BytesIO(manifest_data))
                
        elif format == "zip":
            with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Add all files
                for path, content in {**capsule.source_code, **capsule.tests}.items():
                    zf.writestr(path, content)
                
                zf.writestr("README.md", capsule.documentation)
                zf.writestr("manifest.json", json.dumps(capsule.manifest, indent=2))
        
        output.seek(0)
        return output.read()


class S3DeliveryProvider(DeliveryProvider):
    """AWS S3 delivery provider"""
    
    @handle_errors
    async def deliver(self, capsule: QLCapsule, config: DeliveryConfig) -> DeliveryResult:
        """Deliver capsule to S3"""
        try:
            import aioboto3
            
            # Create archive
            archive_data = self.create_archive(capsule, config.options.get("format", "tar.gz"))
            checksum = self.calculate_checksum(archive_data)
            
            # Generate S3 key
            prefix = config.options.get("prefix", "capsules")
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            key = f"{prefix}/{capsule.id}_{timestamp}.tar.gz"
            
            # Upload to S3
            session = aioboto3.Session(
                aws_access_key_id=config.credentials.get("access_key_id"),
                aws_secret_access_key=config.credentials.get("secret_access_key"),
                region_name=config.options.get("region", "us-east-1")
            )
            
            async with session.client('s3') as s3:
                # Upload with metadata
                await s3.put_object(
                    Bucket=config.destination,
                    Key=key,
                    Body=archive_data,
                    ContentType='application/gzip',
                    Metadata={
                        'capsule-id': capsule.id,
                        'request-id': capsule.request_id,
                        'checksum': checksum,
                        'created-at': datetime.utcnow().isoformat()
                    },
                    ServerSideEncryption='AES256'
                )
                
                # Generate presigned URL (valid for 7 days)
                signed_url = await s3.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': config.destination, 'Key': key},
                    ExpiresIn=604800  # 7 days
                )
            
            logger.info(f"Delivered capsule to S3: s3://{config.destination}/{key}")
            
            return DeliveryResult(
                success=True,
                mode="s3",
                destination=config.destination,
                url=f"s3://{config.destination}/{key}",
                signed_url=signed_url,
                checksum=checksum,
                metadata={
                    'key': key,
                    'size': len(archive_data),
                    'region': config.options.get("region", "us-east-1")
                }
            )
            
        except Exception as e:
            logger.error(f"S3 delivery failed: {str(e)}")
            return DeliveryResult(
                success=False,
                mode="s3",
                destination=config.destination,
                error=str(e)
            )
    
    async def verify(self, delivery_result: DeliveryResult) -> bool:
        """Verify S3 delivery"""
        # Implementation would check if object exists in S3
        return delivery_result.success


class AzureBlobDeliveryProvider(DeliveryProvider):
    """Azure Blob Storage delivery provider"""
    
    @handle_errors
    async def deliver(self, capsule: QLCapsule, config: DeliveryConfig) -> DeliveryResult:
        """Deliver capsule to Azure Blob Storage"""
        try:
            from azure.storage.blob.aio import BlobServiceClient
            from azure.storage.blob import BlobSasPermissions, generate_blob_sas
            
            # Create archive
            archive_data = self.create_archive(capsule, config.options.get("format", "tar.gz"))
            checksum = self.calculate_checksum(archive_data)
            
            # Generate blob name
            prefix = config.options.get("prefix", "capsules")
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            blob_name = f"{prefix}/{capsule.id}_{timestamp}.tar.gz"
            
            # Upload to Azure
            connection_string = config.credentials.get("connection_string")
            if not connection_string:
                # Build from components
                account_name = config.credentials.get("account_name")
                account_key = config.credentials.get("account_key")
                connection_string = f"DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey={account_key};EndpointSuffix=core.windows.net"
            
            async with BlobServiceClient.from_connection_string(connection_string) as client:
                container_client = client.get_container_client(config.destination)
                blob_client = container_client.get_blob_client(blob_name)
                
                # Upload with metadata
                await blob_client.upload_blob(
                    archive_data,
                    overwrite=True,
                    metadata={
                        'capsule_id': capsule.id,
                        'request_id': capsule.request_id,
                        'checksum': checksum,
                        'created_at': datetime.utcnow().isoformat()
                    }
                )
                
                # Generate SAS URL (valid for 7 days)
                sas_token = generate_blob_sas(
                    account_name=config.credentials.get("account_name"),
                    container_name=config.destination,
                    blob_name=blob_name,
                    account_key=config.credentials.get("account_key"),
                    permission=BlobSasPermissions(read=True),
                    expiry=datetime.utcnow() + timedelta(days=7)
                )
                
                signed_url = f"https://{config.credentials.get('account_name')}.blob.core.windows.net/{config.destination}/{blob_name}?{sas_token}"
            
            logger.info(f"Delivered capsule to Azure Blob: {blob_name}")
            
            return DeliveryResult(
                success=True,
                mode="azure",
                destination=config.destination,
                url=f"https://{config.credentials.get('account_name')}.blob.core.windows.net/{config.destination}/{blob_name}",
                signed_url=signed_url,
                checksum=checksum,
                metadata={
                    'blob_name': blob_name,
                    'size': len(archive_data),
                    'container': config.destination
                }
            )
            
        except Exception as e:
            logger.error(f"Azure Blob delivery failed: {str(e)}")
            return DeliveryResult(
                success=False,
                mode="azure",
                destination=config.destination,
                error=str(e)
            )
    
    async def verify(self, delivery_result: DeliveryResult) -> bool:
        """Verify Azure Blob delivery"""
        return delivery_result.success


class GCSDeliveryProvider(DeliveryProvider):
    """Google Cloud Storage delivery provider"""
    
    @handle_errors
    async def deliver(self, capsule: QLCapsule, config: DeliveryConfig) -> DeliveryResult:
        """Deliver capsule to Google Cloud Storage"""
        try:
            from google.cloud import storage
            from google.oauth2 import service_account
            import aiofiles
            
            # Create archive
            archive_data = self.create_archive(capsule, config.options.get("format", "tar.gz"))
            checksum = self.calculate_checksum(archive_data)
            
            # Generate object name
            prefix = config.options.get("prefix", "capsules")
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            object_name = f"{prefix}/{capsule.id}_{timestamp}.tar.gz"
            
            # Create credentials
            if config.credentials.get("service_account_json"):
                credentials = service_account.Credentials.from_service_account_info(
                    config.credentials["service_account_json"]
                )
            else:
                credentials = None  # Use default credentials
            
            # Upload to GCS
            client = storage.Client(
                project=config.credentials.get("project_id"),
                credentials=credentials
            )
            bucket = client.bucket(config.destination)
            blob = bucket.blob(object_name)
            
            # Upload with metadata
            blob.metadata = {
                'capsule-id': capsule.id,
                'request-id': capsule.request_id,
                'checksum': checksum,
                'created-at': datetime.utcnow().isoformat()
            }
            
            # Use async upload
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                async with aiofiles.open(tmp.name, 'wb') as f:
                    await f.write(archive_data)
                
                blob.upload_from_filename(tmp.name)
                Path(tmp.name).unlink()
            
            # Generate signed URL (valid for 7 days)
            signed_url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(days=7),
                method="GET"
            )
            
            logger.info(f"Delivered capsule to GCS: gs://{config.destination}/{object_name}")
            
            return DeliveryResult(
                success=True,
                mode="gcs",
                destination=config.destination,
                url=f"gs://{config.destination}/{object_name}",
                signed_url=signed_url,
                checksum=checksum,
                metadata={
                    'object_name': object_name,
                    'size': len(archive_data),
                    'bucket': config.destination
                }
            )
            
        except Exception as e:
            logger.error(f"GCS delivery failed: {str(e)}")
            return DeliveryResult(
                success=False,
                mode="gcs",
                destination=config.destination,
                error=str(e)
            )
    
    async def verify(self, delivery_result: DeliveryResult) -> bool:
        """Verify GCS delivery"""
        return delivery_result.success


class GitDeliveryProvider(DeliveryProvider):
    """Git repository delivery provider"""
    
    @handle_errors
    async def deliver(self, capsule: QLCapsule, config: DeliveryConfig) -> DeliveryResult:
        """Deliver capsule to Git repository"""
        try:
            import git
            import tempfile
            from github import Github
            
            provider = config.options.get("provider", "github")
            
            if provider == "github":
                return await self._deliver_to_github(capsule, config)
            elif provider == "gitlab":
                return await self._deliver_to_gitlab(capsule, config)
            else:
                raise ValueError(f"Unsupported Git provider: {provider}")
            
        except Exception as e:
            logger.error(f"Git delivery failed: {str(e)}")
            return DeliveryResult(
                success=False,
                mode="git",
                destination=config.destination,
                error=str(e)
            )
    
    async def _deliver_to_github(self, capsule: QLCapsule, config: DeliveryConfig) -> DeliveryResult:
        """Deliver to GitHub repository"""
        from github import Github, GithubException
        
        # Initialize GitHub client
        g = Github(config.credentials.get("token"))
        
        try:
            # Get or create repository
            repo_name = config.destination
            create_new = config.options.get("create_repo", True)
            
            try:
                repo = g.get_repo(repo_name)
            except GithubException:
                if create_new:
                    user = g.get_user()
                    repo = user.create_repo(
                        name=repo_name.split('/')[-1],
                        description=f"Generated by QLP: {capsule.manifest.get('request', {}).get('description', '')[:100]}",
                        private=config.options.get("private", False),
                        auto_init=True
                    )
                else:
                    raise
            
            # Create branch
            branch_name = config.options.get("branch", f"qlp-{capsule.id[:8]}")
            default_branch = repo.default_branch
            
            # Get latest commit
            sha = repo.get_branch(default_branch).commit.sha
            
            # Create new branch
            try:
                repo.create_git_ref(f"refs/heads/{branch_name}", sha)
            except GithubException:
                # Branch might already exist
                pass
            
            # Add all files
            for file_path, content in {**capsule.source_code, **capsule.tests}.items():
                try:
                    # Check if file exists
                    existing = repo.get_contents(file_path, ref=branch_name)
                    repo.update_file(
                        path=file_path,
                        message=f"Update {file_path} via QLP",
                        content=content,
                        sha=existing.sha,
                        branch=branch_name
                    )
                except GithubException:
                    # File doesn't exist, create it
                    repo.create_file(
                        path=file_path,
                        message=f"Add {file_path} via QLP",
                        content=content,
                        branch=branch_name
                    )
            
            # Add documentation
            repo.create_file(
                path="README.md",
                message="Add README via QLP",
                content=capsule.documentation,
                branch=branch_name
            )
            
            # Add manifest
            repo.create_file(
                path="qlp-manifest.json",
                message="Add QLP manifest",
                content=json.dumps(capsule.manifest, indent=2),
                branch=branch_name
            )
            
            # Create pull request if requested
            pr_url = None
            if config.options.get("create_pr", True):
                pr = repo.create_pull(
                    title=f"QLP Generated Code: {capsule.manifest.get('request', {}).get('description', '')[:60]}",
                    body=self._generate_pr_body(capsule),
                    head=branch_name,
                    base=default_branch
                )
                pr_url = pr.html_url
            
            logger.info(f"Delivered capsule to GitHub: {repo.html_url}")
            
            return DeliveryResult(
                success=True,
                mode="git",
                destination=repo_name,
                url=repo.html_url,
                version=branch_name,
                metadata={
                    'branch': branch_name,
                    'pr_url': pr_url,
                    'provider': 'github'
                }
            )
            
        except Exception as e:
            raise QLPError(f"GitHub delivery failed: {str(e)}", severity=ErrorSeverity.HIGH)
    
    async def _deliver_to_gitlab(self, capsule: QLCapsule, config: DeliveryConfig) -> DeliveryResult:
        """Deliver to GitLab repository"""
        import gitlab
        
        # Initialize GitLab client
        gl = gitlab.Gitlab(
            url=config.credentials.get("url", "https://gitlab.com"),
            private_token=config.credentials.get("token")
        )
        
        try:
            # Get or create project
            project_path = config.destination
            
            try:
                project = gl.projects.get(project_path)
            except gitlab.exceptions.GitlabGetError:
                # Create new project
                project = gl.projects.create({
                    'name': project_path.split('/')[-1],
                    'description': f"Generated by QLP: {capsule.manifest.get('request', {}).get('description', '')[:100]}",
                    'visibility': 'private' if config.options.get("private", False) else 'public'
                })
            
            # Create branch
            branch_name = config.options.get("branch", f"qlp-{capsule.id[:8]}")
            
            # Create branch from default branch
            project.branches.create({
                'branch': branch_name,
                'ref': project.default_branch
            })
            
            # Add all files
            actions = []
            for file_path, content in {**capsule.source_code, **capsule.tests}.items():
                actions.append({
                    'action': 'create',
                    'file_path': file_path,
                    'content': content
                })
            
            # Add documentation and manifest
            actions.extend([
                {
                    'action': 'create',
                    'file_path': 'README.md',
                    'content': capsule.documentation
                },
                {
                    'action': 'create',
                    'file_path': 'qlp-manifest.json',
                    'content': json.dumps(capsule.manifest, indent=2)
                }
            ])
            
            # Create commit with all files
            project.commits.create({
                'branch': branch_name,
                'commit_message': f'QLP Generated Code: {capsule.id}',
                'actions': actions
            })
            
            # Create merge request if requested
            mr_url = None
            if config.options.get("create_mr", True):
                mr = project.mergerequests.create({
                    'source_branch': branch_name,
                    'target_branch': project.default_branch,
                    'title': f"QLP Generated Code: {capsule.manifest.get('request', {}).get('description', '')[:60]}",
                    'description': self._generate_pr_body(capsule)
                })
                mr_url = mr.web_url
            
            logger.info(f"Delivered capsule to GitLab: {project.web_url}")
            
            return DeliveryResult(
                success=True,
                mode="git",
                destination=project_path,
                url=project.web_url,
                version=branch_name,
                metadata={
                    'branch': branch_name,
                    'mr_url': mr_url,
                    'provider': 'gitlab'
                }
            )
            
        except Exception as e:
            raise QLPError(f"GitLab delivery failed: {str(e)}", severity=ErrorSeverity.HIGH)
    
    def _generate_pr_body(self, capsule: QLCapsule) -> str:
        """Generate pull request body"""
        return f"""## QLP Generated Code

**Capsule ID**: {capsule.id}
**Request ID**: {capsule.request_id}
**Generated**: {datetime.utcnow().isoformat()}

### Description
{capsule.manifest.get('request', {}).get('description', 'No description provided')}

### Requirements
{capsule.manifest.get('request', {}).get('requirements', 'No requirements specified')}

### Validation Results
- **Confidence Score**: {capsule.metadata.get('confidence_score', 0):.2%}
- **Languages**: {', '.join(capsule.metadata.get('languages', []))}
- **Files Generated**: {len(capsule.source_code) + len(capsule.tests)}

### Quality Metrics
{json.dumps(capsule.validation_report.model_dump() if capsule.validation_report else {}, indent=2)}

---
*Generated by Quantum Layer Platform*
"""
    
    async def verify(self, delivery_result: DeliveryResult) -> bool:
        """Verify Git delivery"""
        return delivery_result.success


class LocalDeliveryProvider(DeliveryProvider):
    """Local filesystem delivery provider"""
    
    @handle_errors
    async def deliver(self, capsule: QLCapsule, config: DeliveryConfig) -> DeliveryResult:
        """Deliver capsule to local filesystem"""
        try:
            destination = Path(config.destination)
            project_name = config.metadata.get("project_name", capsule.id) if config.metadata else capsule.id
            
            # Create project directory
            project_path = destination / project_name
            project_path.mkdir(parents=True, exist_ok=True)
            
            # Write all source files
            for file_path, content in capsule.source_code.items():
                file_full_path = project_path / file_path
                file_full_path.parent.mkdir(parents=True, exist_ok=True)
                file_full_path.write_text(content)
            
            # Write all test files
            for file_path, content in capsule.tests.items():
                file_full_path = project_path / file_path
                file_full_path.parent.mkdir(parents=True, exist_ok=True)
                file_full_path.write_text(content)
            
            # Write documentation
            readme_path = project_path / "README.md"
            readme_path.write_text(capsule.documentation)
            
            # Write manifest
            manifest_path = project_path / "qlp-manifest.json"
            manifest_path.write_text(json.dumps(capsule.manifest, indent=2))
            
            # Calculate size
            total_size = sum(
                len(content.encode()) for content in 
                list(capsule.source_code.values()) + 
                list(capsule.tests.values()) + 
                [capsule.documentation]
            )
            
            logger.info(f"Delivered capsule to local filesystem: {project_path}")
            
            return DeliveryResult(
                success=True,
                mode="local",
                destination=str(project_path),
                url=f"file://{project_path.absolute()}",
                metadata={
                    'project_path': str(project_path),
                    'files_count': len(capsule.source_code) + len(capsule.tests) + 2,
                    'total_size': total_size
                }
            )
            
        except Exception as e:
            logger.error(f"Local delivery failed: {str(e)}")
            return DeliveryResult(
                success=False,
                mode="local",
                destination=config.destination,
                error=str(e)
            )
    
    async def verify(self, delivery_result: DeliveryResult) -> bool:
        """Verify local delivery"""
        if not delivery_result.success:
            return False
        
        project_path = Path(delivery_result.metadata.get('project_path', ''))
        return project_path.exists() and project_path.is_dir()


class CapsuleDeliveryService:
    """Main service for capsule delivery orchestration"""
    
    def __init__(self, db_session=None):
        self.providers: Dict[str, DeliveryProvider] = {
            'local': LocalDeliveryProvider(),
            's3': S3DeliveryProvider(),
            'azure': AzureBlobDeliveryProvider(),
            'gcs': GCSDeliveryProvider(),
            'git': GitDeliveryProvider(),
            'github': GitDeliveryProvider(),
            'gitlab': GitDeliveryProvider()
        }
        self.db = db_session
        if self.db:
            from src.common.database import CapsuleRepository
            self.repository = CapsuleRepository(self.db)
    
    async def deliver(
        self,
        capsule: QLCapsule,
        configs: List[DeliveryConfig],
        version_id: Optional[str] = None
    ) -> List[DeliveryResult]:
        """Deliver capsule to multiple destinations"""
        results = []
        delivery_records = []
        
        # Execute deliveries in parallel
        tasks = []
        for config in configs:
            provider = self.providers.get(config.mode)
            if not provider:
                result = DeliveryResult(
                    success=False,
                    mode=config.mode,
                    destination=config.destination,
                    error=f"Unknown delivery mode: {config.mode}"
                )
                results.append(result)
                
                # Store failed delivery in database
                if self.repository:
                    delivery_data = {
                        'capsule_id': capsule.id,
                        'version_id': version_id,
                        'provider': config.mode,
                        'destination': config.destination,
                        'delivery_config': asdict(config),
                        'status': 'failed',
                        'error_message': result.error
                    }
                    delivery_records.append(self.repository.create_delivery(delivery_data))
                continue
            
            tasks.append(self._deliver_with_tracking(provider, capsule, config, version_id))
        
        # Wait for all deliveries
        if tasks:
            delivery_results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result_data in enumerate(delivery_results):
                if isinstance(result_data, Exception):
                    result = DeliveryResult(
                        success=False,
                        mode=configs[i].mode,
                        destination=configs[i].destination,
                        error=str(result_data)
                    )
                    results.append(result)
                    
                    # Store failed delivery in database
                    if self.repository:
                        delivery_data = {
                            'capsule_id': capsule.id,
                            'version_id': version_id,
                            'provider': configs[i].mode,
                            'destination': configs[i].destination,
                            'delivery_config': asdict(configs[i]),
                            'status': 'failed',
                            'error_message': str(result_data)
                        }
                        delivery_records.append(self.repository.create_delivery(delivery_data))
                else:
                    result, delivery_record = result_data
                    results.append(result)
                    if delivery_record:
                        delivery_records.append(delivery_record)
        
        # Log results
        successful = sum(1 for r in results if r.success)
        logger.info(
            f"Delivered capsule to {successful}/{len(results)} destinations",
            capsule_id=capsule.id,
            successful=successful,
            total=len(results)
        )
        
        return results
    
    async def _deliver_with_tracking(
        self,
        provider: DeliveryProvider,
        capsule: QLCapsule,
        config: DeliveryConfig,
        version_id: Optional[str]
    ) -> tuple:
        """Deliver with database tracking"""
        delivery_record = None
        
        try:
            # Create delivery record in database
            if self.repository:
                delivery_data = {
                    'capsule_id': capsule.id,
                    'version_id': version_id,
                    'provider': config.mode,
                    'destination': config.destination,
                    'delivery_config': config.model_dump(),
                    'status': 'pending'
                }
                delivery_record = self.repository.create_delivery(delivery_data)
            
            # Perform the actual delivery
            result = await provider.deliver(capsule, config)
            
            # Update delivery record with results
            if self.repository and delivery_record:
                update_data = {
                    'status': 'success' if result.success else 'failed',
                    'url': result.url,
                    'signed_url': result.signed_url,
                    'checksum': result.checksum,
                    'metadata': result.metadata or {}
                }
                
                if result.error:
                    update_data['error_message'] = result.error
                
                self.repository.update_delivery_status(str(delivery_record.id), **update_data)
            
            return result, delivery_record
            
        except Exception as e:
            # Update delivery record with error
            if self.repository and delivery_record:
                self.repository.update_delivery_status(
                    str(delivery_record.id),
                    status='failed',
                    error_message=str(e)
                )
            
            raise e
    
    def sign_capsule(self, capsule: QLCapsule, private_key: str) -> str:
        """Create digital signature for capsule"""
        # Create canonical representation
        canonical_data = json.dumps({
            'id': capsule.id,
            'request_id': capsule.request_id,
            'manifest': capsule.manifest,
            'file_checksums': {
                path: hashlib.sha256(content.encode()).hexdigest()
                for path, content in {**capsule.source_code, **capsule.tests}.items()
            }
        }, sort_keys=True).encode()
        
        # Create HMAC signature
        signature = hmac.new(
            private_key.encode(),
            canonical_data,
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def verify_signature(self, capsule: QLCapsule, signature: str, private_key: str) -> bool:
        """Verify capsule signature"""
        expected_signature = self.sign_capsule(capsule, private_key)
        return hmac.compare_digest(signature, expected_signature)
    
    async def create_delivery_report(
        self,
        capsule_id: str,
        results: List[DeliveryResult]
    ) -> Dict[str, Any]:
        """Create comprehensive delivery report"""
        return {
            'capsule_id': capsule_id,
            'timestamp': datetime.utcnow().isoformat(),
            'summary': {
                'total_destinations': len(results),
                'successful': sum(1 for r in results if r.success),
                'failed': sum(1 for r in results if not r.success)
            },
            'destinations': [
                {
                    'mode': r.mode,
                    'destination': r.destination,
                    'success': r.success,
                    'url': r.url,
                    'signed_url': r.signed_url,
                    'error': r.error
                }
                for r in results
            ],
            'recommendations': self._generate_recommendations(results)
        }
    
    def _generate_recommendations(self, results: List[DeliveryResult]) -> List[str]:
        """Generate recommendations based on delivery results"""
        recommendations = []
        
        # Check for failures
        failures = [r for r in results if not r.success]
        if failures:
            recommendations.append(f"Retry failed deliveries: {', '.join(f.mode for f in failures)}")
        
        # Check for missing backup
        modes = {r.mode for r in results if r.success}
        if 'git' not in modes:
            recommendations.append("Consider adding Git repository backup for version control")
        
        if not any(m in modes for m in ['s3', 'azure', 'gcs']):
            recommendations.append("Add cloud storage backup for durability")
        
        return recommendations


def get_delivery_service(db_session=None) -> CapsuleDeliveryService:
    """Get delivery service instance with optional database session"""
    return CapsuleDeliveryService(db_session)