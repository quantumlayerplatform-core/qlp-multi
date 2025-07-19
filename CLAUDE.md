# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Quantum Layer Platform (QLP) is an AI-powered enterprise software development system that transforms natural language requirements into production-ready code through intelligent agent orchestration. The platform uses a microservices architecture with 5 core services communicating via REST APIs and Temporal workflows.

**Core Concept**: Request → Orchestrator → Task Decomposition → Agent Execution → Validation → Capsule Creation → Delivery/GitHub

**Current Status**: Core platform operational with Temporal Cloud integration in progress for production deployment on Azure Kubernetes Service (AKS)

## High-Level Architecture

The platform consists of 5 microservices orchestrated through Temporal workflows:

1. **Meta-Orchestrator (Port 8000)**: Central API gateway and workflow orchestration hub. All client requests enter here. Manages Temporal workflows and coordinates service interactions.

2. **Agent Factory (Port 8001)**: Multi-tier LLM agent system that routes tasks to appropriate models (GPT-4, Claude, Llama) based on complexity. Implements specialized agents for different development tasks.

3. **Validation Mesh (Port 8002)**: 6-stage validation pipeline ensuring code quality through syntax, style, security, type, and runtime checks. Uses ensemble consensus for critical decisions.

4. **Vector Memory (Port 8003)**: Semantic search and learning system using Qdrant. Stores code patterns, learns from past generations, and provides context for new requests.

5. **Execution Sandbox (Port 8004)**: Docker-based secure execution environment for multi-language code testing. Provides resource isolation and safe runtime validation.

**Key Architectural Patterns**:
- Event-driven through Temporal workflows (not traditional pub/sub)
- Service mesh communication with REST APIs
- Shared PostgreSQL for persistent storage
- Redis for caching and session management
- AI-first decision making (no hardcoded templates)

## Critical Commands Reference

### Build & Run
```bash
# ALWAYS activate virtual environment first
source venv/bin/activate

# Quick start with Docker (recommended)
docker-compose -f docker-compose.platform.yml up -d

# Local development start
./start_all.sh

# Build Docker images
./scripts/build-images.sh
```

### Test
```bash
# Run a single test
pytest tests/unit/test_specific.py::test_function -v

# Run all unit tests with coverage
pytest tests/unit -v --cov=src --cov-report=html

# Run integration tests
pytest tests/integration -v

# Test complete flow
./test_complete_flow.sh
python test_enterprise_generation.py
```

### Debug & Troubleshoot
```bash
# Check service health
curl http://localhost:8000/health

# View logs
docker logs qlp-orchestrator -f
docker-compose -f docker-compose.platform.yml logs -f

# Clean stuck workflows
./scripts/cleanup_temporal.sh

# Kill processes on ports (if stuck)
./cleanup_all.sh
```

### Code Quality
```bash
# Format code
black src/

# Lint
ruff check src/

# Type check
mypy src/

# All quality checks
make lint
```

**Latest Milestone** (July 17, 2025): 
- ✅ Complete end-to-end flow from NLP to GitHub repository
- ✅ Enterprise-grade project structure generation using AI
- ✅ Test-Driven Development (TDD) workflow integration
- ✅ Multi-language support (Python, JavaScript, Go, Java, etc.)
- ✅ Capsule packaging and delivery system
- ✅ Production-grade GitHub integration with auto-push
- ✅ AWS Bedrock integration for multi-model support
- ✅ Enterprise scalability improvements (dynamic scaling, circuit breakers)
- ✅ Enhanced fault tolerance and error handling
- ✅ Intelligent LLM-powered file organization (no hardcoded assumptions)
- ✅ Intelligent CI/CD generation (universal language support)
- ✅ GitHub Actions monitoring with auto-fix (self-healing CI/CD)
- ✅ **NEW: Temporal Cloud integration** (API key authentication)
- ✅ **NEW: Azure Container Registry** (multi-arch images)
- ✅ **NEW: Application Gateway Ingress Controller** (production ingress)
- 🔄 **IN PROGRESS: AKS deployment with Temporal Cloud**

## Technology Stack

- **Primary Language**: Python 3.11+
- **Framework**: FastAPI with Uvicorn
- **AI/LLM Integration**: 
  - Azure OpenAI (primary)
  - OpenAI, Anthropic, Groq
  - AWS Bedrock (Claude, Llama, Mistral)
  - LangChain, LlamaIndex
- **Workflow Orchestration**: Temporal Cloud (production), Temporal (local dev)
  - Endpoint: us-west-2.aws.api.temporal.io:7233
  - Namespace: qlp-beta.f6bob
- **Vector Database**: Qdrant (primary), Weaviate (alternative)
- **Traditional Databases**: PostgreSQL (Supabase in production), Redis
- **Message Queue**: Kafka (optional)
- **Container Orchestration**: Docker, Kubernetes (AKS)
  - Azure Container Registry: qlpregistry.azurecr.io
  - Application Gateway: 85.210.217.253
- **Monitoring**: Prometheus, Grafana, Jaeger, OpenTelemetry
- **Version Control**: GitHub API v3 integration

## Service Architecture

### Core Services

1. **Meta-Orchestrator** (`src/orchestrator/`) - Port 8000
   - Main control plane for request processing
   - Temporal workflow management
   - Service coordination
   - API gateway for all operations
   - Intelligent pattern selection (8 reasoning patterns)
   - Enterprise capsule generation
   - GitHub integration management

2. **Agent Factory** (`src/agents/`) - Port 8001
   - Multi-tier agent system (T0-T3)
   - Azure OpenAI optimized client
   - Model selection based on task complexity
   - Performance tracking
   - Specialized agents:
     - Base agents for general tasks
     - Capsule critic agents for quality assessment
     - Execution validators
     - Production architect agents

3. **Validation Mesh** (`src/validation/`) - Port 8002
   - 6-stage validation pipeline
   - Ensemble consensus mechanism
   - AITL (AI-in-the-loop) review
   - Confidence scoring
   - Production-grade validation
   - Runtime validation with Docker

4. **Vector Memory** (`src/memory/`) - Port 8003
   - Semantic search with Qdrant
   - Learning from past executions
   - Pattern recognition and reuse
   - Performance caching
   - Code pattern storage

5. **Execution Sandbox** (`src/sandbox/`) - Port 8004
   - Docker-based secure execution
   - Multi-language support
   - Resource isolation
   - Test execution
   - Runtime validation

### Supporting Services

- **Temporal**: Workflow orchestration
- **PostgreSQL**: Persistent storage for capsules and metadata
- **Redis**: Caching and session management
- **Qdrant**: Vector search for semantic similarity
- **Nginx**: Reverse proxy (optional)

## Key Features & Capabilities

### 1. Universal Language Support
- **No constraints**: Supports ALL programming languages
- **Intelligent detection**: AI determines optimal language based on requirements
- **Language enforcement**: Ensures consistent output in chosen language
- **Multi-language projects**: Can generate polyglot solutions

### 2. Enterprise-Grade Generation
- **Intelligent Capsule Generator**: AI-powered project structure creation
- **No templates**: Pure AI-driven decisions for optimal structure
- **Enterprise patterns**: 
  - Proper source organization
  - Comprehensive testing (unit, integration, e2e)
  - CI/CD pipelines (GitHub Actions, GitLab CI, Jenkins)
  - Containerization (Docker, docker-compose)
  - Documentation (README, API docs, architecture)
  - Security configurations
  - Monitoring and logging setup

### 3. Test-Driven Development (TDD)
- **Automatic TDD detection**: Based on task complexity and type
- **Test-first approach**: Generates tests before implementation
- **Iterative refinement**: Code evolves to pass all tests
- **Coverage tracking**: Ensures comprehensive testing

### 4. GitHub Integration
- **Automatic repository creation**: Public or private repos
- **Intelligent file organization**: Enterprise folder structure
- **Auto-generated files**:
  - README.md with project overview
  - .gitignore for language-specific ignores
  - requirements.txt/package.json/go.mod
  - GitHub Actions workflows
  - LICENSE file
- **Direct push**: No manual intervention needed
- **Pull request support**: Create PRs with generated code

### 5. Delivery System
- **Multiple formats**: ZIP, TAR, TAR.GZ
- **Package generation**: Complete project packages
- **Download endpoints**: Direct file access
- **Delivery methods**:
  - Direct download
  - GitHub push
  - Email delivery (planned)
  - Cloud storage (S3, Azure Blob - planned)

## API Endpoints

### Core Endpoints

#### Execution & Generation
- `POST /execute` - Submit NLP request for code generation
- `POST /generate/capsule` - Generate basic capsule
- `POST /generate/complete-with-github` - Generate and push to GitHub
- `POST /generate/complete-with-github-sync` - Synchronous GitHub generation
- `POST /generate/complete-pipeline` - Full pipeline with all features
- `POST /generate/robust-capsule` - Production-grade generation

#### Enterprise Features
- `POST /api/enterprise/generate` - Enterprise-grade project generation
- `POST /api/enterprise/github-push` - Push existing capsule with enterprise structure
- `GET /api/enterprise/templates` - Available project templates

#### Capsule Management
- `GET /capsule/{capsule_id}` - Get capsule details
- `POST /capsules/{capsule_id}/deliver` - Package and deliver capsule
- `GET /api/capsules/{capsule_id}/download` - Download capsule
- `POST /capsule/{capsule_id}/version` - Create capsule version
- `GET /capsule/{capsule_id}/history` - Version history

#### GitHub Operations
- `POST /api/github/push` - Push capsule to GitHub
- `GET /api/github/{owner}/{repo}/status` - Repository status
- `POST /api/github/{owner}/{repo}/pr` - Create pull request

#### Workflow Management
- `GET /workflow/status/{workflow_id}` - Workflow status
- `GET /status/{workflow_id}` - Simple status check
- `POST /approve/{workflow_id}` - Approve HITL request

#### Analysis & Optimization
- `POST /analyze/extended-reasoning` - Extended analysis
- `POST /patterns/analyze` - Pattern analysis
- `POST /patterns/recommend` - Pattern recommendations
- `POST /decompose/unified-optimization` - Optimized decomposition

### Service Documentation
All services expose OpenAPI documentation at:
- Orchestrator: http://localhost:8000/docs
- Agent Factory: http://localhost:8001/docs
- Validation Mesh: http://localhost:8002/docs
- Vector Memory: http://localhost:8003/docs
- Execution Sandbox: http://localhost:8004/docs

## AKS Deployment & Temporal Cloud

### Production Deployment (AKS)

The platform is deployed to Azure Kubernetes Service (AKS) with Temporal Cloud integration:

```bash
# Deploy to AKS
kubectl apply -f deployments/kubernetes/aks/temporal-cloud/

# Check deployments
kubectl get pods -n qlp-production

# View logs
kubectl logs -n qlp-production -l app=qlp-orchestrator -f
kubectl logs -n qlp-production -l app=qlp-temporal-worker -f

# Access via Application Gateway
curl https://85.210.217.253/health
```

### Temporal Cloud Configuration

Required environment variables for Temporal Cloud:
```bash
TEMPORAL_ADDRESS=us-west-2.aws.api.temporal.io:7233
TEMPORAL_NAMESPACE=qlp-beta.f6bob
TEMPORAL_CLOUD_API_KEY=<your-api-key>
TEMPORAL_USE_API_KEY=true
```

### Building Multi-Arch Images

```bash
# Build and push to Azure Container Registry
docker buildx build --platform linux/amd64,linux/arm64 \
  -t qlpregistry.azurecr.io/qlp/orchestrator:latest \
  -f deployments/docker/orchestrator.dockerfile \
  --push .

docker buildx build --platform linux/amd64,linux/arm64 \
  -t qlpregistry.azurecr.io/qlp/temporal-worker:latest \
  -f deployments/docker/temporal-worker.dockerfile \
  --push .
```

### Known Issues with AKS Deployment

1. **Redis Port Environment Variable Conflict**
   - Kubernetes injects service discovery variables that conflict with REDIS_PORT
   - Solution: Explicitly set `REDIS_PORT: "6379"` in deployment manifests

2. **Temporal SDK Version**
   - Temporal Cloud requires SDK 1.14.1+ for API key authentication
   - Ensure requirements.txt has `temporalio>=1.14.1`

3. **Import Restrictions in Temporal Workers**
   - Move imports inside activity functions to avoid sandbox restrictions
   - Affected imports: httpx, pathlib, urllib, psutil

## Key Implementation Patterns

### Temporal Workflow Pattern
The platform's core workflow (`src/orchestrator/worker_production.py`) follows this pattern:
1. **Request Analysis**: NLP analysis and task decomposition
2. **Agent Assignment**: Tasks distributed to specialized agents
3. **Parallel Execution**: Multiple agents work concurrently
4. **Validation Pipeline**: Each output validated through 6 stages
5. **Capsule Assembly**: Validated components assembled into deliverable
6. **Delivery**: Push to GitHub or package for download

### Agent Hierarchy
- **T0 Agents**: Simple tasks (comments, documentation)
- **T1 Agents**: Standard code generation (functions, classes)
- **T2 Agents**: Complex logic (APIs, services)
- **T3 Agents**: Architecture and system design

### Important Files for Understanding the System
- `src/orchestrator/worker_production.py`: Main workflow implementation
- `src/orchestrator/main.py`: All API endpoints
- `src/common/models.py`: Data models shared across services
- `src/agents/multi_tier_agents.py`: Agent implementation
- `src/orchestrator/intelligent_capsule_generator.py`: AI-driven project generation

### Common Pitfalls & Solutions

#### Temporal Sandbox Restrictions
```python
# ❌ WRONG - Import at module level
import httpx

@activity.defn
async def my_activity():
    # Use httpx

# ✅ CORRECT - Import inside activity
@activity.defn
async def my_activity():
    import httpx  # Import here to avoid sandbox restrictions
    # Use httpx
```

#### Environment Variables in Workflows
```python
# ❌ WRONG in workflow
import os
api_key = os.getenv("API_KEY")

# ✅ CORRECT - Pass as activity parameter
@activity.defn
async def my_activity(api_key: str):
    # Use api_key
```

## Common Development Commands

### Quick Start (Docker Preferred)
```bash
# Start all services with Docker Compose
docker-compose -f docker-compose.platform.yml up -d

# Check service health
docker-compose -f docker-compose.platform.yml ps

# View logs
docker-compose -f docker-compose.platform.yml logs -f

# Stop all services
docker-compose -f docker-compose.platform.yml down
```

### Local Development (Virtual Environment)
```bash
# Activate virtual environment (required)
source venv/bin/activate

# Start all services (recommended)
./start_all.sh

# Alternative methods
./start.sh                                      # Basic startup
./start_temporal_worker.sh                      # Start worker only

# Individual service startup (for debugging)
cd src/orchestrator && uvicorn main:app --reload --port 8000
cd src/agents && uvicorn main:app --reload --port 8001
cd src/validation && uvicorn main:app --reload --port 8002
cd src/memory && uvicorn main:app --reload --port 8003
cd src/sandbox && uvicorn main:app --reload --port 8004
```

### Testing

#### End-to-End Tests
```bash
# Complete flow tests
./test_complete_flow.sh                # Full pipeline test
./test_universal_capability.sh         # Multi-language test
python test_enterprise_generation.py   # Enterprise features
python test_execute_and_push.py       # GitHub integration

# Quick validation
python test_docker_platform.py        # Docker deployment
python test_production_system.py      # Production features
```

#### Specific Feature Tests
```bash
# GitHub integration
./test_github_push_simple.sh         # Simple GitHub push
./test_e2e_github.sh                 # End-to-end GitHub
python test_github_push.py           # Python GitHub test

# Capsule operations
python test_download_capsule.py      # Download functionality
./test_fixed_endpoints.sh            # Endpoint validation

# AWS Bedrock integration
python test_bedrock_integration.py   # Bedrock models test
./verify_bedrock.sh                  # Verify Bedrock setup
```

### Service Management
```bash
# Health checks
curl http://localhost:8000/health  # Orchestrator
curl http://localhost:8001/health  # Agent Factory
curl http://localhost:8002/health  # Validation Mesh
curl http://localhost:8003/health  # Vector Memory
curl http://localhost:8004/health  # Execution Sandbox

# Service operations
./stop_all.sh          # Graceful shutdown
./cleanup_all.sh       # Complete cleanup (kills processes on ports)

# Temporal management
docker exec qlp-temporal temporal workflow list  # List workflows
./scripts/cleanup_temporal.sh                    # Clean stuck workflows
python scripts/terminate_workflows.py            # Terminate specific
```

### Docker Operations
```bash
# Container management
docker-compose -f docker-compose.platform.yml up -d    # Start
docker-compose -f docker-compose.platform.yml down     # Stop
docker-compose -f docker-compose.platform.yml logs -f  # Logs

# Individual service logs
docker logs qlp-orchestrator -f
docker logs qlp-temporal-worker -f
docker logs qlp-agent-factory -f

# Container inspection
docker ps | grep qlp           # List QLP containers
docker stats                   # Resource usage

# Restart specific service
docker-compose -f docker-compose.platform.yml restart orchestrator
```

## Development Workflow

### Working with the Codebase

1. **Adding New Features**
   - Define models in `src/common/models.py`
   - Implement logic in appropriate service
   - Add endpoints in service main.py or router
   - Create tests (unit and integration)
   - Update API documentation

2. **Testing New Features**
   ```bash
   # Quick test of new endpoint
   curl -X POST http://localhost:8000/your-endpoint \
     -H "Content-Type: application/json" \
     -d '{"your": "data"}'
   
   # Run specific test
   python test_your_feature.py
   
   # Run all tests
   make test
   ```

3. **Debugging Issues**
   ```bash
   # Check service logs
   docker logs qlp-orchestrator --tail 100
   
   # Check workflow status
   docker exec qlp-temporal temporal workflow describe -w <workflow-id>
   
   # Database inspection
   docker exec -it qlp-postgres psql -U qlp_user -d qlp_db
   
   # Check Temporal UI
   open http://localhost:8088
   ```

### Code Quality Standards

```bash
# Format code
black src/

# Linting
ruff check src/
pylint src/

# Type checking
mypy src/

# Security scan
bandit -r src/

# Run all checks
make lint
```

## Environment Configuration

Required environment variables in `.env`:
```bash
# Azure OpenAI (Primary LLM)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4

# Alternative LLMs
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
GROQ_API_KEY=your-groq-key

# AWS Bedrock (Optional)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1
BEDROCK_ENABLED=true

# GitHub Integration
GITHUB_TOKEN=your-github-token

# Database
DATABASE_URL=postgresql://qlp_user:qlp_password@postgres:5432/qlp_db
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Services (Local Development)
TEMPORAL_SERVER=temporal:7233
REDIS_URL=redis://redis:6379/0
QDRANT_URL=http://qdrant:6333

# Temporal Cloud (Production)
TEMPORAL_ADDRESS=us-west-2.aws.api.temporal.io:7233
TEMPORAL_NAMESPACE=qlp-beta.f6bob
TEMPORAL_CLOUD_API_KEY=your-temporal-cloud-api-key
TEMPORAL_USE_API_KEY=true
TEMPORAL_TASK_QUEUE=qlp-production-queue

# Feature Flags
TDD_ENABLED=true
AITL_ENABLED=false  # Currently disabled due to overly conservative scoring
ENTERPRISE_FEATURES_ENABLED=true
```

## Advanced Features

### Intelligent Systems

1. **Pattern Selection Engine**
   - 8 reasoning patterns: Abstraction, Emergent, Meta-Learning, etc.
   - Automatic pattern selection based on task
   - 60-70% computational reduction

2. **Meta-Prompt Engineering**
   - Prompt Genome system
   - Evolution strategies
   - Principle library from CS luminaries
   - Self-improving prompts

3. **AITL (AI-in-the-Loop)**
   - Automatic quality review
   - Confidence-based human escalation
   - Continuous learning from feedback

4. **Shared Context System**
   - Maintains consistency across workflow
   - Language enforcement
   - Project-wide context awareness

### Production Features

1. **Capsule Storage**
   - PostgreSQL persistence
   - Version control
   - Metadata tracking
   - Search capabilities

2. **Monitoring & Observability**
   - Structured logging with context
   - Performance metrics
   - Error tracking
   - Workflow visualization

3. **Security**
   - Sandboxed execution
   - Input validation
   - Secret management
   - Rate limiting

## Common Issues & Solutions

### Port Conflicts
```bash
# Find process using port
lsof -i :8000

# Kill process
lsof -ti:8000 | xargs kill -9

# Or use cleanup script
./cleanup_all.sh
```

### Stuck Workflows
```bash
# Identify stuck workflows
docker exec qlp-temporal temporal workflow list

# Clean up
./scripts/cleanup_temporal.sh

# Force terminate specific workflow
python scripts/terminate_workflows.py --workflow-id <id>
```

### Database Issues
```bash
# Reset database
docker-compose down -v
docker-compose up -d

# Manual connection
docker exec -it qlp-postgres psql -U qlp_user -d qlp_db

# Run migrations
alembic upgrade head
```

### Service Not Starting
```bash
# Check logs
docker logs qlp-orchestrator --tail 100

# Verify dependencies
docker ps  # Check if postgres, redis, temporal are running

# Check environment variables
docker exec qlp-orchestrator env | grep AZURE

# Restart specific service
docker-compose restart orchestrator
```

## Project Structure

```
qlp-dev/
├── src/
│   ├── orchestrator/     # Main orchestration service
│   │   ├── main.py      # FastAPI app with all endpoints
│   │   ├── worker_production.py  # Temporal workflow
│   │   ├── enterprise_worker.py  # Enterprise features
│   │   ├── intelligent_capsule_generator.py
│   │   ├── enhanced_github_integration.py
│   │   └── ... (30+ modules)
│   ├── agents/          # AI agent management
│   ├── validation/      # Code validation
│   ├── memory/          # Vector storage
│   ├── sandbox/         # Execution environment
│   └── common/          # Shared utilities
├── deployments/         # K8s and Docker configs
├── scripts/            # Automation scripts
├── tests/              # Test suites
├── docs/               # Documentation
└── logs/               # Service logs
```

## Key Files to Know

- `src/orchestrator/main.py` - All API endpoints
- `src/orchestrator/worker_production.py` - Temporal workflow logic
- `src/orchestrator/enterprise_worker.py` - Enterprise features (circuit breakers, scaling)
- `src/common/models.py` - Shared data models
- `src/common/config.py` - Configuration settings
- `src/common/error_handling.py` - Enterprise error handling
- `docker-compose.platform.yml` - Service definitions
- `.env` - Environment configuration
- `start_all.sh` - Main startup script
- `Makefile` - Common development tasks

## Best Practices

1. **Always use virtual environment**
   ```bash
   source venv/bin/activate
   ```

2. **Check service health before testing**
   ```bash
   curl http://localhost:8000/health
   ```

3. **Use structured logging**
   ```python
   logger.info("Operation completed", 
               capsule_id=capsule_id, 
               duration=duration)
   ```

4. **Follow TDD when enabled**
   - Let the system generate tests first
   - Implementation follows tests

5. **Monitor workflows**
   - Check Temporal UI: http://localhost:8088
   - Use workflow status endpoints

6. **Database Initialization**
   ```bash
   # Initialize database tables
   python init_database.py
   
   # Or with Docker
   python init_db_docker.py
   ```

7. **Handle Temporal Restrictions**
   - Import modules inside activity functions
   - Avoid file system access in workflows
   - Use activity functions for I/O operations

## Recent Updates (July 2025)

- **Enterprise Scalability**: Dynamic resource scaling and adaptive timeouts
- **Enhanced Fault Tolerance**: Circuit breakers with half-open states
- **Improved Error Handling**: Error classification and aggregation
- **AWS Bedrock Integration**: Multi-model support with Claude, Llama, Mistral
- **Enhanced Progress Display**: Real-time Temporal activity tracking
- **Chain of Thought Reasoning**: Improved reasoning capabilities
- **Capsule Packager**: ZIP/TAR generation for downloads
- **Enhanced GitHub Integration**: V2 with enterprise features
- **Production Capsule System**: Robust generation with metrics
- **Enterprise Endpoints**: One-click enterprise projects
- **Intelligent Structure**: AI-driven project organization
- **Delivery System**: Multiple delivery methods
- **Test-Driven Development**: Automatic TDD workflow

### Latest Implementation (July 15, 2025) - Intelligent Universal Language Support

#### 1. **Intelligent File Organization** (`src/orchestrator/intelligent_file_organizer.py`)
- LLM-powered file categorization for ANY programming language
- No hardcoded assumptions - pure AI decision making
- Automatically organizes:
  - Source code → `src/` or language-specific directory
  - Tests → `tests/` or `test/` based on language conventions
  - Documentation → `docs/` or `doc/`
  - Configuration → Root or appropriate config directory
- Handles mixed content (e.g., code with inline tests)
- Supports all languages: Python, JavaScript, Go, Java, Rust, C++, etc.

#### 2. **Intelligent CI/CD Generation** (`src/orchestrator/intelligent_cicd_generator.py`)
- Universal CI/CD pipeline generation using LLM
- Detects language, framework, and dependencies automatically
- Generates appropriate workflows for:
  - GitHub Actions
  - GitLab CI
  - Jenkins
  - CircleCI
  - Azure DevOps
- Includes language-specific best practices:
  - Build commands
  - Test runners
  - Linting tools
  - Security scanning
  - Deployment strategies
- Cleans up markdown formatting from LLM responses

#### 3. **GitHub Actions Monitoring** (`src/orchestrator/github_actions_monitor.py`)
- Real-time monitoring of CI/CD pipeline execution
- Auto-detects workflow failures and their causes
- LLM-powered fix generation for:
  - Syntax errors in workflow files
  - Missing dependencies
  - Incorrect build commands
  - Environment issues
  - Test failures
- Automatic retry with fixes until success
- Self-healing CI/CD pipelines

#### 4. **Integration Points**
- **Enhanced GitHub Integration**: Overrides default templates with intelligent generation
- **Workflow Integration**: Seamlessly integrated into Temporal workflows
- **Activity Registration**: Properly registered in `worker_production_db.py`
- **Environment Handling**: Fixed Temporal sandbox restrictions for environment variables

#### 5. **Key Improvements Made**
- Replaced ALL hardcoded file organization logic
- Removed Python-specific assumptions from CI/CD
- Added universal language detection and handling
- Implemented self-healing CI/CD pipelines
- Fixed Temporal workflow restrictions (os.getenv)
- Properly registered monitoring activities in Docker workers

## Enterprise Improvements (July 2025)

### 1. Enhanced Scalability
- **Dynamic resource scaling**: Automatically adjusts concurrent activities based on system resources
- **Adaptive timeouts**: Calculates timeouts based on task complexity
- **Intelligent batch sizing**: Dynamic batch sizes for parallel execution
- **Resource monitoring**: Real-time CPU/memory monitoring

### 2. Fault Tolerance
- **Circuit breakers**: Prevents cascading failures with half-open states
- **Enhanced retry logic**: Exponential backoff with jitter
- **Error classification**: Categorizes errors by severity and type
- **Graceful degradation**: Falls back to simpler models when needed

### 3. Enterprise Configuration
```python
# src/common/config.py
WORKFLOW_MAX_BATCH_SIZE: int = 50  # Increased from 10
WORKFLOW_MAX_CONCURRENT_ACTIVITIES: int = 100  # Increased from 20
WORKFLOW_MAX_CONCURRENT_WORKFLOWS: int = 50  # Increased from 10
CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = 60
```

### 4. Timeout Configuration
- **Service call timeout**: 600s (10 minutes) for complex enterprise tasks
- **LLM client timeout**: 300s (5 minutes) for AI completions
- **Activity heartbeat**: 30s to detect stuck activities
- **Workflow execution timeout**: 2 hours for complex projects

### 5. Temporal Workflow Restrictions
**IMPORTANT**: Temporal workflow sandbox has strict limitations on imports:
- Move imports inside activity functions to avoid restrictions
- Cannot import modules that access file system in workflow context
- Cannot use `pathlib`, `urllib`, or similar modules in workflows
- Example fix:
```python
@activity.defn
async def my_activity():
    import httpx  # Import inside activity
    # Activity code here
```

## Known Issues & Solutions

### 1. AITL System Too Conservative
- **Issue**: AITL gives 0 confidence scores for valid code with warnings
- **Impact**: Workflows fail even with working code
- **Workaround**: Set `AITL_ENABLED=false` in environment
- **TODO**: Adjust confidence thresholds to be less strict

### 2. Import Errors in Temporal Workflows
- **Issue**: `RestrictedWorkflowAccessError` when importing certain modules
- **Solution**: Move imports inside activity functions
- **Affected modules**: httpx, pathlib, urllib, psutil

### 3. Timeout Issues for Complex Projects
- **Issue**: Complex multi-service projects timeout
- **Solution**: Increased timeouts across the system:
  - SERVICE_CALL_TIMEOUT: 600s
  - LLM timeout: 300s
  - Workflow execution timeout: 2 hours

### 4. Rate Limiting with LLMs
- **Issue**: Rate limit errors with high concurrency
- **Solution**: Implemented intelligent rate limiting with:
  - Provider-specific limits
  - Automatic backoff and retry
  - Dynamic limit reduction on repeated failures

## Support & Troubleshooting

For detailed troubleshooting:
1. Check service logs
2. Verify environment variables
3. Ensure all dependencies are running
4. Review recent changes in git
5. Run health checks on all services

Remember: The platform is designed to be self-healing and includes extensive error handling. Most issues can be resolved by restarting services or cleaning up stuck workflows.

## Future Improvements & Known Limitations

### Areas Needing Attention

1. **AITL System Tuning**
   - Currently disabled due to overly conservative confidence scoring
   - Needs adjusted thresholds for warnings vs errors
   - TODO: Implement configurable strictness levels

2. **Performance Optimization**
   - Implement request batching for LLM calls
   - Add caching for repeated patterns
   - Optimize database queries for large capsules

3. **Enhanced Monitoring**
   - Add distributed tracing with OpenTelemetry
   - Implement SLO/SLA tracking
   - Create Grafana dashboards for intelligent features

4. **Production Readiness**
   - Complete AKS deployment with Temporal Cloud
   - Implement blue-green deployments
   - Add canary testing for new models

## Summary

The Quantum Layer Platform is a sophisticated AI-powered code generation system that transforms natural language into production-ready software. When working with this codebase:

1. **Always use Docker Compose** for consistent development environment
2. **Activate virtual environment** before running local services
3. **Check service health** before testing features
4. **Follow Temporal patterns** - imports inside activities, no file I/O in workflows
5. **Use structured logging** for better debugging
6. **Run tests frequently** - the platform has comprehensive test coverage

The platform is actively developed with a focus on enterprise-grade features, universal language support, and self-healing capabilities. All code generation is AI-driven with no hardcoded templates, making it adaptable to any programming language or framework.