#!/bin/bash
# Development installation script for QuantumLayer CLI

echo "🚀 Installing QuantumLayer CLI for development..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install in editable mode
echo "Installing CLI in editable mode..."
pip install -e .

# Test installation
echo -e "\n🧪 Testing installation..."
qlp --version

echo -e "\n✅ Installation complete!"
echo "You can now use 'qlp' command"
echo ""
echo "Quick start:"
echo "  qlp generate 'REST API for task management'"
echo "  qlp interactive"
echo "  qlp --help"