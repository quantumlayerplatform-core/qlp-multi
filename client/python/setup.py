"""
Setup configuration for QLP Python Client
"""

from setuptools import setup, find_packages
import os

# Read the README file
readme_path = os.path.join(os.path.dirname(__file__), "README.md")
if os.path.exists(readme_path):
    with open(readme_path, "r", encoding="utf-8") as fh:
        long_description = fh.read()
else:
    long_description = "Python client library for Quantum Layer Platform v2 API"

setup(
    name="qlp-client",
    version="2.0.0",
    author="Quantum Layer Platform",
    author_email="support@quantumlayerplatform.com",
    description="Official Python client for Quantum Layer Platform v2 API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/quantumlayer/qlp-python-client",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Code Generators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "httpx>=0.24.0",
        "python-dateutil>=2.8.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.20.0",
            "black>=22.0.0",
            "mypy>=0.990",
            "ruff>=0.0.250",
        ]
    },
    project_urls={
        "Documentation": "https://docs.quantumlayerplatform.com/client/python",
        "API Reference": "https://api.quantumlayerplatform.com/docs",
        "Bug Reports": "https://github.com/quantumlayer/qlp-python-client/issues",
        "Source": "https://github.com/quantumlayer/qlp-python-client",
    },
)