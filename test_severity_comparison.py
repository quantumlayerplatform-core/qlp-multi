#!/usr/bin/env python3
"""Test severity comparison logic"""

from src.moderation.hap_service import Severity

# Test comparison operations
print("Testing Severity comparisons:")
print(f"CLEAN < LOW: {Severity.CLEAN < Severity.LOW}")
print(f"LOW < MEDIUM: {Severity.LOW < Severity.MEDIUM}")
print(f"MEDIUM < HIGH: {Severity.MEDIUM < Severity.HIGH}")
print(f"HIGH < CRITICAL: {Severity.HIGH < Severity.CRITICAL}")
print()
print(f"LOW >= HIGH: {Severity.LOW >= Severity.HIGH}")
print(f"HIGH >= LOW: {Severity.HIGH >= Severity.LOW}")
print()

# Test the specific case from our error
blocking_threshold = Severity.HIGH
test_severity = Severity.LOW

print(f"Test case: severity={test_severity.value}, threshold={blocking_threshold.value}")
print(f"Should block (severity >= threshold)? {test_severity >= blocking_threshold}")
print(f"Expected: False (LOW < HIGH, so it should NOT block)")