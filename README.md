# Quantum Layer Platform (QLP)

## 🚀 Overview

The **Quantum Layer Platform** is an enterprise-grade, AI-powered software development platform that transforms natural language requests into production-ready software through intelligent agent orchestration, continuous learning, and human collaboration.

## 🏗️ Architecture

The platform consists of 5 core microservices:

### 1. **Meta-Orchestrator** (Port 8000)
- Decomposes natural language requests into atomic tasks
- Creates intelligent execution plans with dependency management
- Manages workflow orchestration through the entire pipeline

### 2. **Agent Factory** (Port 8001)
- Multi-tier agent system (T0-T3) for different complexity levels
- Dynamic agent selection based on task requirements
- Supports multiple LLMs (GPT-3.5, GPT-4, Claude, Llama)

### 3. **Validation Mesh** (Port 8002)
- Multi-stage validation pipeline
- 5 validators: Syntax, Style, Security, Type, Runtime
- Ensemble consensus mechanism with confidence scoring

### 4. **Vector Memory** (Port 8003)
- Semantic search using Qdrant vector database
- Learns from past executions to improve future performance
- Stores code patterns, decisions, and error patterns

### 5. **Execution Sandbox** (Port 8004)
- Secure Docker-based code execution
- Multi-language support (Python, JavaScript, Go, Java, Rust)
- Resource limits and isolation for safety

## 🚀 Quick Start

### Prerequisites
- Python 3.13+
- Docker
- Virtual environment

### Installation

1. **Activate virtual environment:**
```bash
cd /Users/satish/qlp-projects/qlp-multi
source venv/bin/activate
```

2. **Start all services:**
```bash
./start.sh
```

3. **Verify health:**
```bash
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:8004/health
```

### 🧪 Test the Platform

**Simple test:**
```bash
python test_quick.py
```

**Integration test:**
```bash
python test_integration.py
```

**Sandbox test:**
```bash
python test_sandbox.py
```

## 📊 API Examples

### Generate Code from Natural Language

```bash
curl -X POST http://localhost:8000/test/decompose \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Create a Python function to calculate fibonacci numbers",
    "tenant_id": "default",
    "user_id": "test"
  }'
```

### Execute Code in Sandbox

```bash
curl -X POST http://localhost:8004/execute \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def hello(): return \"Hello from Quantum Layer Platform!\"\nprint(hello())",
    "language": "python"
  }'
```

## 🎯 Key Features

- **Natural Language Understanding**: Converts requirements to code
- **Multi-Tier AI Agents**: From simple to meta-cognitive agents
- **Secure Execution**: Docker-based isolation
- **Continuous Learning**: Improves with every execution
- **Enterprise Ready**: Multi-tenant, scalable architecture

## 📚 Service Documentation

Each service has interactive API documentation:
- Orchestrator: http://localhost:8000/docs
- Agent Factory: http://localhost:8001/docs
- Validation Mesh: http://localhost:8002/docs
- Vector Memory: http://localhost:8003/docs
- Execution Sandbox: http://localhost:8004/docs

## 🛠️ Development

### Stop all services:
```bash
./stop_platform.sh
```

### Restart all services:
```bash
./restart_all.sh
```

### View logs:
```bash
tail -f logs/*.log
```

## 🏆 Platform Capabilities

- **Languages**: Python, JavaScript, TypeScript, Go, Java, Rust
- **AI Models**: GPT-3.5, GPT-4, Claude, Llama
- **Agent Tiers**: T0 (simple), T1 (context-aware), T2 (reasoning), T3 (meta-agents)
- **Validation**: Syntax, Style, Security, Type checking, Runtime
- **Learning**: Semantic search and pattern recognition

## 📈 Architecture Benefits

1. **Microservices**: Independent scaling and deployment
2. **AI-Powered**: Leverages best-in-class language models
3. **Secure**: Sandboxed execution environment
4. **Learning System**: Gets smarter with usage
5. **Extensible**: Easy to add new capabilities

---

Built with ❤️ by the Quantum Layer Platform team
