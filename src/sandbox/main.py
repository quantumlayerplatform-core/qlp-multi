"""
Execution Sandbox Service

Secure code execution environment with Docker-based isolation.
Supports multiple languages and resource limits.
"""

import asyncio
import docker
import json
import logging
import os
import tempfile
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
import httpx
from pydantic import BaseModel, Field, ConfigDict

# Import Kata executor if available
try:
    from .kata_executor import KataExecutor
    kata_available = True
except ImportError:
    kata_available = False
    KataExecutor = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Supported languages and their Docker images
LANGUAGE_IMAGES = {
    "python": "python:3.11-slim",
    "javascript": "node:18-slim",
    "typescript": "node:18-slim",
    "go": "golang:1.21-alpine",
    "java": "openjdk:17-slim",
    "rust": "rust:1.75-slim",
}

# Language-specific file extensions
LANGUAGE_EXTENSIONS = {
    "python": ".py",
    "javascript": ".js",
    "typescript": ".ts",
    "go": ".go",
    "java": ".java",
    "rust": ".rs",
}

# Language-specific run commands
LANGUAGE_COMMANDS = {
    "python": ["python", "{filename}"],
    "javascript": ["node", "{filename}"],
    "typescript": ["sh", "-c", "npx tsx {filename}"],
    "go": ["sh", "-c", "go run {filename}"],
    "java": ["sh", "-c", "javac {filename} && java {classname}"],
    "rust": ["sh", "-c", "rustc {filename} -o /tmp/program && /tmp/program"],
}

class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

class ResourceLimits(BaseModel):
    """Resource limits for execution"""
    cpu_count: int = Field(default=1, description="Number of CPU cores")
    memory: str = Field(default="512m", description="Memory limit (e.g., '512m', '1g')")
    timeout: int = Field(default=30, description="Execution timeout in seconds")
    disk_size: str = Field(default="100m", description="Disk size limit")

class ExecutionRequest(BaseModel):
    """Request to execute code"""
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})
    
    code: str = Field(..., description="Code to execute")
    language: str = Field(..., description="Programming language")
    inputs: Optional[Dict[str, Any]] = Field(default=None, description="Input data")
    resource_limits: Optional[ResourceLimits] = Field(default_factory=ResourceLimits)
    dependencies: Optional[List[str]] = Field(default=None, description="Package dependencies")
    test_mode: bool = Field(default=False, description="Run in test mode")
    runtime: Optional[str] = Field(default="docker", description="Execution runtime: docker or kata")

class ExecutionResult(BaseModel):
    """Result of code execution"""
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})
    
    execution_id: str
    status: ExecutionStatus
    output: Optional[str] = None
    error: Optional[str] = None
    exit_code: Optional[int] = None
    duration_ms: Optional[int] = None
    runtime: Optional[str] = Field(default="docker", description="Runtime used for execution")
    resource_usage: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

class SandboxManager:
    """Manages Docker containers for code execution"""
    
    def __init__(self):
        self.client = None
        try:
            self.client = docker.from_env()
            logger.info("Docker client initialized successfully")
            # Test connection
            self.client.ping()
        except Exception as e:
            logger.warning(f"Docker client initialization failed: {e}")
            logger.warning("Sandbox service will run with limited functionality")
    
    async def execute_code(
        self,
        code: str,
        language: str,
        inputs: Optional[Dict[str, Any]] = None,
        resource_limits: ResourceLimits = ResourceLimits(),
        dependencies: Optional[List[str]] = None
    ) -> ExecutionResult:
        """Execute code in a secure Docker container"""
        
        execution_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Check if Docker is available
        if not self.client:
            return ExecutionResult(
                execution_id=execution_id,
                status=ExecutionStatus.FAILED,
                error="Docker is not available",
                execution_time=0
            )
        
        # Validate language
        if language not in LANGUAGE_IMAGES:
            raise ValueError(f"Unsupported language: {language}")
        
        result = ExecutionResult(
            execution_id=execution_id,
            status=ExecutionStatus.PENDING
        )
        
        container = None
        temp_dir = None
        
        try:
            # Create temporary directory for code
            temp_dir = tempfile.mkdtemp(prefix="sandbox_")
            code_file = os.path.join(temp_dir, f"main{LANGUAGE_EXTENSIONS[language]}")
            
            # Prepare code with any inputs
            if inputs:
                # Inject inputs as environment variables or command line args
                # This is language-specific
                prepared_code = self._prepare_code_with_inputs(code, language, inputs)
            else:
                prepared_code = code
            
            # Write code to file
            with open(code_file, 'w') as f:
                f.write(prepared_code)
            
            # Install dependencies if needed
            if dependencies and language in ["python", "javascript", "typescript"]:
                await self._install_dependencies(temp_dir, language, dependencies)
            
            # Prepare Docker run command
            image = LANGUAGE_IMAGES[language]
            command = self._get_run_command(language, "main")
            
            # Create and run container
            logger.info(f"Creating container for {language} execution")
            
            container = self.client.containers.run(
                image=image,
                command=command,
                volumes={temp_dir: {'bind': '/app', 'mode': 'rw'}},
                working_dir='/app',
                detach=True,
                mem_limit=resource_limits.memory,
                cpu_count=resource_limits.cpu_count,
                remove=False,
                network_mode='none',  # No network access for security
                read_only=False,  # Allow writing to /tmp
                environment={
                    'PYTHONUNBUFFERED': '1',
                    'NODE_ENV': 'production'
                }
            )
            
            result.status = ExecutionStatus.RUNNING
            
            # Wait for completion with timeout
            try:
                exit_code = container.wait(timeout=resource_limits.timeout)['StatusCode']
                
                # Get output
                output = container.logs(stdout=True, stderr=False).decode('utf-8')
                error = container.logs(stdout=False, stderr=True).decode('utf-8')
                
                result.exit_code = exit_code
                result.output = output
                result.error = error if error else None
                result.status = ExecutionStatus.COMPLETED if exit_code == 0 else ExecutionStatus.FAILED
                
            except Exception as timeout_error:
                logger.warning(f"Container execution timeout: {timeout_error}")
                result.status = ExecutionStatus.TIMEOUT
                result.error = f"Execution exceeded timeout of {resource_limits.timeout} seconds"
                
                # Force stop container
                try:
                    container.stop(timeout=5)
                except:
                    container.kill()
            
            # Get resource usage
            try:
                stats = container.stats(stream=False)
                result.resource_usage = {
                    'cpu_percent': self._calculate_cpu_percent(stats),
                    'memory_usage_mb': stats['memory_stats'].get('usage', 0) / (1024 * 1024),
                    'memory_limit_mb': stats['memory_stats'].get('limit', 0) / (1024 * 1024)
                }
            except:
                pass
            
        except docker.errors.ImageNotFound:
            result.status = ExecutionStatus.FAILED
            result.error = f"Docker image not found for {language}. Pulling image..."
            # Try to pull the image
            try:
                self.client.images.pull(LANGUAGE_IMAGES[language])
                # Retry execution
                return await self.execute_code(code, language, inputs, resource_limits, dependencies)
            except Exception as pull_error:
                result.error = f"Failed to pull Docker image: {str(pull_error)}"
                
        except Exception as e:
            logger.error(f"Execution error: {e}")
            result.status = ExecutionStatus.FAILED
            result.error = str(e)
            
        finally:
            # Cleanup
            if container:
                try:
                    container.remove(force=True)
                except:
                    pass
            
            if temp_dir and os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
            
            # Calculate duration
            result.duration_ms = int((time.time() - start_time) * 1000)
            result.completed_at = datetime.utcnow()
        
        return result
    
    def _prepare_code_with_inputs(self, code: str, language: str, inputs: Dict[str, Any]) -> str:
        """Prepare code with inputs based on language"""
        
        if language == "python":
            # Inject inputs as variables at the beginning
            input_code = "# Injected inputs\n"
            for key, value in inputs.items():
                input_code += f"{key} = {repr(value)}\n"
            return input_code + "\n" + code
            
        elif language in ["javascript", "typescript"]:
            # Inject as const declarations
            input_code = "// Injected inputs\n"
            for key, value in inputs.items():
                input_code += f"const {key} = {json.dumps(value)};\n"
            return input_code + "\n" + code
            
        elif language == "go":
            # For Go, we might need to modify the code more carefully
            # For now, just return as-is
            return code
            
        else:
            return code
    
    async def _install_dependencies(self, temp_dir: str, language: str, dependencies: List[str]):
        """Install dependencies before execution"""
        
        if language == "python":
            # Create requirements.txt
            req_file = os.path.join(temp_dir, "requirements.txt")
            with open(req_file, 'w') as f:
                f.write('\n'.join(dependencies))
                
        elif language in ["javascript", "typescript"]:
            # Create package.json
            package_json = {
                "name": "sandbox-execution",
                "version": "1.0.0",
                "dependencies": {dep: "*" for dep in dependencies}
            }
            pkg_file = os.path.join(temp_dir, "package.json")
            with open(pkg_file, 'w') as f:
                json.dump(package_json, f)
    
    def _get_run_command(self, language: str, filename: str) -> List[str]:
        """Get the run command for a language"""
        
        command_template = LANGUAGE_COMMANDS[language]
        command = []
        
        for part in command_template:
            if "{filename}" in part:
                part = part.replace("{filename}", f"{filename}{LANGUAGE_EXTENSIONS[language]}")
            if "{classname}" in part:
                part = part.replace("{classname}", filename.capitalize())
            command.append(part)
        
        return command
    
    def _calculate_cpu_percent(self, stats: Dict) -> float:
        """Calculate CPU usage percentage from Docker stats"""
        try:
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                       stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                          stats['precpu_stats']['system_cpu_usage']
            
            if system_delta > 0 and cpu_delta > 0:
                cpu_percent = (cpu_delta / system_delta) * \
                             len(stats['cpu_stats']['cpu_usage'].get('percpu_usage', [1])) * 100.0
                return round(cpu_percent, 2)
        except:
            pass
        return 0.0

# Global sandbox manager
sandbox_manager = None
kata_executor = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global sandbox_manager, kata_executor
    
    logger.info("Starting Execution Sandbox Service...")
    
    # Initialize sandbox manager
    try:
        sandbox_manager = SandboxManager()
        logger.info("Sandbox manager initialized")
    except Exception as e:
        logger.error(f"Failed to initialize sandbox manager: {e}")
        # Don't raise - allow service to start without Docker
    
    # Initialize Kata executor if available
    if kata_available:
        try:
            kata_executor = KataExecutor()
            logger.info("Kata executor initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Kata executor: {e}")
            kata_executor = None
    else:
        kata_executor = None
    
    yield
    
    logger.info("Shutting down Execution Sandbox Service...")

# Create FastAPI app
app = FastAPI(
    title="Quantum Layer Platform Execution Sandbox",
    description="Secure code execution environment for Quantum Layer Platform",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Check service health"""
    
    # Check Docker availability
    docker_status = "unavailable"
    try:
        if sandbox_manager and sandbox_manager.client:
            sandbox_manager.client.ping()
            docker_status = "healthy"
    except:
        pass
    
    return {
        "status": "healthy" if docker_status == "healthy" else "degraded",
        "service": "execution_sandbox",
        "docker": docker_status,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/execute", response_model=ExecutionResult)
async def execute_code(request: ExecutionRequest):
    """Execute code in sandbox"""
    
    # Check if Kata runtime is requested
    if request.runtime == "kata":
        if not kata_executor:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Kata executor not available"
            )
        
        try:
            # Execute using Kata Containers
            result = await kata_executor.execute_code(
                code=request.code,
                language=request.language,
                timeout=request.resource_limits.timeout if request.resource_limits else 30,
                memory_limit=request.resource_limits.memory if request.resource_limits else "256Mi",
                cpu_limit="100m"
            )
            
            # Convert to ExecutionResult format
            execution_result = ExecutionResult(
                execution_id=result["execution_id"],
                status=ExecutionStatus(result["status"]),
                output=result.get("output"),
                error=result.get("error"),
                exit_code=result.get("exit_code"),
                duration_ms=result.get("duration_ms"),
                runtime=result.get("runtime", "kata")
            )
            
            return JSONResponse(content=jsonable_encoder(execution_result))
            
        except Exception as e:
            logger.error(f"Kata execution error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Kata execution failed: {str(e)}"
            )
    
    # Default Docker execution
    if not sandbox_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sandbox manager not initialized"
        )
    
    try:
        result = await sandbox_manager.execute_code(
            code=request.code,
            language=request.language,
            inputs=request.inputs,
            resource_limits=request.resource_limits or ResourceLimits(),
            dependencies=request.dependencies
        )
        
        return JSONResponse(content=jsonable_encoder(result))
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Execution error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Execution failed: {str(e)}"
        )

@app.get("/languages")
async def list_languages():
    """List supported languages"""
    return {
        "languages": list(LANGUAGE_IMAGES.keys()),
        "details": {
            lang: {
                "image": image,
                "extension": LANGUAGE_EXTENSIONS.get(lang),
                "command": LANGUAGE_COMMANDS.get(lang)
            }
            for lang, image in LANGUAGE_IMAGES.items()
        }
    }

@app.post("/test/simple")
async def test_simple_execution():
    """Test simple code execution"""
    
    test_code = {
        "python": "print('Hello from Python!')\nprint(2 + 2)",
        "javascript": "console.log('Hello from JavaScript!');\nconsole.log(2 + 2);",
        "go": 'package main\nimport "fmt"\nfunc main() { fmt.Println("Hello from Go!") }'
    }
    
    results = {}
    
    for language, code in test_code.items():
        try:
            result = await sandbox_manager.execute_code(
                code=code,
                language=language,
                resource_limits=ResourceLimits(timeout=10)
            )
            results[language] = {
                "status": result.status,
                "output": result.output,
                "error": result.error,
                "duration_ms": result.duration_ms
            }
        except Exception as e:
            results[language] = {
                "status": "error",
                "error": str(e)
            }
    
    return results

@app.post("/test/with_inputs")
async def test_with_inputs():
    """Test execution with inputs"""
    
    python_code = """
# Use the injected inputs
result = x + y
print(f"The sum of {x} and {y} is {result}")
print(f"User: {user_name}")
"""
    
    result = await sandbox_manager.execute_code(
        code=python_code,
        language="python",
        inputs={
            "x": 10,
            "y": 20,
            "user_name": "Test User"
        }
    )
    
    return JSONResponse(content=jsonable_encoder(result))

@app.post("/test/resource_limits")
async def test_resource_limits():
    """Test resource limit enforcement"""
    
    # Test timeout
    timeout_code = """
import time
print("Starting long operation...")
time.sleep(10)
print("This should not print")
"""
    
    result = await sandbox_manager.execute_code(
        code=timeout_code,
        language="python",
        resource_limits=ResourceLimits(timeout=2)
    )
    
    return JSONResponse(content=jsonable_encoder(result))

if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment or use default
    port = int(os.getenv("SANDBOX_PORT", "8004"))
    
    uvicorn.run(
        app,  # Use the app object directly
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
