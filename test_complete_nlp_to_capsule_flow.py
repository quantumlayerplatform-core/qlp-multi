#!/usr/bin/env python3
"""
Complete NLP-to-Capsule Validation Flow Demo
Shows the entire pipeline from natural language to deployment-ready capsule
"""

import asyncio
import json
import time
from datetime import datetime
import requests
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from src.common.models import QLCapsule
from src.orchestrator.enhanced_capsule import EnhancedCapsuleGenerator
from src.validation.qlcapsule_runtime_validator import QLCapsuleRuntimeValidator
from src.validation.confidence_engine import AdvancedConfidenceEngine
from src.validation.capsule_schema import CapsuleValidator, CapsuleLanguage


class NLPToCapsuleDemo:
    """Demonstrates complete NLP to validated capsule flow"""
    
    def __init__(self):
        self.capsule_generator = EnhancedCapsuleGenerator()
        self.runtime_validator = QLCapsuleRuntimeValidator()
        self.confidence_engine = AdvancedConfidenceEngine()
        self.schema_validator = CapsuleValidator()
    
    async def run_complete_demo(self):
        """Run the complete demo flow"""
        print("🚀 QLP Complete NLP-to-Capsule Validation Demo")
        print("=" * 60)
        
        # Step 1: Natural Language Input
        nlp_request = """
        Create a REST API service for user authentication that:
        1. Allows users to register with email and password
        2. Provides JWT token-based login
        3. Has password hashing with bcrypt
        4. Includes rate limiting for login attempts
        5. Has health check endpoint
        6. Uses FastAPI framework
        7. Includes comprehensive tests
        8. Has proper error handling and logging
        9. Uses environment variables for secrets
        10. Is production-ready with Docker support
        """
        
        print(f"📝 Step 1: Natural Language Request")
        print(f"Request: {nlp_request.strip()}")
        print()
        
        # Step 2: Generate Capsule
        print(f"🔧 Step 2: Generating QLCapsule...")
        start_time = time.time()
        
        capsule = await self.generate_capsule(nlp_request)
        generation_time = time.time() - start_time
        
        print(f"✅ Capsule generated in {generation_time:.2f}s")
        print(f"   - Capsule ID: {capsule.id}")
        print(f"   - Title: {capsule.title}")
        print(f"   - Files: {len(capsule.source_code)} source files")
        print(f"   - Tests: {len(capsule.tests) if capsule.tests else 0} test files")
        print()
        
        # Step 3: Show Generated Files
        print(f"📁 Step 3: Generated Capsule Structure")
        self.display_capsule_structure(capsule)
        print()
        
        # Step 4: Runtime Validation
        print(f"🐳 Step 4: Runtime Validation (Docker Execution)")
        start_time = time.time()
        
        runtime_result = await self.runtime_validator.validate_capsule_runtime(capsule)
        runtime_time = time.time() - start_time
        
        print(f"⏱️  Runtime validation completed in {runtime_time:.2f}s")
        self.display_runtime_results(runtime_result)
        print()
        
        # Step 5: Confidence Analysis
        print(f"🎯 Step 5: Advanced Confidence Analysis")
        start_time = time.time()
        
        # Parse manifest if present
        manifest = None
        if "capsule.yaml" in capsule.source_code:
            try:
                is_valid, manifest, errors = self.schema_validator.validate_manifest(
                    capsule.source_code["capsule.yaml"]
                )
                if not is_valid:
                    print(f"⚠️  Manifest validation errors: {errors}")
            except Exception as e:
                print(f"⚠️  Manifest parsing failed: {e}")
        
        confidence_analysis = await self.confidence_engine.analyze_confidence(
            capsule, manifest, runtime_result
        )
        confidence_time = time.time() - start_time
        
        print(f"📊 Confidence analysis completed in {confidence_time:.2f}s")
        self.display_confidence_analysis(confidence_analysis)
        print()
        
        # Step 6: Final Assessment
        print(f"🏁 Step 6: Final Deployment Assessment")
        self.display_final_assessment(capsule, runtime_result, confidence_analysis)
        print()
        
        # Step 7: API Demo (if services are running)
        print(f"🌐 Step 7: API Integration Demo")
        await self.demo_api_integration(capsule, runtime_result, confidence_analysis)
        
        return capsule, runtime_result, confidence_analysis
    
    async def generate_capsule(self, nlp_request: str) -> QLCapsule:
        """Generate capsule from NLP request"""
        # Simulate capsule generation (in real system, this would call the orchestrator)
        return QLCapsule(
            id=f"auth_api_{int(time.time())}",
            title="JWT Authentication API",
            description="FastAPI-based authentication service with JWT tokens",
            source_code={
                "main.py": '''"""
FastAPI Authentication Service with JWT
"""
import os
import bcrypt
import jwt
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import logging
import time
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="JWT Authentication API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Configuration from environment
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Rate limiting storage (in production, use Redis)
rate_limit_storage = defaultdict(list)
RATE_LIMIT_ATTEMPTS = 5
RATE_LIMIT_WINDOW = 300  # 5 minutes

# Models
class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class User(BaseModel):
    email: str
    created_at: datetime

# In-memory user storage (in production, use database)
users_db = {}

# Utility functions
def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def check_rate_limit(email: str) -> bool:
    """Check if user is within rate limit"""
    now = time.time()
    user_attempts = rate_limit_storage[email]
    
    # Remove old attempts
    user_attempts[:] = [attempt for attempt in user_attempts if now - attempt < RATE_LIMIT_WINDOW]
    
    # Check if under limit
    if len(user_attempts) >= RATE_LIMIT_ATTEMPTS:
        return False
    
    # Add current attempt
    user_attempts.append(now)
    return True

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from JWT token"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return email
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Routes
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "jwt-auth-api",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@app.post("/register", response_model=User)
async def register_user(user: UserCreate):
    """Register a new user"""
    try:
        # Check if user already exists
        if user.email in users_db:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Hash password
        hashed_password = hash_password(user.password)
        
        # Store user
        users_db[user.email] = {
            "email": user.email,
            "hashed_password": hashed_password,
            "created_at": datetime.utcnow()
        }
        
        logger.info(f"User registered: {user.email}")
        
        return User(
            email=user.email,
            created_at=users_db[user.email]["created_at"]
        )
        
    except Exception as e:
        logger.error(f"Registration failed for {user.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@app.post("/login", response_model=Token)
async def login_user(user: UserLogin):
    """Login user and return JWT token"""
    try:
        # Check rate limit
        if not check_rate_limit(user.email):
            logger.warning(f"Rate limit exceeded for {user.email}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Please try again later."
            )
        
        # Check if user exists
        if user.email not in users_db:
            logger.warning(f"Login attempt for non-existent user: {user.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        # Verify password
        stored_user = users_db[user.email]
        if not verify_password(user.password, stored_user["hashed_password"]):
            logger.warning(f"Invalid password for user: {user.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        
        logger.info(f"User logged in: {user.email}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed for {user.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@app.get("/profile", response_model=User)
async def get_user_profile(current_user: str = Depends(get_current_user)):
    """Get current user profile"""
    try:
        if current_user not in users_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user_data = users_db[current_user]
        return User(
            email=user_data["email"],
            created_at=user_data["created_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile fetch failed for {current_user}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch profile"
        )

@app.get("/protected")
async def protected_route(current_user: str = Depends(get_current_user)):
    """Protected route that requires authentication"""
    return {
        "message": f"Hello {current_user}! This is a protected route.",
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
''',
                "requirements.txt": '''fastapi==0.104.1
uvicorn[standard]==0.24.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
bcrypt==4.0.1
pydantic[email]==2.5.0
PyJWT==2.8.0
python-multipart==0.0.6
''',
                "Dockerfile": '''FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
''',
                "capsule.yaml": '''name: jwt-auth-api
version: 1.0.0
language: python
type: api
description: FastAPI-based JWT authentication service

author: QLP Generator
homepage: https://github.com/your-org/jwt-auth-api

entry_point: main.py

commands:
  install: pip install -r requirements.txt
  start: uvicorn main:app --host 0.0.0.0 --port 8000
  dev: uvicorn main:app --reload --host 0.0.0.0 --port 8000
  test: pytest tests/ -v
  lint: flake8 . --max-line-length=88
  format: black .

dependencies:
  runtime:
    - fastapi>=0.104.0
    - uvicorn[standard]>=0.24.0
    - python-jose[cryptography]>=3.3.0
    - passlib[bcrypt]>=1.7.4
    - bcrypt>=4.0.1
    - pydantic[email]>=2.5.0
    - PyJWT>=2.8.0

environment:
  - name: JWT_SECRET_KEY
    secret: jwt-secret
  - name: ACCESS_TOKEN_EXPIRE_MINUTES
    value: "30"

ports:
  - port: 8000
    protocol: TCP
    name: http

health_check:
  type: http
  endpoint: /health
  interval: 30
  timeout: 5
  retries: 3

resources:
  memory: 512Mi
  cpu: 500m

metadata:
  tags:
    - authentication
    - jwt
    - fastapi
    - api
  category: security
  license: MIT
''',
                ".env.example": '''# JWT Configuration
JWT_SECRET_KEY=your-super-secret-key-change-this-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Database Configuration (for future use)
DATABASE_URL=postgresql://user:password@localhost/auth_db
''',
                "README.md": '''# JWT Authentication API

A production-ready FastAPI-based authentication service with JWT tokens.

## Features

- ✅ User registration with email validation
- ✅ JWT token-based authentication
- ✅ Password hashing with bcrypt
- ✅ Rate limiting for login attempts
- ✅ Health check endpoint
- ✅ Comprehensive error handling
- ✅ Structured logging
- ✅ Docker support
- ✅ Environment-based configuration

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. Run the application:
   ```bash
   uvicorn main:app --reload
   ```

4. Access the API documentation:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## API Endpoints

- `POST /register` - Register a new user
- `POST /login` - Login and get JWT token  
- `GET /profile` - Get user profile (requires auth)
- `GET /protected` - Protected route example
- `GET /health` - Health check

## Docker Usage

```bash
# Build image
docker build -t jwt-auth-api .

# Run container
docker run -p 8000:8000 -e JWT_SECRET_KEY=your-secret jwt-auth-api
```

## Security Features

- Passwords hashed with bcrypt
- JWT tokens with configurable expiration
- Rate limiting on login attempts
- CORS middleware
- Environment-based secrets
- Non-root user in Docker

## Testing

Run the test suite:
```bash
pytest tests/ -v
```

## Production Deployment

1. Set strong JWT secret key
2. Configure proper CORS origins
3. Use HTTPS in production
4. Set up proper logging
5. Monitor rate limiting
6. Consider using Redis for session storage
'''
            },
            tests={
                "test_main.py": '''"""
Tests for JWT Authentication API
"""
import pytest
from fastapi.testclient import TestClient
from main import app
import json

client = TestClient(app)

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "jwt-auth-api"

def test_user_registration():
    """Test user registration"""
    user_data = {
        "email": "test@example.com",
        "password": "testpassword123"
    }
    response = client.post("/register", json=user_data)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == user_data["email"]
    assert "created_at" in data

def test_duplicate_registration():
    """Test duplicate user registration fails"""
    user_data = {
        "email": "test@example.com", 
        "password": "testpassword123"
    }
    # First registration
    client.post("/register", json=user_data)
    
    # Second registration should fail
    response = client.post("/register", json=user_data)
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]

def test_user_login():
    """Test user login"""
    # Register user first
    user_data = {
        "email": "login@example.com",
        "password": "testpassword123"
    }
    client.post("/register", json=user_data)
    
    # Login
    response = client.post("/login", json=user_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_invalid_login():
    """Test login with invalid credentials"""
    user_data = {
        "email": "nonexistent@example.com",
        "password": "wrongpassword"
    }
    response = client.post("/login", json=user_data)
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]

def test_protected_route():
    """Test protected route with valid token"""
    # Register and login
    user_data = {
        "email": "protected@example.com",
        "password": "testpassword123"
    }
    client.post("/register", json=user_data)
    login_response = client.post("/login", json=user_data)
    token = login_response.json()["access_token"]
    
    # Access protected route
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/protected", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "Hello protected@example.com" in data["message"]

def test_protected_route_no_token():
    """Test protected route without token"""
    response = client.get("/protected")
    assert response.status_code == 403

def test_protected_route_invalid_token():
    """Test protected route with invalid token"""
    headers = {"Authorization": "Bearer invalid_token"}
    response = client.get("/protected", headers=headers)
    assert response.status_code == 401

def test_user_profile():
    """Test user profile endpoint"""
    # Register and login
    user_data = {
        "email": "profile@example.com",
        "password": "testpassword123"
    }
    client.post("/register", json=user_data)
    login_response = client.post("/login", json=user_data)
    token = login_response.json()["access_token"]
    
    # Get profile
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/profile", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == user_data["email"]
    assert "created_at" in data

def test_rate_limiting():
    """Test rate limiting on login attempts"""
    user_data = {
        "email": "ratelimit@example.com",
        "password": "wrongpassword"
    }
    
    # Make multiple failed login attempts
    for _ in range(6):  # Exceed rate limit
        response = client.post("/login", json=user_data)
    
    # Should get rate limited
    assert response.status_code == 429
    assert "Too many login attempts" in response.json()["detail"]
'''
            },
            manifest={
                "language": "python",
                "framework": "fastapi",
                "type": "api",
                "version": "1.0.0"
            },
            documentation="JWT Authentication API with FastAPI - Production ready with Docker support"
        )
    
    def display_capsule_structure(self, capsule: QLCapsule):
        """Display the generated capsule structure"""
        print("📂 Capsule Structure:")
        for file_path in sorted(capsule.source_code.keys()):
            lines = len(capsule.source_code[file_path].split('\n'))
            print(f"   📄 {file_path} ({lines} lines)")
        
        if capsule.tests:
            print("🧪 Test Files:")
            for test_path in sorted(capsule.tests.keys()):
                lines = len(capsule.tests[test_path].split('\n'))
                print(f"   🧪 {test_path} ({lines} lines)")
    
    def display_runtime_results(self, runtime_result):
        """Display runtime validation results"""
        status_emoji = "✅" if runtime_result.success else "❌"
        
        print(f"{status_emoji} Runtime Validation Results:")
        print(f"   Language: {runtime_result.language}")
        print(f"   Overall Success: {runtime_result.success}")
        print(f"   Confidence Score: {runtime_result.confidence_score:.2f}")
        print(f"   Execution Time: {runtime_result.execution_time:.2f}s")
        print(f"   Memory Usage: {runtime_result.memory_usage}MB")
        
        print(f"   📋 Stage Results:")
        print(f"      Install: {'✅' if runtime_result.install_success else '❌'}")
        print(f"      Runtime: {'✅' if runtime_result.runtime_success else '❌'}")
        print(f"      Tests: {'✅' if runtime_result.test_success else '❌'}")
        
        if runtime_result.issues:
            print(f"   ⚠️  Issues ({len(runtime_result.issues)}):")
            for issue in runtime_result.issues[:3]:  # Show top 3
                print(f"      - {issue}")
        
        if runtime_result.recommendations:
            print(f"   💡 Recommendations:")
            for rec in runtime_result.recommendations[:2]:  # Show top 2
                print(f"      - {rec}")
    
    def display_confidence_analysis(self, analysis):
        """Display confidence analysis results"""
        level_emoji = {
            "critical": "🚀",
            "high": "✅", 
            "medium": "⚠️",
            "low": "🔍",
            "very_low": "🚫"
        }
        
        emoji = level_emoji.get(analysis.confidence_level.value, "❓")
        
        print(f"{emoji} Confidence Analysis:")
        print(f"   Overall Score: {analysis.overall_score:.3f}")
        print(f"   Confidence Level: {analysis.confidence_level.value.upper()}")
        print(f"   Success Probability: {analysis.estimated_success_probability:.3f}")
        print(f"   Human Review Required: {analysis.human_review_required}")
        
        print(f"   📊 Dimensional Scores:")
        for dimension, metric in analysis.dimensions.items():
            score_emoji = "✅" if metric.score > 0.8 else "⚠️" if metric.score > 0.5 else "❌"
            print(f"      {score_emoji} {dimension.value}: {metric.score:.3f}")
        
        if analysis.risk_factors:
            print(f"   ⚠️  Top Risk Factors:")
            for risk in analysis.risk_factors[:3]:
                print(f"      - {risk}")
        
        if analysis.success_indicators:
            print(f"   ✅ Success Indicators:")
            for indicator in analysis.success_indicators[:3]:
                print(f"      - {indicator}")
    
    def display_final_assessment(self, capsule, runtime_result, confidence_analysis):
        """Display final deployment assessment"""
        deployment_ready = (
            runtime_result.success and 
            confidence_analysis.overall_score >= 0.7 and
            not confidence_analysis.human_review_required
        )
        
        print(f"🏁 Final Assessment:")
        print(f"   Capsule ID: {capsule.id}")
        print(f"   Deployment Ready: {'✅ YES' if deployment_ready else '❌ NO'}")
        print(f"   Recommendation: {confidence_analysis.deployment_recommendation}")
        
        if deployment_ready:
            print(f"   🎉 CAPSULE APPROVED FOR DEPLOYMENT!")
            print(f"   📦 Ready for production use")
        else:
            print(f"   🔄 Additional work required before deployment")
            
            if runtime_result.issues:
                print(f"   🔧 Blocking Issues:")
                for issue in runtime_result.issues:
                    if any(keyword in issue.lower() for keyword in ['failed', 'error', 'critical']):
                        print(f"      - {issue}")
        
        print(f"   📈 Quality Metrics:")
        print(f"      Runtime Success: {runtime_result.success}")
        print(f"      Confidence Score: {confidence_analysis.overall_score:.3f}")
        print(f"      Success Probability: {confidence_analysis.estimated_success_probability:.3f}")
    
    async def demo_api_integration(self, capsule, runtime_result, confidence_analysis):
        """Demo API integration with validation service"""
        print("🌐 API Integration Demo:")
        
        # Try to connect to validation service
        try:
            response = requests.get("http://localhost:8002/health", timeout=5)
            if response.status_code == 200:
                print("   ✅ Validation service is running")
                await self.test_validation_endpoints(capsule, runtime_result, confidence_analysis)
            else:
                print("   ❌ Validation service not responding properly")
        except requests.exceptions.RequestException:
            print("   ⚠️  Validation service not running (start with: python src/validation/main.py)")
            print("   📝 Would call these endpoints:")
            print("      POST /validate/capsule/runtime")
            print("      POST /validate/capsule/confidence") 
            print("      POST /validate/capsule/complete")
    
    async def test_validation_endpoints(self, capsule, runtime_result, confidence_analysis):
        """Test validation service endpoints"""
        base_url = "http://localhost:8002"
        
        # Test complete validation endpoint
        try:
            payload = {
                "capsule": {
                    "id": capsule.id,
                    "title": capsule.title,
                    "description": capsule.description,
                    "source_code": capsule.source_code,
                    "tests": capsule.tests,
                    "manifest": capsule.manifest,
                    "documentation": capsule.documentation
                }
            }
            
            response = requests.post(
                f"{base_url}/validate/capsule/complete",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                print("   ✅ Complete validation API succeeded")
                result = response.json()
                print(f"      Validation ID: {result.get('validation_id', 'N/A')}")
                print(f"      Deployment Ready: {result.get('assessment', {}).get('deployment_ready', False)}")
            else:
                print(f"   ❌ Complete validation API failed: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ API call failed: {str(e)}")


async def main():
    """Run the complete demo"""
    demo = NLPToCapsuleDemo()
    
    try:
        capsule, runtime_result, confidence_analysis = await demo.run_complete_demo()
        
        print("\n" + "=" * 60)
        print("🎊 DEMO COMPLETE!")
        print(f"   Generated: {len(capsule.source_code)} source files")
        print(f"   Runtime Success: {runtime_result.success}")
        print(f"   Confidence: {confidence_analysis.confidence_level.value}")
        print(f"   Recommendation: {confidence_analysis.deployment_recommendation}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())