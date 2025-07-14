#!/bin/bash

echo "Testing QuantumLayer CLI with simple request..."
echo "=================================="

# Test with a very simple request and short timeout
cd /Users/satish/qlp-projects/qlp-dev/qlp-cli
source ../.venv/bin/activate

echo -e "\n1. Testing simple generation with 5 minute timeout:"
python run_cli.py generate "hello world program" --timeout 5

echo -e "\n2. If the workflow times out, check its status with:"
echo "   qlp status <workflow-id>"
echo ""
echo "3. Or use the debug script:"
echo "   python debug_workflow.py <workflow-id>"