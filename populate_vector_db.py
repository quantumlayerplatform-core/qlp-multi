#!/usr/bin/env python3
"""
Script to populate Qdrant Cloud with initial seed data
Run this to fix the empty vector DB issue
"""

import asyncio
import json
import httpx
import os
from datetime import datetime
from typing import List, Dict, Any

# Sample seed data for the vector DB
SEED_REQUESTS = [
    {
        "id": "seed_1",
        "description": "Create a REST API for user management with authentication",
        "tasks": [
            {"id": "api_task_1", "type": "code_generation", "description": "Create FastAPI app structure"},
            {"id": "api_task_2", "type": "code_generation", "description": "Add user authentication endpoints"},
            {"id": "api_task_3", "type": "test_creation", "description": "Create API tests"}
        ],
        "dependencies": {"api_task_2": ["api_task_1"], "api_task_3": ["api_task_1", "api_task_2"]},
        "success_rate": 0.9,
        "patterns": ["api_pattern", "auth_pattern"],
        "metadata": {
            "complexity": "medium",
            "language": "python",
            "framework": "fastapi"
        }
    },
    {
        "id": "seed_2", 
        "description": "Build a React frontend with user dashboard and charts",
        "tasks": [
            {"id": "fe_task_1", "type": "code_generation", "description": "Create React app structure"},
            {"id": "fe_task_2", "type": "code_generation", "description": "Build user dashboard components"},
            {"id": "fe_task_3", "type": "code_generation", "description": "Add chart visualizations"},
            {"id": "fe_task_4", "type": "test_creation", "description": "Create React component tests"}
        ],
        "dependencies": {
            "fe_task_2": ["fe_task_1"], 
            "fe_task_3": ["fe_task_1", "fe_task_2"],
            "fe_task_4": ["fe_task_1", "fe_task_2", "fe_task_3"]
        },
        "success_rate": 0.85,
        "patterns": ["frontend_pattern", "dashboard_pattern"],
        "metadata": {
            "complexity": "medium",
            "language": "typescript", 
            "framework": "react"
        }
    },
    {
        "id": "seed_3",
        "description": "Create a Python script for data processing and analysis",
        "tasks": [
            {"id": "script_task_1", "type": "code_generation", "description": "Create main data processing script"},
            {"id": "script_task_2", "type": "code_generation", "description": "Add data analysis functions"},
            {"id": "script_task_3", "type": "test_creation", "description": "Create unit tests"},
            {"id": "script_task_4", "type": "documentation", "description": "Create usage documentation"}
        ],
        "dependencies": {
            "script_task_2": ["script_task_1"],
            "script_task_3": ["script_task_1", "script_task_2"],
            "script_task_4": ["script_task_1"]
        },
        "success_rate": 0.92,
        "patterns": ["data_processing_pattern", "analysis_pattern"],
        "metadata": {
            "complexity": "simple",
            "language": "python",
            "domain": "data_science"
        }
    },
    {
        "id": "seed_4",
        "description": "Build a microservice for file upload and processing",
        "tasks": [
            {"id": "ms_task_1", "type": "code_generation", "description": "Create microservice structure"},
            {"id": "ms_task_2", "type": "code_generation", "description": "Implement file upload endpoints"},
            {"id": "ms_task_3", "type": "code_generation", "description": "Add file processing logic"},
            {"id": "ms_task_4", "type": "deployment", "description": "Create Docker configuration"},
            {"id": "ms_task_5", "type": "test_creation", "description": "Create integration tests"}
        ],
        "dependencies": {
            "ms_task_2": ["ms_task_1"],
            "ms_task_3": ["ms_task_1", "ms_task_2"], 
            "ms_task_4": ["ms_task_1"],
            "ms_task_5": ["ms_task_1", "ms_task_2", "ms_task_3"]
        },
        "success_rate": 0.88,
        "patterns": ["microservice_pattern", "file_processing_pattern"],
        "metadata": {
            "complexity": "complex",
            "language": "python",
            "deployment": "docker"
        }
    },
    {
        "id": "seed_5",
        "description": "Create a CLI tool for database migration and management",
        "tasks": [
            {"id": "cli_task_1", "type": "code_generation", "description": "Create CLI application structure"},
            {"id": "cli_task_2", "type": "code_generation", "description": "Add database connection logic"},
            {"id": "cli_task_3", "type": "code_generation", "description": "Implement migration commands"},
            {"id": "cli_task_4", "type": "documentation", "description": "Create CLI usage guide"},
            {"id": "cli_task_5", "type": "test_creation", "description": "Create CLI tests"}
        ],
        "dependencies": {
            "cli_task_2": ["cli_task_1"],
            "cli_task_3": ["cli_task_1", "cli_task_2"],
            "cli_task_4": ["cli_task_1", "cli_task_3"],
            "cli_task_5": ["cli_task_1", "cli_task_2", "cli_task_3"]
        },
        "success_rate": 0.87,
        "patterns": ["cli_pattern", "database_pattern"],
        "metadata": {
            "complexity": "medium",
            "language": "python",
            "tool_type": "cli"
        }
    }
]

SEED_PATTERNS = [
    {
        "id": "api_pattern_1",
        "pattern_type": "api_development",
        "code_snippet": "from fastapi import FastAPI, Depends\nfrom pydantic import BaseModel\n\napp = FastAPI()\n\nclass UserCreate(BaseModel):\n    email: str\n    password: str",
        "usage_count": 45,
        "success_rate": 0.91,
        "metadata": {
            "framework": "fastapi",
            "language": "python",
            "pattern": "user_management"
        }
    },
    {
        "id": "react_pattern_1", 
        "pattern_type": "frontend_component",
        "code_snippet": "import React, { useState, useEffect } from 'react';\nimport { Chart } from 'chart.js';\n\nconst Dashboard = () => {\n  const [data, setData] = useState([]);",
        "usage_count": 32,
        "success_rate": 0.88,
        "metadata": {
            "framework": "react",
            "language": "typescript",
            "pattern": "dashboard"
        }
    },
    {
        "id": "data_pattern_1",
        "pattern_type": "data_processing",
        "code_snippet": "import pandas as pd\nimport numpy as np\n\ndef process_data(df):\n    # Clean and transform data\n    df_cleaned = df.dropna()",
        "usage_count": 28,
        "success_rate": 0.93,
        "metadata": {
            "language": "python",
            "domain": "data_science",
            "pattern": "data_cleaning"
        }
    }
]

async def populate_vector_memory(base_url: str, timeout: float = 30.0):
    """
    Populate the vector memory service with seed data
    """
    print(f"🌱 Populating vector memory at {base_url}")
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        
        # 1. Store seed requests
        print(f"📝 Storing {len(SEED_REQUESTS)} seed requests...")
        for request_data in SEED_REQUESTS:
            try:
                response = await client.post(
                    f"{base_url}/store/decomposition",
                    json={
                        "request": {
                            "id": request_data["id"],
                            "description": request_data["description"],
                            "tenant_id": "seed",
                            "user_id": "system"
                        },
                        "tasks": request_data["tasks"],
                        "dependencies": request_data["dependencies"],
                        "metadata": {
                            **request_data["metadata"],
                            "success_rate": request_data["success_rate"],
                            "patterns": request_data["patterns"],
                            "seed_data": True,
                            "created_at": datetime.utcnow().isoformat()
                        }
                    }
                )
                
                if response.status_code == 200:
                    print(f"✅ Stored request: {request_data['id']}")
                else:
                    print(f"❌ Failed to store request {request_data['id']}: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Error storing request {request_data['id']}: {e}")
        
        # 2. Store seed patterns
        print(f"🔧 Storing {len(SEED_PATTERNS)} seed patterns...")
        for pattern_data in SEED_PATTERNS:
            try:
                response = await client.post(
                    f"{base_url}/patterns/code",
                    json={
                        "content": pattern_data["code_snippet"],
                        "metadata": {
                            **pattern_data["metadata"],
                            "pattern_id": pattern_data["id"],
                            "pattern_type": pattern_data["pattern_type"],
                            "usage_count": pattern_data["usage_count"],
                            "success_rate": pattern_data["success_rate"],
                            "seed_data": True,
                            "created_at": datetime.utcnow().isoformat()
                        }
                    }
                )
                
                if response.status_code == 200:
                    print(f"✅ Stored pattern: {pattern_data['id']}")
                else:
                    print(f"❌ Failed to store pattern {pattern_data['id']}: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Error storing pattern {pattern_data['id']}: {e}")
        
        # 3. Verify the data was stored
        print("🔍 Verifying stored data...")
        try:
            # Test search for requests
            search_response = await client.post(
                f"{base_url}/search/requests",
                json={
                    "description": "API",
                    "limit": 3
                }
            )
            
            if search_response.status_code == 200:
                results = search_response.json()
                result_list = results if isinstance(results, list) else results.get("results", [])
                print(f"✅ Search test successful: Found {len(result_list)} results")
            else:
                print(f"❌ Search test failed: {search_response.status_code}")
                
        except Exception as e:
            print(f"❌ Search verification failed: {e}")

async def check_vector_db_status(base_url: str):
    """
    Check the current status of the vector DB
    """
    print(f"🔍 Checking vector DB status at {base_url}")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test basic connectivity
            health_response = await client.get(f"{base_url}/health")
            if health_response.status_code == 200:
                print("✅ Vector memory service is reachable")
            else:
                print(f"⚠️  Vector memory service returned: {health_response.status_code}")
            
            # Test search to see if DB has data
            search_response = await client.post(
                f"{base_url}/search/requests",
                json={"description": "test", "limit": 1}
            )
            
            if search_response.status_code == 200:
                results = search_response.json()
                result_list = results if isinstance(results, list) else results.get("results", [])
                
                if len(result_list) > 0:
                    print(f"✅ Vector DB has data: {len(result_list)} results found")
                    return True
                else:
                    print("📭 Vector DB is empty (no results found)")
                    return False
            else:
                print(f"❌ Vector DB search failed: {search_response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Failed to check vector DB: {e}")
        return False

async def main():
    """
    Main function to populate vector DB with seed data
    """
    # Get vector memory URL from environment or use default
    vector_memory_url = os.getenv("VECTOR_MEMORY_URL", "http://vector-memory:8002")
    
    print(f"🚀 Starting vector DB population")
    print(f"📍 Target URL: {vector_memory_url}")
    
    # Check current status
    has_data = await check_vector_db_status(vector_memory_url)
    
    if has_data:
        print("✅ Vector DB already has data. Skipping population.")
        response = input("Do you want to add more seed data anyway? (y/N): ")
        if response.lower() != 'y':
            print("👍 Exiting without changes")
            return
    
    # Populate with seed data
    await populate_vector_memory(vector_memory_url)
    
    print("🎉 Vector DB population completed!")
    print("\n💡 Next steps:")
    print("1. Restart your qlp-temporal-worker to pick up the new data")
    print("2. Try running a decomposition request")
    print("3. The 'list index out of range' error should be resolved")

if __name__ == "__main__":
    # Run the population script
    asyncio.run(main())
