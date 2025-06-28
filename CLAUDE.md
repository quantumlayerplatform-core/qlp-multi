# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Quantum Layer Platform (QLP) is an AI-powered enterprise software development system that transforms natural language requirements into production-ready code through intelligent agent orchestration. The platform uses a microservices architecture with 5 core services communicating via REST APIs and Temporal workflows.

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
# Activate virtual environment
source venv/bin/activate

# Start all services (simplest method)
./start.sh

# Alternative startup methods
./start_all.sh          # Complete platform with all dependencies
./run_quick.sh          # Quick start (assumes Docker running)
make run-local          # Using Makefile
```

### Testing
```bash
# Quick validation tests
python test_quick.py     # Basic functionality test
python test_integration.py  # Service integration test
python test_sandbox.py   # Sandbox execution test

# Comprehensive testing
make test               # Run all tests
make test-unit          # Unit tests only
make test-integration   # Integration tests
make test-e2e          # End-to-end tests

# Run specific test
pytest tests/unit/test_orchestrator.py::test_specific_function -v
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
./restart_failed.sh     # Restart failed services
./stop_all.sh          # Graceful shutdown
./cleanup_all.sh       # Complete cleanup
./start_worker.sh      # Start Temporal worker
```

### Build and Deployment
```bash
# Build operations
make build             # Build all services
make install-deps      # Install all dependencies
make clean            # Clean build artifacts

# Infrastructure
make infra-up         # Start local infrastructure
make infra-down       # Stop infrastructure
make deploy           # Deploy to Kubernetes
```

### Code Quality
```bash
# Format code
black src/              # Auto-format Python code
make format            # Format all code

# Linting
ruff check src/        # Fast Python linter
pylint src/            # Comprehensive linting
make lint              # Run all linters

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

2. **Agent Factory** (`src/agents/`) - Port 8001
   - Multi-tier agent system (T0-T3)
   - Model selection based on task complexity
   - Performance tracking and optimization

3. **Validation Mesh** (`src/validation/`) - Port 8002
   - 5-stage validation pipeline
   - Ensemble consensus mechanism
   - Human escalation for low confidence

4. **Vector Memory** (`src/memory/`) - Port 8003
   - Semantic search with Qdrant
   - Learning from past executions
   - Pattern recognition and reuse

5. **Execution Sandbox** (`src/sandbox/`) - Port 8004
   - Docker-based secure execution
   - Multi-language support
   - Resource isolation

All services communicate via REST APIs with OpenAPI documentation available at `/docs` endpoint.

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