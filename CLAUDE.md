# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Quantum Layer Platform (QLP) is an AI-powered enterprise software development system that transforms natural language requirements into production-ready code through intelligent agent orchestration. The platform uses a microservices architecture with 5 core services communicating via REST APIs and Temporal workflows.

**Core Concept**: Request → Orchestrator → Task Decomposition → Agent Execution → Validation → Capsule Creation → Delivery/GitHub

**Current Status**: Core platform fully operational with enterprise features, GitHub integration, and intelligent capsule generation

**Latest Milestone** (July 12, 2025): 
- ✅ Complete end-to-end flow from NLP to GitHub repository
- ✅ Enterprise-grade project structure generation using AI
- ✅ Test-Driven Development (TDD) workflow integration
- ✅ Multi-language support (Python, JavaScript, Go, Java, etc.)
- ✅ Capsule packaging and delivery system
- ✅ Production-grade GitHub integration with auto-push

## Technology Stack

- **Primary Language**: Python 3.11+
- **Framework**: FastAPI with Uvicorn
- **AI/LLM Integration**: 
  - Azure OpenAI (primary)
  - OpenAI, Anthropic, Groq
  - LangChain, LlamaIndex
- **Workflow Orchestration**: Temporal
- **Vector Database**: Qdrant (primary), Weaviate (alternative)
- **Traditional Databases**: PostgreSQL (with persistence), Redis
- **Message Queue**: Kafka (optional)
- **Container Orchestration**: Docker, Kubernetes (AKS-ready)
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

## Common Development Commands

### Quick Start
```bash
# Activate virtual environment (required)
source venv/bin/activate

# Start all services (recommended)
./start_all.sh

# Alternative methods
./start.sh                                      # Basic startup
docker-compose -f docker-compose.platform.yml up -d  # Docker only
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
./cleanup_all.sh       # Complete cleanup
./start_temporal_worker.sh  # Start worker only

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
   ```

3. **Debugging Issues**
   ```bash
   # Check service logs
   docker logs qlp-orchestrator --tail 100
   
   # Check workflow status
   docker exec qlp-temporal temporal workflow describe -w <workflow-id>
   
   # Database inspection
   docker exec -it qlp-postgres psql -U qlp_user -d qlp_db
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

# GitHub Integration
GITHUB_TOKEN=your-github-token

# Database
DATABASE_URL=postgresql://qlp_user:qlp_password@postgres:5432/qlp_db
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Services
TEMPORAL_SERVER=temporal:7233
REDIS_URL=redis://redis:6379/0
QDRANT_URL=http://qdrant:6333

# Feature Flags
TDD_ENABLED=true
AITL_ENABLED=true
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
```

### Database Issues
```bash
# Reset database
docker-compose down -v
docker-compose up -d

# Manual connection
docker exec -it qlp-postgres psql -U qlp_user -d qlp_db
```

### Service Not Starting
```bash
# Check logs
docker logs qlp-orchestrator --tail 100

# Verify dependencies
docker ps  # Check if postgres, redis, temporal are running

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
- `src/common/models.py` - Shared data models
- `docker-compose.platform.yml` - Service definitions
- `.env` - Environment configuration
- `start_all.sh` - Main startup script

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

## Recent Updates (July 2025)

- **Capsule Packager**: ZIP/TAR generation for downloads
- **Enhanced GitHub Integration**: V2 with enterprise features
- **Production Capsule System**: Robust generation with metrics
- **Enterprise Endpoints**: One-click enterprise projects
- **Intelligent Structure**: AI-driven project organization
- **Delivery System**: Multiple delivery methods
- **Test-Driven Development**: Automatic TDD workflow

## Support & Troubleshooting

For detailed troubleshooting:
1. Check service logs
2. Verify environment variables
3. Ensure all dependencies are running
4. Review recent changes in git
5. Run health checks on all services

Remember: The platform is designed to be self-healing and includes extensive error handling. Most issues can be resolved by restarting services or cleaning up stuck workflows.