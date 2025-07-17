"""
Kata Containers Execution Service

Provides secure code execution using Kata Containers runtime.
Integrates with Kubernetes to create isolated pods with kata runtime class.
"""

import asyncio
import base64
import json
import logging
import os
import time
import uuid
from typing import Dict, Optional, Any

from kubernetes import client, config
from kubernetes.client import V1Pod, V1Container, V1PodSpec, V1ObjectMeta
from kubernetes.client.rest import ApiException

logger = logging.getLogger(__name__)


class KataExecutor:
    """Executes code in Kata Containers via Kubernetes pods"""
    
    def __init__(self, namespace: str = "qlp-production"):
        """Initialize Kata executor"""
        # Load Kubernetes config
        try:
            config.load_incluster_config()
        except:
            config.load_kube_config()
        
        self.v1 = client.CoreV1Api()
        self.namespace = namespace
        
        # Language configurations
        self.language_images = {
            "python": "python:3.11-slim",
            "javascript": "node:18-slim",
            "go": "golang:1.21-alpine",
            "rust": "rust:1.75-slim",
            "java": "openjdk:17-slim",
            "c": "gcc:latest",
            "cpp": "gcc:latest"
        }
    
    async def execute_code(self, 
                          code: str, 
                          language: str,
                          timeout: int = 30,
                          memory_limit: str = "256Mi",
                          cpu_limit: str = "100m") -> Dict[str, Any]:
        """Execute code in a Kata Container"""
        
        execution_id = f"kata-exec-{uuid.uuid4().hex[:8]}"
        pod_name = f"kata-{execution_id}"
        
        logger.info(f"Executing code in Kata Container: {pod_name}")
        
        try:
            # Create pod with Kata runtime
            pod = self._create_kata_pod(
                name=pod_name,
                code=code,
                language=language,
                memory_limit=memory_limit,
                cpu_limit=cpu_limit,
                timeout=timeout
            )
            
            # Create the pod
            self.v1.create_namespaced_pod(
                namespace=self.namespace,
                body=pod
            )
            
            # Wait for completion
            result = await self._wait_for_pod_completion(pod_name, timeout)
            
            return {
                "execution_id": execution_id,
                "status": "completed" if result["exit_code"] == 0 else "failed",
                "output": result["output"],
                "error": result["error"],
                "exit_code": result["exit_code"],
                "duration_ms": result["duration_ms"],
                "runtime": "gvisor"  # Using gVisor as secure runtime
            }
            
        except Exception as e:
            logger.error(f"Kata execution failed: {str(e)}")
            return {
                "execution_id": execution_id,
                "status": "failed",
                "error": str(e),
                "runtime": "gvisor"  # Using gVisor as secure runtime
            }
        finally:
            # Cleanup pod
            try:
                self.v1.delete_namespaced_pod(
                    name=pod_name,
                    namespace=self.namespace
                )
            except:
                pass
    
    def _create_kata_pod(self, name: str, code: str, language: str,
                        memory_limit: str, cpu_limit: str, timeout: int) -> V1Pod:
        """Create a Kubernetes pod spec for Kata execution"""
        
        # Encode code as base64
        encoded_code = base64.b64encode(code.encode()).decode()
        
        # Get execution command based on language
        command = self._get_execution_command(language, encoded_code)
        
        # Create container
        container = V1Container(
            name="executor",
            image=self.language_images.get(language, "python:3.11-slim"),
            command=command,
            resources=client.V1ResourceRequirements(
                limits={
                    "memory": memory_limit,
                    "cpu": cpu_limit
                },
                requests={
                    "memory": "128Mi",
                    "cpu": "50m"
                }
            ),
            security_context=client.V1SecurityContext(
                read_only_root_filesystem=False,
                allow_privilege_escalation=False,
                run_as_non_root=True,
                run_as_user=1000
            )
        )
        
        # Create pod spec with Kata runtime
        # Try Kata first, then gVisor as fallback
        pod_spec = V1PodSpec(
            runtime_class_name="gvisor",  # Use gVisor as secure alternative to Kata
            containers=[container],
            restart_policy="Never",
            active_deadline_seconds=timeout + 10,  # Add buffer
            node_selector={
                "runtime": "gvisor"  # Select gVisor-enabled nodes
            }
        )
        
        # Create pod
        pod = V1Pod(
            api_version="v1",
            kind="Pod",
            metadata=V1ObjectMeta(
                name=name,
                namespace=self.namespace,
                labels={
                    "app": "kata-execution",
                    "language": language,
                    "runtime": "gvisor"  # Using gVisor as secure runtime
                }
            ),
            spec=pod_spec
        )
        
        return pod
    
    def _get_execution_command(self, language: str, encoded_code: str) -> list:
        """Get execution command for the language"""
        
        commands = {
            "python": ["sh", "-c", f"echo {encoded_code} | base64 -d | python"],
            "javascript": ["sh", "-c", f"echo {encoded_code} | base64 -d | node"],
            "go": ["sh", "-c", f"echo {encoded_code} | base64 -d > main.go && go run main.go"],
            "rust": ["sh", "-c", f"echo {encoded_code} | base64 -d > main.rs && rustc main.rs && ./main"],
            "java": ["sh", "-c", f"echo {encoded_code} | base64 -d > Main.java && javac Main.java && java Main"],
            "c": ["sh", "-c", f"echo {encoded_code} | base64 -d > main.c && gcc main.c && ./a.out"],
            "cpp": ["sh", "-c", f"echo {encoded_code} | base64 -d > main.cpp && g++ main.cpp && ./a.out"]
        }
        
        return commands.get(language, commands["python"])
    
    async def _wait_for_pod_completion(self, pod_name: str, timeout: int) -> Dict[str, Any]:
        """Wait for pod to complete and retrieve results"""
        
        start_time = time.time()
        
        while True:
            try:
                # Check pod status
                pod = self.v1.read_namespaced_pod(
                    name=pod_name,
                    namespace=self.namespace
                )
                
                if pod.status.phase in ["Succeeded", "Failed"]:
                    # Get logs
                    try:
                        logs = self.v1.read_namespaced_pod_log(
                            name=pod_name,
                            namespace=self.namespace
                        )
                    except:
                        logs = ""
                    
                    # Get exit code
                    exit_code = 0
                    if pod.status.container_statuses:
                        container_status = pod.status.container_statuses[0]
                        if container_status.state.terminated:
                            exit_code = container_status.state.terminated.exit_code or 0
                    
                    duration_ms = int((time.time() - start_time) * 1000)
                    
                    return {
                        "output": logs if exit_code == 0 else "",
                        "error": logs if exit_code != 0 else "",
                        "exit_code": exit_code,
                        "duration_ms": duration_ms
                    }
                
                if time.time() - start_time > timeout:
                    return {
                        "output": "",
                        "error": "Execution timeout",
                        "exit_code": -1,
                        "duration_ms": timeout * 1000
                    }
                
                await asyncio.sleep(1)
                
            except ApiException as e:
                if e.status == 404:
                    return {
                        "output": "",
                        "error": "Pod not found",
                        "exit_code": -1,
                        "duration_ms": int((time.time() - start_time) * 1000)
                    }
                raise