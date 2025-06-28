# QLP API Endpoints Documentation

All services provide automatic Swagger UI documentation at `/docs` endpoint.

## 🎯 Orchestrator Service (Port 8000)
**Swagger UI**: http://localhost:8000/docs

### Core Endpoints:
- `GET /health` - Health check
- `POST /generate` - Generate code with basic agents
- `POST /generate/capsule` - Generate complete QLCapsule
- `POST /generate/robust-capsule` - Generate robust capsule with quality targets
- `GET /task/{task_id}` - Get task status
- `GET /tasks` - List all tasks

### MCP Endpoints:
- `GET /mcp/info` - MCP server information
- `POST /mcp/tools/invoke` - Invoke MCP tool
- `GET /mcp/resources/list` - List MCP resources
- `GET /mcp/prompts/list` - List MCP prompts

## 🤖 Agent Factory Service (Port 8001)
**Swagger UI**: http://localhost:8001/docs

### Endpoints:
- `GET /health` - Health check
- `GET /metrics` - Service metrics
- `POST /spawn` - Spawn new agent
- `GET /agents` - List active agents
- `GET /agents/{agent_id}` - Get agent details
- `DELETE /agents/{agent_id}` - Terminate agent
- `POST /execute` - Execute task with agent

### Advanced Endpoints:
- `POST /generate/advanced` - Advanced code generation
- `POST /generate/test-driven` - Test-driven development
- `POST /generate/multi-model` - Multi-model consensus
- `POST /generate/pattern-based` - Pattern-based generation

## ✅ Validation Service (Port 8002)
**Swagger UI**: http://localhost:8002/docs

### Endpoints:
- `GET /health` - Health check
- `POST /validate` - Validate code/artifact
- `POST /validate/syntax` - Syntax validation only
- `POST /validate/security` - Security validation
- `POST /validate/performance` - Performance validation
- `POST /validate/ensemble` - Ensemble validation

## 🧠 Memory Service (Port 8003)
**Swagger UI**: http://localhost:8003/docs

### Endpoints:
- `GET /health` - Health check
- `POST /store` - Store execution pattern
- `GET /search` - Search patterns
- `GET /patterns/similar` - Find similar patterns
- `POST /patterns/execution` - Store execution results
- `GET /patterns/successful` - Get successful patterns
- `POST /embeddings` - Generate embeddings

## 🏗️ Sandbox Service (Port 8004)
**Swagger UI**: http://localhost:8004/docs

### Endpoints:
- `GET /health` - Health check
- `POST /execute` - Execute code in sandbox
- `GET /languages` - List supported languages
- `POST /test` - Run tests in sandbox
- `GET /containers` - List active containers
- `DELETE /containers/{container_id}` - Stop container

## 🚀 Example Usage with Swagger UI:

1. **Open Swagger UI**:
   ```bash
   open http://localhost:8000/docs
   ```

2. **Try an endpoint**:
   - Click on any endpoint
   - Click "Try it out"
   - Fill in the request body
   - Click "Execute"
   - See the response

3. **Example - Generate Robust Capsule**:
   ```json
   {
     "prompt": "Create a REST API with authentication",
     "target_score": 0.9,
     "language": "python",
     "requirements": {
       "framework": "FastAPI",
       "auth": "JWT",
       "database": "PostgreSQL"
     }
   }
   ```

## 📊 Metrics and Monitoring:

- **Prometheus Metrics**: http://localhost:9090 (if configured)
- **Health Endpoints**: Each service has `/health` endpoint
- **Service Metrics**: Some services expose `/metrics`

## 🔧 Authentication:

Currently, the services don't require authentication for local development. In production, you would add:
- API Keys via headers
- JWT tokens
- OAuth2 flows

## 📝 OpenAPI Specifications:

Each service exposes its OpenAPI schema at:
- `/openapi.json` - JSON format
- Can be imported into Postman, Insomnia, etc.

## 🎨 ReDoc Alternative:

If you prefer ReDoc's documentation style:
- http://localhost:8000/redoc
- http://localhost:8001/redoc
- etc.

ReDoc provides a cleaner, more readable documentation format.