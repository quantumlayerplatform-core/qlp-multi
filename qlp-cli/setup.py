"""
QuantumLayer CLI - Build entire systems with one command
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="quantumlayer",
    version="0.1.0",
    author="QuantumLayer",
    author_email="team@quantumlayer.ai",
    description="Build complete software systems from natural language",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/quantumlayer/qlp-cli",
    project_urls={
        "Bug Tracker": "https://github.com/quantumlayer/qlp-cli/issues",
        "Documentation": "https://docs.quantumlayer.ai",
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Code Generators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "click>=8.1.0",
        "rich>=13.0.0",
        "httpx>=0.24.0",
        "python-dotenv>=1.0.0",
        "websockets>=11.0",
        "pydantic>=2.0.0",
        "Pillow>=9.0.0",
    ],
    entry_points={
        "console_scripts": [
            "qlp=qlp_cli.main:cli",
            "quantumlayer=qlp_cli.main:cli",
        ],
    },
    include_package_data=True,
    package_data={
        "qlp_cli": ["templates/*.json"],
    },
)