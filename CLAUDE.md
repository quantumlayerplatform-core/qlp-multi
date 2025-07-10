# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Quantum Layer Platform (QLP) is an AI-powered enterprise software development system that transforms natural language requirements into production-ready code through intelligent agent orchestration. The platform uses a microservices architecture with 5 core services communicating via REST APIs and Temporal workflows.

**Core Concept**: Request → Orchestrator → Task Decomposition → Agent Execution → Validation → Capsule Creation

**Current Status**: Core platform operational, UI development pending

## Technology Stack

- **Primary Language**: Python 3.11+
- **Framework**: FastAPI with Uvicorn
- **AI/LLM Integration**: OpenAI, Anthropic, Groq, LangChain, LlamaIndex
- **Workflow Orchestration**: Temporal
- **Vector Database**: Qdrant (primary), Weaviate (alternative)
- **Traditional Databases**: PostgreSQL, Redis
- **Message Queue**: Kafka
- **Container Orchestration**: Docker, Kubernetes (AKS-ready)
- **Monitoring**: Prometheus, Grafana, Jaeger, OpenTelemetry

## Common Development Commands

### Quick Start
```bash
# Activate virtual environment (required before starting services)
source venv/bin/activate

# Start all services (simplest method)
./start.sh

# Alternative startup methods
./start_all.sh          # Complete platform with all dependencies
make run-local          # Using Makefile
docker-compose -f docker-compose.platform.yml up -d  # Docker only
```

### Testing
```bash
# Quick validation tests
python test_docker_platform.py     # Test Docker deployment
python test_production_system.py   # Production system test
python test_end_to_end.py          # End-to-end functionality
python test_complete_nlp_to_capsule_flow.py  # Complete NLP flow

# Available test files (no pytest configuration found)
python test_azure_integration.py   # Azure integration test
python test_full_e2e.py            # Full end-to-end test
python test_k8s_platform.py        # Kubernetes platform test

# Enhanced testing commands
python test_aitl.py                # AITL (AI-in-the-loop) testing
python test_enhanced_sandbox.py    # Enhanced sandbox features
python test_agent_powered_validation.py  # Agent validation testing

# Run tests with coverage (if pytest is available)
pytest --cov=src tests/
```

### Service Management
```bash
# Check service health
curl http://localhost:8000/health  # Orchestrator
curl http://localhost:8001/health  # Agent Factory
curl http://localhost:8002/health  # Validation Mesh
curl http://localhost:8003/health  # Vector Memory
curl http://localhost:8004/health  # Execution Sandbox

# Service-specific operations
./stop_all.sh          # Graceful shutdown
./cleanup_all.sh       # Complete cleanup (kills processes, frees ports)
./start_temporal_worker.sh  # Start Temporal worker

# Temporal workflow management
python scripts/cleanup_stuck_workflows.py --max-age 1  # Clean stuck workflows
python scripts/terminate_workflow.py <workflow_id>     # Terminate specific workflow
temporal workflow list                                 # List all workflows
```

### Build and Deployment
```bash
# Docker operations
docker-compose -f docker-compose.platform.yml up -d  # Start all services
docker-compose -f docker-compose.platform.yml down   # Stop all services
docker-compose -f docker-compose.platform.yml logs -f  # View logs

# Kubernetes deployment
kubectl apply -f deployments/kubernetes/  # Deploy to K8s
kubectl apply -f k8s/                    # Alternative K8s configs

# Build operations
make build             # Build all services
make install-deps      # Install all dependencies
make clean            # Clean build artifacts
```

### Code Quality
```bash
# Format code
black src/              # Auto-format Python code

# Linting
ruff check src/        # Fast Python linter
pylint src/            # Comprehensive linting

# Type checking
mypy src/              # Type check Python code

# Security scanning
bandit -r src/         # Security vulnerability scan
```

## Architecture Overview

The platform consists of 5 microservices:

1. **Meta-Orchestrator** (`src/orchestrator/`) - Port 8000
   - Decomposes requests into atomic tasks
   - Manages Temporal workflows
   - Coordinates service interactions
   - **Intelligent Pattern Selection Engine**: Automatically selects from 8 reasoning patterns (Abstraction, Emergent, Meta-Learning, etc.) for 60-70% computational reduction

2. **Agent Factory** (`src/agents/`) - Port 8001
   - Multi-tier agent system (T0-T3)
   - Model selection based on task complexity
   - Performance tracking and optimization

3. **Validation Mesh** (`src/validation/`) - Port 8002
   - 5-stage validation pipeline
   - Ensemble consensus mechanism
   - AITL (AI-in-the-loop) review when confidence < 0.7

4. **Vector Memory** (`src/memory/`) - Port 8003
   - Semantic search with Qdrant
   - Learning from past executions
   - Pattern recognition and reuse

5. **Execution Sandbox** (`src/sandbox/`) - Port 8004
   - Docker-based secure execution
   - Multi-language support
   - Resource isolation

All services communicate via REST APIs with OpenAPI documentation available at `/docs` endpoint. Service discovery uses container names (e.g., `http://orchestrator:8000`) in Docker environments.

## Key Implementation Patterns

### Agent Tier System
- **T0**: Simple tasks (Llama/GPT-3.5) - basic code generation
- **T1**: Context-aware (enhanced GPT-3.5) - understands project context
- **T2**: Reasoning loops (Claude) - complex problem solving
- **T3**: Meta-agents - orchestrate other agents for large tasks

### Validation Pipeline
1. **Syntax Validation**: AST parsing
2. **Style Validation**: Black formatting
3. **Security Validation**: Bandit scanning
4. **Type Validation**: mypy checking
5. **Runtime Validation**: Docker execution

### Service Communication
- Synchronous: HTTP REST APIs with Pydantic models
- Asynchronous: Temporal workflows for long-running tasks
- Event-driven: Kafka for service events
- Caching: Redis for frequently accessed data

## Development Workflow

### Adding New Features
1. Define API contracts in `src/common/models/`
2. Implement service logic in appropriate service directory
3. Add comprehensive tests (unit, integration)
4. Update API documentation
5. Run validation suite before committing

### Testing Requirements
- Minimum 80% code coverage
- All new endpoints must have integration tests
- Complex logic requires unit tests
- End-to-end tests for critical user flows

### Error Handling
- Use structured logging with context
- Return standardized error responses
- Implement retry logic for transient failures
- Circuit breakers for external services

## Environment Configuration

Required environment variables (set in `.env`):
- `OPENAI_API_KEY`: OpenAI API access
- `ANTHROPIC_API_KEY`: Claude API access
- `GROQ_API_KEY`: Groq/Llama access
- `TEMPORAL_HOST`: Temporal server address
- `POSTGRES_*`: Database configuration
- `REDIS_*`: Cache configuration
- `QDRANT_*`: Vector database configuration

## Performance Considerations

- Agent selection optimizes for cost/performance balance
- Vector memory reduces redundant processing
- Caching implemented at multiple levels
- Async processing for long-running tasks
- Resource limits enforced in sandbox execution

## Special Features

### Meta-Prompt Engineering System
The platform includes an advanced prompt engineering system (`src/agents/meta_prompts/`) that implements recursive self-improvement:
- Prompt Genome: DNA-like structures encoding prompt strategies
- Evolution strategies: Conjecture & Refutation, Explanation Depth, Error Correction
- Automatic learning from each execution
- Principle library with wisdom from Deutsch, Popper, Dijkstra, Kay, Liskov

### Intelligent Architecture
- **Intelligent Capsule Generator** (`src/orchestrator/intelligent_capsule_generator.py`): Universal intelligence without templates
- **Enhanced Meta-Prompt Engineer** (`src/agents/meta_prompts/enhanced_meta_engineer.py`): Meta-cognitive reasoning
- **Unified Intelligent Orchestrator** (`src/orchestrator/unified_intelligent_orchestrator.py`): Combines all intelligence systems
- **Shared Context System** (`src/orchestrator/shared_context.py`): Maintains consistency across all workflow activities

### Temporal Workflow Integration
- Production workflow in `src/orchestrator/worker_production.py`
- Activities: Decompose → Select agent → Execute → Validate → Sandbox test → AITL review → Create capsule
- Language enforcement ensures consistent output throughout pipeline

## API Documentation

All services expose OpenAPI documentation at:
- Orchestrator: http://localhost:8000/docs
- Agent Factory: http://localhost:8001/docs
- Validation Mesh: http://localhost:8002/docs
- Vector Memory: http://localhost:8003/docs
- Execution Sandbox: http://localhost:8004/docs

Comprehensive endpoint documentation available in `docs/API_ENDPOINTS.md`.

## Common Debugging Commands

```bash
# View service logs (local development)
tail -f logs/orchestrator.log
tail -f logs/agents.log
tail -f logs/validation.log
tail -f logs/memory.log
tail -f logs/sandbox.log

# View Docker service logs
docker logs qlp-orchestrator -f
docker logs qlp-agent-factory -f
docker logs qlp-validation-mesh -f
docker logs qlp-vector-memory -f
docker logs qlp-execution-sandbox -f

# Check Temporal workflow status
temporal workflow list
temporal workflow describe -w <workflow-id>

# Test API endpoints
curl http://localhost:8000/health  # Orchestrator health
curl http://localhost:8000/docs    # API documentation

# Quick platform test
curl -X POST http://localhost:8000/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "default",
    "user_id": "test",
    "description": "Write a hello world function in Python"
  }'

# Generate capsule test
curl -X POST http://localhost:8000/generate/capsule \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "test-request",
    "tenant_id": "demo",
    "user_id": "developer",
    "project_name": "Test Project",
    "description": "Simple test project",
    "requirements": "Basic functionality",
    "tech_stack": ["Python"]
  }'
```

## Project Structure Reference

Key directories to know:
- `src/common/models.py` - Shared Pydantic models for API contracts
- `src/common/config.py` - Centralized configuration management
- `src/orchestrator/` - Main orchestration service
- `src/agents/` - Agent factory and AI model management
- `src/validation/` - Code validation and quality checks
- `src/memory/` - Vector memory and pattern recognition
- `src/sandbox/` - Secure code execution environment
- `src/agents/meta_prompts/` - Advanced prompt engineering system
- `deployments/kubernetes/` - Kubernetes deployment manifests
- `deployments/docker/` - Docker-specific configurations
- `scripts/` - Automation and deployment scripts
- `docs/` - API and architecture documentation
- `capsule_versions/` - Generated capsule version history
- `logs/` - Service logs directory

## Important Files

- `docker-compose.platform.yml` - Complete platform Docker setup
- `start.sh` - Quick service startup script
- `start_all.sh` - Complete platform startup with dependencies
- `requirements.txt` - Python dependencies
- `Dockerfile` - Multi-service container build
- `.env` - Environment variables (create from README instructions)

## Common Troubleshooting

### Port Conflicts
If services fail to start due to port conflicts:
```bash
# Check what's using a port
lsof -i :8000

# Kill process on specific port
lsof -ti:8000 | xargs kill -9

# Or use the cleanup script
./cleanup_all.sh
```

### Temporal Workflow Issues
```bash
# Check for stuck workflows
python scripts/cleanup_stuck_workflows.py --max-age 2

# View workflow details
temporal workflow describe -w <workflow-id>

# Force terminate workflow
python scripts/terminate_workflow.py <workflow-id>
```

### Complete Reset Workflow
```bash
# 1. Stop everything
./stop_all.sh

# 2. Clean up completely
./cleanup_all.sh

# 3. Activate virtual environment
source venv/bin/activate

# 4. Start fresh
./start_all.sh
```