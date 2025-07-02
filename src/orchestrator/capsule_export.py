"""
QLCapsule Export and Streaming Services
Production-ready export functionality with multiple formats
"""

from typing import Dict, Any, List, Optional, AsyncIterator
from pathlib import Path
import asyncio
import tarfile
import zipfile
import json
import yaml
from io import BytesIO
import tempfile
from datetime import datetime
import structlog

from src.common.models import QLCapsule
from src.common.error_handling import handle_errors, QLPError, ErrorSeverity


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

logger = structlog.get_logger()


class CapsuleExporter:
    """Export QLCapsules in various formats"""
    
    @handle_errors
    async def export_as_zip(self, capsule: QLCapsule) -> bytes:
        """Export capsule as ZIP archive"""
        output = BytesIO()
        
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add source files
            for path, content in capsule.source_code.items():
                zf.writestr(path, content)
            
            # Add test files
            for path, content in capsule.tests.items():
                zf.writestr(path, content)
            
            # Add documentation
            zf.writestr("README.md", capsule.documentation)
            
            # Add manifest
            zf.writestr("qlp-manifest.json", json.dumps(capsule.manifest, indent=2, default=json_serial))
            
            # Add validation report
            if capsule.validation_report:
                zf.writestr(
                    "validation-report.json",
                    json.dumps(capsule.validation_report.dict(), indent=2, default=json_serial)
                )
            
            # Add deployment configuration
            if capsule.deployment_config:
                # Kubernetes manifests
                if "kubernetes" in capsule.deployment_config:
                    k8s_config = capsule.deployment_config["kubernetes"]
                    if "deployment" in k8s_config:
                        zf.writestr("k8s/deployment.yaml", k8s_config["deployment"])
                    if "service" in k8s_config:
                        zf.writestr("k8s/service.yaml", k8s_config["service"])
                    if "ingress" in k8s_config:
                        zf.writestr("k8s/ingress.yaml", k8s_config["ingress"])
                
                # Terraform configuration
                if "terraform" in capsule.deployment_config:
                    tf_config = capsule.deployment_config["terraform"]
                    if "main" in tf_config:
                        zf.writestr("terraform/main.tf", tf_config["main"])
                    if "variables" in tf_config:
                        zf.writestr("terraform/variables.tf", tf_config["variables"])
            
            # Add metadata
            metadata = {
                "capsule_id": capsule.id,
                "request_id": capsule.request_id,
                "exported_at": datetime.utcnow().isoformat(),
                "export_format": "zip",
                "metadata": capsule.metadata
            }
            zf.writestr("qlp-metadata.json", json.dumps(metadata, indent=2, default=json_serial))
        
        output.seek(0)
        logger.info(f"Exported capsule as ZIP: {capsule.id}")
        return output.read()
    
    @handle_errors
    async def export_as_tar(self, capsule: QLCapsule, compression: str = "gz") -> bytes:
        """Export capsule as TAR archive"""
        output = BytesIO()
        mode = f'w:{compression}' if compression else 'w'
        
        with tarfile.open(fileobj=output, mode=mode) as tar:
            # Helper to add content as file
            def add_file(name: str, content: str):
                data = content.encode('utf-8')
                info = tarfile.TarInfo(name=name)
                info.size = len(data)
                info.mtime = int(datetime.utcnow().timestamp())
                tar.addfile(info, BytesIO(data))
            
            # Add all source files
            for path, content in capsule.source_code.items():
                add_file(path, content)
            
            # Add all test files
            for path, content in capsule.tests.items():
                add_file(path, content)
            
            # Add documentation
            add_file("README.md", capsule.documentation)
            
            # Add manifest
            add_file("qlp-manifest.json", json.dumps(capsule.manifest, indent=2, default=json_serial))
            
            # Add validation report
            if capsule.validation_report:
                add_file(
                    "validation-report.json",
                    json.dumps(capsule.validation_report.dict(), indent=2, default=json_serial)
                )
            
            # Add deployment configs
            if capsule.deployment_config:
                if "kubernetes" in capsule.deployment_config:
                    k8s = capsule.deployment_config["kubernetes"]
                    for key, content in k8s.items():
                        # Convert content to string if it's not already
                        if isinstance(content, str):
                            add_file(f"k8s/{key}.yaml", content)
                        else:
                            # Convert to YAML string for complex objects
                            add_file(f"k8s/{key}.yaml", yaml.dump(content, default_flow_style=False))
                
                if "terraform" in capsule.deployment_config:
                    tf = capsule.deployment_config["terraform"]
                    for key, content in tf.items():
                        # Convert content to string if it's not already
                        if isinstance(content, str):
                            add_file(f"terraform/{key}.tf", content)
                        else:
                            # Convert to JSON string for complex objects
                            add_file(f"terraform/{key}.tf", json.dumps(content, indent=2, default=json_serial))
        
        output.seek(0)
        logger.info(f"Exported capsule as TAR: {capsule.id}")
        return output.read()
    
    @handle_errors
    async def export_as_docker_image(self, capsule: QLCapsule, registry: Optional[str] = None) -> str:
        """Export capsule as Docker image"""
        import docker
        import tempfile
        
        # Check if Dockerfile exists
        dockerfile_content = None
        for path, content in capsule.source_code.items():
            if path.lower() == "dockerfile":
                dockerfile_content = content
                break
        
        if not dockerfile_content:
            raise QLPError("No Dockerfile found in capsule", severity=ErrorSeverity.MEDIUM)
        
        # Create temporary directory for build context
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write all files to temp directory
            for path, content in {**capsule.source_code, **capsule.tests}.items():
                file_path = Path(tmpdir) / path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content)
            
            # Write documentation
            (Path(tmpdir) / "README.md").write_text(capsule.documentation)
            
            # Build Docker image
            client = docker.from_env()
            image_tag = f"qlp-capsule:{capsule.id[:8]}"
            
            try:
                # Build image
                image, build_logs = client.images.build(
                    path=tmpdir,
                    tag=image_tag,
                    rm=True,
                    labels={
                        "qlp.capsule.id": capsule.id,
                        "qlp.request.id": capsule.request_id,
                        "qlp.created.at": datetime.utcnow().isoformat()
                    }
                )
                
                # Log build output
                for log in build_logs:
                    if 'stream' in log:
                        logger.debug(f"Docker build: {log['stream'].strip()}")
                
                # Push to registry if specified
                if registry:
                    full_tag = f"{registry}/{image_tag}"
                    image.tag(full_tag)
                    
                    # Push image
                    push_logs = client.images.push(full_tag, stream=True, decode=True)
                    for log in push_logs:
                        if 'status' in log:
                            logger.debug(f"Docker push: {log['status']}")
                    
                    logger.info(f"Pushed Docker image: {full_tag}")
                    return full_tag
                else:
                    logger.info(f"Built Docker image: {image_tag}")
                    return image_tag
                    
            except docker.errors.BuildError as e:
                raise QLPError(f"Docker build failed: {str(e)}", severity=ErrorSeverity.HIGH)
    
    @handle_errors
    async def export_as_helm_chart(self, capsule: QLCapsule) -> Dict[str, Any]:
        """Export capsule as Helm chart"""
        # Extract application metadata
        app_name = capsule.manifest.get("request", {}).get("description", "qlp-app")[:30]
        app_name = app_name.lower().replace(" ", "-").replace("_", "-")
        
        # Create Helm chart structure
        chart = {
            "apiVersion": "v2",
            "name": app_name,
            "description": f"Helm chart for {capsule.manifest.get('request', {}).get('description', 'QLP Generated Application')}",
            "type": "application",
            "version": "0.1.0",
            "appVersion": "1.0.0",
            "keywords": ["qlp", "generated"],
            "home": "https://quantumlayer.platform",
            "sources": ["https://github.com/quantumlayer/platform"],
            "maintainers": [{
                "name": "QLP",
                "email": "support@quantumlayer.platform"
            }]
        }
        
        # Values.yaml
        values = {
            "replicaCount": 2,
            "image": {
                "repository": f"qlp/{app_name}",
                "pullPolicy": "IfNotPresent",
                "tag": "latest"
            },
            "service": {
                "type": "ClusterIP",
                "port": 80,
                "targetPort": 8000
            },
            "ingress": {
                "enabled": True,
                "className": "nginx",
                "hosts": [{
                    "host": f"{app_name}.local",
                    "paths": [{
                        "path": "/",
                        "pathType": "Prefix"
                    }]
                }]
            },
            "resources": {
                "limits": {
                    "cpu": "500m",
                    "memory": "512Mi"
                },
                "requests": {
                    "cpu": "250m",
                    "memory": "256Mi"
                }
            },
            "autoscaling": {
                "enabled": True,
                "minReplicas": 2,
                "maxReplicas": 10,
                "targetCPUUtilizationPercentage": 80
            }
        }
        
        # Templates
        templates = {}
        
        # Deployment template
        templates["deployment.yaml"] = f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{{{ include "{app_name}.fullname" . }}}}
  labels:
    {{{{- include "{app_name}.labels" . | nindent 4 }}}}
spec:
  replicas: {{{{ .Values.replicaCount }}}}
  selector:
    matchLabels:
      {{{{- include "{app_name}.selectorLabels" . | nindent 6 }}}}
  template:
    metadata:
      labels:
        {{{{- include "{app_name}.selectorLabels" . | nindent 8 }}}}
    spec:
      containers:
      - name: {{{{ .Chart.Name }}}}
        image: "{{{{ .Values.image.repository }}}}:{{{{ .Values.image.tag | default .Chart.AppVersion }}}}"
        imagePullPolicy: {{{{ .Values.image.pullPolicy }}}}
        ports:
        - name: http
          containerPort: {{{{ .Values.service.targetPort }}}}
          protocol: TCP
        resources:
          {{{{- toYaml .Values.resources | nindent 12 }}}}
"""
        
        # Service template
        templates["service.yaml"] = f"""apiVersion: v1
kind: Service
metadata:
  name: {{{{ include "{app_name}.fullname" . }}}}
  labels:
    {{{{- include "{app_name}.labels" . | nindent 4 }}}}
spec:
  type: {{{{ .Values.service.type }}}}
  ports:
  - port: {{{{ .Values.service.port }}}}
    targetPort: http
    protocol: TCP
    name: http
  selector:
    {{{{- include "{app_name}.selectorLabels" . | nindent 4 }}}}
"""
        
        # Helpers template
        templates["_helpers.tpl"] = f"""{{{{- define "{app_name}.name" -}}}}
{{{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}}}
{{{{- end }}}}

{{{{- define "{app_name}.fullname" -}}}}
{{{{- if .Values.fullnameOverride }}}}
{{{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}}}
{{{{- else }}}}
{{{{- $name := default .Chart.Name .Values.nameOverride }}}}
{{{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}}}
{{{{- end }}}}
{{{{- end }}}}

{{{{- define "{app_name}.labels" -}}}}
helm.sh/chart: {{{{ include "{app_name}.chart" . }}}}
{{{{ include "{app_name}.selectorLabels" . }}}}
{{{{- if .Chart.AppVersion }}}}
app.kubernetes.io/version: {{{{ .Chart.AppVersion | quote }}}}
{{{{- end }}}}
app.kubernetes.io/managed-by: {{{{ .Release.Service }}}}
{{{{- end }}}}

{{{{- define "{app_name}.selectorLabels" -}}}}
app.kubernetes.io/name: {{{{ include "{app_name}.name" . }}}}
app.kubernetes.io/instance: {{{{ .Release.Name }}}}
{{{{- end }}}}

{{{{- define "{app_name}.chart" -}}}}
{{{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}}}
{{{{- end }}}}
"""
        
        result = {
            "chart": chart,
            "values": values,
            "templates": templates,
            "capsule_id": capsule.id
        }
        
        logger.info(f"Exported capsule as Helm chart: {app_name}")
        return result
    
    @handle_errors
    async def export_as_terraform(self, capsule: QLCapsule) -> Dict[str, str]:
        """Export capsule deployment as Terraform configuration"""
        tf_files = {}
        
        # Main configuration
        tf_files["main.tf"] = """terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${var.app_name}-cluster"
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# Task Definition
resource "aws_ecs_task_definition" "app" {
  family                   = var.app_name
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn
  
  container_definitions = jsonencode([{
    name  = var.app_name
    image = var.container_image
    
    portMappings = [{
      containerPort = var.container_port
      protocol      = "tcp"
    }]
    
    environment = [
      for k, v in var.environment_variables : {
        name  = k
        value = v
      }
    ]
    
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.main.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])
}

# ECS Service
resource "aws_ecs_service" "main" {
  name            = var.app_name
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.app_count
  launch_type     = "FARGATE"
  
  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }
  
  load_balancer {
    target_group_arn = aws_lb_target_group.main.arn
    container_name   = var.app_name
    container_port   = var.container_port
  }
}
"""
        
        # Variables
        tf_files["variables.tf"] = f"""variable "app_name" {{
  description = "Application name"
  type        = string
  default     = "qlp-{capsule.id[:8]}"
}}

variable "aws_region" {{
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}}

variable "container_image" {{
  description = "Container image URL"
  type        = string
  default     = "qlp/{capsule.id[:8]}:latest"
}}

variable "container_port" {{
  description = "Container port"
  type        = number
  default     = 8000
}}

variable "task_cpu" {{
  description = "Task CPU units"
  type        = string
  default     = "256"
}}

variable "task_memory" {{
  description = "Task memory (MB)"
  type        = string
  default     = "512"
}}

variable "app_count" {{
  description = "Number of app instances"
  type        = number
  default     = 2
}}

variable "environment_variables" {{
  description = "Environment variables for the container"
  type        = map(string)
  default     = {{}}
}}

variable "private_subnet_ids" {{
  description = "Private subnet IDs"
  type        = list(string)
}}

variable "vpc_id" {{
  description = "VPC ID"
  type        = string
}}
"""
        
        # Outputs
        tf_files["outputs.tf"] = """output "cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "service_name" {
  value = aws_ecs_service.main.name
}

output "load_balancer_dns" {
  value = aws_lb.main.dns_name
}
"""
        
        # IAM roles (abbreviated)
        tf_files["iam.tf"] = """# ECS Execution Role
resource "aws_iam_role" "ecs_execution_role" {
  name = "${var.app_name}-ecs-execution-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution_role_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ECS Task Role
resource "aws_iam_role" "ecs_task_role" {
  name = "${var.app_name}-ecs-task-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
}
"""
        
        logger.info(f"Exported capsule as Terraform configuration")
        return tf_files


class CapsuleStreamer:
    """Stream large capsules efficiently"""
    
    async def stream_capsule(
        self,
        capsule: QLCapsule,
        format: str = "tar.gz",
        chunk_size: int = 8192
    ) -> AsyncIterator[bytes]:
        """Stream capsule in chunks"""
        
        # Create exporter
        exporter = CapsuleExporter()
        
        # Export to desired format
        if format == "zip":
            archive_data = await exporter.export_as_zip(capsule)
        elif format.startswith("tar"):
            compression = format.split(".")[-1] if "." in format else None
            archive_data = await exporter.export_as_tar(capsule, compression)
        else:
            raise QLPError(f"Unsupported format: {format}", severity=ErrorSeverity.MEDIUM)
        
        # Stream in chunks
        total_size = len(archive_data)
        offset = 0
        
        while offset < total_size:
            chunk = archive_data[offset:offset + chunk_size]
            yield chunk
            offset += chunk_size
            
            # Allow other tasks to run
            await asyncio.sleep(0)
        
        logger.info(f"Streamed capsule {capsule.id}: {total_size} bytes")
    
    async def stream_capsule_files(
        self,
        capsule: QLCapsule,
        file_filter: Optional[List[str]] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream individual files from capsule"""
        
        all_files = {
            **capsule.source_code,
            **capsule.tests,
            "README.md": capsule.documentation,
            "qlp-manifest.json": json.dumps(capsule.manifest, indent=2, default=json_serial)
        }
        
        # Apply filter if provided
        if file_filter:
            all_files = {k: v for k, v in all_files.items() if k in file_filter}
        
        # Stream each file
        for file_path, content in all_files.items():
            yield {
                "path": file_path,
                "content": content,
                "size": len(content),
                "type": self._get_file_type(file_path)
            }
            
            # Allow other tasks to run
            await asyncio.sleep(0)
    
    def _get_file_type(self, file_path: str) -> str:
        """Determine file type from path"""
        ext = Path(file_path).suffix.lower()
        
        type_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".java": "java",
            ".go": "go",
            ".rs": "rust",
            ".cpp": "cpp",
            ".c": "c",
            ".h": "c",
            ".hpp": "cpp",
            ".cs": "csharp",
            ".rb": "ruby",
            ".php": "php",
            ".swift": "swift",
            ".kt": "kotlin",
            ".scala": "scala",
            ".r": "r",
            ".md": "markdown",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".xml": "xml",
            ".html": "html",
            ".css": "css",
            ".scss": "scss",
            ".less": "less",
            ".sql": "sql",
            ".sh": "shell",
            ".bash": "shell",
            ".zsh": "shell",
            ".fish": "shell",
            ".ps1": "powershell",
            ".dockerfile": "dockerfile",
            ".tf": "terraform",
            ".tfvars": "terraform"
        }
        
        return type_map.get(ext, "text")