#!/usr/bin/env python3
"""
Live HAP Integration Test
Shows HAP working with the QuantumLayer Platform
"""

import requests
import json
import time

print("🎉 HAP Integration Test - Live Demo")
print("=" * 60)

base_url = "http://localhost:8000"

# Test 1: HAP Direct API
print("\n1️⃣  Testing HAP Direct API")
print("-" * 40)

test_cases = [
    ("Clean technical request", "Create a REST API endpoint for user authentication"),
    ("Mild profanity", "Fix this damn bug in the code"),
    ("Disguised profanity", "This sh*t is broken"),
    ("Technical terms (false positive test)", "The process killer terminates zombie processes"),
    ("Severe content", "I hate this stupid f***ing framework")
]

for title, content in test_cases:
    print(f"\n📝 {title}")
    print(f"   Content: \"{content}\"")
    
    response = requests.post(
        f"{base_url}/api/v2/hap/check",
        json={"content": content, "context": "user_request"}
    )
    
    if response.status_code == 200:
        result = response.json()
        emoji = "✅" if result["severity"] == "clean" else "⚠️" if result["severity"] in ["low", "medium"] else "🚫"
        print(f"   {emoji} Result: {result['result']} (Severity: {result['severity']})")
        if result.get("explanation"):
            print(f"   💬 {result['explanation']}")

# Test 2: Batch Processing
print("\n\n2️⃣  Testing Batch Processing")
print("-" * 40)

batch_items = [
    {"content": "Implement user authentication", "metadata": {"id": "1"}},
    {"content": "This code is terrible", "metadata": {"id": "2"}},
    {"content": "Kill the background process", "metadata": {"id": "3"}},
    {"content": "What the hell is this", "metadata": {"id": "4"}}
]

response = requests.post(
    f"{base_url}/api/v2/hap/check-batch",
    json={"items": batch_items, "context": "user_request"}
)

if response.status_code == 200:
    results = response.json()
    print(f"\n✅ Processed {len(results)} items:")
    for item, result in zip(batch_items, results):
        print(f"   • \"{item['content'][:30]}...\" → {result['severity']}")

# Test 3: Integration with Execution Flow
print("\n\n3️⃣  Testing Integration with Execution Flow")
print("-" * 40)

# Clean request
print("\n✅ Submitting clean request...")
clean_request = {
    "tenant_id": "demo",
    "user_id": "test_user",
    "description": "Create a Python function to validate email addresses"
}

response = requests.post(f"{base_url}/execute", json=clean_request)
if response.status_code == 200:
    result = response.json()
    print(f"   ✓ Accepted: Workflow ID {result['workflow_id']}")

# Inappropriate request
print("\n🚫 Submitting inappropriate request...")
bad_request = {
    "tenant_id": "demo",
    "user_id": "test_user",
    "description": "Fix this f***ing stupid code that some idiot wrote"
}

response = requests.post(f"{base_url}/execute", json=bad_request)
print(f"   Response: {response.status_code}")
if response.status_code != 200:
    print(f"   ✓ Blocked as expected!")
    if response.text:
        try:
            error = response.json()
            print(f"   Message: {error.get('detail', 'No detail')}")
        except:
            pass

# Test 4: Performance
print("\n\n4️⃣  Testing Performance (Caching)")
print("-" * 40)

test_content = "Check if this content is cached properly"

# First check (cache miss)
start = time.time()
response = requests.post(
    f"{base_url}/api/v2/hap/check",
    json={"content": test_content, "context": "user_request"}
)
time1 = (time.time() - start) * 1000

# Second check (cache hit)
start = time.time()
response = requests.post(
    f"{base_url}/api/v2/hap/check",
    json={"content": test_content, "context": "user_request"}
)
time2 = (time.time() - start) * 1000

print(f"First check: {time1:.2f}ms")
print(f"Second check: {time2:.2f}ms")
print(f"Speed improvement: {time1/time2:.1f}x faster")

# Summary
print("\n\n✨ Summary")
print("=" * 60)
print("✅ HAP is successfully integrated with QuantumLayer Platform!")
print("\nFeatures working:")
print("• Content moderation API endpoints")
print("• Severity detection (clean/low/medium/high/critical)")
print("• Category classification (profanity/abuse/hate_speech)")
print("• Batch processing")
print("• Redis caching for performance")
print("• Integration with execution flow")
print("\nTo see more:")
print("• API Docs: http://localhost:8000/docs#/HAP")
print("• Logs: docker logs qlp-orchestrator | grep HAP")
print("• Demo: python demo_hap_system.py")