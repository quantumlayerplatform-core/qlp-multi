#!/bin/bash
# Extract and examine the capsule content

echo "=== Extracting capsule content ==="
mkdir -p /tmp/capsule_check
cd /tmp/capsule_check
unzip -q /Users/satish/qlp-projects/quantumlayer-platform/qlp-multi/circle_area_capsule.zip

echo -e "\n=== README.md content ==="
if [ -f README.md ]; then
    head -20 README.md
else
    echo "No README.md found"
fi

echo -e "\n=== Source code sample (circle_area_basic.py) ==="
if [ -f circle_area_basic.py ]; then
    cat circle_area_basic.py
else
    echo "No circle_area_basic.py found"
fi

echo -e "\n=== Test file sample ==="
if [ -f test_circle_area_basic.py ]; then
    head -15 test_circle_area_basic.py
else
    echo "No test file found"
fi

echo -e "\n=== File structure ==="
find . -type f -name "*.py" -o -name "*.md" -o -name "*.json" | sort

# Cleanup
cd /
rm -rf /tmp/capsule_check
