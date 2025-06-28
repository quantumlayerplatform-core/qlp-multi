.PHONY: help install-deps infra-up infra-down run-local test test-unit test-integration test-e2e test-all build deploy clean

# Default target
help:
	@echo "Quantum Leap Platform - Make Commands"
	@echo ""
	@echo "Development:"
	@echo "  make install-deps    - Install all dependencies"
	@echo "  make infra-up       - Start local infrastructure"
	@echo "  make infra-down     - Stop local infrastructure"
	@echo "  make run-local      - Run platform locally"
	@echo ""
	@echo "Testing:"
	@echo "  make test           - Run all tests"
	@echo "  make test-unit      - Run unit tests"
	@echo "  make test-integration - Run integration tests"
	@echo "  make test-e2e       - Run end-to-end tests"
	@echo ""
	@echo "Build & Deploy:"
	@echo "  make build          - Build all services"
	@echo "  make deploy         - Deploy to Kubernetes"
	@echo "  make clean          - Clean build artifacts"

# Install dependencies
install-deps:
	@echo "Installing Python dependencies..."
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	@echo "Installing Go dependencies..."
	cd src/orchestrator && go mod download
	@echo "Installing Node dependencies..."
	cd src/ui && npm install
	@echo "Installing infrastructure tools..."
	./scripts/install-tools.sh

# Infrastructure management
infra-up:
	@echo "Starting local infrastructure..."
	docker-compose -f infrastructure/docker/docker-compose.local.yml up -d
	@echo "Waiting for services to be ready..."
	./scripts/wait-for-services.sh
	@echo "Applying Kubernetes manifests..."
	kubectl apply -f infrastructure/k8s/local/

infra-down:
	@echo "Stopping local infrastructure..."
	kubectl delete -f infrastructure/k8s/local/
	docker-compose -f infrastructure/docker/docker-compose.local.yml down -v

# Run locally
run-local: infra-up
	@echo "Starting Meta-Orchestrator..."
	cd src/orchestrator && go run . &
	@echo "Starting Agent Factory..."
	cd src/agents && python -m uvicorn main:app --reload --port 8001 &
	@echo "Starting Validation Service..."
	cd src/validation && python -m uvicorn main:app --reload --port 8002 &
	@echo "Starting Memory Service..."
	cd src/memory && python -m uvicorn main:app --reload --port 8003 &
	@echo "Starting API Gateway..."
	cd src/api && python -m uvicorn main:app --reload --port 8000 &
	@echo "Platform is running!"
	@echo "API: http://localhost:8000"
	@echo "UI: http://localhost:3000"

# Testing
test: test-unit test-integration

test-unit:
	@echo "Running unit tests..."
	pytest tests/unit -v --cov=src --cov-report=html
	cd src/orchestrator && go test ./... -v

test-integration:
	@echo "Running integration tests..."
	pytest tests/integration -v

test-e2e:
	@echo "Running end-to-end tests..."
	pytest tests/e2e -v --browser chromium

test-all: test-unit test-integration test-e2e

# Build
build:
	@echo "Building Docker images..."
	./scripts/build-images.sh
	@echo "Building UI..."
	cd src/ui && npm run build

# Deploy
deploy:
	@echo "Deploying to Kubernetes..."
	./scripts/deploy.sh

# Clean
clean:
	@echo "Cleaning build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .coverage htmlcov
	rm -rf src/ui/build src/ui/node_modules
	docker system prune -f
