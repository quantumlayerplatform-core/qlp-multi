#!/usr/bin/env python3
"""Check for missing dependencies by attempting imports"""

import importlib
import subprocess

missing_deps = []

deps_to_check = [
    ("sentry_sdk", "sentry-sdk==1.39.1"),
    ("pythonjsonlogger", "python-json-logger==2.0.7"),
    ("psycopg2", "psycopg2-binary==2.9.9"),
    ("otter_ai", "otter-ai==0.1.2"),
    ("jaeger_client", "jaeger-client==4.8.0"),
    ("sklearn", "scikit-learn==1.3.2"),
    ("neo4j", "neo4j==5.14.1"),
    ("pinecone", "pinecone-client==2.2.4"),
    ("chromadb", "chromadb==0.4.18"),
    ("faiss", "faiss-cpu==1.7.4"),
    ("accelerate", "accelerate==0.25.0"),
    ("sentencepiece", "sentencepiece==0.1.99"),
    ("instructor", "instructor==0.3.5"),
    ("guidance", "guidance==0.0.64"),
    ("marvin", "marvin==2.1.4"),
    ("pydantic_ai", "pydantic-ai==0.0.11"),
    ("httpx_ws", "httpx-ws==0.5.2"),
    ("bs4", "beautifulsoup4==4.12.2"),
    ("litellm", "litellm==1.10.0"),
    ("semantic_kernel", "semantic-kernel==0.4.3.dev0"),
    ("autogen", "pyautogen==0.2.2"),
    ("crewai", "crewai==0.1.30")
]

for module_name, package_name in deps_to_check:
    try:
        importlib.import_module(module_name)
        print(f"✓ {module_name} is installed")
    except ImportError:
        print(f"✗ {module_name} is missing - install with: {package_name}")
        missing_deps.append(package_name)

if missing_deps:
    print("\nMissing dependencies found. Add these to requirements.txt:")
    for dep in missing_deps:
        print(f"  {dep}")
else:
    print("\nAll dependencies are installed!")