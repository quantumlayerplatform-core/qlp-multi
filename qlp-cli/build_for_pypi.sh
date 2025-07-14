#!/bin/bash

echo "🚀 Building QuantumLayer CLI for PyPI distribution"
echo "================================================"

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info/

# Ensure we're in the right directory
cd /Users/satish/qlp-projects/qlp-dev/qlp-cli

# Activate virtual environment
source ../.venv/bin/activate

# Create source distribution and wheel
echo -e "\nBuilding distributions..."
python -m pip install --upgrade build twine
python -m build

# Check the distributions
echo -e "\nChecking distributions..."
python -m twine check dist/*

# Show what was built
echo -e "\nBuilt packages:"
ls -la dist/

echo -e "\n✅ Build complete!"
echo -e "\nTo upload to PyPI Test:"
echo "  python -m twine upload --repository testpypi dist/*"
echo -e "\nTo upload to PyPI (production):"
echo "  python -m twine upload dist/*"
echo -e "\nNote: You'll need PyPI credentials configured in ~/.pypirc"